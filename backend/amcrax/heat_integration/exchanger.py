"""Shell-and-tube exchanger sizing and cost (Phase 2, task X1): feed/effluent exchanger (FEHE).

Public API (deterministic, no network)::

    from amcrax.heat_integration.exchanger import size_and_cost, annualised_cost, U_CASES
    r = size_and_cost(duty_kW=612.2, T_hot_in=600.0, T_hot_out=228.4, T_cold_in=75.9, T_cold_out=550.0,
                      U_case="central")            # temperatures in degC
    r["area_m2"], r["n_shells"], r["F"], r["purchase_USD"], r["installed_USD"], r["tci_equivalent_USD"], r["*_SGD"]
    a = annualised_cost(r["tci_equivalent_USD"])   # USD/yr on the reference-scenario finance basis

Method
------
1. LMTD of counter-current flow. A shell-and-tube unit with one shell pass and an even number of tube passes
   (1-2 shell) needs the correction factor F (Bowman, Mueller and Nagle 1940 form, as given in Towler and Sinnott
   2013, Sec. 19.6). With a temperature cross (cold outlet above hot outlet, as in the AmCraX FEHE) one 1-2 shell
   is infeasible; the smallest number N of 1-2 shells in series with F >= F_MIN (0.75, textbook rule) is used.
   A pure counter-current unit (F = 1) is also reported. When the caller passes a segmented UA (from the H-T
   curves, ``amcrax.heat_integration.analyse``), the area uses that UA instead of Q / LMTD, divided by F.
2. Area A = UA / (U F). U is NOT computed here: three cases from typical-range tables (U_CASES, below).
3. Cost (CORRELATIONS): Turton et al. (2018) module costing (purchased cost Cp0 at CEPCI 397, pressure factor,
   material factor, bare-module factor) as the central correlation; Towler and Sinnott (2013) U-tube
   correlation (CEPCI 532.9, Jan 2010) with the Hand installation factor 3.5 as a cross-check. Escalated to the
   2024 cost year of the reference CAPEX by CEPCI (CEPCI_2024 below; the library values conflict, so the range is
   carried). An area above the correlation range is split into equal parallel units; below the range the cost
   is evaluated at the lower bound (flagged).
4. TCI-equivalent = installed (bare-module) cost x the reference-scenario indirect factor
   (1 + OSBL)(1 + engineering + contingency), i.e. the same factor as every item of
   amcrax.economics.reference.reference_capex. Turton's bare-module cost already contains some indirect costs,
   so this is conservative (it counts against heat integration).
5. Annualised cost: capital charge (reference CRF) + maintenance + insurance + plant overhead on maintenance,
   with G&A, exactly as the fixed-opex formula of amcrax.economics.singapore.evaluate.

All values carry a source label; typical-range values are labelled as such.
"""
from __future__ import annotations

import math
from typing import Optional

from amcrax.economics.reference import load_reference_scenario

F_MIN = 0.75  # Towler and Sinnott 2013 Sec. 19.6 rule of thumb: F below 0.75 is uneconomic / sensitive
MAX_SHELLS = 12

