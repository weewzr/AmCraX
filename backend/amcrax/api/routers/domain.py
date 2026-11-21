"""Domain routers wired to the real AmCraX modules.

Every call into another module is lazy (503 ``module_unavailable`` only when the import really fails) and every
response carries a ``source`` / provenance label plus the module's own assumption / limitation notes.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from amcrax import paths

from .. import store
from ..errors import ApiError, call_flex, jsonable, lazy_attr, lazy_module

router = APIRouter(prefix="/api")

PY = "python_model"


def _read_json(p, code: str, what: str):
    if not p.exists():
        raise ApiError(404, code, f"{what} has not been generated yet", {"file": p.name})
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:  # noqa: BLE001
        raise ApiError(500, "data_unreadable", f"{p.name} is not valid JSON: {str(e)[:200]}")


# ------------------------------------------------------------------ thermo
_EOS = {"ideal": "ideal", "pr": "pr", "peng-rob": "pr", "peng_rob": "pr"}


def _eos(eos: str) -> str:
    k = _EOS.get(eos.lower())
    if k is None:
        raise ApiError(422, "invalid_eos", f"eos '{eos}' not supported; use 'ideal' or 'pr' (alias 'PENG-ROB')", {"allowed": ["ideal", "pr"]})
    return k


def _equilibrium(T_C: float, P_bar: float, eos: str):
    fn = lazy_attr("thermodynamics", "solve_equilibrium")
    return call_flex(fn, T_C + 273.15, P_bar, {"NH3": 1.0}, eos=_eos(eos))


@router.get("/thermo/equilibrium")
def thermo_equilibrium(T_C: float = Query(600.0, ge=0, le=1500), P_bar: float = Query(20.0, gt=0, le=500),
                       eos: str = Query("ideal", description="ideal | pr (alias PENG-ROB)")):
    r = jsonable(_equilibrium(T_C, P_bar, eos))
    T_K = T_C + 273.15
    th = lazy_module("thermodynamics")
    dH = call_flex(th.reaction_enthalpy_kJ_mol, T_K)
    dG = call_flex(th.reaction_gibbs_kJ_mol, T_K)
    return {"T_C": T_C, "P_bar": P_bar, "eos": eos, "basis": "1 mol NH3 feed; reaction NH3 <-> 0.5 N2 + 1.5 H2",
            "source": PY, "result": r,
            "reaction_enthalpy_kJ_mol": dH, "reaction_gibbs_kJ_mol": dG,
            "reaction_basis": "per mol NH3 decomposed, standard state 1 bar; enthalpy > 0 = endothermic",
            "notes": ["Independent NASA-7 thermochemistry (Cantera data) + Gibbs-equilibrium solver; used to validate the Aspen RGibbs block.",
                      "eos 'ideal' neglects fugacity corrections; 'pr' = Peng-Robinson fugacity coefficients."]}


@router.get("/thermo/grid")
def thermo_grid(T_min_C: float = Query(250, ge=0), T_max_C: float = Query(800, le=1500), n_T: int = Query(12, ge=2, le=60),
                P_bar: str = Query("1,5,10,20,30", description="comma separated"), eos: str = Query("ideal")):
    try:
        ps = [float(x) for x in P_bar.split(",") if x.strip()]
    except ValueError:
        raise ApiError(422, "invalid_P_bar", "P_bar must be comma separated numbers")
    if not ps or len(ps) > 10 or T_max_C <= T_min_C:
        raise ApiError(422, "invalid_grid", "Need 1-10 pressures and T_max_C > T_min_C")
    pts = []
    for p in ps:
        for i in range(n_T):
            T = T_min_C + (T_max_C - T_min_C) * i / (n_T - 1)
            r = jsonable(_equilibrium(T, p, eos))
            conv = r.get("conversion") if isinstance(r, dict) else None
            pts.append({"T_C": T, "P_bar": p, "conversion": conv, "result": r})
    return {"eos": eos, "source": PY, "count": len(pts), "points": pts}


# ------------------------------------------------------------------ kinetics / reactor
def _catalysts() -> list[dict]:
    fn = lazy_attr("kinetics", "list_catalysts")
    return jsonable(call_flex(fn))


def _check_catalyst(cid: Optional[str]) -> dict:
    cats = _catalysts()
    ids = [c.get("id") for c in cats]
    if not cid:
        raise ApiError(422, "missing_parameter", "catalyst_id is required", {"allowed": ids})
    for c in cats:
        if c.get("id") == cid:
            return c
    raise ApiError(422, "invalid_catalyst", f"Unknown catalyst_id '{cid}'", {"allowed": ids})


@router.get("/kinetics/catalysts")
def kinetics_catalysts():
    cats = _catalysts()
    return {"count": len(cats), "source": "literature", "catalysts": cats,
            "notes": ["Rate laws are literature models (see each source citation); validity ranges and limitations are listed per catalyst.",
                      "Evaluating them at conditions outside the validity range is an extrapolation and is labelled python_model."]}


class PFRRequest(BaseModel):
    catalyst_id: str = Field(..., description="id from GET /api/kinetics/catalysts")
    catalyst_mass_kg: float = Field(..., gt=0, le=1e6, alias="W_kg")
    T_C: float = Field(600.0, ge=100, le=1200, description="inlet temperature")
    P_bar: float = Field(20.0, gt=0, le=200, description="inlet pressure")
    feed: Optional[dict[str, float]] = Field(None, description="feed kmol/h by species, default {NH3: 100}")
    feed_nh3_kmol_h: Optional[float] = Field(None, gt=0, description="shortcut for feed={'NH3': x}")
    mode: Literal["isothermal", "adiabatic", "heated", "external"] = "isothermal"
    T_wall_C: Optional[float] = Field(None, description="heated/external mode: wall temperature")
    U_W_m2K: Optional[float] = Field(None, gt=0, description="heated/external mode: overall heat-transfer coefficient")
    approach_factor: Optional[bool] = Field(None, description="multiply irreversible rate laws by (1-Q/Kp); null = model default")
    keq_basis: Literal["amcrax_thermo", "published"] = "amcrax_thermo"
    pressure_drop: bool = True
    n_tubes: int = Field(1, ge=1, le=10000)
    eps_b: Optional[float] = Field(None, gt=0, lt=1)
    dp_m: Optional[float] = Field(None, gt=0)
    tube_inner_diameter_m: Optional[float] = Field(None, gt=0)
    n_points: int = Field(101, ge=11, le=1001)

    model_config = {"populate_by_name": True, "extra": "forbid"}


@router.post("/reactor/pfr")
def reactor_pfr(req: PFRRequest):
    cat = _check_catalyst(req.catalyst_id)
    fn = lazy_attr("reactor", "simulate_pfr")
    feed = req.feed or {"NH3": req.feed_nh3_kmol_h or 100.0}
    if "NH3" not in feed or feed["NH3"] <= 0 or any(v < 0 for v in feed.values()):
        raise ApiError(422, "invalid_feed", "feed must contain NH3 > 0 and non-negative flows (kmol/h)", {"feed": feed})
    mode = "external" if req.mode == "heated" else req.mode
    if mode == "external" and (req.T_wall_C is None or req.U_W_m2K is None):
        raise ApiError(422, "missing_parameter", "mode 'heated' requires T_wall_C and U_W_m2K")
    kw: dict[str, Any] = dict(T_in_C=req.T_C, P_in_bar=req.P_bar, feed_kmol_h=feed, mode=mode, T_wall_C=req.T_wall_C,
                              U_W_m2K=req.U_W_m2K, approach_factor=req.approach_factor, keq_basis=req.keq_basis,
                              pressure_drop=req.pressure_drop, n_tubes=req.n_tubes, n_points=req.n_points)
    for k in ("eps_b", "dp_m", "tube_inner_diameter_m"):
        if getattr(req, k) is not None:
            kw[k] = getattr(req, k)
    res = jsonable(call_flex(fn, req.catalyst_id, req.catalyst_mass_kg, **kw))
    eq = None
    try:
        eq_r = jsonable(_equilibrium(req.T_C, req.P_bar, "ideal"))
        eq = {"T_C": req.T_C, "P_bar": req.P_bar, "conversion": eq_r.get("conversion"), "basis": "pure NH3 feed, ideal gas, inlet T and P",
              "note": "Local equilibrium conversion along the bed is res.X_eq_local (varies with T and P)."}
    except ApiError:
        pass
    outlet = res.get("outlet") or {}
    warnings = []
    reached = outlet.get("W_reached_kg") if isinstance(outlet, dict) else None
    if reached is not None and reached < req.catalyst_mass_kg * 0.999:
        warnings.append(f"Integration stopped at {reached:.4g} kg of the requested {req.catalyst_mass_kg:g} kg (pressure fell to the model floor); increase n_tubes, tube diameter or particle size, or set pressure_drop=false.")
    return {"source": PY, "provenance": PY, "catalyst": {"id": cat.get("id"), "label": cat.get("label"), "source": cat.get("source"),
                                                          "validity": cat.get("validity"), "provenance": cat.get("provenance")},
            "request": json.loads(req.model_dump_json(by_alias=False)),
            "profiles": {k: res.get(k) for k in ("W_kg", "conversion", "T_K", "P_bar", "y", "rate_mol_per_kgcat_s", "X_eq_local",
                                                "approach_to_equilibrium", "Q_over_K", "residence_time_s")},
            "warnings": warnings, "outlet_summary": {**outlet, "conversion": res.get("conversion")} if isinstance(outlet, dict) else outlet,
            "equilibrium_limit": eq,
            "GHSV_h_inv": res.get("GHSV_h_inv"), "bed_volume_m3": res.get("bed_volume_m3"),
            "limitations": list(res.get("assumptions") or []) + [f"[catalyst] {x}" for x in (cat.get("limitations") or [])],
            "result": res}


@router.get("/reactor/catalyst-mass")
def reactor_catalyst_mass(catalyst_id: str = Query(...), T_C: float = Query(600.0, ge=100, le=1200),
                          P_bar: float = Query(20.0, gt=0, le=200),
                          target: Optional[float] = Query(None, gt=0, lt=1, description="target NH3 conversion"),
                          fraction_of_equilibrium: Optional[float] = Query(None, gt=0, lt=1),
                          mode: Literal["isothermal", "adiabatic"] = "isothermal",
                          pressure_drop: bool = True, n_tubes: int = Query(1, ge=1, le=10000)):
    cat = _check_catalyst(catalyst_id)
    if (target is None) == (fraction_of_equilibrium is None):
        raise ApiError(422, "invalid_target", "give exactly one of target (conversion) or fraction_of_equilibrium")
    fn = lazy_attr("reactor", "catalyst_mass_for_conversion")
    W = call_flex(fn, catalyst_id, target, fraction_of_equilibrium=fraction_of_equilibrium, T_in_C=T_C, P_in_bar=P_bar, mode=mode, pressure_drop=pressure_drop, n_tubes=n_tubes)
    Wj = jsonable(W)
    warn = [] if Wj is not None else ["Target not reachable with these settings (null): the model returned no finite catalyst mass; try pressure_drop=false, more n_tubes, a lower target or a higher temperature."]
    return {"source": PY, "provenance": PY, "catalyst_id": catalyst_id, "T_C": T_C, "P_bar": P_bar, "mode": mode,
            "target_conversion": target, "fraction_of_equilibrium": fraction_of_equilibrium,
            "catalyst_mass_kg": Wj, "reachable": Wj is not None, "pressure_drop": pressure_drop, "n_tubes": n_tubes, "warnings": warn, "basis": "100 kmol/h NH3 feed (reactor.BASELINE_FEED_kmol_h) unless the model states otherwise",
            "catalyst_source": cat.get("source"),
            "notes": ["1-D pseudo-homogeneous PFR; no internal/external diffusion limitation, kinetics may be extrapolated beyond the fitted range."]
            + [f"[catalyst] {x}" for x in (cat.get("limitations") or [])]}


# ------------------------------------------------------------------ analyses on a stored case
@router.get("/heat-integration/{case_id}")
def heat_integration(case_id: str, dT_min_K: float = Query(20.0, gt=0, le=200)):
    res = store.get(case_id)
    fn = lazy_attr("heat_integration", "analyse")
    return {"case_id": case_id, "dT_min_K": dT_min_K, "source": PY, "input_source": res.source.value,
            "result": jsonable(call_flex(fn, res, dT_min_K=dT_min_K))}


# ------------------------------------------------------------------ economics
def _assumptions(overrides: dict[str, Any]):
    mod = lazy_module("economics")
    unknown = sorted(set(overrides) - set(mod.EconomicAssumptions.model_fields))
    if unknown:
        raise ApiError(422, "invalid_overrides", f"Unknown economic assumption(s): {unknown}",
                       {"allowed": list(mod.EconomicAssumptions.model_fields)})
    try:
        return mod.EconomicAssumptions(**overrides)
    except Exception as e:  # noqa: BLE001
        raise ApiError(422, "invalid_overrides", f"Invalid economic overrides: {str(e)[:400]}",
                       {"allowed": list(mod.EconomicAssumptions.model_fields)})


class LCOHRequest(BaseModel):
    case_id: str
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.post("/economics/lcoh")
def economics_lcoh(req: LCOHRequest):
    res = store.get(req.case_id)
    fn = lazy_attr("economics", "compute_lcoh")
    out = jsonable(call_flex(fn, res, _assumptions(req.overrides)))
    return {"case_id": req.case_id, "overrides": req.overrides, "source": PY, "input_source": res.source.value, "result": out,
            "notes": out.get("notes", []) if isinstance(out, dict) else []}


@router.get("/economics/defaults")
def economics_defaults():
    mod = lazy_module("economics")
    d = jsonable(call_flex(mod.load_economics_data))
    return {"source": "literature", "defaults": d.get("defaults"), "cost_basis": d.get("cost_basis"),
            "capex_references": d.get("capex_references"), "equipment_shares": d.get("equipment_shares"),
            "literature_lcoh": d.get("literature_lcoh"), "schema": d.get("schema"),
            "assumption_fields": list(mod.EconomicAssumptions.model_fields),
            "notes": ["Defaults come from backend/amcrax/data/economics.yaml; each entry carries its citation or is marked as an assumption."]}


class CaseOverrides(BaseModel):
    case_id: str
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.post("/economics/sensitivity")
def economics_sensitivity(req: CaseOverrides):
    res = store.get(req.case_id)
    fn = lazy_attr("economics", "lcoh_sensitivity")
    bars = jsonable(call_flex(fn, res, _assumptions(req.overrides)))
    bars = sorted(bars, key=lambda b: -abs((b.get("lcoh_at_high") or 0) - (b.get("lcoh_at_low") or 0)))
    return {"case_id": req.case_id, "source": PY, "input_source": res.source.value, "rows": bars, "count": len(bars),
            "notes": ["One-at-a-time variation of each input between its low and high value (source_of_range per row); sorted by swing."]}


@router.get("/economics/price-curve")
def economics_price_curve(case_id: str, min: float = Query(200, ge=0), max: float = Query(1000, gt=0), n: int = Query(9, ge=2, le=100),
                          target_lcoh: Optional[float] = Query(None, gt=0, description="USD/kg H2 for the break-even ammonia price")):
    if max <= min:
        raise ApiError(422, "invalid_range", "max must exceed min")
    res = store.get(case_id)
    mod = lazy_module("economics")
    prices = [min + (max - min) * i / (n - 1) for i in range(n)]
    a = _assumptions({})
    pts = call_flex(mod.lcoh_vs_ammonia_price, res, a, prices)
    out = {"case_id": case_id, "source": PY, "input_source": res.source.value, "unit_price": "USD/t NH3", "unit_lcoh": "USD/kg H2",
           "points": [{"nh3_price_USD_per_t": p, "lcoh_USD_per_kg": v} for p, v in pts]}
    be: dict[str, Any] = {}
    if target_lcoh is not None:
        be[str(target_lcoh)] = call_flex(mod.breakeven_ammonia_price, res, a, target_lcoh)
    out["breakeven"] = [{"target_lcoh_USD_per_kg": float(k), "nh3_price_USD_per_t": v} for k, v in be.items()]
    if target_lcoh is None:
        out["breakeven"] = None
        out["breakeven_note"] = ("No target LCOH supplied and amcrax.economics defines no default target, so no break-even is reported "
                                 "(null). Pass target_lcoh (USD/kg H2).")
    out["notes"] = ["Break-even = ammonia price at which LCOH equals target_lcoh_USD_per_kg (null if outside the searched range). "
                    "Pass target_lcoh to obtain it."]
    return jsonable(out)


# ------------------------------------------------------------------ environment
class CarbonRequest(BaseModel):
    case_id: str
    scenario: str = "grey"
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.post("/environment/carbon-intensity")
def environment_ci(req: CarbonRequest):
    res = store.get(req.case_id)
    fn = lazy_attr("environmental", "carbon_intensity")
    out = jsonable(call_flex(fn, res, req.scenario, **req.overrides))
    return {"case_id": req.case_id, "scenario": req.scenario, "source": PY, "input_source": res.source.value, "result": out,
            "notes": out.get("notes", []) if isinstance(out, dict) else []}


@router.get("/environment/scenarios")
def environment_scenarios(case_id: str = "baseline"):
    res = store.get(case_id)
    fn = lazy_attr("environmental", "compare_scenarios")
    out = jsonable(call_flex(fn, res))
    return {"case_id": case_id, "source": PY, "input_source": res.source.value, "result": out,
            "notes": out.get("notes", []) if isinstance(out, dict) else []}


@router.get("/environment/factors")
def environment_factors():
    mod = lazy_module("environmental")
    f = jsonable(call_flex(mod.load_factors))
    return {"source": "literature", "factors": f,
            "notes": ["Emission factors from backend/amcrax/data/environmental.yaml with their sources and verification flags; "
                      "simplified accounting, NOT a life-cycle assessment."]}


# ------------------------------------------------------------------ separation
class SepRequest(BaseModel):
    case_id: str
    membrane_recoveries: Optional[list[float]] = None
    membrane_T_K: Optional[float] = None
    permeate_pressure_bar: Optional[float] = None
    product_pressure_bar: Optional[float] = None
    compressor_eta: Optional[float] = None


@router.post("/separation/compare")
def separation_compare(req: SepRequest):
    res = store.get(req.case_id)
    fn = lazy_attr("separation", "compare_purification")
    kw = {k: v for k, v in req.model_dump().items() if k != "case_id" and v is not None}
    if "membrane_recoveries" in kw:
        kw["membrane_recoveries"] = tuple(kw["membrane_recoveries"])
    out = jsonable(call_flex(fn, res, **kw))
    return {"case_id": req.case_id, "source": PY, "input_source": res.source.value, "model": "reduced-order model", "result": out,
            "notes": ["Reduced-order purification models; the PSA is a literature operating point, the membrane ideal Sieverts flux."]}


class MembraneRequest(BaseModel):
    feed_kmol_h: dict[str, float] = Field(default_factory=lambda: {"H2": 150.0, "N2": 50.0})
    feed_pressure_bar: float = Field(20.0, gt=0, le=200)
    area_m2: Optional[float] = Field(None, gt=0)
    target_recovery: Optional[float] = Field(None, gt=0, lt=1)
    permeate_pressure_bar: Optional[float] = Field(None, gt=0)
    T_K: Optional[float] = Field(None, gt=0)
    permeability: Optional[str] = None
    thickness_m: Optional[float] = Field(None, gt=0)
    flux_multiplier: float = Field(1.0, gt=0)


@router.post("/separation/membrane")
def separation_membrane(req: MembraneRequest):
    mod = lazy_module("separation")
    area = req.area_m2
    if area is None and req.target_recovery is None:
        raise ApiError(422, "missing_parameter", "give area_m2 or target_recovery")
    if area is None:
        area = call_flex(mod.area_for_recovery, req.feed_kmol_h, req.target_recovery, req.feed_pressure_bar,
                         req.permeate_pressure_bar, req.T_K)
        if area is None:
            raise ApiError(422, "recovery_unreachable", "target_recovery is not reachable with the model's driving force")
    out = call_flex(mod.membrane_separator, req.feed_kmol_h, area, req.feed_pressure_bar, req.permeate_pressure_bar, req.T_K,
                    permeability=req.permeability, thickness_m=req.thickness_m, flux_multiplier=req.flux_multiplier)
    return {"source": PY, "model": "reduced-order model", "area_m2": area, "result": jsonable(out),
            "notes": ["Ideal Sieverts-law Pd-Ag membrane with literature permeability; not a designed or validated unit."]}


class PSARequest(BaseModel):
    feed_kmol_h: dict[str, float] = Field(default_factory=lambda: {"H2": 150.0, "N2": 50.0})
    feed_pressure_bar: float = Field(20.0, gt=0, le=200)
    tailgas_pressure_bar: Optional[float] = Field(None, gt=0)
    target_purity: Optional[float] = Field(None, gt=0, le=1)
    basis: str = "cho2026_5A"
    h2_recovery: Optional[float] = Field(None, gt=0, le=1)
    feed_temperature_K: float = Field(313.15, gt=0)
    compressor_eta: Optional[float] = Field(None, gt=0, le=1)


@router.post("/separation/psa")
def separation_psa(req: PSARequest):
    fn = lazy_attr("separation", "psa_performance")
    d = req.model_dump()
    feed, p = d.pop("feed_kmol_h"), d.pop("feed_pressure_bar")
    out = call_flex(fn, feed, p, **{k: v for k, v in d.items() if v is not None})
    return {"source": PY, "model": "reduced-order model", "result": jsonable(out),
            "notes": ["PSA performance is a literature operating point applied as a split, not a designed PSA."]}


# ------------------------------------------------------------------ optimisation / scenarios
OPT_TIMEOUT_S = 20.0
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="amcrax-opt")


class OptRequest(BaseModel):
    model_config = {"extra": "allow"}
    objective: str = Field("min_lcoh", description="min_lcoh | max_lhv_efficiency | min_specific_heat | max_h2_production | max_conversion")
    bounds: Optional[dict[str, list[float]]] = None
    constraints: Optional[dict[str, Any]] = None
    method: Optional[str] = Field(None, description="'de' (default) or 'grid'; both answer in about 5 s on the Python model")
    case_id: Optional[str] = Field(None, description="optional stored case whose inputs define the base case")


@router.post("/optimisation/run")
def optimisation_run(req: OptRequest):
    fn = lazy_attr("optimisation", "run")
    kw = req.model_dump(exclude_none=True)
    case_id = kw.pop("case_id", None)
    if case_id:
        kw["base_result"] = store.get(case_id)
    fut = _POOL.submit(call_flex, fn, **kw)
    try:
        res = fut.result(timeout=OPT_TIMEOUT_S)
    except FutureTimeout:
        raise ApiError(504, "timeout", f"optimisation did not finish within {OPT_TIMEOUT_S:g} s; try method 'grid' or fewer variables",
                       {"timeout_s": OPT_TIMEOUT_S})
    req_echo = {k: v for k, v in kw.items() if k != "base_result"}
    if case_id:
        req_echo["case_id"] = case_id
    return {"source": PY, "request": req_echo, "result": jsonable(res)}


def _opt_file(name: str):
    p = paths.RESULTS_OPTIMISATION / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return None


@router.get("/optimisation/results")
def optimisation_results():
    parts = {"single_objective": "single_objective.json", "pareto": "pareto.json", "objective_conflicts": "objective_conflicts.json",
             "candidates": "candidates_for_aspen.json", "aspen_verification": "aspen_verification.json"}
    out: dict[str, Any] = {k: _opt_file(v) for k, v in parts.items()}
    d = paths.RESULTS_OPTIMISATION
    out["files"] = sorted(p.name for p in d.glob("*") if p.is_file()) if d.exists() else []
    out["available"] = {k: out[k] is not None for k in parts}
    av = out["aspen_verification"]
    if isinstance(av, dict):
        cands = [c for c in av.get("candidates", []) if isinstance(c, dict)]
        out["aspen_verification_summary"] = {
            "criterion": av.get("criterion"), "tolerance_relative": av.get("tolerance_relative"),
            "primary_metrics": av.get("primary_metrics"), "source": "aspen_plus_v15",
            "candidates": [{"id": c.get("id"), "label": c.get("label"), "case_id": c.get("case_id"), "status": c.get("status"),
                            "aspen_converged": c.get("aspen_converged"),
                            "max_relative_deviation_primary": c.get("max_relative_deviation_primary"),
                            "max_relative_deviation_primary_metric": c.get("max_relative_deviation_primary_metric"),
                            "tolerance": c.get("tolerance")} for c in cands],
            "counts": {s: sum(1 for c in cands if c.get("status") == s) for s in sorted({str(c.get("status")) for c in cands})}}
    else:
        out["aspen_verification_summary"] = None
    grid = d / "design_grid.csv"
    par = out["pareto"] if isinstance(out["pareto"], dict) else {}
    meta: dict[str, Any] = {"available": grid.exists(), "file": "design_grid.csv", "data_endpoint": "/api/data/optimisation/design_grid",
                            "n_grid_points": par.get("n_grid_points"), "n_feasible": par.get("n_feasible")}
    if grid.exists():
        meta["bytes"] = grid.stat().st_size
        try:
            with grid.open(encoding="utf-8-sig") as f:
                meta["columns"] = f.readline().strip().split(",")
                meta["rows"] = sum(1 for _ in f)
        except OSError:
            pass
    out["design_grid"] = meta
    out["source"] = "python_model (aspen_verification: aspen_plus_v15 when present)"
    return jsonable(out)


class AnalyseRequest(BaseModel):
    model_config = {"extra": "forbid"}
    scenario_ids: list[str] = Field(default_factory=list, description="empty = all process scenarios")
    nh3_origin: Optional[Literal["grey", "blue", "green"]] = None
    heat_source: Optional[str] = Field(None, description="ammonia | natural_gas | electric (or the scenarios.json overlay names)")
    grid: Optional[str] = None
    price_policy: Optional[Literal["sourced", "base"]] = None
    prefer_aspen: Optional[bool] = None
    include_overlays: Optional[bool] = Field(None, description="include the origin x heat-source overlay table per scenario (default true)")
    overlays: Optional[dict[str, Any]] = Field(None, description="legacy: dict with any of nh3_origin, heat_source, grid, price_policy")


@router.post("/scenarios/analyse")
def scenarios_analyse(req: AnalyseRequest):
    fn = lazy_attr("scenarios", "compare")
    kw: dict[str, Any] = {k: v for k, v in (req.overlays or {}).items() if k in ("nh3_origin", "heat_source", "grid", "price_policy")}
    for k in ("nh3_origin", "heat_source", "grid", "price_policy", "prefer_aspen"):
        if getattr(req, k) is not None:
            kw[k] = getattr(req, k)
    if req.include_overlays is not None:
        kw["overlays"] = req.include_overlays
    ids = req.scenario_ids or None
    return {"source": PY, "request": {"scenario_ids": req.scenario_ids, **kw}, "result": jsonable(call_flex(fn, ids, **kw))}


@router.get("/scenarios/comparison")
def scenarios_comparison():
    return _read_json(paths.RESULTS_SIMULATIONS / "scenario_comparison.json", "scenario_comparison_not_found",
                      "results/simulations/scenario_comparison.json")


# ------------------------------------------------------------------ validation / references / traceability / figures
@router.get("/validation")
def validation():
    return _read_json(paths.RESULTS_VALIDATION / "validation_matrix.json", "validation_not_found",
                      "results/validation/validation_matrix.json")


@router.get("/validation/summary")
def validation_summary():
    d = _read_json(paths.RESULTS_VALIDATION / "validation_matrix.json", "validation_not_found",
                   "results/validation/validation_matrix.json")
    items = d if isinstance(d, list) else (d.get("items") or d.get("matrix") or d.get("checks") or [])
    by: dict[str, dict[str, int]] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        cat = str(it.get("model_component") or "all")
        st = str(it.get("status") or it.get("result") or "unknown")
        by.setdefault(cat, {})[st] = by.setdefault(cat, {}).get(st, 0) + 1
    tot: dict[str, int] = {}
    for c in by.values():
        for s, n in c.items():
            tot[s] = tot.get(s, 0) + n
    meta = {k: v for k, v in d.items() if not isinstance(v, (list, dict))} if isinstance(d, dict) else {}
    return {"count": len(items), "by_status": tot, "by_category": by, "meta": meta, "file_summary": d.get("summary") if isinstance(d, dict) else None, "source": "results/validation/validation_matrix.json"}


@router.get("/references")
def references():
    return _read_json(paths.RESEARCH_DIR / "references.json", "references_not_found", "research/references.json")


@router.get("/traceability")
def traceability():
    return _read_json(paths.RESEARCH_DIR / "traceability.json", "traceability_not_found", "research/traceability.json")


@router.get("/figures")
def figures():
    d = paths.RESULTS_FIGURES
    fs = sorted(d.glob("*.png")) if d.exists() else []
    return {"count": len(fs), "figures": [{"name": f.name, "url": f"/figures/{f.name}", "size_bytes": f.stat().st_size} for f in fs]}


