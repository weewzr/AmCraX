"""Reusable validation checks returning structured :class:`CheckResult` objects.

Every check computes a numeric metric and compares it with an explicit tolerance. A check never
returns ``pass`` without both. Inputs that do not exist give ``not_run`` with the reason.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable, Optional

from amcrax.schemas import MOLAR_MASS, SimulationResult

PASS, FAIL, NOT_RUN, INFO = "pass", "fail", "not_run", "informational"

#: Atoms per molecule for the AmCraX components.
ELEMENTS: dict[str, dict[str, int]] = {
    "NH3": {"N": 1, "H": 3},
    "H2": {"H": 2},
    "N2": {"N": 2},
    "H2O": {"H": 2, "O": 1},
    "O2": {"O": 2},
}
R_J_molK = 8.314462618


@dataclass
class CheckResult:
    """Outcome of one validation check."""

    id: str
    name: str
    status: str                       # pass | fail | not_run | informational
    metric: str = ""                  # what was measured (name + unit)
    value: Optional[float] = None     # the computed metric
    tolerance: Optional[float] = None
    detail: str = ""
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.status not in (PASS, FAIL, NOT_RUN, INFO):
            raise ValueError(f"invalid status {self.status!r}")
        if self.status == PASS and (self.value is None or self.tolerance is None
                                    or not math.isfinite(self.value)):
            raise ValueError(f"check {self.id}: 'pass' requires a finite computed metric and a tolerance")

    @property
    def ok(self) -> bool:
        return self.status == PASS

    def to_dict(self) -> dict:
        return asdict(self)


def judge(value: Optional[float], tolerance: float) -> str:
    """pass if |value| <= tolerance; fail otherwise (also for nan); not_run if value is None."""
    if value is None:
        return NOT_RUN
    if not math.isfinite(value):
        return FAIL
    return PASS if abs(value) <= tolerance else FAIL


def not_run(id: str, name: str, reason: str, evidence: Iterable[str] = ()) -> CheckResult:
    return CheckResult(id=id, name=name, status=NOT_RUN, detail=reason, evidence=list(evidence))


def _rel(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return 0.0 if scale == 0 else (b - a) / scale


# ------------------------------------------------------------------ stoichiometry / closure
def element_totals(n: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for s, v in n.items():
        for el, k in ELEMENTS.get(s, {}).items():
            out[el] = out.get(el, 0.0) + k * (v or 0.0)
    return out


def check_reaction_stoichiometry(nu: dict[str, float], id: str = "stoich", tol: float = 1e-12) -> CheckResult:
    """Each element must be conserved by the stoichiometric coefficients ``nu``."""
    bal = element_totals(nu)
    worst = max((abs(v) for v in bal.values()), default=0.0)
    return CheckResult(id, "reaction stoichiometry element balance", judge(worst, tol),
                       "max |sum nu_i a_ij| (atoms)", worst, tol, f"element sums {bal}")


def check_element_closure(n_in: dict[str, float], n_out: dict[str, float], id: str = "elements",
                          tol: float = 1e-6) -> CheckResult:
    ei, eo = element_totals(n_in), element_totals(n_out)
    rel = {el: _rel(ei.get(el, 0.0), eo.get(el, 0.0)) for el in sorted(set(ei) | set(eo))}
    worst = max((abs(v) for v in rel.values()), default=0.0)
    return CheckResult(id, "element closure (N, H, O)", judge(worst, tol), "max relative element imbalance",
                       worst, tol, "; ".join(f"{k}: in {ei.get(k, 0):.6g} out {eo.get(k, 0):.6g} kmol/h"
                                             for k in rel))


def check_mass_closure(m_in: float, m_out: float, id: str = "mass", tol: float = 1e-6) -> CheckResult:
    r = _rel(m_in, m_out)
    return CheckResult(id, "mass closure", judge(r, tol), "relative mass imbalance", r, tol,
                       f"in {m_in:.6g} kg/h, out {m_out:.6g} kg/h")


BOUNDARY_IN = ("FEED", "AIR")
BOUNDARY_OUT = ("H2PROD", "STACK")


def _boundary(result: SimulationResult) -> tuple[dict, dict, float, float]:
    n_in: dict[str, float] = {}
    n_out: dict[str, float] = {}
    m_in = m_out = 0.0
    outs = [s for s in BOUNDARY_OUT if s in result.streams] or []
    if "STACK" not in result.streams and "FLUE" in result.streams:
        outs.append("FLUE")
    for sid, acc in [(s, "in") for s in BOUNDARY_IN] + [(s, "out") for s in outs]:
        st = result.streams.get(sid)
        if st is None:
            continue
        tgt = n_in if acc == "in" else n_out
        for c, v in st.component_mole_flow_kmol_h.items():
            tgt[c] = tgt.get(c, 0.0) + (v or 0.0)
        m = st.mass_flow_kg_h
        if m is None:
            m = sum(MOLAR_MASS[c] * (v or 0.0) for c, v in st.component_mole_flow_kmol_h.items())
        if acc == "in":
            m_in += m
        else:
            m_out += m
    return n_in, n_out, m_in, m_out


def simulation_closures(result: SimulationResult, prefix: str, *, tol_mass: float = 1e-6,
                        tol_elem: float = 1e-6, tol_energy: float = 1e-4) -> list[CheckResult]:
    """Mass, element and energy closure of a flowsheet result (plant boundary FEED+AIR -> H2PROD+STACK)."""
    n_in, n_out, m_in, m_out = _boundary(result)
    res = []
    if not n_in or not n_out:
        res.append(not_run(f"{prefix}.mass", "mass closure", "boundary streams missing"))
    else:
        res.append(check_mass_closure(m_in, m_out, f"{prefix}.mass", tol_mass))
        res.append(check_element_closure(n_in, n_out, f"{prefix}.elements", tol_elem))
    e = result.balances.energy_closure_rel
    if e is None:
        res.append(not_run(f"{prefix}.energy", "energy closure", "balances.energy_closure_rel not available"))
    else:
        res.append(CheckResult(f"{prefix}.energy", "energy closure", judge(e, tol_energy),
                               "relative energy imbalance (balances.energy_closure_rel)", float(e), tol_energy,
                               f"in {result.balances.energy_in_kW} kW, out {result.balances.energy_out_kW} kW"))
    return res


def check_nonnegative(result: SimulationResult, id: str = "nonneg", tol: float = 1e-9) -> CheckResult:
    worst = 0.0
    where = ""
    for sid, st in result.streams.items():
        vals = {"mole_flow": st.mole_flow_kmol_h, "mass_flow": st.mass_flow_kg_h,
                **{f"n_{c}": v for c, v in st.component_mole_flow_kmol_h.items()}}
        for k, v in vals.items():
            if v is not None and v < worst:
                worst, where = v, f"{sid}.{k}"
    return CheckResult(id, "non-negative flows", PASS if worst >= -tol else FAIL,
                       "most negative flow (kmol/h or kg/h)", worst, tol, where or "all flows >= 0")


def check_unit_sanity(result: SimulationResult, id: str = "units", tol: float = 1e-6) -> CheckResult:
    """Mole fractions sum to 1, fractions in [0,1], T above absolute zero, P > 0, KPI fractions in [0,1]."""
    problems: list[str] = []
    worst = 0.0
    for sid, st in result.streams.items():
        if st.mole_frac and (st.mole_flow_kmol_h or 0) > 0:
            d = abs(sum(st.mole_frac.values()) - 1.0)
            worst = max(worst, d)
            if d > tol:
                problems.append(f"{sid}: sum(y) - 1 = {d:.2e}")
        for c, y in st.mole_frac.items():
            if y < -tol or y > 1 + tol:
                problems.append(f"{sid}.y_{c} = {y}")
                worst = max(worst, abs(y))
        if st.temperature_C is not None and not (-273.15 < st.temperature_C < 3000):
            problems.append(f"{sid}.T = {st.temperature_C}")
        if st.pressure_bar is not None and st.pressure_bar <= 0:
            problems.append(f"{sid}.P = {st.pressure_bar}")
        if st.vapor_fraction is not None and not (-tol <= st.vapor_fraction <= 1 + tol):
            problems.append(f"{sid}.vf = {st.vapor_fraction}")
    k = result.kpis
    for name in ("nh3_conversion", "h2_purity_mole_frac", "h2_yield_overall", "lhv_efficiency"):
        v = getattr(k, name)
        if v is not None and not (0.0 <= v <= 1.0):
            problems.append(f"kpi.{name} = {v}")
    status = PASS if not problems else FAIL
    return CheckResult(id, "unit / range sanity", status, "max |sum(y) - 1|", worst, tol,
                       "; ".join(problems) if problems else "all stream fractions, T, P, KPI fractions in range")


def check_converged(result: SimulationResult, id: str = "converged") -> CheckResult:
    st = result.status
    v = 0.0 if (st.converged and not st.has_errors) else 1.0
    return CheckResult(id, "converged without errors", PASS if v == 0 else FAIL, "1 if not converged/has errors",
                       v, 0.0, f"converged={st.converged}, has_errors={st.has_errors}, has_warnings={st.has_warnings}")


# ------------------------------------------------------------------ thermodynamic consistency
def check_vant_hoff(lnK: Callable[[float], float], dH_kJ_mol: Callable[[float], float], T_K: Iterable[float],
                    id: str = "vant_hoff", tol: float = 1e-3, h: float = 0.5) -> CheckResult:
    """d lnK / dT = dH / (R T^2): relative deviation of the numerical derivative from the van't Hoff value."""
    worst = 0.0
    at = None
    for T in T_K:
        d_num = (lnK(T + h) - lnK(T - h)) / (2 * h)
        d_vh = dH_kJ_mol(T) * 1000.0 / (R_J_molK * T * T)
        r = abs(d_num - d_vh) / abs(d_vh)
        if r > worst:
            worst, at = r, T
    return CheckResult(id, "van't Hoff consistency of K(T) and dH(T)", judge(worst, tol),
                       "max relative |dlnK/dT - dH/RT^2| / (dH/RT^2)", worst, tol, f"worst at T = {at} K")


