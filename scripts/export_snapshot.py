"""Export the real stored results into frontend/public/snapshot/ for the frontend SNAPSHOT mode.

Nothing is synthesised: every file is a verbatim copy of a stored result or the JSON the live API returns
for it (the API is called in-process through a TestClient, so the shapes are identical to LIVE mode).

Layout (URL shapes the frontend requests, see frontend/src/api/client.ts):
    snapshot/manifest.json            {exported_utc, files[], sources[]}
    snapshot/flowsheet.json           GET /api/flowsheet
    snapshot/cases.json               [{case_id, source, file}]  (index of cases/)
    snapshot/cases/<id>.json          GET /api/cases/<id>  (SimulationResult)
    snapshot/data/<category>.json     GET /api/data/<category>            (listing)
    snapshot/data/<category>/<name>.json   GET /api/data/<category>/<name>   (sensitivity, validation, optimisation, analysis)
    snapshot/sensitivity/<name>.csv   verbatim CSV copies;  sensitivity_index.json = list of names
    snapshot/api/<name>.json (validation, references, traceability, figures, reports, screenshots, catalysts, economics defaults,\n                                environment factors, optimisation results, scenario comparison), aspen-screenshots/*, dashboard-screenshots/*\n    snapshot/scenarios_definitions.json, validation_matrix.json, references.json (when present), figures/*.png
    snapshot/research/{index,validation_summary,evidence_matrix,aspen_evidence}.json, research/<area>/<file>.json (GET /api/research/...),
    aspen-evidence/*.png (captures listed in the manifest), research-figures/*.png (only figures linked from the evidence matrix)
    snapshot/research/*  (index, <area>/<file>.json, validation_summary, evidence_matrix, aspen_evidence), aspen-evidence/*.png, research-figures/*.png
    (research items come from GET /api/research/...; research-figures holds only figures linked from the evidence matrix)
    snapshot/research/<area>/<file>.json for the Phase 2 files in PHASE2_FILES (same shapes as the API), research/data/<name>.json,
    research/validation/by_kind.json (counts by evidence kind), research/phase2_index.json, research-figures/*.png (all research figures)
    snapshot/simulator/{model,aspen_anchors,parity_report}.json   verbatim copies of results/research/simulator/ (browser simulator)

Run:  python scripts/export_snapshot.py
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax import paths  # noqa: E402

OUT = ROOT / "frontend" / "public" / "snapshot"

# Phase 2 result files mirrored for the static site in the same shapes as GET /api/research/<area>/<file>
# (CSV -> {name, area, file, columns, rows, count, source_note}; JSON verbatim, or a subset of named top-level keys
# with `served_keys`). area -> {file -> None (whole file) or tuple of top-level keys}. Missing files are skipped and listed.
# The live API whitelist (backend/amcrax/api/routers/research.py ALLOWED) does not hold these yet: in LIVE mode they 404.
PHASE2_FILES: dict[str, dict[str, tuple[str, ...] | None]] = {
    "reference_scenario": {"baseline.json": None, "capex_audit.json": None, "supersession.json": None},
    "carbon_pricing": {"site_summary.json": None, "feed_dominance.json": None, "thresholds.json": None,
                       "carbon_intensity.json": None, "scenarios.json": None, "row_evidence.json": None, "price_sweep.csv": None},
    "catalyst_economics": {"catalyst_prices_sgd.json": None,
                           "catalyst_economics.json": ("provenance", "basis", "findings", "resolution", "row_evidence", "unmodelled_catalysts"),
                           "catalyst_cost_table.csv": None, "catalyst_breakeven.csv": None, "catalyst_crossover.csv": None},
    "heat_exchanger": {"heat_exchanger_study.json": ("provenance", "U_cases", "fx_SGD_per_USD", "fx_date", "baseline",
                                                     "reference_capex_comparison", "row_evidence"),
                       "fehe_duty_diagnosis.json": None},
    "uq": {"gsa_cost_decomposition.json": None, "row_evidence.json": None},
    "enduse": {"turbine_threshold.json": ("provenance", "what_each_pathway_assumes", "statement_of_result", "sourced_values",
                                          "forty_percent_figure", "row_evidence", "notes"),
               "turbine_threshold.csv": None, "sensitivity_turbine_efficiency.csv": None, "sensitivity_nh3_price.csv": None,
               "sensitivity_capital.csv": None, "nox_n2o_blends.json": None},
    "kinetics": {"validity_classification.json": None},
    "purification": {"phase2_comparison.json": None, "phase2_comparison.csv": None, "phase2_psa_recovery_sensitivity.csv": None},
}
# Literature data files the pages cite (research/data/*.json), served as /snapshot/research/data/<name>.json
PHASE2_DATA_FILES = ("carbon_policy_sg.json", "catalyst_prices.json", "enduse_cost_literature.json", "membrane_trl.json",
                     "methodology_transfer.json", "purification_literature.json", "turbine_efficiency_literature.json")
EVIDENCE_KINDS = ("numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation")


def _slim_sobol(body: dict) -> dict:
    """gsa_sobol.json without the convergence arrays (450 kB): per case the distributions and, per output, the moments, indices and groups."""
    out = {k: body[k] for k in ("provenance", "evidence_kind", "analysis_kind", "label", "method", "notes", "groups", "inputs",
                                "capex_lognormal_ranking_change", "tornado_swing_grey_HIon") if k in body}
    cases = {}
    for cid, c in (body.get("cases") or {}).items():
        if not isinstance(c, dict):
            continue
        outs = {o: {k: v for k, v in (ov or {}).items() if k in ("V", "mean", "sd", "p5", "p95", "indices", "groups")}
                for o, ov in (c.get("outputs") or {}).items()}
        cases[cid] = {k: c[k] for k in ("distributions", "N", "seed", "d", "n_evaluations", "lcoh_mean_mc_comparable") if k in c}
        cases[cid]["outputs"] = outs
    out["cases"] = cases
    out["served_keys"] = list(out.keys())
    out["source_note"] = "results/research/uq/gsa_sobol.json; convergence arrays omitted, every other value as stored"
    return out


def validation_by_kind(vdir: Path, rel) -> dict:
    """Counts of results/research/validation/<area>.json items by evidence_kind and status. Items without an evidence_kind are
    counted under 'not_labelled' (never assigned a kind here). Failures are listed with their stored cause or note; when the
    item has neither, the documented cause that summary.json carries for the same area and id is used. The method is kept
    in its own field and is never shown as a cause."""
    kinds: dict[str, dict] = {}
    areas: dict[str, dict] = {}
    summary_causes: dict[tuple[str, str], str] = {}
    sp = vdir / "summary.json"
    if sp.is_file():
        s_areas = json.loads(sp.read_text(encoding="utf-8-sig")).get("areas", {})
        for area, block in (s_areas.items() if isinstance(s_areas, dict) else []):
            for f in (block.get("failures") or []) if isinstance(block, dict) else []:
                if isinstance(f, dict) and isinstance(f.get("id"), str) and isinstance(f.get("cause"), str):
                    summary_causes[(area, f["id"])] = f["cause"]
    # a cause that is only a key of the core matrix's failure_root_causes (results/validation/validation_matrix.json) is
    # printed with that entry's stored description
    core_causes: dict[str, str] = {}
    cp = vdir.parents[1] / "validation" / "validation_matrix.json"
    if cp.is_file():
        for c in json.loads(cp.read_text(encoding="utf-8-sig")).get("summary", {}).get("failure_root_causes", []) or []:
            if isinstance(c, dict) and isinstance(c.get("cause"), str) and isinstance(c.get("description"), str):
                core_causes[c["cause"]] = c["description"]

    def cause_text(c):
        return f"{c} (core validation matrix): {core_causes[c]}" if isinstance(c, str) and c in core_causes else c
    for p in sorted(vdir.glob("*.json")) if vdir.is_dir() else []:
        if p.name == "summary.json":
            continue
        body = json.loads(p.read_text(encoding="utf-8-sig"))
        items = body.get("items", []) if isinstance(body, dict) else body
        items = [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []
        a = areas.setdefault(p.stem, {"file": rel(p), "n_items": 0, "by_kind": {}})
        for it in items:
            k = it.get("evidence_kind") or "not_labelled"
            st = str(it.get("status") or "informational")
            e = kinds.setdefault(k, {"total": 0, "by_status": {}, "failures": []})
            e["total"] += 1
            e["by_status"][st] = e["by_status"].get(st, 0) + 1
            a["n_items"] += 1
            a["by_kind"][k] = a["by_kind"].get(k, 0) + 1
            if st == "fail":
                e["failures"].append({"area": p.stem, "id": it.get("id"), "description": it.get("description"),
                                      "observed": it.get("observed"), "expected": it.get("expected"), "tolerance": it.get("tolerance"),
                                      "unit": it.get("unit"), "method": it.get("method"),
                                      "cause": cause_text(it.get("cause") or it.get("note") or summary_causes.get((p.stem, str(it.get("id")))))})
    for k in EVIDENCE_KINDS:
        kinds.setdefault(k, {"total": 0, "by_status": {}, "failures": []})
    return {"source": "results/research/validation/*.json (summary.json excluded), counted by evidence_kind and status",
            "evidence_kinds": list(EVIDENCE_KINDS), "kinds": kinds, "areas": areas,
            "statement": "AmCraX has no independent experimental validation. Pass counts are numerical verification, Python against "
                         "Aspen comparison or comparison with published literature, never experimental validation."}


def export_phase2(files, skipped, write, copy, rel) -> None:
    """Mirror the Phase 2 result files, research data, validation counts by evidence kind and the research figures."""
    from amcrax.api.errors import jsonable
    from amcrax.api.routers import research as rs

    rdir = ROOT / "results" / "research"
    mirrored: dict[str, list[str]] = {}
    for area, fl in PHASE2_FILES.items():
        for fname, keys in fl.items():
            p = rdir / area / fname
            if not p.is_file():
                skipped.append(f"results/research/{area}/{fname} missing")
                continue
            if p.suffix == ".csv":
                cols, rows = rs._read_csv(p)
                body = {"name": p.stem, "area": area, "file": p.name, "columns": cols, "rows": rows, "count": len(rows),
                        "source_note": f"{rel(p)}; values as stored, no post-processing"}
            else:
                body = json.loads(p.read_text(encoding="utf-8-sig"))
                if keys is not None and isinstance(body, dict):
                    body = {k: body[k] for k in keys if k in body}
                    body["served_keys"] = list(body.keys())
                    body["source_note"] = f"{rel(p)}; subset of top-level keys, values as stored"
            write(f"research/{area}/{fname}.json", jsonable(body), rel(p), "phase 2 mirror (same shape as GET /api/research/<area>/<file>)")
            mirrored.setdefault(area, []).append(fname)
    sob = rdir / "uq" / "gsa_sobol.json"
    if sob.is_file():
        write("research/uq/gsa_sobol.json.json", jsonable(_slim_sobol(json.loads(sob.read_text(encoding="utf-8-sig")))), rel(sob),
              "phase 2 mirror (convergence arrays omitted)")
        mirrored.setdefault("uq", []).append("gsa_sobol.json")
    else:
        skipped.append("results/research/uq/gsa_sobol.json missing")
    for name in PHASE2_DATA_FILES:
        p = ROOT / "research" / "data" / name
        if p.is_file():
            write(f"research/data/{name}.json", jsonable(json.loads(p.read_text(encoding="utf-8-sig"))), rel(p), "verbatim JSON (research data)")
            mirrored.setdefault("data", []).append(name)
        else:
            skipped.append(f"research/data/{name} missing")
    write("research/validation/by_kind.json", jsonable(validation_by_kind(rdir / "validation", rel)), "results/research/validation/*.json",
          "counted by evidence_kind")
    figs = rdir.parent / "figures" / "research"
    copied = []
    for p in sorted(figs.glob("*.png")) if figs.is_dir() else []:
        dst = OUT / "research-figures" / p.name
        if not dst.exists():
            copy(p, f"research-figures/{p.name}")
        copied.append(p.name)
    write("research/phase2_index.json", {"areas": mirrored, "figures": copied,
                                         "evidence_matrix_methodology_version": _matrix_version(rdir / "evidence_matrix.json")},
          "index of the phase 2 mirror", "index")


def _matrix_version(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig")).get("methodology_version")
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    from fastapi.testclient import TestClient

    from amcrax.api.main import app

    client = TestClient(app)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    files: list[dict] = []

    def rel(p: Path) -> str:
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            return str(p)

    def write(relpath: str, obj, source: str, how: str) -> None:
        dst = OUT / relpath
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(obj, indent=1, allow_nan=False), encoding="utf-8")
        files.append({"path": relpath, "source": source, "bytes": dst.stat().st_size, "how": how})

    def copy(src: Path, relpath: str) -> None:
        dst = OUT / relpath
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        files.append({"path": relpath, "source": rel(src), "bytes": dst.stat().st_size, "how": "verbatim copy"})

    def api(url: str):
        r = client.get(url)
        if r.status_code != 200:
            raise RuntimeError(f"{url} -> HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    # flowsheet
    if (paths.CONFIG_DIR / "flowsheet.json").exists():
        write("flowsheet.json", api("/api/flowsheet"), "config/flowsheet.json", "GET /api/flowsheet")

    # cases (only files that validate as SimulationResult)
    index = []
    for c in api("/api/cases")["cases"]:
        cid = c["case_id"]
        write(f"cases/{cid}.json", api(f"/api/cases/{cid}"), f"results/simulations/{c['file']}", "GET /api/cases/<id>")
        index.append({"case_id": cid, "source": c["source"], "file": f"cases/{cid}.json"})
    write("cases.json", index, "index of cases/", "index")

    skipped_dups: list[str] = []
    # generic data categories (same JSON as GET /api/data/...)
    for cat, d in (("sensitivity", paths.RESULTS_SENSITIVITY), ("validation", paths.RESULTS_VALIDATION),
                   ("optimisation", paths.RESULTS_OPTIMISATION), ("analysis", paths.RESULTS_SIMULATIONS)):
        listing = api(f"/api/data/{cat}")
        write(f"data/{cat}.json", listing, rel(d) + "/", f"GET /api/data/{cat}")
        stems_json = {i["name"] for i in listing["items"] if i["kind"] == "json"}
        for it in listing["items"]:
            if it["kind"] == "csv" and it["name"] in stems_json:
                # the snapshot mirror is keyed by stem (extension stripped); JSON wins, same rule as the live API
                skipped_dups.append(f"data/{cat}/{it['file']} (same stem as the .json; use the live API for the CSV)")
                continue
            write(f"data/{cat}/{it['name']}.json", api(f"/api/data/{cat}/{it['file']}"), f"{rel(d)}/{it['file']}",
                  f"GET /api/data/{cat}/<name>")
            if cat == "sensitivity":
                copy(d / it["file"], f"sensitivity/{it['file']}")
    write("sensitivity_index.json", [i["name"] for i in api("/api/data/sensitivity")["items"]], "index", "index")

    # config / reference files
    write("scenarios_definitions.json", api("/api/scenarios/definitions"), "config/scenarios.json", "GET /api/scenarios/definitions")
    for src, dst in ((paths.RESULTS_VALIDATION / "validation_matrix.json", "validation_matrix.json"),
                     (paths.RESEARCH_DIR / "references.json", "references.json")):
        if src.exists():
            copy(src, dst)
    for p in sorted(paths.RESULTS_FIGURES.glob("*.png")) if paths.RESULTS_FIGURES.exists() else []:
        copy(p, f"figures/{p.name}")

    # other endpoints (JSON identical to the live API); optional ones are skipped when not generated yet
    skipped: list[str] = []
    for url, dst in (("/api/validation", "api/validation.json"), ("/api/validation/summary", "api/validation_summary.json"),
                     ("/api/references", "api/references.json"), ("/api/traceability", "api/traceability.json"),
                     ("/api/figures", "api/figures.json"), ("/api/reports", "api/reports.json"),
                     ("/api/screenshots", "api/screenshots.json"), ("/api/kinetics/catalysts", "api/kinetics_catalysts.json"),
                     ("/api/economics/defaults", "api/economics_defaults.json"), ("/api/environment/factors", "api/environment_factors.json"),
                     ("/api/optimisation/results", "api/optimisation_results.json"),
                     ("/api/scenarios/comparison", "api/scenarios_comparison.json")):
        r = client.get(url)
        if r.status_code == 200:
            write(dst, r.json(), url.replace("/api/", "api: "), f"GET {url}")
        else:
            skipped.append(f"{url} -> HTTP {r.status_code}")
    # only the dashboard captures are mirrored (docs/screenshots also holds public-site captures)
    for d, name, pattern in ((paths.ASPEN_SCREENSHOTS, "aspen-screenshots", "*.png"),
                             (paths.DOCS_DIR / "screenshots", "dashboard-screenshots", "dashboard_*.png")):
        for p in sorted(d.glob(pattern)) if d.exists() else []:
            copy(p, f"{name}/{p.name}")
    if (paths.ASPEN_SCREENSHOTS / "manifest.json").exists():
        copy(paths.ASPEN_SCREENSHOTS / "manifest.json", "aspen-screenshots/manifest.json")

    # research expansion (hypotheses H1-H4): only the whitelisted files the Hypotheses pages use, as the live API returns them
    from amcrax.api.routers import research as rs

    idx = api("/api/research/index")
    write("research/index.json", idx, "results/research/ (whitelist)", "GET /api/research/index")
    for area, items in idx["areas"].items():
        for it in items:
            write(f"research/{area}/{it['file']}.json", api(f"/api/research/{area}/{it['file']}"),
                  f"results/research/{area}/{it['file']}", "GET /api/research/<area>/<file>")
    write("research/validation_summary.json", api("/api/research/validation-summary"), "results/research/validation/*.json",
          "GET /api/research/validation-summary")
    em = client.get("/api/research/evidence-matrix")
    if em.status_code == 200:
        write("research/evidence_matrix.json", em.json(), "results/research/evidence_matrix.json", "GET /api/research/evidence-matrix")
        # figures linked from the matrix rows (only those a page shows)
        figs = {f for h in em.json().get("hypotheses", []) for r in h.get("rows", []) for f in (r.get("links", {}) or {}).get("figures", [])}
        for f in sorted(figs):
            src = ROOT / f
            if src.is_file() and src.suffix.lower() == ".png" and rs.RESEARCH_FIGURES in src.parents:
                copy(src, f"research-figures/{src.name}")
    else:
        skipped.append(f"/api/research/evidence-matrix -> HTTP {em.status_code}")
    ae = client.get("/api/research/aspen-evidence")
    if ae.status_code == 200:
        write("research/aspen_evidence.json", ae.json(), "docs/images/aspen_evidence/manifest.json", "GET /api/research/aspen-evidence")
        for c in ae.json()["captures"]:
            copy(rs.ASPEN_EVIDENCE_DIR / Path(c["file"]).name, f"aspen-evidence/{Path(c['file']).name}")
    else:
        skipped.append(f"/api/research/aspen-evidence -> HTTP {ae.status_code}")

    export_phase2(files, skipped, write, copy, rel)

    # browser-side simulator data (Phase 2 S1): verbatim copies of results/research/simulator/*.json
    # (generated by scripts/research/export_simulator_data.py; the app fetches snapshot/simulator/<name>)
    sim_dir = ROOT / "results" / "research" / "simulator"
    for name in ("model.json", "aspen_anchors.json", "parity_report.json"):
        if (sim_dir / name).exists():
            copy(sim_dir / name, f"simulator/{name}")
        else:
            skipped.append(f"results/research/simulator/{name} missing (run scripts/research/export_simulator_data.py)")

    sources = sorted({"/".join(f["source"].split("/")[:2]) for f in files if "/" in f["source"]})
    manifest = {"exported_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": files,
                "sources": sources, "skipped_endpoints": skipped, "not_mirrored_same_stem_csv": skipped_dups,"case_sources": sorted({c["source"] for c in index}),
                "note": "Real stored results only; no demonstration data."}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"snapshot written to {OUT}: {len(files)} files, {len(index)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