#: Overall heat-transfer coefficient cases, W/(m2 K), gas-gas shell-and-tube at about 20 bar.
#: The VDI Heat Atlas (2010) chapter C3 table gives 5-35 for gas (~1 bar) / gas (~1 bar) and 150-500 for
#: high-pressure gas (200-300 bar) / high-pressure gas. No sourced value AT 20 bar was found: the low case is the
#: top of the 1-bar range, the high case the bottom of the 200-300 bar range, the central case their geometric mean
#: (derived interpolation, not a sourced number).
U_CASES = {
    "low": {"U_W_m2K": 35.0, "source_type": "literature (typical range)",
            "source": "vdi2010heatatlas, ch. C3 table, shell-and-tube, gas (~1 bar) / gas (~1 bar): 5-35 W/(m2 K) (upper bound)",
            "url": "https://doi.org/10.1007/978-3-540-77877-6"},
    "central": {"U_W_m2K": math.sqrt(35.0 * 150.0), "source_type": "derived (interpolation between typical ranges)",
                "source": "geometric mean of the low and high cases (35 and 150 W/(m2 K)); no sourced value at 20 bar",
                "url": "https://doi.org/10.1007/978-3-540-77877-6"},
    "high": {"U_W_m2K": 150.0, "source_type": "literature (typical range)",
             "source": "vdi2010heatatlas, ch. C3 table, shell-and-tube, high-pressure gas (200-300 bar) both sides: 150-500 W/(m2 K) (lower bound)",
             "url": "https://doi.org/10.1007/978-3-540-77877-6"},
    "phase1_assumption": {"U_W_m2K": 50.0, "source_type": "assumption",
                          "source": "Phase 1 amcrax.heat_integration.analysis.U_ASSUMED_W_M2K (unsourced), kept for comparison",
                          "url": None},
}

#: CEPCI values. Cost year of the reference CAPEX is 2024 (reference_scenario.yaml capex.cost_year).
CEPCI = {
    "turton_base_2001": {"value": 397.0, "source": "turton2018analysis Appendix A (CEPCI 397, 2001); also chopra2026decentralized Eq. 4"},
    "towler_base_2010": {"value": 532.9, "source": "towler2013chemical Table 6.6 basis (US Gulf Coast, Jan 2010, CEPCI 532.9); also kum2026heatintegrated Sec. 3.4.1"},
    "target_2024_central": {"value": 797.9, "source": "chemengonline.com: 2023 annual average 797.9 and 2024 monthly values 'relatively stable at just below 800' (search-result text, 2026-11-23); used as the 2024 value"},
    "target_2024_low": {"value": 720.2, "source": "kum2026heatintegrated Sec. 3.4.1 (CEPCI 2024 = 720.2; conflicts with the other library values)"},
    "target_2024_high": {"value": 800.3, "source": "ahmad2025gtcc Eq. 8 text (CEPCI 2024 = 800.3)"},
}

#: Turton et al. (2018) Appendix A, shell-and-tube heat exchangers (Tables A.1-A.4, Fig. A.18).
TURTON = {
    "fixed_tube_sheet": (4.3247, -0.3030, 0.1634),
    "floating_head": (4.8306, -0.8509, 0.3187),
    "u_tube": (4.1884, -0.2503, 0.1974),
    "area_range_m2": (10.0, 1000.0),
    "pressure_both_sides": (0.03881, -0.11272, 0.08183),   # 5 < P < 140 barg
    "B1": 1.63, "B2": 1.66,
    "FM": {"CS/CS": 1.0, "CS/SS": 1.81, "SS/SS": 2.73, "CS/Ni": 2.68, "Ni/Ni": 3.73},
}
#: Towler and Sinnott (2013) Table 6.6: U-tube shell-and-tube, Ce = a + b S^n (USD, CS, Jan 2010), S = area m2.
TOWLER = {"u_tube": (28000.0, 54.0, 1.2), "floating_head": (32000.0, 70.0, 1.2), "area_range_m2": (10.0, 1000.0),
          "install_factor": 3.5, "fm": {"CS": 1.0, "SS304": 1.3, "SS316": 1.3}}

SOURCES = {
    "turton2018analysis": "Turton, R., Shaeiwitz, J. A., Bhattacharyya, D., & Whiting, W. B. (2018). Analysis, synthesis, and design of chemical processes (5th ed.). Prentice Hall. Appendix A.",
    "towler2013chemical": "Towler, G., & Sinnott, R. (2013). Chemical engineering design (2nd ed.). Butterworth-Heinemann. https://doi.org/10.1016/C2009-0-61216-2",
    "vdi2010heatatlas": "VDI e. V. (Ed.). (2010). VDI heat atlas (2nd ed.). Springer. https://doi.org/10.1007/978-3-540-77877-6 (ch. C3, typical overall heat-transfer coefficients)",
}