def check_vant_hoff_data(T_K: list[float], lnK: list[float], dH_kJ_mol: list[float], id: str = "vant_hoff_data",
                         tol: float = 0.01) -> CheckResult:
    """Integral van't Hoff test on tabulated data: lnK(T2)-lnK(T1) vs int dH/(RT^2) dT.

    dH is taken linear in T between nodes (dH = a + bT), integrated exactly:
    int (a + bT)/(R T^2) dT = [-a/T + b ln T] / R  (exact for constant or linear dH).
    """
    pts = sorted(zip(T_K, lnK, dH_kJ_mol))
    worst = 0.0
    at = None
    for (T1, k1, h1), (T2, k2, h2) in zip(pts, pts[1:]):
        b = (h2 - h1) * 1000 / (T2 - T1)
        a = h1 * 1000 - b * T1
        integ = (a * (1 / T1 - 1 / T2) + b * math.log(T2 / T1)) / R_J_molK
        r = abs((k2 - k1) - integ) / abs(integ)
        if r > worst:
            worst, at = r, (T1, T2)
    return CheckResult(id, "van't Hoff consistency of tabulated lnK and dH", judge(worst, tol),
                       "max relative |dlnK - int dH/RT^2 dT| per interval", worst, tol,
                       f"worst interval {at} K (dH linear between nodes; residual includes dH curvature)")


