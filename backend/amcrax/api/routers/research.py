"""Read-only endpoints over the stored research-expansion results (hypotheses H1-H4).

GET /api/research/index                 whitelist of served files per area (name, kind, bytes, modified)
GET /api/research/evidence-matrix       results/research/evidence_matrix.json (404 until the file exists)
GET /api/research/validation-summary    pass / fail / informational counts per area, failures named (from results/research/validation/*.json)
GET /api/research/aspen-evidence        docs/images/aspen_evidence/manifest.json (captures whose PNG exists)
GET /api/research/addendum              results/research/addendum_2026-11-24.json (record of the addendum of 24 November 2026)
GET /api/research/validation/by_kind    counts of the research validation items by evidence kind and status, failures with causes
GET /api/research/{area}/{name}         one whitelisted file: CSV -> {name, area, columns, rows, count, source_note}; JSON as stored
                                        (a few large JSON files are served as a subset of named top-level keys, stated in `served_keys`;
                                        the Phase 2 files of PHASE2_FILES and the research data files, area "data", are included)

Only the files in ``ALLOWED`` can be read; names are matched against that list, never joined into a path from the request,
so path traversal is not possible. Nothing here runs a model or Aspen Plus.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from amcrax import paths

from ..errors import ApiError, jsonable

router = APIRouter(prefix="/api/research")

RESEARCH_DIR = paths.RESULTS_DIR / "research"
EVIDENCE_MATRIX = RESEARCH_DIR / "evidence_matrix.json"
ADDENDUM = RESEARCH_DIR / "addendum_2026-11-24.json"
ASPEN_EVIDENCE_DIR = paths.DOCS_DIR / "images" / "aspen_evidence"
RESEARCH_FIGURES = paths.RESULTS_FIGURES / "research"

# area -> {file name -> None (whole file) or tuple of top-level keys to serve (large JSON files)}
ALLOWED: dict[str, dict[str, tuple[str, ...] | None]] = {
    "kinetics": {
        "study_conversion_vs_T.csv": None,
        "study_conversion_vs_P.csv": None,
        "study_mass_for_fraction_of_equilibrium.csv": None,
        "assumptions.json": None,
    },
    "aspen_kinetic": {
        "catalyst_mass_targets.csv": None,
        "aspen_vs_python.csv": None,
        "aspen_kinetic_plotdata.csv": None,
    },
    "catalyst_comparison": {
        "catalyst_heat_duty_plotdata.csv": None,
        "catalyst_cost_breakdown_plotdata.csv": None,
        "catalyst_breakeven_price.csv": None,
        "catalyst_design_curves.csv": None,
        "catalyst_sensitivity_ranking.csv": None,
        "catalyst_ranking_robustness.json": ("provenance", "cases"),
        "catalyst_comparison.json": ("provenance", "basis", "findings"),
        "catalyst_cho_comparison.json": ("provenance", "boundary_differences", "summary"),
        "assumptions.json": None,
    },
    "singapore": {
        "scenario_results.json": None,
        "tornado.json": None,
        "breakeven_ammonia_price.json": None,
        "monte_carlo.json": None,
        "benchmarks.json": None,
        "cost_vs_capacity.csv": None,
        "heatmap_nh3_price_x_capacity.csv": None,
        "heatmap_nh3_price_x_carbon_tax_nh3_heat.csv": None,
        "heatmap_nh3_price_x_carbon_tax_gas_heat_hypothetical.csv": None,
        "assumptions.json": None,
    },
    "purification": {
        "purification_configurations.csv": None,
        "recovery_vs_cost.csv": None,
        "psa_recovery_vs_purity.csv": None,
        "singapore_price_scenario.csv": None,
        "membrane_required_selectivity.csv": None,
        "purification_study.json": ("provenance", "iso_14687", "summary", "not_modelled", "delivery_pressures_bar"),
        "assumptions.json": None,
    },
    "enduse": {
        "pathway_table_power.csv": None,
        "pathway_table_hydrogen.csv": None,
        "claim_check_direct_vs_cracking.csv": None,
        "price_sweep.csv": None,
        "enduse_results.json": ("provenance", "halim_claim_check", "hydrogen_summary", "limitations", "nox_note"),
        "assumptions.json": None,
    },
    "lca": {
        "lca_routes.csv": None,
        "lca_distance.csv": None,
        "lca_results.json": ("provenance", "method", "system_boundary", "alternatives", "limitations"),
        "assumptions.json": None,
    },
}

# Phase 2 result files (the same files and key subsets that scripts/export_snapshot.py mirrors for the static site), merged
# into ALLOWED so that LIVE mode serves the same pages. area -> {file -> None (whole file) or tuple of top-level keys}.
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
    # gsa_sobol.json is served without its convergence arrays (450 kB), see _slim_sobol
    "uq": {"gsa_cost_decomposition.json": None, "row_evidence.json": None, "gsa_sobol.json": None},
    "enduse": {"turbine_threshold.json": ("provenance", "what_each_pathway_assumes", "statement_of_result", "sourced_values",
                                          "cracker_heat_fuel_efficiency_sensitivity", "forty_percent_figure", "row_evidence",
                                          "notes"),
               "turbine_threshold.csv": None, "sensitivity_turbine_efficiency.csv": None, "sensitivity_nh3_price.csv": None,
               "sensitivity_capital.csv": None, "nox_n2o_blends.json": None},
    "kinetics": {"validity_classification.json": None},
    "purification": {"phase2_comparison.json": None, "phase2_comparison.csv": None, "phase2_psa_recovery_sensitivity.csv": None},
}
# Literature data files the pages cite: research/data/<name> (not under results/), served as area "data" (verbatim JSON)
DATA_DIR = paths.RESEARCH_DIR / "data"
PHASE2_DATA_FILES = ("carbon_policy_sg.json", "catalyst_prices.json", "enduse_cost_literature.json", "membrane_trl.json",
                     "methodology_transfer.json", "purification_literature.json", "turbine_efficiency_literature.json")
for _area, _files in PHASE2_FILES.items():
    ALLOWED.setdefault(_area, {}).update(_files)
ALLOWED["data"] = {n: None for n in PHASE2_DATA_FILES}
# areas whose files do not live under results/research/<area>/
AREA_DIRS: dict[str, Path] = {"data": DATA_DIR}
EVIDENCE_KINDS = ("numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation")


def _area_dir(area: str) -> Path:
    return AREA_DIRS.get(area, RESEARCH_DIR / area)


def _slim_sobol(body: dict) -> dict:
    """gsa_sobol.json without the convergence arrays: per case the distributions and, per output, the moments, indices and groups."""
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


def _num(x):
    if x is None or x == "":
        return None
    try:
        f = float(x)
    except ValueError:
        return x
    return f if f == f and abs(f) != float("inf") else None


def _read_csv(p: Path) -> tuple[list[str], list[dict]]:
    with p.open(newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        rows = [{k: _num(v) for k, v in r.items()} for r in rd]
        return list(rd.fieldnames or []), rows


def _rel(p: Path) -> str:
    try:
        return p.relative_to(paths.ROOT).as_posix()
    except ValueError:
        return p.name


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:  # noqa: BLE001
        raise ApiError(500, "data_unreadable", f"{p.name} is not valid JSON: {str(e)[:200]}") from e


def _resolve(area: str, name: str) -> tuple[Path, tuple[str, ...] | None]:
    files = ALLOWED.get(area)
    if files is None:
        raise ApiError(404, "research_not_found", f"Unknown research area '{area}'", {"areas": sorted(ALLOWED)})
    if name in files:
        fname = name
    else:  # bare stem: JSON preferred over CSV
        same = sorted((f for f in files if Path(f).stem == name), key=lambda f: (not f.endswith(".json"), f))
        if not same:
            raise ApiError(404, "research_not_found", f"No research file '{name}' in area '{area}'", {"area": area})
        fname = same[0]
    p = _area_dir(area) / fname
    if not p.is_file():
        raise ApiError(404, "research_not_found", f"{area}/{fname} has not been generated yet", {"area": area, "file": fname})
    return p, files[fname]


def serve_file(area: str, name: str) -> dict:
    p, keys = _resolve(area, name)
    if p.suffix == ".csv":
        cols, rows = _read_csv(p)
        return {"name": p.stem, "area": area, "file": p.name, "columns": cols, "rows": rows, "count": len(rows),
                "source_note": f"{_rel(p)}; values as stored, no post-processing"}
    body = _load_json(p)
    if area == "uq" and p.name == "gsa_sobol.json" and isinstance(body, dict):
        return jsonable(_slim_sobol(body))
    if keys is not None and isinstance(body, dict):
        sub = {k: body[k] for k in keys if k in body}
        if area == "purification" and p.name == "purification_study.json":
            # id -> label of the purification configurations (the full file is 370 kB, so only the labels are served from "cases")
            cases = body.get("cases") or {}
            first = next(iter(cases.values()), {}) if isinstance(cases, dict) else {}
            sub["config_labels"] = {c["id"]: c.get("label", c["id"]) for c in first.get("configs", []) if isinstance(c, dict) and "id" in c}
        sub["served_keys"] = list(sub.keys())
        sub["source_note"] = f"{_rel(p)}; subset of top-level keys, values as stored"
        body = sub
    return jsonable(body)


@router.get("/index")
def index():
    out: dict[str, list[dict]] = {}
    for area, files in ALLOWED.items():
        items = []
        for fname in files:
            p = _area_dir(area) / fname
            if p.is_file():
                st = p.stat()
                items.append({"name": p.stem, "file": fname, "kind": p.suffix.lstrip("."), "bytes": st.st_size,
                              "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")})
        out[area] = items
    return {"areas": out, "evidence_matrix": EVIDENCE_MATRIX.is_file(),
            "aspen_evidence": (ASPEN_EVIDENCE_DIR / "manifest.json").is_file(),
            "validation_areas": sorted(p.stem for p in (RESEARCH_DIR / "validation").glob("*.json"))
            if (RESEARCH_DIR / "validation").is_dir() else []}


@router.get("/evidence-matrix")
def evidence_matrix():
    if not EVIDENCE_MATRIX.is_file():
        raise ApiError(404, "research_not_found", "The evidence matrix (results/research/evidence_matrix.json) has not been generated yet")
    return jsonable(_load_json(EVIDENCE_MATRIX))


def _items(body) -> list[dict]:
    if isinstance(body, dict):
        body = body.get("items", [])
    return [x for x in body if isinstance(x, dict)] if isinstance(body, list) else []


def validation_summary() -> dict:
    d = RESEARCH_DIR / "validation"
    areas: dict[str, dict] = {}
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        items = _items(_load_json(p))
        by = {"pass": 0, "fail": 0, "informational": 0}
        for it in items:
            by[it.get("status", "informational")] = by.get(it.get("status", "informational"), 0) + 1
        keep = ("id", "description", "method", "reference_source", "observed", "expected", "tolerance", "unit")
        areas[p.stem] = {
            "n_items": len(items), "by_status": by, "file": _rel(p),
            "failures": [{k: it.get(k) for k in keep} for it in items if it.get("status") == "fail"],
            "informational": [{"id": it.get("id"), "description": it.get("description")} for it in items if it.get("status") == "informational"],
        }
    tot = {"pass": 0, "fail": 0, "informational": 0}
    for a in areas.values():
        for k, v in a["by_status"].items():
            tot[k] = tot.get(k, 0) + v
    return jsonable({"areas": areas, "totals": tot, "n_items": sum(a["n_items"] for a in areas.values())})


@router.get("/validation-summary")
def validation_summary_endpoint():
    return validation_summary()


def aspen_evidence() -> dict:
    m = ASPEN_EVIDENCE_DIR / "manifest.json"
    if not m.is_file():
        raise ApiError(404, "research_not_found", "docs/images/aspen_evidence/manifest.json has not been generated yet")
    body = _load_json(m)
    caps = [c for c in body.get("captures", []) if isinstance(c, dict) and c.get("file") and (ASPEN_EVIDENCE_DIR / Path(c["file"]).name).is_file()]
    return jsonable({"aspen_version": body.get("aspen_version"), "note": body.get("note"), "generated_by": body.get("generated_by"),
                     "n_in_manifest": len(body.get("captures", [])), "captures": caps})


@router.get("/addendum")
def addendum_endpoint():
    if not ADDENDUM.is_file():
        raise ApiError(404, "research_not_found", "The addendum record (results/research/addendum_2026-11-24.json) has not been generated yet")
    return jsonable(_load_json(ADDENDUM))


@router.get("/aspen-evidence")
def aspen_evidence_endpoint():
    return aspen_evidence()


def validation_by_kind() -> dict:
    """Counts of results/research/validation/<area>.json items by evidence_kind and status. Items without an evidence_kind are
    counted under 'not_labelled' (never assigned a kind here). Failures are listed with their stored cause or note; when the
    item has neither, the documented cause that summary.json carries for the same area and id is used. The method is kept
    in its own field and is never shown as a cause."""
    vdir = RESEARCH_DIR / "validation"
    kinds: dict[str, dict] = {}
    areas: dict[str, dict] = {}
    summary_causes: dict[tuple[str, str], str] = {}
    sp = vdir / "summary.json"
    if sp.is_file():
        s_areas = _load_json(sp).get("areas", {})
        for area, block in (s_areas.items() if isinstance(s_areas, dict) else []):
            for f in (block.get("failures") or []) if isinstance(block, dict) else []:
                if isinstance(f, dict) and isinstance(f.get("id"), str) and isinstance(f.get("cause"), str):
                    summary_causes[(area, f["id"])] = f["cause"]
    # a cause that is only a key of the core matrix's failure_root_causes (results/validation/validation_matrix.json) is
    # printed with that entry's stored description
    core_causes: dict[str, str] = {}
    cp = RESEARCH_DIR.parent / "validation" / "validation_matrix.json"
    if cp.is_file():
        for c in _load_json(cp).get("summary", {}).get("failure_root_causes", []) or []:
            if isinstance(c, dict) and isinstance(c.get("cause"), str) and isinstance(c.get("description"), str):
                core_causes[c["cause"]] = c["description"]

    def cause_text(c):
        return f"{c} (core validation matrix): {core_causes[c]}" if isinstance(c, str) and c in core_causes else c
    for p in sorted(vdir.glob("*.json")) if vdir.is_dir() else []:
        if p.name == "summary.json":
            continue
        items = _items(_load_json(p))
        a = areas.setdefault(p.stem, {"file": _rel(p), "n_items": 0, "by_kind": {}})
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
    return jsonable({"source": "results/research/validation/*.json (summary.json excluded), counted by evidence_kind and status",
                     "evidence_kinds": list(EVIDENCE_KINDS), "kinds": kinds, "areas": areas,
                     "statement": "AmCraX has no independent experimental validation. Pass counts are numerical verification, Python against "
                                  "Aspen comparison or comparison with published literature, never experimental validation."})


@router.get("/validation/by_kind")
def validation_by_kind_endpoint():
    return validation_by_kind()


@router.get("/{area}/{name}")
def get_research_file(area: str, name: str):
    return serve_file(area, name)
