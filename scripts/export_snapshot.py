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
    snapshot/research/<area>/<file>.json for the Phase 2 files (research.py PHASE2_FILES, in the live whitelist, so written by the
    GET /api/research/... loop like every other research file), research/data/<name>.json (area "data"),
    research/validation/by_kind.json (GET /api/research/validation/by_kind), research/phase2_index.json, research-figures/*.png
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

def export_phase2(files, skipped, write, copy, rel, api) -> None:
    """Phase 2 part of the mirror. The Phase 2 result files and the research data files are in the live whitelist
    (backend/amcrax/api/routers/research.py PHASE2_FILES, PHASE2_DATA_FILES, merged into ALLOWED), so main() has already
    written them through GET /api/research/<area>/<file>; here missing ones are listed, the counts by evidence kind are
    written from GET /api/research/validation/by_kind, and the research figures are copied."""
    from amcrax.api.routers import research as rs

    rdir = ROOT / "results" / "research"
    mirrored: dict[str, list[str]] = {}
    for area, fl in rs.PHASE2_FILES.items():
        for fname in fl:
            if (rdir / area / fname).is_file():
                mirrored.setdefault(area, []).append(fname)
            else:
                skipped.append(f"results/research/{area}/{fname} missing")
    for name in rs.PHASE2_DATA_FILES:
        if (rs.DATA_DIR / name).is_file():
            mirrored.setdefault("data", []).append(name)
        else:
            skipped.append(f"research/data/{name} missing")
    write("research/validation/by_kind.json", api("/api/research/validation/by_kind"), "results/research/validation/*.json",
          "GET /api/research/validation/by_kind (counted by evidence_kind)")
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
    ad = client.get("/api/research/addendum")
    if ad.status_code == 200:
        write("research/addendum.json", ad.json(), "results/research/addendum_2026-11-24.json", "GET /api/research/addendum")
    else:
        skipped.append(f"/api/research/addendum -> HTTP {ad.status_code}")

    export_phase2(files, skipped, write, copy, rel, api)

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