# ------------------------------------------------------------------ hooks for other modules
def check_optimisation_feasibility(values: dict[str, float], bounds: dict[str, tuple[float, float]],
                                   constraints: Optional[dict[str, tuple[float, str, float]]] = None,
                                   id: str = "opt_feasibility", tol: float = 1e-6) -> CheckResult:
    """Decision variables inside bounds; constraints (value, op, limit) with op in '<=', '>=', '=='."""
    viol = 0.0
    msgs = []
    for k, (lo, hi) in bounds.items():
        v = values.get(k)
        if v is None:
            msgs.append(f"{k} missing")
            viol = max(viol, math.inf)
            continue
        d = max(lo - v, v - hi, 0.0)
        if d > tol:
            msgs.append(f"{k}={v} outside [{lo}, {hi}]")
        viol = max(viol, d)
    for k, (v, op, lim) in (constraints or {}).items():
        d = {"<=": max(v - lim, 0.0), ">=": max(lim - v, 0.0), "==": abs(v - lim)}[op]
        if d > tol:
            msgs.append(f"{k}: {v} {op} {lim} violated")
        viol = max(viol, d)
    return CheckResult(id, "optimisation result feasibility", judge(viol, tol), "max bound/constraint violation",
                       viol, tol, "; ".join(msgs) or "feasible")


