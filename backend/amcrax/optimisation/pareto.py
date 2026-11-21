"""Design grid, objective-conflict test and Pareto fronts (non-dominated sorting with numpy).

Every point is an actual Python-process-model evaluation (no interpolation, smoothing or invented points).
"""
from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from typing import Optional, Sequence

import numpy as np
from scipy.stats import spearmanr

from amcrax.process_model import FlowsheetSpecError, run_python_case
from amcrax.schemas import CaseInputs

from .evaluate import evaluate_result
from .problems import DEFAULT_CONSTRAINTS, constraint_values

#: Pareto objectives: metric -> sense
PARETO_OBJECTIVES = {
    "lcoh_USD_per_kg": "min",
    "lhv_efficiency": "max",
    "h2_yield_overall": "max",
    "carbon_intensity_kgCO2e_per_kgH2": "min",
    "nh3_conversion": "max",
}

DEFAULT_GRID = {
    "reactor_temperature_C": [400.0 + 25.0 * i for i in range(17)],
    "reactor_pressure_bar": [5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0],
    "psa_h2_recovery": [0.70, 0.75, 0.80, 0.85, 0.90, 0.95],
    "fehe_hot_end_approach_K": [20.0, 35.0, 50.0, 75.0, 100.0, 150.0],
}

#: overlays evaluated at every grid point: (suffix, heat_source, nh3_route)
OVERLAYS = [("", "ammonia", "grey"), ("ng_grey", "natural_gas", "grey"),
            ("nh3_green", "ammonia", "green"), ("ng_green", "natural_gas", "green")]

KEEP = ["lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2", "lhv_efficiency", "nh3_conversion", "h2_yield_overall",
        "h2_product_kg_h", "h2_purity_mole_frac", "nh3_feed_kg_per_kgH2", "nh3_total_kg_per_kgH2",
        "total_external_heating_kW", "net_fuel_heat_deficit_kW", "specific_heat_demand_kWh_per_kgH2",
        "cracked_gas_nh3_mole_frac", "compression_power_kW", "fehe_min_internal_dT_K"]


def nh3_price_for_route(route: str) -> float:
    """Ammonia price (USD/t) for an ammonia origin: the sourced 'renewable NH3 current' value for green
    ammonia, the base default otherwise (no sourced blue/grey split exists in data/economics.yaml).
    Mirrors amcrax.scenarios.nh3_price_for_origin so that Pareto overlays and scenario overlays agree."""
    from amcrax.economics import load_economics_data

    d = load_economics_data()["defaults"]["nh3_price_USD_per_t"]
    if route == "green":
        for alt in d.get("alternatives", []):
            if alt.get("label") == "renewable NH3 current":
                return float(alt["value"])
    return float(d["value"])


def design_grid(grid: Optional[dict] = None, constraints: Optional[dict] = None,
                base: Optional[CaseInputs] = None) -> list[dict]:
    """Full factorial grid on the Python model. Each row: inputs, metrics, overlay LCOH/CI, feasibility flags."""
    g = grid or DEFAULT_GRID
    cons = dict(DEFAULT_CONSTRAINTS)
    cons.update(constraints or {})
    base = base or CaseInputs()
    names = list(g)
    rows = []
    for vals in np.array(np.meshgrid(*[g[n] for n in names], indexing="ij")).reshape(len(names), -1).T:
        d = base.model_dump()
        d.update({n: float(v) for n, v in zip(names, vals)})
        d["case_id"] = "grid"
        row = {n: float(v) for n, v in zip(names, vals)}
        try:
            res = run_python_case(CaseInputs(**d))
        except FlowsheetSpecError as e:
            row.update({"model_ok": False, "feasible": False, "infeasibility": str(e)[:120]})
            rows.append(row)
            continue
        m = evaluate_result(res)
        for k in KEEP:
            row[k] = m.get(k)
        for suf, hs, route in OVERLAYS[1:]:
            # same sourced, origin-specific ammonia price as amcrax.scenarios (green NH3 is not 450 USD/t)
            mo = evaluate_result(res, heat_source=hs, nh3_route=route, nh3_price_USD_per_t=nh3_price_for_route(route))
            row[f"lcoh_USD_per_kg_{suf}"] = mo["lcoh_USD_per_kg"]
            row[f"carbon_intensity_{suf}"] = mo["carbon_intensity_kgCO2e_per_kgH2"]
        gv = constraint_values(m, cons)
        bad = [k for k, v in gv.items() if v < -1e-9]
        row.update({"model_ok": True, "feasible": not bad, "infeasibility": ";".join(bad)})
        rows.append(row)
    return rows


def _matrix(rows: Sequence[dict], metrics: Sequence[str], senses: Sequence[str]) -> np.ndarray:
    """Objective matrix in minimisation sense."""
    a = np.array([[r[m] for m in metrics] for r in rows], float)
    s = np.array([1.0 if x == "min" else -1.0 for x in senses])
    return a * s


def non_dominated(F: np.ndarray) -> np.ndarray:
    """Boolean mask of non-dominated rows of F (all objectives minimised). Duplicates are all kept."""
    n = F.shape[0]
    mask = np.ones(n, bool)
    for i in range(n):
        if not mask[i]:
            continue
        dom = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        if dom.any():
            mask[i] = False
    return mask


