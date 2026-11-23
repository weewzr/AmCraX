"""Hydrogen purification study models (workstream P): ISO 14687 evaluation, PSA recovery-purity relation,
membrane with finite N2 selectivity, configuration mass balances and costs.

Everything here is a reduced-order model. None of it is an adsorption-cycle simulation or a membrane-module design.
Additive to amcrax.separation: no existing function or default result is changed.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

from .compression import compression_power_kW
from .membrane import permeance, sieverts_flux
from .params import params

# --------------------------------------------------------------------------------------------------
# 1. Standards (ISO 14687:2019, Tables 2-4). Values transcribed from the standard text (full text of the
#    published edition as reproduced in a public standards-body consultation document, accessed 23 Nov 2026).
# --------------------------------------------------------------------------------------------------
ISO_SOURCE = ("ISO 14687:2019 Hydrogen fuel quality - Product specification, first edition 2019-11; Table 2 (grade D), "
              "Table 3 (grade E), Table 4 (grades A-C); text read from https://consultations.standards.govt.nz/"
              "draft-standards/hydrogen-standards-pc/user_uploads/dz-14687.pdf, accessed 2026-11-23")

# limits in umol/mol (ppm, mole basis) unless 'fraction'
GRADES: dict[str, dict] = {
    "D": {
        "name": "ISO 14687:2019 Type I/II grade D (PEM fuel cell road vehicles)",
        "table": "Table 2",
        "index_min_pct": 99.97, "total_non_h2_max_ppm": 300.0,
        "limits_ppm": {"H2O": 5.0, "THC_ex_CH4": 2.0, "CH4": 100.0, "O2": 5.0, "He": 300.0, "N2": 300.0, "Ar": 300.0,
                       "CO2": 2.0, "CO": 0.2, "S_total": 0.004, "HCHO": 0.2, "HCOOH": 0.2, "NH3": 0.1,
                       "halogenated": 0.05},
        "other": {"particulate_mg_per_kg": 1.0, "CO_HCHO_HCOOH_sum_ppm": 0.2},
    },
    "E3": {
        "name": "ISO 14687:2019 Type I grade E category 3 (PEM stationary, gaseous hydrogen)",
        "table": "Table 3",
        "index_min_pct": 99.9, "total_non_h2_max_ppm": 1000.0,
        "limits_ppm": {"THC_ex_CH4": 2.0, "CH4": 100.0, "O2": 50.0, "N2+Ar+He": 1000.0, "CO2": 2.0, "CO": 0.2,
                       "S_total": 0.004, "HCHO": 0.2, "HCOOH": 0.2, "NH3": 0.1, "halogenated": 0.05},
        "other": {"water": "non-condensing at any ambient conditions (site specific, not evaluated)",
                  "particulate_mg_per_kg": 1.0},
    },
    "B": {
        "name": "ISO 14687:2019 Type I grade B (Table 4, applications other than PEM fuel cells), used here as the "
                "industrial 99.9 % hydrogen specification",
        "table": "Table 4",
        "index_min_pct": 99.9, "total_non_h2_max_ppm": 1000.0,
        "limits_ppm": {},
        "other": {"note": "Only the hydrogen fuel index (99.90 %) and total gases (1000 umol/mol) are used. Per-species "
                          "rows of Table 4 (N2 400, O2 100, total hydrocarbons 100 umol/mol and others) are printed "
                          "in a column layout that the text extraction could not assign to a grade with certainty, so "
                          "they are NOT applied and are listed as not evaluated."},
    },
    "A": {
        "name": "ISO 14687:2019 Type I grade A (Table 4, gaseous hydrogen for combustion engines and other "
                "non-PEM uses)",
        "table": "Table 4",
        "index_min_pct": 98.0, "total_non_h2_max_ppm": 20000.0,
        "limits_ppm": {},
        "other": {"note": "Combined water, oxygen, nitrogen and argon at most 1.9 % (19 000 umol/mol) per Table 4 "
                          "footnote b; other rows not applied."},
    },
}

# Contaminants a cracked-gas stream can contain in this model. Everything else in a grade is 'not evaluated'.
MODELLED_SPECIES = ("NH3", "N2", "H2O")


def evaluate_product(y_ppm: dict[str, float], grade: str, *, h2_frac: Optional[float] = None,
                     nh3_basis: str = "computed") -> dict:
    """Evaluate a product composition (mole fractions of non-H2 species given as ppm, mole basis) against a grade.

    Overall purity and each individual contaminant limit are checked separately. 'meets_within_model_scope'
    is true only if the hydrogen index, the total non-H2 limit and every modelled contaminant limit pass;
    unmodelled contaminants of the grade are returned in 'not_evaluated'.
    """
    G = GRADES[grade]
    nonh2_ppm = sum(y_ppm.get(s, 0.0) for s in MODELLED_SPECIES)
    index_pct = 100.0 - nonh2_ppm / 1e4 if h2_frac is None else 100.0 * h2_frac
    checks = []
    checks.append({"item": "hydrogen fuel index", "value": index_pct, "limit": G["index_min_pct"], "unit": "% min",
                   "pass": index_pct >= G["index_min_pct"] - 1e-12, "kind": "overall"})
    checks.append({"item": "total non-hydrogen gases (modelled species)", "value": nonh2_ppm,
                   "limit": G["total_non_h2_max_ppm"], "unit": "umol/mol max",
                   "pass": nonh2_ppm <= G["total_non_h2_max_ppm"] + 1e-12, "kind": "overall"})
    lim = G["limits_ppm"]
    evaluated = set()
    for sp in MODELLED_SPECIES:
        key = sp if sp in lim else None
        if sp == "N2" and "N2" not in lim and "N2+Ar+He" in lim:
            key = "N2+Ar+He"  # N2 only is modelled, so this is a lower bound on the sum
        if key is None:
            continue
        evaluated.add(key)
        v = y_ppm.get(sp, 0.0)
        c = {"item": sp if key == sp else f"{sp} (counted in {key}; Ar, He not modelled)", "value": v,
             "limit": lim[key], "unit": "umol/mol max", "pass": v <= lim[key] + 1e-12, "kind": "contaminant"}
        if sp == "NH3":
            c["value_basis"] = nh3_basis
        checks.append(c)
    not_eval = [k for k in lim if k not in evaluated]
    not_eval += [k for k in G["other"] if k not in ("note",)]
    if "note" in G["other"]:
        not_eval.append("per-species rows not applied (see grade note)")
    modelled_missing = [sp for sp in MODELLED_SPECIES if sp not in lim and sp != "N2"]
    return {"grade": grade, "grade_name": G["name"], "source": ISO_SOURCE, "checks": checks,
            "all_modelled_pass": all(c["pass"] for c in checks), "not_evaluated": not_eval,
            "modelled_species_without_limit_in_grade": modelled_missing,
            "meets_within_model_scope": all(c["pass"] for c in checks)}


# --------------------------------------------------------------------------------------------------
# 2. PSA reduced-order recovery-purity relation (NOT an adsorption cycle simulation)
# --------------------------------------------------------------------------------------------------
PSA_LABEL = ("reduced-order mass-balance relation anchored on published PSA operating points; "
             "not an adsorption-cycle simulation (no isotherms, no bed dynamics)")


def psa_tail_h2_fraction_from_point(feed: dict[str, float], recovery: float, purity: float) -> float:
    """Tail-gas H2 mole fraction implied by a published (recovery, purity) pair applied to a feed.

    Non-H2 product impurity is N2; NH3 and H2O go entirely to tail (existing AmCraX assumption).
    """
    h2 = feed["H2"]
    h2p = recovery * h2
    n2p = min(h2p * (1 - purity) / purity, feed.get("N2", 0.0))
    tail_other = sum(v for k, v in feed.items() if k != "H2") - n2p
    h2t = h2 - h2p
    return h2t / (h2t + tail_other)


def psa_recovery_at_purity(feed: dict[str, float], purity: float, y_tail_h2: float) -> float:
    """H2 recovery for a product purity when the tail-gas H2 mole fraction is held at y_tail_h2.

    Mass balance only: tail non-H2 = feed non-H2 - product N2; tail H2 = tail_other * y/(1-y).
    This is a LOWER BOUND on the purity penalty: in a real PSA, tighter purity needs more purge or lower
    adsorption throughput, so the tail H2 fraction rises with purity and recovery falls faster than shown.
    """
    h2 = feed["H2"]
    other = sum(v for k, v in feed.items() if k != "H2")
    # product: x = H2 product; n2p = x (1-p)/p ; tail_other = other - n2p ; tail_h2 = h2 - x = tail_other*y/(1-y)
    # h2 - x = (other - x q) * k with q = (1-p)/p, k = y/(1-y)
    q = (1 - purity) / purity
    k = y_tail_h2 / (1 - y_tail_h2)
    x = (h2 - other * k) / (1 - q * k)
    n2p = x * q
    if n2p > feed.get("N2", 0.0):  # product N2 cannot exceed feed N2
        x = (h2 - (other - feed.get("N2", 0.0)) * k)
    return max(0.0, min(1.0, x / h2))


def psa_split(feed: dict[str, float], recovery: float, purity: float) -> tuple[dict, dict]:
    """Product and tail flows (kmol/h) for given recovery and purity (N2 is the product impurity)."""
    h2p = recovery * feed["H2"]
    n2p = min(h2p * (1 - purity) / purity, feed.get("N2", 0.0))
    prod = {"H2": h2p, "N2": n2p}
    tail = {k: v - prod.get(k, 0.0) for k, v in feed.items()}
    return prod, tail


# --------------------------------------------------------------------------------------------------
# 3. Pd-alloy membrane with hydrogen depletion and finite H2/N2 ideal selectivity
# --------------------------------------------------------------------------------------------------
def membrane_with_leakage(feed_kmol_h: dict[str, float], area_m2: float, P_feed_bar: float, P_perm_bar: float,
                          T_K: float, *, alpha_H2_N2: float = math.inf, permeability: str | None = None,
                          thickness_m: float | None = None, flux_multiplier: float = 1.0, n: float = 0.5,
                          n_profile: int = 2) -> dict:
    """Integrate H2 (Sieverts) and N2 (linear, finite selectivity) along the retentate side.

    Ideal selectivity alpha is defined as J_H2/J_N2 for single gases at a transmembrane pressure difference of
    1 bar with vacuum permeate (the usual lab convention). N2 flux = (J_H2,ref/alpha/dP_ref) * (p_N2,ret - p_N2,perm),
    with p_N2,perm taken as 0 (conservative: largest leakage). NH3 and H2O do not permeate in this model.
    Permeate H2 partial pressure = P_perm (pure-H2 permeate approximation, valid for small leakage).
    """
    k = permeance(T_K, permeability, thickness_m) * flux_multiplier
    dP_ref = 1e5
    J_ref = k * (dP_ref ** n)
    L_N2 = 0.0 if math.isinf(alpha_H2_N2) else J_ref / alpha_H2_N2 / dP_ref  # mol m-2 s-1 Pa-1
    feed = {s: float(v) for s, v in feed_kmol_h.items() if v}
    h2_0, n2_0 = feed.get("H2", 0.0) / 3.6, feed.get("N2", 0.0) / 3.6
    inert = sum(v for s, v in feed.items() if s not in ("H2", "N2")) / 3.6
    Pr, Pp = P_feed_bar * 1e5, P_perm_bar * 1e5

    def rhs(_A, x):
        h2, n2 = max(x[0], 0.0), max(x[1], 0.0)
        tot = h2 + n2 + inert
        jh = sieverts_flux(h2 / tot * Pr, Pp, k, n, 1.0)
        jn = L_N2 * (n2 / tot * Pr)
        return [-jh, -jn]

    if area_m2 > 0:
        sol = solve_ivp(rhs, (0, area_m2), [h2_0, n2_0], method="LSODA", rtol=1e-10, atol=1e-14)
        h2_r, n2_r = max(sol.y[0, -1], 0.0), max(sol.y[1, -1], 0.0)
    else:
        h2_r, n2_r = h2_0, n2_0
    h2_p, n2_p = (h2_0 - h2_r), (n2_0 - n2_r)
    ret = dict(feed)
    ret["H2"], ret["N2"] = h2_r * 3.6, n2_r * 3.6
    return {"permeate_kmol_h": {"H2": h2_p * 3.6, "N2": n2_p * 3.6}, "retentate_kmol_h": ret,
            "h2_recovery": h2_p / h2_0 if h2_0 else 0.0,
            "n2_in_permeate_ppm": 1e6 * n2_p / (h2_p + n2_p) if h2_p + n2_p > 0 else 0.0,
            "permeance_mol_m2_s_Pa05": k, "alpha_H2_N2": alpha_H2_N2, "area_m2": area_m2}


def pinch_recovery(feed_kmol_h: dict[str, float], P_feed_bar: float, P_perm_bar: float, n: float = 0.5) -> float:
    """Maximum H2 recovery from the partial-pressure pinch y_H2,ret * P_feed = P_perm (Sieverts, n arbitrary)."""
    h2 = feed_kmol_h["H2"]
    other = sum(v for s, v in feed_kmol_h.items() if s != "H2")
    y_p = P_perm_bar / P_feed_bar
    if y_p >= 1:
        return 0.0
    return max(0.0, 1.0 - (y_p / (1 - y_p) * other) / h2)


def membrane_area_for_recovery(feed: dict[str, float], R: float, P_feed_bar: float, P_perm_bar: float, T_K: float,
                               **kw) -> Optional[float]:
    from scipy.optimize import brentq

    if R >= pinch_recovery(feed, P_feed_bar, P_perm_bar, kw.get("n", 0.5)):
        return None
    f = lambda A: membrane_with_leakage(feed, A, P_feed_bar, P_perm_bar, T_K, **kw)["h2_recovery"] - R
    hi = 1.0
    while f(hi) < 0:
        hi *= 2
        if hi > 1e7:
            return None
    return brentq(f, 0.0, hi, xtol=1e-9)


def required_selectivity(feed: dict[str, float], area: float, P_feed_bar: float, P_perm_bar: float, T_K: float,
                         n2_limit_ppm: float, **kw) -> Optional[float]:
    """Smallest ideal H2/N2 selectivity that keeps permeate N2 <= limit (bisection on log alpha); None if
    even alpha = 1e9 is not enough."""
    def ppm(a):
        return membrane_with_leakage(feed, area, P_feed_bar, P_perm_bar, T_K, alpha_H2_N2=a, **kw)["n2_in_permeate_ppm"]

    if ppm(1e9) > n2_limit_ppm:
        return None
    lo, hi = 1.0, 1e9
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if ppm(mid) > n2_limit_ppm:
            lo = mid
        else:
            hi = mid
    return hi


# --------------------------------------------------------------------------------------------------
# 4. Helpers: heat value, compression, mass balance closure
# --------------------------------------------------------------------------------------------------
def lhv_kW(flows_kmol_h: dict[str, float]) -> float:
    return sum(v * LHV_KJ_PER_MOL.get(s, 0.0) for s, v in flows_kmol_h.items()) / 3.6


def mass_kg_h(flows_kmol_h: dict[str, float]) -> float:
    return sum(v * MOLAR_MASS[s] for s, v in flows_kmol_h.items())


def closure(feed: dict[str, float], outs: list[dict[str, float]]) -> dict:
    """Component mole balance closure (relative error per species and overall mass)."""
    sp = set(feed)
    for o in outs:
        sp |= set(o)
    rel = {}
    for s in sorted(sp):
        out = sum(o.get(s, 0.0) for o in outs)
        rel[s] = (out - feed.get(s, 0.0)) / feed[s] if feed.get(s, 0.0) else (0.0 if abs(out) < 1e-12 else float("inf"))
    mf, mo = mass_kg_h(feed), sum(mass_kg_h(o) for o in outs)
    return {"component_rel_error": rel, "max_abs_rel_error": max(abs(v) for v in rel.values()),
            "mass_rel_error": (mo - mf) / mf}


def h2_compression_kWh_per_kg(P_in_bar: float, P_out_bar: float, T_K: float = 313.15,
                              eta: float | None = None) -> float:
    r = compression_power_kW(1.0, {"H2": 1.0}, T_K, P_in_bar, P_out_bar, None, eta)
    return r["power_kW"] / MOLAR_MASS["H2"]  # 1 kmol/h = 2.016 kg/h, so kW / (kg/h) = kWh/kg


def gas_compression_kWh_per_kg_h2(flows: dict[str, float], T_K: float, P_in_bar: float, P_out_bar: float,
                                  h2_kg_h: float, eta: float | None = None) -> float:
    tot = sum(flows.values())
    r = compression_power_kW(tot, flows, T_K, P_in_bar, P_out_bar, None, eta)
    return r["power_kW"] / h2_kg_h if h2_kg_h > 0 else float("nan")
