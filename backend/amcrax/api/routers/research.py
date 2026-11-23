"""Read-only endpoints over the stored research-expansion results (hypotheses H1-H4).

GET /api/research/index                 whitelist of served files per area (name, kind, bytes, modified)
GET /api/research/evidence-matrix       results/research/evidence_matrix.json (404 until the file exists)
GET /api/research/validation-summary    pass / fail / informational counts per area, failures named (from results/research/validation/*.json)
GET /api/research/aspen-evidence        docs/images/aspen_evidence/manifest.json (captures whose PNG exists)
GET /api/research/{area}/{name}         one whitelisted file: CSV -> {name, area, columns, rows, count, source_note}; JSON as stored
                                        (a few large JSON files are served as a subset of named top-level keys, stated in `served_keys`)

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
    p = RESEARCH_DIR / area / fname
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
            p = RESEARCH_DIR / area / fname
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


@router.get("/aspen-evidence")
def aspen_evidence_endpoint():
    return aspen_evidence()


@router.get("/{area}/{name}")
def get_research_file(area: str, name: str):
    return serve_file(area, name)