def conflicts(rows: Sequence[dict], objectives: Optional[dict] = None) -> dict:
    """Spearman rank correlation (minimisation sense) for each objective pair over the feasible grid, plus the
    size and spread of the pairwise non-dominated set. Classification: rho < -0.3 'conflict', |rho| <= 0.3 'weak',
    rho > 0.3 'aligned'; a pair whose non-dominated set is a single point is 'no trade-off' regardless of rho."""
    obj = objectives or PARETO_OBJECTIVES
    feas = [r for r in rows if r.get("feasible")]
    out = []
    for a, b in combinations(obj, 2):
        F = _matrix(feas, [a, b], [obj[a], obj[b]])
        rho = float(spearmanr(F[:, 0], F[:, 1]).statistic)
        nd = non_dominated(F)
        uniq = np.unique(np.round(F[nd], 9), axis=0)
        span = {m: [float(np.min(np.array([r[m] for r, k in zip(feas, nd) if k]))),
                    float(np.max(np.array([r[m] for r, k in zip(feas, nd) if k])))] for m in (a, b)}
        cls = "conflict" if rho < -0.3 else ("aligned" if rho > 0.3 else "weak")
        if len(uniq) <= 1:
            cls = "no trade-off (single non-dominated point)"
        elif cls != "conflict" and len(uniq) >= 3:
            cls += f" globally; local trade-off ({len(uniq)} distinct non-dominated points)"
        out.append({"pair": [a, b], "senses": [obj[a], obj[b]], "spearman_rho_min_sense": rho,
                    "n_feasible_points": len(feas), "n_non_dominated": int(nd.sum()),
                    "n_distinct_non_dominated": int(len(uniq)), "front_ranges": span, "classification": cls})
    return {"method": ("Spearman rank correlation of objectives expressed in minimisation sense over the feasible "
                       "design grid (negative = improving one worsens the other), plus the pairwise non-dominated set."),
            "caveat": "Correlations depend on the grid ranges/spacing; the non-dominated set size is the direct test.",
            "pairs": out}


def front(rows: Sequence[dict], metrics: Sequence[str], senses: Sequence[str], *, feasible_only: bool = True) -> list[dict]:
    """Non-dominated grid points for the given metrics; each point carries its 'feasible' flag."""
    cand = [r for r in rows if r.get("model_ok") and (r.get("feasible") or not feasible_only)
            and all(r.get(m) is not None for m in metrics)]
    if not cand:
        return []
    F = _matrix(cand, metrics, senses)
    nd = non_dominated(F)
    pts = [dict(r) for r, k in zip(cand, nd) if k]
    pts.sort(key=lambda r: r[metrics[0]])
    return pts


def pareto(rows: Optional[Sequence[dict]] = None, pairs: Optional[Sequence[Sequence[str]]] = None,
           grid: Optional[dict] = None, constraints: Optional[dict] = None) -> dict:
    """Pareto fronts for objective pairs/triples (default: those classified 'conflict' plus the LCOH-CI heat-source
    and ammonia-origin overlays). Returns a JSON-serialisable dict."""
    rows = list(rows) if rows is not None else design_grid(grid, constraints)
    conf = conflicts(rows)
    if pairs is None:
        pairs = [p["pair"] for p in conf["pairs"]
                 if p["classification"] == "conflict" or "local trade-off" in p["classification"]]
    fronts = []
    for p in pairs:
        p = list(p)
        senses = [PARETO_OBJECTIVES.get(m, "min") for m in p]
        pts = front(rows, p, senses)
        unc = front(rows, p, senses, feasible_only=False)
        fronts.append({"objectives": p, "senses": senses, "overlay": "grey NH3, heat deficit by burning NH3 (default)",
                       "points": pts, "n_points": len(pts),
                       "unconstrained_front_infeasible_points": [r for r in unc if not r.get("feasible")]})
    for suf, hs, route in OVERLAYS:
        lk = "lcoh_USD_per_kg" + (f"_{suf}" if suf else "")
        ck = "carbon_intensity_kgCO2e_per_kgH2" if not suf else f"carbon_intensity_{suf}"
        pts = front(rows, [lk, ck], ["min", "min"])
        fronts.append({"objectives": [lk, ck], "senses": ["min", "min"], "overlay": f"{route} NH3, heat source {hs}",
                       "heat_source": hs, "nh3_route": route, "points": pts, "n_points": len(pts),
                       "unconstrained_front_infeasible_points": []})
    triple = ["lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2", "lhv_efficiency"]
    pts = front(rows, triple, [PARETO_OBJECTIVES[m] for m in triple])
    fronts.append({"objectives": triple, "senses": [PARETO_OBJECTIVES[m] for m in triple],
                   "overlay": "grey NH3, heat deficit by burning NH3 (default)", "points": pts, "n_points": len(pts),
                   "unconstrained_front_infeasible_points": []})
    return {"engine": "python_model", "source": "python_model",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "method": "non-dominated sorting of full-factorial design-grid evaluations (numpy); no interpolation",
            "n_grid_points": len(rows), "n_feasible": sum(1 for r in rows if r.get("feasible")),
            "constraints": {**DEFAULT_CONSTRAINTS, **(constraints or {})},
            "conflicts": conf, "fronts": fronts}


__all__ = ["PARETO_OBJECTIVES", "DEFAULT_GRID", "OVERLAYS", "design_grid", "conflicts", "non_dominated", "front", "pareto"]
