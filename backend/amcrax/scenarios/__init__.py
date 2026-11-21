"""AmCraX scenario analysis back end (P2.6).

* Process scenarios come from config/scenarios.json. For each one the stored Aspen Plus V15 result
  (results/simulations/<id>.json, converged) is used; otherwise the Python process model is run. The source
  is labelled per scenario. The Python model is ALSO run for every scenario so that the Aspen-minus-Python
  difference of each metric is shown (model-form uncertainty).
* Overlays (not Aspen cases): ammonia origin (green/blue/grey: upstream CI factor from
  data/environmental.yaml; NH3 price only where data/economics.yaml has a sourced colour-specific value,
  otherwise the base price is kept and the row says so), heat source for the heat deficit (burning NH3,
  natural gas / fired heat, electric) and grid emission factor.
All metrics come from amcrax.optimisation.evaluate_result (same definitions for Aspen and Python results).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from amcrax import paths
from amcrax.economics import load_economics_data
from amcrax.optimisation.evaluate import evaluate_result
from amcrax.process_model import run_python_case
from amcrax.schemas import CaseInputs, DataSource, SimulationResult

HEAT_SOURCE_MAP = {  # config/scenarios.json overlay name -> evaluate_result heat_source
    "tail_gas_plus_ammonia": "ammonia",
    "tail_gas_plus_natural_gas": "natural_gas",
    "tail_gas_plus_electric": "electric",
}

METRICS = ["lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2", "lhv_efficiency", "nh3_conversion", "h2_yield_overall",
           "h2_product_kg_h", "h2_purity_mole_frac", "nh3_feed_kg_per_kgH2", "nh3_total_kg_per_kgH2",
           "total_external_heating_kW", "net_fuel_heat_deficit_kW", "specific_heat_demand_kWh_per_kgH2",
           "cracked_gas_nh3_mole_frac", "compression_power_kW", "recovered_heat_kW"]
LCOH_PARTS = ["capex", "fixed_opex", "ammonia_feed", "imported_heat", "electricity", "cooling_water", "catalyst"]
CI_PARTS = ["upstream_ammonia", "transport", "electricity", "external_heat"]


def load_definitions(path: Optional[Path] = None) -> dict:
    p = path or (paths.CONFIG_DIR / "scenarios.json")
    return json.loads(Path(p).read_text(encoding="utf-8"))


def scenario_inputs(sc: dict) -> CaseInputs:
    return CaseInputs(**{**CaseInputs().model_dump(), **sc.get("overrides", {}), "case_id": sc["id"]})


def load_result(sc: dict, prefer_aspen: bool = True) -> tuple[SimulationResult, str]:
    """(result, note). Stored Aspen result if present and converged, else the Python model."""
    p = paths.RESULTS_SIMULATIONS / f"{sc['id']}.json"
    if prefer_aspen and p.exists():
        r = SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
        if r.source == DataSource.ASPEN and r.status.converged:
            # the stored case must have been solved for THIS scenario definition
            want = scenario_inputs(sc).model_dump(exclude={"case_id"})
            have = r.inputs.model_dump(exclude={"case_id"})
            if want == have:
                return r, f"stored Aspen result {p.relative_to(paths.ROOT).as_posix()}"
            r = run_python_case(scenario_inputs(sc))
            return r, ("Python process model (the stored Aspen result was solved for different inputs than the "
                       "current scenario definition - re-run aspen/automation/run_scenarios.py --force)")
    r = run_python_case(scenario_inputs(sc))
    return r, "Python process model (no converged Aspen result stored)"


def nh3_price_for_origin(origin: str, policy: str = "sourced") -> dict:
    """NH3 price for an ammonia origin. policy 'base' -> always the base default; 'sourced' -> a colour-specific value
    only where economics.yaml has one (green: renewable NH3 'current' cho2026nickel p. 17 Fig. 11), else base."""
    d = load_economics_data()["defaults"]["nh3_price_USD_per_t"]
    base = float(d["value"])
    base_src = f"{d['citekey']} p. {d['page']} {d['locator']}"
    if policy == "sourced" and origin == "green":
        for alt in d.get("alternatives", []):
            if alt.get("label") == "renewable NH3 current":
                return {"price_USD_per_t": float(alt["value"]), "price_basis": "sourced colour-specific price",
                        "price_source": f"{alt['citekey']} p. {alt['page']} {alt['locator']} ({alt['label']})",
                        "variants": [{"label": a["label"], "price_USD_per_t": float(a["value"]),
                                      "source": f"{a['citekey']} p. {a['page']} {a['locator']}"}
                                     for a in d["alternatives"] if str(a.get("label", "")).startswith("renewable")]}
    note = ("base price kept: no sourced colour-specific price in data/economics.yaml" if origin != "green" or policy == "base"
            else "base price")
    if origin == "blue":
        note = "base price kept: " + str(d.get("note", "no blue NH3 price in the library"))
    return {"price_USD_per_t": base, "price_basis": note, "price_source": base_src, "variants": []}


def _metrics(m: dict) -> dict:
    return {k: m.get(k) for k in METRICS}


def _diff(a: dict, b: dict) -> dict:
    out = {}
    for k in METRICS:
        x, y = a.get(k), b.get(k)
        out[k] = None if x is None or y is None else x - y
    return out


def compare(scenario_ids: Optional[Sequence[str]] = None, *, nh3_origin: str = "grey", heat_source: str = "ammonia",
            grid: str = "singapore_2024", price_policy: str = "sourced", prefer_aspen: bool = True,
            overlays: bool = True) -> dict:
    """Side-by-side scenario table. Returns a JSON-serialisable dict (see module docstring)."""
    defs = load_definitions()
    scs = defs["process_scenarios"]
    if scenario_ids:
        want = list(scenario_ids)
        unknown = [s for s in want if s not in {x["id"] for x in scs}]
        if unknown:
            raise ValueError(f"unknown scenario ids {unknown}")
        scs = [x for x in scs if x["id"] in want or x["id"] == "baseline"]
    hs = HEAT_SOURCE_MAP.get(heat_source, heat_source)
    price = nh3_price_for_origin(nh3_origin, price_policy)
    opts = dict(heat_source=hs, nh3_route=nh3_origin, grid=grid, nh3_price_USD_per_t=price["price_USD_per_t"])
    base_in = CaseInputs().model_dump()
    rows = []
    for sc in scs:
        res, note = load_result(sc, prefer_aspen)
        m = evaluate_result(res, **opts)
        py = res if res.source == DataSource.PYTHON else run_python_case(scenario_inputs(sc))
        mp = evaluate_result(py, **opts)
        differing = {k: v for k, v in res.inputs.model_dump().items() if k != "case_id" and v != base_in.get(k)}
        row = {"id": sc["id"], "label": sc["label"], "rationale": sc.get("rationale", ""),
               "source": res.source.value, "source_note": note, "converged": res.status.converged,
               "inputs_differing_from_baseline": differing,
               "stored_kpis": res.kpis.model_dump(),
               "metrics": _metrics(m),
               "lcoh_breakdown_USD_per_kg": {c: m[f"lcoh_{c}_USD_per_kg"] for c in LCOH_PARTS},
               "ci_breakdown_kgCO2e_per_kgH2": {c: m[f"ci_{c}"] for c in CI_PARTS},
               "python_metrics": _metrics(mp),
               "aspen_minus_python": _diff(m, mp) if res.source == DataSource.ASPEN else None}
        if overlays:
            ov = []
            for origin in ("grey", "blue", "green"):
                pr = nh3_price_for_origin(origin, price_policy)
                for name, h in HEAT_SOURCE_MAP.items():
                    mo = evaluate_result(res, heat_source=h, nh3_route=origin, grid=grid,
                                         nh3_price_USD_per_t=pr["price_USD_per_t"])
                    mb = evaluate_result(res, heat_source=h, nh3_route=origin, grid=grid) if pr["price_USD_per_t"] != \
                        float(load_economics_data()["defaults"]["nh3_price_USD_per_t"]["value"]) else mo
                    ov.append({"nh3_origin": origin, "heat_source": name, "nh3_price_USD_per_t": pr["price_USD_per_t"],
                               "price_basis": pr["price_basis"], "lcoh_USD_per_kg": mo["lcoh_USD_per_kg"],
                               "lcoh_at_base_price_USD_per_kg": mb["lcoh_USD_per_kg"],
                               "carbon_intensity_kgCO2e_per_kgH2": mo["carbon_intensity_kgCO2e_per_kgH2"],
                               "ci_breakdown_kgCO2e_per_kgH2": {c: mo[f"ci_{c}"] for c in CI_PARTS}})
            row["overlays"] = ov
        rows.append(row)
    base = next(r for r in rows if r["id"] == "baseline")
    for r in rows:
        r["delta_vs_baseline"] = _diff(r["metrics"], base["metrics"])
        r["delta_rel_vs_baseline"] = {k: (None if d is None or not base["metrics"].get(k) else d / abs(base["metrics"][k]))
                                      for k, d in r["delta_vs_baseline"].items()}
    return {"engine": "evaluate_result on stored Aspen results (else python_model)",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "settings": {"nh3_origin": nh3_origin, "heat_source": heat_source, "grid": grid, "price_policy": price_policy,
                         "nh3_price": price},
            "provenance": {"process": "per-row 'source' (aspen_plus_v15 or python_model)",
                           "lcoh": "amcrax.economics (data/economics.yaml)",
                           "carbon_intensity": "amcrax.environmental - simplified carbon-intensity accounting, NOT an LCA",
                           "compression": "amcrax.separation reduced-order compression when PSA feed < 7 bar"},
            "notes": ["aspen_minus_python = evaluate_result(Aspen) - evaluate_result(Python) at the same inputs: "
                      "model-form difference, not an error bar.",
                      "Low-pressure scenario: cracked-gas compression to the 7 bar PSA requirement is added by the "
                      "evaluator (electricity only; no compressor CAPEX)."],
            "metric_names": METRICS, "rows": rows}


def flat_table(comp: dict) -> list[dict]:
    """One CSV row per scenario: metric, python value and Aspen-minus-Python columns."""
    out = []
    for r in comp["rows"]:
        d = {"id": r["id"], "label": r["label"], "source": r["source"],
             "inputs_differing": ";".join(f"{k}={v}" for k, v in r["inputs_differing_from_baseline"].items())}
        for k in METRICS:
            d[k] = r["metrics"][k]
            d[f"{k}__python"] = r["python_metrics"][k]
            d[f"{k}__aspen_minus_python"] = None if r["aspen_minus_python"] is None else r["aspen_minus_python"][k]
            d[f"{k}__delta_vs_baseline"] = r["delta_vs_baseline"][k]
        for c, v in r["lcoh_breakdown_USD_per_kg"].items():
            d[f"lcoh_{c}_USD_per_kg"] = v
        for c, v in r["ci_breakdown_kgCO2e_per_kgH2"].items():
            d[f"ci_{c}"] = v
        out.append(d)
    return out


__all__ = ["compare", "flat_table", "load_definitions", "load_result", "scenario_inputs", "nh3_price_for_origin",
           "HEAT_SOURCE_MAP", "METRICS"]