def check_economic_consistency(components: dict[str, float], total: float, id: str = "econ_consistency",
                               tol: float = 1e-6) -> CheckResult:
    """LCOH (or cost) components must sum to the total; capital/O&M components must be finite."""
    s = sum(components.values())
    r = _rel(total, s)
    bad = [k for k, v in components.items() if v is None or not math.isfinite(v)]
    status = judge(r, tol) if not bad else FAIL
    return CheckResult(id, "economic components sum to total", status, "relative |sum(components) - total|", r, tol,
                       f"sum {s:.6g} vs total {total:.6g}" + (f"; non-finite: {bad}" if bad else ""))


def check_value(id: str, name: str, value: float, reference: float, tol: float, *, relative: bool = False,
                metric: str = "") -> CheckResult:
    d = (value - reference) / abs(reference) if relative else value - reference
    return CheckResult(id, name, judge(d, tol), metric or ("relative deviation" if relative else "deviation"), d, tol,
                       f"value {value:.6g} vs reference {reference:.6g}")


def check_aspen_verification(doc: dict, id: str = "OPT-ASPEN") -> CheckResult:
    """Judge ``results/optimisation/aspen_verification.json`` by the criterion the file itself states.

    pass = every candidate converged in Aspen AND its max relative deviation over the *primary* metrics
    is within the file's tolerance (the per-candidate ``status`` must agree with that recomputation).
    Secondary metrics (individual duties, minor cost items) are reported in ``detail``, not judged.
    """
    cands = doc.get("candidates") or []
    tol = doc.get("tolerance_relative")
    if not cands or tol is None:
        return CheckResult(id, "optimisation candidates re-solved in Aspen", NOT_RUN,
                           detail="no candidates or no tolerance_relative in file")
    tol = float(tol)
    worst_p, worst_s, bad, inconsistent = (0.0, ""), (0.0, ""), [], []
    for c in cands:
        p = c.get("max_relative_deviation_primary")
        s = c.get("max_relative_deviation_secondary")
        if p is None or not math.isfinite(float(p)):
            bad.append(f"{c.get('id')}: no primary deviation")
            continue
        p = abs(float(p))
        ok = bool(c.get("aspen_converged")) and p <= float(c.get("tolerance", tol))
        if not ok:
            bad.append(f"{c.get('id')}: converged={c.get('aspen_converged')}, primary {p:.4g}")
        if (c.get("status") == PASS) != ok:
            inconsistent.append(str(c.get("id")))
        if p > worst_p[0]:
            worst_p = (p, f"{c.get('id')} {c.get('max_relative_deviation_primary_metric')}")
        if s is not None and math.isfinite(float(s)) and abs(float(s)) > worst_s[0]:
            worst_s = (abs(float(s)), f"{c.get('id')} {c.get('max_relative_deviation_secondary_metric')}")
    status = PASS if not bad and not inconsistent else FAIL
    detail = (f"{len(cands)} candidates, {len(cands) - len(bad)} converged within tolerance on "
              f"{len(doc.get('primary_metrics') or [])} primary metrics; worst primary {worst_p[1]}; "
              f"secondary (not judged, per file criterion) max {worst_s[0]:.4g} ({worst_s[1]})")
    if bad:
        detail += "; failing: " + ", ".join(bad)
    if inconsistent:
        detail += "; per-candidate status inconsistent with recomputation: " + ", ".join(inconsistent)
    return CheckResult(id, "optimisation candidates re-solved in Aspen", status,
                       "max over candidates of max |relative deviation| on primary metrics (Python - Aspen)/Aspen",
                       worst_p[0], tol, detail)