# ------------------------------------------------------------------------------------------ thermal
def lmtd(dT1: float, dT2: float) -> float:
    if dT1 <= 0 or dT2 <= 0:
        raise ValueError(f"terminal temperature differences must be > 0 (got {dT1}, {dT2})")
    return dT1 if abs(dT1 - dT2) < 1e-9 else (dT1 - dT2) / math.log(dT1 / dT2)


def _f_12(P: float, R: float) -> Optional[float]:
    """F of one 1-2 shell (Bowman et al. 1940). None if infeasible."""
    if P <= 0:
        return 1.0
    if abs(R - 1.0) < 1e-9:
        if P >= 1:
            return None
        den_arg = (2 - P * (2 - math.sqrt(2))) / (2 - P * (2 + math.sqrt(2)))
        if den_arg <= 0 or 2 - P * (2 + math.sqrt(2)) <= 0:
            return None
        return (P * math.sqrt(2) / (1 - P)) / math.log(den_arg)
    s = math.sqrt(R * R + 1.0)
    a = (1 - P) / (1 - P * R)
    d1, d2 = 2 - P * (R + 1 - s), 2 - P * (R + 1 + s)
    if a <= 0 or d1 <= 0 or d2 <= 0:
        return None
    num = s * math.log(a)
    den = (R - 1) * math.log(d1 / d2)
    if den == 0:
        return None
    f = num / den
    return f if 0 < f <= 1.0 + 1e-9 else None


def f_correction(T_hot_in: float, T_hot_out: float, T_cold_in: float, T_cold_out: float, n_shells: int = 1) -> Optional[float]:
    """LMTD correction factor for N 1-2 shells in series (overall P, R converted to one shell)."""
    P = (T_cold_out - T_cold_in) / (T_hot_in - T_cold_in)
    R = (T_hot_in - T_hot_out) / (T_cold_out - T_cold_in)
    if n_shells == 1:
        return _f_12(P, R)
    if abs(R - 1.0) < 1e-9:
        P1 = P / (n_shells - (n_shells - 1) * P)
    else:
        base = (1 - P * R) / (1 - P)
        if base <= 0:
            return None
        S = base ** (1.0 / n_shells)
        P1 = (S - 1) / (S - R)
    return _f_12(P1, R)


def shells_needed(T_hot_in, T_hot_out, T_cold_in, T_cold_out, f_min: float = F_MIN) -> tuple[int, float]:
    for n in range(1, MAX_SHELLS + 1):
        f = f_correction(T_hot_in, T_hot_out, T_cold_in, T_cold_out, n)
        if f is not None and f >= f_min:
            return n, f
    raise ValueError(f"no 1-2 shell arrangement up to {MAX_SHELLS} shells reaches F >= {f_min}")


# ------------------------------------------------------------------------------------------ cost
def _split(area: float, rng: tuple[float, float]) -> tuple[int, float, bool]:
    n = max(1, math.ceil(area / rng[1]))
    a = area / n
    return n, a, a < rng[0]


