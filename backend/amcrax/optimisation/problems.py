"""Single-objective process optimisation on the Python process model (engine = python_model).

Decision variables (bounds = the Aspen-simulated / validated ranges, never below the 3 bar flowsheet minimum):
    reactor_temperature_C     400 - 800 degC   (Aspen T sweep results/sensitivity/aspen_temperature.csv)
    reactor_pressure_bar        5 - 40 bar     (Aspen P sweep aspen_pressure.csv)
    psa_h2_recovery          0.70 - 0.95       (Aspen sweep aspen_psa_recovery.csv)
    fehe_hot_end_approach_K    20 - 150 K      (Aspen sweep aspen_fehe_approach.csv)

Constraints (each a documented function g(metrics) >= 0 when satisfied) - see CONSTRAINTS.
Solver: scipy differential_evolution (fixed seed) on variables scaled to [0, 1], then an SLSQP polish
from the DE point; the better feasible point is reported.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Sequence

import numpy as np
from scipy.optimize import NonlinearConstraint, differential_evolution, minimize

from amcrax.process_model import FlowsheetSpecError, run_python_case
from amcrax.schemas import CaseInputs, SimulationResult
from amcrax.separation import params as sep_params

from .evaluate import evaluate_result

# --------------------------------------------------------------------------------------------- variables
VARIABLES: dict[str, dict] = {
    "reactor_temperature_C": {"lower": 400.0, "upper": 800.0, "unit": "degC",
                              "basis": "range of the Aspen Plus V15 temperature sweep (results/sensitivity/aspen_temperature.csv)"},
    "reactor_pressure_bar": {"lower": 5.0, "upper": 40.0, "unit": "bar",
                             "basis": "range of the Aspen pressure sweep (aspen_pressure.csv); flowsheet minimum is 3 bar"},
    "psa_h2_recovery": {"lower": 0.70, "upper": 0.95, "unit": "-",
                        "basis": "range of the Aspen PSA-recovery sweep (aspen_psa_recovery.csv); literature PSA points 0.71-0.81 (separation.yaml)"},
    "fehe_hot_end_approach_K": {"lower": 20.0, "upper": 150.0, "unit": "K",
                                "basis": "range of the Aspen FEHE-approach sweep (aspen_fehe_approach.csv)"},
}
MIN_FLOWSHEET_PRESSURE_BAR = 3.0

#: Why a variable sitting on a bound is not a 'discovered' optimum (what the model does not cost / see).
MODEL_LIMITATIONS = {
    "fehe_hot_end_approach_K": ("FEHE area is not costed: the plant-level CAPEX correlation (economics.yaml capex_references) "
                                "scales with H2 capacity only, so a tighter approach is 'free' heat recovery in this model."),
    "psa_h2_recovery": ("PSA size, bed count, cycle and the recovery-purity trade-off are not modelled (reduced-order "
                        "splitter with fixed N2 slip); recoveries above the literature 0.71-0.81 are not demonstrated."),
    "reactor_temperature_C": ("Equilibrium (RGibbs-type) reactor: catalyst activity, catalyst volume, reactor material "
                              "limits (creep, nitriding) and heat-transfer area are not costed."),
    "reactor_pressure_bar": ("Reactor/PSA vessel cost does not depend on pressure in the CAPEX correlation; below the 7 bar PSA "
                             "requirement only compressor electricity (not compressor CAPEX) is charged."),
}

# --------------------------------------------------------------------------------------------- constraints
DEFAULT_CONSTRAINTS: dict[str, Any] = {
    "fehe_min_internal_dT_K": 0.0,
    "min_nh3_conversion": 0.95,
    "max_cracked_gas_nh3_mole_frac": None,
    "min_h2_purity": None,          # None -> separation.yaml product_purity_spec (0.99, chopra2026decentralized p. 4)
    "thermal_self_sufficiency": False,
}

CONSTRAINT_DOCS = {
    "fehe_feasibility": ("FEHE feasibility: no temperature cross. The process model raises FlowsheetSpecError for a cross "
                         "(41-point counter-current T-Q profile) or a cold outlet below the cold inlet; g = min internal dT - "
                         "fehe_min_internal_dT_K (default 0 K = 'no cross'). Model failure counts as infeasible."),
    "min_nh3_conversion": ("Minimum equilibrium NH3 conversion, g = X - min_nh3_conversion. DESIGN ASSUMPTION, default 0.95: "
                           "limits the NH3 load sent to the PSA/tail-gas burner (NOx precursor, not modelled). Literature "
                           "crackers report 99.42 % and 99.6 % (hansen2024hysys p. 4 Table 3, p. 5 Table 4); a 0.99 variant is "
                           "reported separately. The baseline (600 degC, 20 bar) has X = 0.981."),
    "max_cracked_gas_nh3_mole_frac": "Optional maximum NH3 mole fraction in S5 (off by default).",
    "product_purity": ("H2 purity >= min_h2_purity (default 0.99, separation.yaml product_purity_spec, chopra2026decentralized "
                       "p. 4 Sec. 2.2). Implied by the reduced-order splitter (fixed N2 slip, NH3/H2O fully retained), so it is "
                       "reported but practically never active."),
    "thermal_self_sufficiency": "Optional: net_fuel_heat_deficit_kW <= 0 (tail-gas heat covers all external heating), g = -deficit.",
    "kinetic_feasibility": "NOT IMPLEMENTED (unfinished): catalyst-mass bound from amcrax.reactor.",
}


def _purity_spec() -> float:
    return float(sep_params()["psa"]["product_purity_spec"]["value"])


def constraint_values(m: Optional[dict], c: dict) -> dict[str, float]:
    """g >= 0 means satisfied. ``m`` None (model infeasible) -> all -1."""
    names = ["fehe_feasibility", "min_nh3_conversion", "product_purity"]
    if c.get("max_cracked_gas_nh3_mole_frac") is not None:
        names.append("max_cracked_gas_nh3_mole_frac")
    if c.get("thermal_self_sufficiency"):
        names.append("thermal_self_sufficiency")
    if m is None:
        return {n: -1.0 for n in names}
    g = {}
    dT = m.get("fehe_min_internal_dT_K")
    g["fehe_feasibility"] = (dT - float(c["fehe_min_internal_dT_K"])) if dT is not None else 0.0
    xmin = c.get("min_nh3_conversion")
    g["min_nh3_conversion"] = (m["nh3_conversion"] - xmin) if xmin is not None else 1.0
    pmin = c.get("min_h2_purity") if c.get("min_h2_purity") is not None else _purity_spec()
    g["product_purity"] = m["h2_purity_mole_frac"] - pmin
    if "max_cracked_gas_nh3_mole_frac" in names:
        g["max_cracked_gas_nh3_mole_frac"] = c["max_cracked_gas_nh3_mole_frac"] - m["cracked_gas_nh3_mole_frac"]
    if "thermal_self_sufficiency" in names:
        g["thermal_self_sufficiency"] = -m["net_fuel_heat_deficit_kW"] / 1000.0  # MW scale
    return g


# --------------------------------------------------------------------------------------------- objectives
OBJECTIVES: dict[str, dict] = {
    "min_lcoh": {"metric": "lcoh_USD_per_kg", "sense": "min", "label": "Minimise LCOH (USD/kg H2)"},
    "max_lhv_efficiency": {"metric": "lhv_efficiency", "sense": "max", "label": "Maximise LHV efficiency"},
    "min_specific_heat": {"metric": "specific_heat_demand_kWh_per_kgH2", "sense": "min",
                          "label": "Minimise external heating per kg H2 (kWh/kg)"},
    "max_h2_production": {"metric": "h2_product_kg_h", "sense": "max",
                          "label": "Maximise H2 production (kg/h, fixed 100 kmol/h feed)"},
    "max_conversion": {"metric": "nh3_conversion", "sense": "max", "label": "Maximise NH3 conversion"},
}


def _signed(metric_value: float, sense: str) -> float:
    return metric_value if sense == "min" else -metric_value


# --------------------------------------------------------------------------------------------- evaluation
class Evaluator:
    """Cached x -> (metrics | None). ``fixed`` holds CaseInputs overrides not optimised."""

    def __init__(self, names: Sequence[str], fixed: Optional[dict] = None, eval_options: Optional[dict] = None,
                 base_inputs: Optional[CaseInputs] = None):
        self.names = list(names)
        self.fixed = dict(fixed or {})
        self.opts = dict(eval_options or {})
        self.base = base_inputs or CaseInputs()
        self.cache: dict[tuple, Optional[dict]] = {}
        self.n_model_runs = 0
        self.n_failures = 0

    def inputs(self, x: Sequence[float], case_id: str = "opt") -> CaseInputs:
        d = self.base.model_dump()
        d.update(self.fixed)
        d.update({n: float(v) for n, v in zip(self.names, x)})
        d["case_id"] = case_id
        return CaseInputs(**d)

    def __call__(self, x: Sequence[float]) -> Optional[dict]:
        key = tuple(round(float(v), 9) for v in x)
        if key in self.cache:
            return self.cache[key]
        self.n_model_runs += 1
        try:
            res = run_python_case(self.inputs(x))
            m = evaluate_result(res, **self.opts)
        except (FlowsheetSpecError, ValueError):
            self.n_failures += 1
            m = None
        self.cache[key] = m
        return m


def minimise(fun: Callable[[np.ndarray], float], bounds: Sequence[tuple[float, float]],
             constraints: Optional[Callable[[np.ndarray], np.ndarray]] = None, *, seed: int = 12345,
             popsize: int = 10, maxiter: int = 30, polish: bool = True, tol: float = 1e-7) -> dict:
    """Generic bounded (optionally constrained) global + local minimisation.

    DE (scipy, deterministic for a fixed seed) on [0,1]-scaled variables, then SLSQP from the DE point.
    ``constraints(x)`` returns an array that must be >= 0. Returns dict(x, fun, success, nfev, message...).
    """
    lo = np.array([b[0] for b in bounds], float)
    hi = np.array([b[1] for b in bounds], float)
    span = np.where(hi > lo, hi - lo, 1.0)
    to_x = lambda z: lo + np.clip(z, 0, 1) * span  # noqa: E731
    nfev = {"n": 0}

    def f(z):
        nfev["n"] += 1
        return fun(to_x(z))

    cons = []
    if constraints is not None:
        cons = [NonlinearConstraint(lambda z: np.asarray(constraints(to_x(z)), float), 0.0, np.inf)]
    de = differential_evolution(f, [(0.0, 1.0)] * len(bounds), constraints=cons, seed=seed, popsize=popsize,
                                maxiter=maxiter, tol=tol, polish=False, init="sobol", updating="deferred")
    best_z, best_f, best_from = de.x, float(de.fun), "differential_evolution"
    loc_info = None
    if polish:
        sl_cons = [{"type": "ineq", "fun": (lambda z: np.asarray(constraints(to_x(z)), float))}] if constraints else []
        loc = minimize(f, de.x, method="SLSQP", bounds=[(0.0, 1.0)] * len(bounds), constraints=sl_cons,
                       options={"maxiter": 100, "ftol": 1e-10, "eps": 1e-5})
        ok = bool(np.all(np.asarray(constraints(to_x(loc.x))) >= -1e-7)) if constraints else True
        loc_info = {"success": bool(loc.success), "message": str(loc.message), "nit": int(loc.nit),
                    "feasible": ok, "fun": float(loc.fun)}
        if ok and np.isfinite(loc.fun) and loc.fun < best_f - 1e-12:
            best_z, best_f, best_from = loc.x, float(loc.fun), "SLSQP polish"
    feas = bool(np.all(np.asarray(constraints(to_x(best_z))) >= -1e-7)) if constraints else True
    return {"x": to_x(best_z), "z": np.clip(best_z, 0, 1), "fun": best_f, "success": bool(de.success) and feas,
            "feasible": feas, "nfev": nfev["n"], "de_nit": int(de.nit), "de_message": str(de.message),
            "de_success": bool(de.success), "polish": loc_info, "best_from": best_from}


# --------------------------------------------------------------------------------------------- run
PENALTY = 1e6


def _bounds(names, bounds_override):
    out = {}
    for n in names:
        lo, hi = VARIABLES[n]["lower"], VARIABLES[n]["upper"]
        if bounds_override and n in bounds_override:
            lo, hi = map(float, bounds_override[n])
        if n == "reactor_pressure_bar":
            lo = max(lo, MIN_FLOWSHEET_PRESSURE_BAR)
        if not hi >= lo:
            raise ValueError(f"invalid bounds for {n}: {lo}, {hi}")
        out[n] = (lo, hi)
    return out


def _clean(m: Optional[dict]) -> Optional[dict]:
    if m is None:
        return None
    return {k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in m.items()}


def flatness(ev: Evaluator, x_opt: np.ndarray, bounds: dict, metric: str, sense: str, cons: dict,
             tol_rel: float = 0.01, n: int = 41) -> dict:
    """1-D scans through the optimum: range of each variable keeping the objective within tol_rel of the optimum
    (others fixed at the optimum, feasible points only). Scan points are actual model evaluations."""
    m0 = ev(x_opt)
    f0 = m0[metric]
    out = {}
    for i, name in enumerate(ev.names):
        lo, hi = bounds[name]
        grid = np.linspace(lo, hi, n)
        vals, ok = [], []
        for v in grid:
            x = np.array(x_opt, float)
            x[i] = v
            m = ev(x)
            feas = m is not None and all(g >= -1e-9 for g in constraint_values(m, cons).values())
            vals.append(None if m is None else float(m[metric]))
            ok.append(feas)
        within = [g for g, v, f in zip(grid, vals, ok)
                  if f and v is not None and abs(v - f0) <= tol_rel * abs(f0)]
        out[name] = {"tolerance_rel": tol_rel, "range_within_tol": [float(min(within)), float(max(within))] if within else None,
                     "fraction_of_bound_range": (float((max(within) - min(within)) / (hi - lo)) if within and hi > lo else None),
                     "scan": [{"x": float(g), "value": v, "feasible": f} for g, v, f in zip(grid, vals, ok)]}
    return out


def run(objective: str = "min_lcoh", bounds: Optional[dict] = None, constraints: Optional[dict] = None,
        method: str = "de", *, variables: Optional[Sequence[str]] = None, fixed: Optional[dict] = None,
        eval_options: Optional[dict] = None, seed: int = 12345, popsize: int = 8, maxiter: int = 20,
        flatness_points: int = 21, base_result: Optional[SimulationResult] = None, **_ignored) -> dict:
    """Optimise one objective on the Python process model. Returns a JSON-serialisable dict.

    objective: key of OBJECTIVES. bounds: {var: [lo, hi]}. constraints: overrides of DEFAULT_CONSTRAINTS.
    variables: subset of VARIABLES to optimise (others fixed at the base inputs or ``fixed``).
    method: 'de' (differential evolution + SLSQP polish) or 'grid' (coarse grid + SLSQP polish).
    base_result: optional SimulationResult whose inputs define the base case (API use).
    """
    t0 = time.perf_counter()
    if objective not in OBJECTIVES:
        raise ValueError(f"unknown objective {objective!r}; use one of {list(OBJECTIVES)}")
    spec = OBJECTIVES[objective]
    cons = dict(DEFAULT_CONSTRAINTS)
    cons.update(constraints or {})
    names = list(variables or VARIABLES)
    for n in names:
        if n not in VARIABLES:
            raise ValueError(f"unknown decision variable {n!r}")
    bnd = _bounds(names, bounds)
    base_inputs = base_result.inputs if base_result is not None else CaseInputs()
    base_inputs = base_inputs.model_copy(update={"heat_integration": True})
    ev = Evaluator(names, fixed, eval_options, base_inputs)

    def fun(x):
        m = ev(x)
        return PENALTY if m is None else _signed(m[spec["metric"]], spec["sense"])

    def cfun(x):
        return np.array(list(constraint_values(ev(x), cons).values()), float)

    blist = [bnd[n] for n in names]
    if method == "grid":
        k = 5
        axes = [np.linspace(lo, hi, k) for lo, hi in blist]
        best, bx = math.inf, None
        for pt in np.array(np.meshgrid(*axes, indexing="ij")).reshape(len(names), -1).T:
            if np.all(cfun(pt) >= 0):
                v = fun(pt)
                if v < best:
                    best, bx = v, pt
        if bx is None:
            raise RuntimeError("no feasible grid point")
        lo = np.array([b[0] for b in blist]); span = np.array([b[1] - b[0] for b in blist]); span[span == 0] = 1
        z0 = (bx - lo) / span
        loc = minimize(lambda z: fun(lo + np.clip(z, 0, 1) * span), z0, method="SLSQP", bounds=[(0, 1)] * len(names),
                       constraints=[{"type": "ineq", "fun": lambda z: cfun(lo + np.clip(z, 0, 1) * span)}],
                       options={"maxiter": 100, "ftol": 1e-10, "eps": 1e-5})
        xl = lo + np.clip(loc.x, 0, 1) * span
        use_loc = np.all(cfun(xl) >= -1e-7) and loc.fun < best
        x_opt = xl if use_loc else bx
        sol = {"x": x_opt, "fun": float(fun(x_opt)), "success": True, "feasible": True,
               "nfev": ev.n_model_runs, "polish": {"success": bool(loc.success), "message": str(loc.message)},
               "best_from": "SLSQP polish" if use_loc else "grid", "de_nit": None, "de_message": None}
    elif method == "de":
        sol = minimise(fun, blist, cfun, seed=seed, popsize=popsize, maxiter=maxiter)
    else:
        raise ValueError("method must be 'de' or 'grid'")

    x_opt = np.asarray(sol["x"], float)
    # bound snap: a variable within 3 % of a bound is evaluated exactly on the bound; kept if feasible and better
    snapped = []
    for i, n in enumerate(names):
        lo, hi = bnd[n]
        for b in (lo, hi):
            if hi > lo and abs(x_opt[i] - b) <= 0.03 * (hi - lo) and x_opt[i] != b:
                xt = x_opt.copy()
                xt[i] = b
                if np.all(cfun(xt) >= -1e-9) and fun(xt) < fun(x_opt) - 1e-12:
                    x_opt = xt
                    snapped.append(f"{n}->{b:g}")
    sol["bound_snap"] = snapped
    m_opt = ev(x_opt)
    g_opt = constraint_values(m_opt, cons)
    inp_opt = ev.inputs(x_opt, case_id=f"opt_{objective}")
    base_m = evaluate_result(run_python_case(base_inputs.model_copy(update={"case_id": "baseline"})), **(eval_options or {}))

    dv, active, limitations = {}, [], []
    for i, n in enumerate(names):
        lo, hi = bnd[n]
        tol = 1e-3 * (hi - lo)
        at = "lower" if x_opt[i] - lo <= tol else ("upper" if hi - x_opt[i] <= tol else None)
        dv[n] = {"lower": lo, "upper": hi, "optimum": float(x_opt[i]), "at_bound": at, "unit": VARIABLES[n]["unit"],
                 "bounds_basis": VARIABLES[n]["basis"]}
        if at:
            active.append(f"{n}={at}")
            limitations.append(f"{n} at its {at} bound ({dv[n]['optimum']:g}): bound-driven, not a discovered interior optimum. "
                               + MODEL_LIMITATIONS[n])
    flat = flatness(ev, x_opt, bnd, spec["metric"], spec["sense"], cons, n=flatness_points) if flatness_points else {}
    for n, fl in flat.items():
        if fl.get("fraction_of_bound_range") is not None and fl["fraction_of_bound_range"] >= 0.999:
            limitations.append(f"Objective is flat in {n} (within 1 % over the whole bound range): its optimum value is "
                               "not meaningful for this objective.")
    active_cons = [n for n, g in g_opt.items() if abs(g) <= 1e-4 * max(1.0, abs(g))]
    driver = []
    if active:
        driver.append("variable bounds: " + ", ".join(active))
    if active_cons:
        driver.append("active constraints: " + ", ".join(active_cons))
    if m_opt is not None and m_opt.get("psa_feed_pressure_bar") is not None and m_opt.get("psa_feed_pressure_requirement_bar"):
        if abs(m_opt["psa_feed_pressure_bar"] - m_opt["psa_feed_pressure_requirement_bar"]) <= 0.05:
            driver.append("PSA feed-pressure requirement kink: PSA feed pressure = "
                          f"{m_opt['psa_feed_pressure_requirement_bar']:g} bar (cho2026nickel p. 6 Table 3), below which "
                          "cracked-gas compression is charged; the optimum pressure is set by this literature requirement")
            limitations.append("Reactor pressure optimum coincides with the lowest pressure that needs no cracked-gas "
                               "compression; it moves with the assumed PSA feed-pressure requirement (alternatives 2.5 and 15 bar "
                               "in separation.yaml) and compressor CAPEX is not costed.")
    feasible = m_opt is not None and all(g >= -1e-7 for g in g_opt.values())
    if not feasible:
        violated = [n for n, g in g_opt.items() if g < -1e-7]
        driver.insert(0, "NO FEASIBLE POINT FOUND - reported point violates: " + ", ".join(violated))
        limitations.insert(0, "The reported point is INFEASIBLE (constraints " + ", ".join(violated) + " violated); it is "
                           "the solver's least-infeasible point, not an optimum. The constraint set may be infeasible "
                           "within the bounds.")
    if not driver:
        driver.append("interior optimum (no bound or constraint active)")

    metric = spec["metric"]
    improvement = None
    if m_opt is not None and base_m is not None:
        d = m_opt[metric] - base_m[metric]
        improvement = {"metric": metric, "optimum": m_opt[metric], "baseline": base_m[metric], "delta": d,
                       "delta_rel": d / abs(base_m[metric]) if base_m[metric] else None,
                       "better": (d < 0) if spec["sense"] == "min" else (d > 0)}
    return {
        "objective": objective, "label": spec["label"], "metric": metric, "sense": spec["sense"], "feasible": feasible,
        "engine": "python_model", "source": "python_model",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision_variables": dv,
        "fixed_inputs": {k: v for k, v in inp_opt.model_dump().items() if k not in names and k != "case_id"},
        "constraints": {"settings": cons, "values_at_optimum": g_opt, "active": active_cons,
                        "definitions": CONSTRAINT_DOCS, "convention": "g >= 0 satisfied"},
        "optimum_inputs": inp_opt.model_dump(),
        "optimum_metrics": _clean(m_opt),
        "baseline_inputs": base_inputs.model_dump(),
        "baseline_metrics": _clean(base_m),
        "improvement": improvement,
        "bound_active": active,
        "driver": "; ".join(driver),
        "model_limitation": limitations,
        "flatness": flat,
        "solver": {"method": method, "success": bool(sol["success"]) and feasible, "feasible": feasible,
                   "success_note": ("success = DE converged within maxiter AND the reported point is feasible; DE stopping at "
                                    "maxiter with a converged SLSQP polish is reported as success=False with the polish status"),
                   "nfev_objective": sol["nfev"],
                   "model_runs": ev.n_model_runs, "model_failures": ev.n_failures, "de_iterations": sol.get("de_nit"),
                   "de_message": sol.get("de_message"), "polish": sol.get("polish"), "best_from": sol["best_from"],
                   "bound_snap": sol.get("bound_snap", []),
                   "seed": seed, "popsize": popsize, "maxiter": maxiter, "wall_time_s": time.perf_counter() - t0},
        "evaluation_options": eval_options or {},
        "limitations": [
            "Python process model (equilibrium cracker, reduced-order PSA); optimum must be re-solved in Aspen Plus "
            "(results/optimisation/aspen_verification.json, coordinator).",
            "LCOH: preliminary capacity-factored CAPEX (no equipment sizing); compressor CAPEX not included.",
            "Carbon intensity: simplified accounting, not an LCA.",
            "Kinetic feasibility (catalyst mass) not constrained (unfinished).",
        ] + limitations,
        "provenance": {"metrics": "python_model", "economic_inputs": "data/economics.yaml (literature/assumption labels)",
                       "emission_factors": "data/environmental.yaml"},
    }


__all__ = ["VARIABLES", "OBJECTIVES", "DEFAULT_CONSTRAINTS", "CONSTRAINT_DOCS", "MODEL_LIMITATIONS",
           "constraint_values", "Evaluator", "minimise", "run", "flatness"]