def check_single_objective_feasibility(doc: dict, id: str = "OPT-FEAS", tol: float = 1e-6,
                                       at_bound_tol_rel: float = 1e-3) -> CheckResult:
    """Every reported optimum in ``single_objective.json``: bounds respected, constraints g >= 0 satisfied when
    the result is flagged feasible (an infeasible flag must be backed by a violated constraint), and every
    ``at_bound`` flag consistent with the optimum value (within ``at_bound_tol_rel`` x range)."""
    res = doc.get("results") or []
    if not res:
        return CheckResult(id, "optimisation optimum feasibility", NOT_RUN, detail="no results in file")
    worst, msgs, n_feas, infeasible = 0.0, [], 0, []
    for r in res:
        rid = r.get("id") or r.get("objective")
        dv = r.get("decision_variables") or {}
        vals = {k: float(v["optimum"]) for k, v in dv.items()}
        bounds = {k: (float(v["lower"]), float(v["upper"])) for k, v in dv.items()}
        g = ((r.get("constraints") or {}).get("values_at_optimum") or {})
        cons = {k: (float(v), ">=", 0.0) for k, v in g.items() if v is not None}
        cb = check_optimisation_feasibility(vals, bounds, None, tol=tol)
        cc = check_optimisation_feasibility({}, {}, cons, tol=tol)
        worst = max(worst, cb.value)
        if cb.status != PASS:
            msgs.append(f"{rid}: bounds {cb.detail}")
        if r.get("feasible"):
            n_feas += 1
            worst = max(worst, cc.value)
            if cc.status != PASS:
                msgs.append(f"{rid}: flagged feasible but {cc.detail}")
        else:
            infeasible.append(f"{rid} ({cc.detail})")
            if cc.status == PASS:
                msgs.append(f"{rid}: flagged infeasible but no constraint violated")
                worst = max(worst, math.inf)
        for k, v in dv.items():
            span = float(v["upper"]) - float(v["lower"])
            near = ("lower" if abs(vals[k] - float(v["lower"])) <= at_bound_tol_rel * span else
                    "upper" if abs(vals[k] - float(v["upper"])) <= at_bound_tol_rel * span else None)
            if near != v.get("at_bound"):
                msgs.append(f"{rid}: {k} at_bound={v.get('at_bound')!r} but value {vals[k]:.8g} -> {near!r}")
                worst = max(worst, math.inf)
    detail = (f"{len(res)} reported optima ({n_feas} flagged feasible); bounds and g >= 0 constraints checked, "
              f"at_bound flags consistent")
    if infeasible:
        detail += "; reported as infeasible by the optimiser (not an optimum): " + "; ".join(infeasible)
    if msgs:
        detail += "; problems: " + "; ".join(msgs)
    return CheckResult(id, "optimisation optimum feasibility", judge(worst, tol) if math.isfinite(worst) else FAIL,
                       "max bound / constraint violation over reported optima (constraint units)", worst, tol, detail)