def turton_cost(area_m2: float, P_barg: float = 19.5, material: str = "SS/SS", kind: str = "fixed_tube_sheet",
                cepci_target: float = CEPCI["target_2024_central"]["value"], min_units: int = 1) -> dict:
    """Turton module costing: purchased Cp0 (CS, ambient P) and bare-module cost, escalated to cepci_target."""
    rng = TURTON["area_range_m2"]
    n, a, below = _split(area_m2, rng)
    if min_units > n:
        n, a = min_units, area_m2 / min_units
        below = a < rng[0]
    a_eval = max(a, rng[0])
    K1, K2, K3 = TURTON[kind]
    la = math.log10(a_eval)
    cp0 = 10 ** (K1 + K2 * la + K3 * la * la)
    C1, C2, C3 = TURTON["pressure_both_sides"]
    if P_barg < 5:
        FP = 1.0
    else:
        lp = math.log10(P_barg)
        FP = 10 ** (C1 + C2 * lp + C3 * lp * lp)
    FM = TURTON["FM"][material]
    fbm = TURTON["B1"] + TURTON["B2"] * FM * FP
    esc = cepci_target / CEPCI["turton_base_2001"]["value"]
    purchased = n * cp0 * FM * FP * esc       # purchased cost at the actual material and pressure
    bare = n * cp0 * fbm * esc
    return {"correlation": "turton2018_" + kind, "n_units": n, "area_per_unit_m2": a, "below_range": below,
            "Cp0_per_unit_USD_2001": cp0, "FP": FP, "FM": FM, "F_BM": fbm, "escalation": esc,
            "purchase_USD": purchased, "installed_USD": bare, "installed_definition": "bare-module cost (Turton)"}


def towler_cost(area_m2: float, material: str = "SS304", kind: str = "u_tube",
                cepci_target: float = CEPCI["target_2024_central"]["value"], min_units: int = 1) -> dict:
    rng = TOWLER["area_range_m2"]
    n, a, below = _split(area_m2, rng)
    if min_units > n:
        n, a = min_units, area_m2 / min_units
        below = a < rng[0]
    a_eval = max(a, rng[0])
    ca, cb, cn = TOWLER[kind]
    ce = ca + cb * a_eval ** cn
    esc = cepci_target / CEPCI["towler_base_2010"]["value"]
    fm = TOWLER["fm"][material]
    purchased = n * ce * fm * esc
    # Hand method: installed = f_I x purchased carbon-steel cost, with the alloy premium added on top
    installed = n * ce * esc * (TOWLER["install_factor"] + (fm - 1.0))
    return {"correlation": "towler2013_" + kind, "n_units": n, "area_per_unit_m2": a, "below_range": below,
            "Ce_per_unit_USD_2010": ce, "FM": fm, "escalation": esc, "purchase_USD": purchased,
            "installed_USD": installed, "installed_definition": "Hand installation factor 3.5 on CS cost + alloy premium"}


def indirect_factor() -> float:
    c = load_reference_scenario().raw["capex"]
    return (1.0 + c["osbl_frac_isbl"]["value"]) * (1.0 + c["engineering_frac_isbl_osbl"]["value"]
                                                   + c["contingency_frac_isbl_osbl"]["value"])


def annual_charge_factor(crf: Optional[float] = None) -> float:
    """USD/yr per USD of capital: CRF + maintenance + insurance + overhead on maintenance, with G&A."""
    r = load_reference_scenario()
    f = r.crf() if crf is None else crf
    return f + (r.maintenance_frac_capex_per_yr * (1.0 + r.plant_overhead_frac_labour_maint)
                + r.insurance_frac_capex_per_yr) * (1.0 + r.g_and_a_frac_fixed_opex)


def annualised_cost(capital_USD: float, crf: Optional[float] = None) -> float:
    return capital_USD * annual_charge_factor(crf)


def size_and_cost(duty_kW: float, T_hot_in: float, T_hot_out: float, T_cold_in: float, T_cold_out: float,
                  U_case: str | float = "central", *, ua_kW_K: Optional[float] = None, P_barg: float = 19.5,
                  material: str = "SS/SS", correlation: str = "turton", counter_current: bool = False,
                  cepci_target: Optional[float] = None) -> dict:
    """Size and cost one exchanger. Temperatures degC. U_case: key of U_CASES or a number in W/(m2 K).

    ua_kW_K: optional segmented UA of the counter-current exchanger (else Q / LMTD).
    counter_current: True gives F = 1 (e.g. a hairpin / multi-tube unit) instead of N 1-2 shells."""
    if duty_kW <= 0:
        raise ValueError("duty_kW must be > 0")
    if isinstance(U_case, str):
        uc = U_CASES[U_case]
        U = uc["U_W_m2K"]
        u_src = {k: uc[k] for k in ("source_type", "source", "url")}
    else:
        U = float(U_case)
        u_src = {"source_type": "caller", "source": "value passed by caller", "url": None}
    dT1, dT2 = T_hot_in - T_cold_out, T_hot_out - T_cold_in
    lm = lmtd(dT1, dT2)
    ua = duty_kW / lm if ua_kW_K is None else float(ua_kW_K)
    if counter_current:
        n_sh, F = 1, 1.0
    else:
        n_sh, F = shells_needed(T_hot_in, T_hot_out, T_cold_in, T_cold_out)
    area = ua * 1000.0 / (U * F)
    cep = CEPCI["target_2024_central"]["value"] if cepci_target is None else cepci_target
    if correlation == "turton":
        c = turton_cost(area, P_barg, material, cepci_target=cep, min_units=n_sh)
    elif correlation == "towler":
        mat = {"SS/SS": "SS304", "CS/CS": "CS"}.get(material, "SS304")
        c = towler_cost(area, mat, cepci_target=cep, min_units=n_sh)
    else:
        raise ValueError("correlation must be 'turton' or 'towler'")
    fac = indirect_factor()
    fx = load_reference_scenario().fx_SGD_per_USD
    tci = c["installed_USD"] * fac
    return {
        "duty_kW": duty_kW, "T_hot_in_C": T_hot_in, "T_hot_out_C": T_hot_out, "T_cold_in_C": T_cold_in,
        "T_cold_out_C": T_cold_out, "hot_end_dT_K": dT1, "cold_end_dT_K": dT2, "lmtd_K": lm,
        "temperature_cross": bool(T_cold_out > T_hot_out), "ua_kW_K": ua,
        "ua_basis": "Q/LMTD" if ua_kW_K is None else "segmented H-T curves (caller)",
        "F": F, "n_shells": n_sh, "arrangement": "counter-current (F = 1)" if counter_current else f"{n_sh} x 1-2 shell in series",
        "U_W_m2K": U, "U_case": U_case if isinstance(U_case, str) else "custom", "U_source": u_src,
        "area_m2": area, "P_barg": P_barg, "material": material, "cepci_target": cep, "cost_year": 2024,
        "cost": c, "purchase_USD": c["purchase_USD"], "installed_USD": c["installed_USD"],
        "indirect_factor": fac, "tci_equivalent_USD": tci, "annualised_USD_per_yr": annualised_cost(tci),
        "fx_SGD_per_USD": fx, "purchase_SGD": c["purchase_USD"] * fx, "installed_SGD": c["installed_USD"] * fx,
        "tci_equivalent_SGD": tci * fx,
    }


def capital_for_annual(annual_USD_per_yr: float, crf: Optional[float] = None) -> float:
    """Capital (TCI-equivalent) whose annual charge equals annual_USD_per_yr (break-even exchanger cost)."""
    return annual_USD_per_yr / annual_charge_factor(crf)


def breakeven_U(duty_kW: float, T_hot_in, T_hot_out, T_cold_in, T_cold_out, tci_breakeven_USD: float, *,
                ua_kW_K: Optional[float] = None, **kw) -> Optional[float]:
    """Overall U (W/(m2 K)) at which the TCI-equivalent cost equals tci_breakeven_USD (bisection on log U)."""
    def tci(U):
        return size_and_cost(duty_kW, T_hot_in, T_hot_out, T_cold_in, T_cold_out, U, ua_kW_K=ua_kW_K, **kw)["tci_equivalent_USD"]
    lo, hi = 0.01, 5000.0
    if tci(lo) <= tci_breakeven_USD:
        return lo
    if tci(hi) > tci_breakeven_USD:
        return None
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if tci(mid) > tci_breakeven_USD:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1 + 1e-10:
            break
    return hi
