"""Workstream K, task 5: Aspen-ready kinetics specification (results/research/kinetics/aspen_kinetics_spec.json).

Deterministic; run from the project root:  python scripts/research/kinetics_aspen_spec.py

For every catalyst: an Aspen Plus native reaction representation (LHHW, rate basis Cat (wt)), parameters in SI
(kmol, kg, s, J/kmol, Pa or kmol/m3), the error of the native form against the Python law, bed properties and
6-10 reference test points (python PFR, isothermal, no pressure drop) for the Aspen agent to cross-check.

Aspen LHHW form (Aspen Plus V15 help, "LHHW reaction type"):
  r = [k (T/T0)^n exp(-E/R (1/T - 1/T0))] [K1 prod C_i^a_i - K2 prod C_j^b_j] / [sum_m K_m prod C_k^g_k]^m_ads
  with ln K = A + B/T + C ln T + D T for every driving-force and adsorption constant (T0 left blank: plain Arrhenius).
"""
from __future__ import annotations

import math

import numpy as np
from kinetics_common import OUT, provenance, write_json
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

from amcrax.kinetics import get_catalyst, rate_mol_per_kgcat_s
from amcrax.kinetics.rate_laws import R_KIN_J_molK
from amcrax.reactor.pfr import DEFAULT_BED, simulate_pfr
from amcrax.thermodynamics import equilibrium_constant

SCRIPT = "scripts/research/kinetics_aspen_spec.py"
LN_PA_PER_BAR = math.log(1e5)
FEED_PURE = {"NH3": 100.0}
FEED_SEED = {"NH3": 100.0, "H2": 1.0e-4}   # 1 ppm H2 seed for the Temkin-Pyzhev law (singular at p_H2 = 0)


# --------------------------------------------------------------------------- equilibrium constant fit
def fit_lnKp(T_lo=573.15, T_hi=1123.15):
    """ln Kp(T) [bar, per mol NH3] of amcrax.thermodynamics fitted to A + B/T + C ln T + D T."""
    T = np.linspace(T_lo, T_hi, 111)
    y = np.array([math.log(equilibrium_constant(t)) for t in T])
    X = np.column_stack([np.ones_like(T), 1 / T, np.log(T), T])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    err = X @ coef - y
    return {"A": coef[0], "B": coef[1], "C": coef[2], "D": coef[3], "T_range_K": [T_lo, T_hi],
            "max_abs_error_lnK": float(np.max(np.abs(err))), "max_rel_error_K": float(np.max(np.abs(np.expm1(err)))),
            "source": "fit to Kp(T) of amcrax.thermodynamics.equilibrium_constant (NASA7 / GRI-Mech 3.0, 1 bar standard state)"}


def coeffs(A=0.0, B=0.0, C=0.0, D=0.0):
    return {"A": float(A), "B": float(B), "C": float(C), "D": float(D)}


# --------------------------------------------------------------------------- generic isothermal PFR for an approximation
def pfr_conversion(rate_fn, W_kg, T_K, P_bar, feed_kmol_h):
    F = {k: v * 1000 / 3600 for k, v in feed_kmol_h.items()}
    F0 = F["NH3"]

    def rhs(_W, u):
        X = min(max(u[0], 0.0), 1 - 1e-15)
        n = dict(F)
        n["NH3"] = F0 * (1 - X)
        n["N2"] = F.get("N2", 0.0) + 0.5 * F0 * X
        n["H2"] = F.get("H2", 0.0) + 1.5 * F0 * X
        Ft = sum(n.values())
        p = {k: v / Ft * P_bar for k, v in n.items()}
        return [rate_fn(T_K, p) / F0]
    s = solve_ivp(rhs, (0, W_kg), [0.0], method="LSODA", rtol=1e-8, atol=1e-12)
    return float(s.y[0, -1])


def python_point(cid, T_C, P_bar, W_kg, feed):
    r = simulate_pfr(cid, W_kg, T_in_C=T_C, P_in_bar=P_bar, feed_kmol_h=feed, mode="isothermal",
                     pressure_drop=False, n_points=2)
    return {"T_C": T_C, "P_bar": P_bar, "W_cat_kg": W_kg, "feed_kmol_h": feed, "mode": "isothermal, no pressure drop",
            "X_python": r.outlet["conversion"], "X_eq": r.outlet["X_eq_outlet"],
            "H2_out_kmol_h": r.outlet["H2_kmol_h"], "source_type": "python"}


# --------------------------------------------------------------------------- Kum Temkin-Pyzhev -> native LHHW
def kum_spec(lnKp):
    cat = get_catalyst("ru_kum_temkin_pyzhev")
    p = {k: v["value"] for k, v in cat.parameters.items()}
    b = p["beta"]
    # term1 (bar) = pNH3^(2b) pH2^(-3b); in Pa: multiply by (1e5)^(-(2b-3b)) = (1e5)^(b)
    t1 = coeffs(A=b * LN_PA_PER_BAR)
    # term2 (bar) = pN2 pH2^(3(1-b)) pNH3^(-2(1-b)) / Kp^2; net exponent 2-b; ln(1/Kp^2) = -2 lnKp
    t2 = coeffs(A=-2 * lnKp["A"] - (2 - b) * LN_PA_PER_BAR, B=-2 * lnKp["B"], C=-2 * lnKp["C"], D=-2 * lnKp["D"])
    # error of the native form = error of the lnKp fit only (term algebra is exact); check on rates
    Ts = np.linspace(623.15, 873.15, 6)
    errs = []
    for T in Ts:
        for X in (0.05, 0.3, 0.6, 0.9):
            for P in (1.0, 10.0, 40.0):
                pn, ph, pn2 = (1 - X), 1.5 * X, 0.5 * X
                tot = pn + ph + pn2
                pp = {"NH3": pn / tot * P, "H2": ph / tot * P, "N2": pn2 / tot * P}
                r_py = rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T, pp, keq_basis="amcrax_thermo")
                Pa = {k: v * 1e5 for k, v in pp.items()}
                k = p["ko"] * math.exp(-p["Ea"] / (R_KIN_J_molK * T))
                K1 = math.exp(t1["A"])
                K2 = math.exp(t2["A"] + t2["B"] / T + t2["C"] * math.log(T) + t2["D"] * T)
                df = K1 * Pa["NH3"] ** (2 * b) * Pa["H2"] ** (-3 * b) - K2 * Pa["N2"] * Pa["H2"] ** (3 * (1 - b)) * Pa["NH3"] ** (-2 * (1 - b))
                r_asp = k * df * 1000.0
                if abs(r_py) > 1e-6 * abs(k * 1000 * K1 * Pa["NH3"] ** (2 * b) * Pa["H2"] ** (-3 * b)):
                    errs.append(abs(r_asp - r_py) / abs(r_py))
    pts = []
    for T_C, P, W in ((400, 1.0, 50.0), (400, 10.0, 200.0), (450, 1.0, 50.0), (450, 10.0, 200.0),
                      (500, 5.0, 100.0), (500, 20.0, 500.0), (550, 40.0, 1000.0), (600, 20.0, 500.0)):
        pts.append(python_point("ru_kum_temkin_pyzhev", T_C, P, W, FEED_SEED))
    rho_p, eps = 980.0, 0.36
    return {
        "catalyst_id": cat.id, "label": cat.label, "python_law": cat.rate_law_text, "source": cat.source,
        "aspen_native": True, "aspen_reaction_type": "LHHW",
        "stoichiometry": {"NH3": -1, "N2": 0.5, "H2": 1.5}, "rate_basis": "Cat (wt)", "phase": "Vapor",
        "concentration_basis": "Partial pressure", "unit_system": "SI: rate kmol/(kg_cat s), p in N/m2 (Pa), E in J/kmol, T in K",
        "kinetic_factor": {"k": p["ko"], "k_unit": "kmol/(kg_cat s) (= mol/(g_cat s) of the source)", "n": 0.0,
                           "E_J_per_mol": p["Ea"], "E_J_per_kmol": p["Ea"] * 1000, "E_kJ_per_mol": p["Ea"] / 1000,
                           "T0": "blank (no reference temperature)"},
        "driving_force": {
            "term1": {"exponents": {"NH3": 2 * b, "H2": -3 * b, "N2": 0.0}, "lnK_coefficients": t1,
                      "note": "beta*ln(1e5) converts the bar-based law to Pa"},
            "term2": {"exponents": {"NH3": -2 * (1 - b), "H2": 3 * (1 - b), "N2": 1.0}, "lnK_coefficients": t2,
                      "note": "ln(1/Kp^2) with Kp fitted (see equilibrium_constant_fit) minus (2-beta) ln(1e5) for Pa"}},
        "adsorption": {"exponent": 1.0, "terms": [{"exponents": {}, "lnK_coefficients": coeffs()}],
                       "note": "adsorption expression = 1 (Temkin-Pyzhev has no denominator)"},
        "native_form_error_vs_python": {"max_rel_rate_error": max(errs) if errs else None, "n_samples": len(errs),
                                        "range": "623-873 K, X 0.05-0.9, 1-40 bar (rates near equilibrium excluded)",
                                        "origin": "only the ln Kp fit; exact algebra otherwise"},
        "keq_basis_python": "amcrax_thermo (PFR default); the kinetics.yaml 'published' Keq (Kum Eq. 4) differs slightly",
        "numerical_note": "rate singular at p_H2 = 0: feed a 1 ppm H2 seed (1e-4 kmol/h in 100 kmol/h) in Aspen, as in the test points",
        "bed_properties": {"particle_density_kg_m3": {"value": rho_p, "source": "kum2026heatintegrated Table 1 (p. 5)"},
                           "bed_voidage": {"value": eps, "source": "kum2026heatintegrated Table 1 (p. 5)"},
                           "bulk_density_kg_m3": {"value": (1 - eps) * rho_p, "source": "derived (1-eps)*rho_p as in Kum Table 2"},
                           "particle_diameter_m": {"value": 0.0006, "source": "kum2026heatintegrated Table 1 (p. 5)"},
                           "tube_inner_diameter_m": {"value": 0.126, "source": "kum2026heatintegrated Table 1 (p. 5)"}},
        "validity": cat.validity,
        "reference_test_points": pts,
    }


# --------------------------------------------------------------------------- Lucentini LHHW -> native LHHW (exact)
def lucentini_spec(cid, lnKp):
    cat = get_catalyst(cid)
    p = {k: v["value"] for k, v in cat.parameters.items()}
    K1_kmol = p["K1"] * 1000.0           # m3/mol -> m3/kmol
    K4_kmol = p["K4"] / 1000.0           # mol/m3 -> kmol/m3
    ln_RP0 = math.log(1e5 / R_KIN_J_molK / 1000.0)   # Kc [kmol/m3] = Kp * (1e5/(R T))/1000
    # term2 constant = K1 / Kc ; ln = ln K1 - lnKp - ln(1e5/R/1000) + ln T
    t2 = coeffs(A=math.log(K1_kmol) - lnKp["A"] - ln_RP0, B=-lnKp["B"], C=1.0 - lnKp["C"], D=-lnKp["D"])
    # check native vs python with approach factor (exact up to lnKp fit)
    errs = []
    for T in np.linspace(623.15, 1073.15, 7):
        for X in (0.05, 0.3, 0.6, 0.9):
            for P in (1.01325, 10.0, 40.0):
                pn, ph, pn2 = (1 - X), 1.5 * X, 0.5 * X
                tot = pn + ph + pn2
                pp = {"NH3": pn / tot * P, "H2": ph / tot * P, "N2": pn2 / tot * P}
                r_py = rate_mol_per_kgcat_s(cid, T, pp)
                C = {k: v * 1e5 / (R_KIN_J_molK * T) / 1000.0 for k, v in pp.items()}
                k = p["k0"] * math.exp(-p["Ek"] * 1000 / (R_KIN_J_molK * T))
                K2 = math.exp(t2["A"] + t2["B"] / T + t2["C"] * math.log(T) + t2["D"] * T)
                df = K1_kmol * C["NH3"] - K2 * C["N2"] ** 0.5 * C["H2"] ** 1.5
                ads = 1 + K1_kmol * C["NH3"] + K4_kmol ** -0.5 * C["H2"] ** 0.5
                r_asp = k * df / ads**2 * 1000.0
                fwd = k * K1_kmol * C["NH3"] / ads**2 * 1000.0
                if abs(r_py) > 1e-3 * fwd:
                    errs.append(abs(r_asp - r_py) / abs(r_py))
    pts = []
    for T_C, P, W in ((400, 1.01325, 100.0), (450, 1.01325, 100.0), (500, 1.01325, 100.0), (450, 1.01325, 400.0),
                      (500, 10.0, 400.0), (550, 20.0, 1000.0), (600, 40.0, 1000.0), (650, 20.0, 400.0)):
        pts.append(python_point(cid, T_C, P, W, FEED_PURE))
    bp = cat.extra.get("bed_properties", {})
    return {
        "catalyst_id": cid, "label": cat.label, "python_law": cat.rate_law_text, "source": cat.source,
        "aspen_native": True, "aspen_reaction_type": "LHHW",
        "stoichiometry": {"NH3": -1, "N2": 0.5, "H2": 1.5}, "rate_basis": "Cat (wt)", "phase": "Vapor",
        "concentration_basis": "Molarity", "unit_system": "SI: rate kmol/(kg_cat s), C in kmol/m3, E in J/kmol, T in K",
        "kinetic_factor": {"k": p["k0"], "k_unit": "kmol/(kg_cat s) (= mol NH3/(g_cat s) of the source)", "n": 0.0,
                           "E_J_per_mol": p["Ek"] * 1000, "E_J_per_kmol": p["Ek"] * 1e6, "E_kJ_per_mol": p["Ek"],
                           "T0": "blank"},
        "driving_force": {
            "term1": {"exponents": {"NH3": 1.0, "H2": 0.0, "N2": 0.0}, "lnK_coefficients": coeffs(A=math.log(K1_kmol)),
                      "note": "K1 = %g m3/kmol (source %g m3/mol)" % (K1_kmol, p["K1"])},
            "term2": {"exponents": {"NH3": 0.0, "H2": 1.5, "N2": 0.5}, "lnK_coefficients": t2,
                      "note": "K1/Kc with Kc = Kp (P0/RT) in kmol/m3: reproduces the AmCraX approach factor (1-Q/Kp) exactly "
                              "(up to the ln Kp fit). Set term2 constant to a very small value (A = -1e3) for the published irreversible law."}},
        "adsorption": {"exponent": 2.0, "terms": [
            {"exponents": {}, "lnK_coefficients": coeffs()},
            {"exponents": {"NH3": 1.0}, "lnK_coefficients": coeffs(A=math.log(K1_kmol))},
            {"exponents": {"H2": 0.5}, "lnK_coefficients": coeffs(A=-0.5 * math.log(K4_kmol)),
             "note": "sqrt(C_H2/K4) with K4 = %g kmol/m3" % K4_kmol}]},
        "native_form_error_vs_python": {"max_rel_rate_error": max(errs) if errs else None, "n_samples": len(errs),
                                        "range": "623-1073 K, X 0.05-0.9, 1-40 bar (rates within 0.1 % of equilibrium excluded)",
                                        "origin": "only the ln Kp fit; the LHHW algebra is exact"},
        "bed_properties": {
            "particle_density_kg_m3": {"value": bp.get("rho_apparent_kg_m3", {}).get("value"), "source": "lucentini2021nirukinetic Sec. 2.4 (MIP apparent density)"},
            "bed_voidage": {"value": 0.36, "source": "assumption: industrial bed value of kum2026heatintegrated Table 1; the source beds are lab beds "
                                                       "(eps 0.3855 catalyst only, 0.2451 with SiC, d_i 4.572 mm)"},
            "bulk_density_kg_m3": {"value": (1 - 0.36) * bp.get("rho_apparent_kg_m3", {}).get("value", float("nan")),
                                   "source": "derived (1-eps)*rho_p with the assumed voidage"},
            "particle_diameter_m": {"value": bp.get("d_cat_m", {}).get("value"),
                                    "source": "lucentini2021nirukinetic Sec. 2.4 (lab powder; an industrial pellet needs an effectiveness factor)"}},
        "validity": cat.validity,
        "extrapolation_note": "fitted at 1 atm only; test points above 1 atm are model extrapolations",
        "reference_test_points": pts,
    }


# --------------------------------------------------------------------------- Takahashi microkinetic -> fitted approximation
def takahashi_spec(cid, lnKp, T_fit, P_design=20.0):
    cat = get_catalyst(cid)
    Ts = np.linspace(T_fit[0], T_fit[1], 7)
    samples = []
    for T in Ts:
        for yn in (0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0):
            for yh in (0.0, 0.01, 0.05, 0.15, 0.3, 0.5, 0.7):
                if yn + yh > 1.0 + 1e-9:
                    continue
                yh_eff = max(yh, 1e-4)
                pp = {"NH3": yn, "H2": yh_eff, "Ar": max(1.0 - yn - yh_eff, 0.0)}
                r = rate_mol_per_kgcat_s(cid, T, pp, approach_factor=False)
                if r > 0:
                    samples.append((T, yn, yh_eff, r))
    S = np.array(samples)

    Tm = float(np.mean(Ts))

    def den(theta, T, yn, yh):
        _, _, _, AH, BH, bh, AN, BN, m = theta
        return 1.0 + np.exp(AH + BH * (1 / T - 1 / Tm)) * yh**bh + np.exp(AN + BN * (1 / T - 1 / Tm)) * yn

    def model(theta, T, yn, yh):
        lnk0, E, a, *_ = theta
        m = theta[8]
        return lnk0 - E / (R_KIN_J_molK * T) + a * np.log(yn) - m * np.log(den(theta, T, yn, yh))

    def resid(theta):
        return model(theta, S[:, 0], S[:, 1], S[:, 2]) - np.log(S[:, 3])
    fit = least_squares(resid, x0=[20.0, 100e3, 1.0, 2.0, 0.0, 0.5, 0.0, 0.0, 2.0],
                        x_scale=[1, 1e4, 0.1, 1, 1e3, 0.1, 1, 1e3, 0.5],
                        bounds=([-50, 0, 0, -30, -1e6, 0.05, -30, -1e6, 0.5], [80, 4e5, 3, 30, 1e6, 3, 30, 1e6, 4]))
    lnk0, E, a, AH, BH, bh, AN, BN, m = fit.x
    rel = np.expm1(np.abs(fit.fun))
    # Aspen ln K = A + B/T: convert the centred form exp(A' + B'(1/T - 1/Tm)) -> A = A' - B'/Tm, B = B'
    KH_c = coeffs(A=AH - BH / Tm, B=BH)
    KN_c = coeffs(A=AN - BN / Tm, B=BN)

    # PFR check of the approximation (with approach factor, as AmCraX default)
    def approx_rate(T, p):
        P = sum(p.values())
        yn, yh = p["NH3"] / P, max(p["H2"] / P, 0.0)
        if yn <= 0:
            return 0.0
        r = math.exp(lnk0 - E / (R_KIN_J_molK * T)) * yn**a / float(den(fit.x, T, yn, yh)) ** m
        Q = p["N2"] ** 0.5 * p["H2"] ** 1.5 / p["NH3"]
        return r * (1 - Q / equilibrium_constant(T))
    pts, conv_err = [], []
    Tc_list = [T_fit[0] - 273.15 + d for d in (0, 50, 100, 150, 200, 250)]
    for T_C in Tc_list:
        for P, W in ((1.01325, 100.0), (P_design, 1000.0)):
            if len(pts) >= 10:
                break
            pt = python_point(cid, T_C, P, W, FEED_PURE)
            pt["X_native_approximation_python"] = pfr_conversion(approx_rate, W, T_C + 273.15, P, FEED_PURE)
            conv_err.append(abs(pt["X_native_approximation_python"] - pt["X_python"]))
            pts.append(pt)
    # driving-force term2 on mole-fraction basis at a FIXED design pressure: Q/K = y_N2^.5 y_H2^1.5 (P/1 bar)/(y_NH3 Kp)
    t2 = coeffs(A=math.log(P_design) - lnKp["A"], B=-lnKp["B"], C=-lnKp["C"], D=-lnKp["D"])
    return {
        "catalyst_id": cid, "label": cat.label, "python_law": cat.rate_law_text, "source": cat.source,
        "aspen_native": False,
        "why_not_native": "elementary-step model with a quasi-steady-state coverage solve (site balance solved numerically); "
                          "Aspen LHHW/POWERLAW cannot represent it exactly (a user kinetics subroutine would be needed)",
        "best_native_approximation": {
            "aspen_reaction_type": "LHHW", "rate_basis": "Cat (wt)", "concentration_basis": "Mole fraction",
            "form": "r = k0 exp(-E/RT) [y_NH3^a - (P/1bar)/Kp y_N2^0.5 y_H2^1.5 y_NH3^(a-1)] / (1 + K_H y_H2^b + K_N y_NH3)^m  [kmol/(kg s)]",
            "kinetic_factor": {"k": math.exp(lnk0) / 1000.0, "k_unit": "kmol/(kg_cat s)", "E_J_per_mol": E, "E_J_per_kmol": E * 1000, "n": 0.0},
            "driving_force": {"term1": {"exponents": {"NH3": a}, "lnK_coefficients": coeffs()},
                              "term2": {"exponents": {"NH3": a - 1.0, "N2": 0.5, "H2": 1.5}, "lnK_coefficients": t2,
                                        "note": f"valid ONLY at P = {P_design} bar (mole-fraction basis puts P into the constant); "
                                                "omit term2 for the published irreversible law"}},
            "adsorption": {"exponent": float(m), "terms": [{"exponents": {}, "lnK_coefficients": coeffs()},
                                                           {"exponents": {"H2": float(bh)}, "lnK_coefficients": KH_c},
                                                           {"exponents": {"NH3": 1.0}, "lnK_coefficients": KN_c}]},
            "fitted_parameters": {"ln_k0_mol_per_kg_s": lnk0, "E_J_per_mol": E, "a_NH3": a, "lnK_H": KH_c, "b_H2": bh,
                                  "lnK_N": KN_c, "adsorption_exponent_m": m,
                                  "label": "python (least-squares fit of the native form to the published microkinetic rate; not a literature value)"},
            "fit_range": {"T_K": list(T_fit), "y_NH3": [0.02, 1.0], "y_H2": [1e-4, 0.7], "n_samples": int(len(S))},
            "rate_error_vs_python_law": {"rms_rel": float(np.sqrt(np.mean(np.expm1(fit.fun) ** 2))), "max_rel": float(rel.max())},
            "conversion_error_vs_python_pfr": {"max_abs": float(max(conv_err)), "points": len(conv_err)},
            "note": "rate in Python is in mol/(kg s); 1 mol/(kg s) = 1e-3 kmol/(kg s): k above is given in kmol/(kg s)",
        },
        "bed_properties": {"particle_density_kg_m3": {"value": DEFAULT_BED["rho_particle_kg_m3"], "source": "assumption (no bed data in takahashi2016kinetic); kum2026heatintegrated Table 1 values as in pfr.py"},
                           "bed_voidage": {"value": DEFAULT_BED["eps_b"], "source": "assumption, as above"},
                           "bulk_density_kg_m3": {"value": (1 - DEFAULT_BED["eps_b"]) * DEFAULT_BED["rho_particle_kg_m3"], "source": "derived"},
                           "particle_diameter_m": {"value": DEFAULT_BED["dp_m"], "source": "assumption, as above (source: 22-42 mesh powder)"}},
        "validity": cat.validity,
        "reference_test_points": pts,
    }


def main() -> None:
    lnKp = fit_lnKp()
    specs = [kum_spec(lnKp),
             lucentini_spec("nire_ceo2_5ni1ru_lucentini_lhhw", lnKp),
             lucentini_spec("nire_ceo2_2p5ni0p5ru_lucentini_lhhw", lnKp),
             takahashi_spec("ni_takahashi_microkinetic", lnKp, (623.15, 923.15)),
             takahashi_spec("ru_takahashi_microkinetic", lnKp, (573.15, 823.15))]
    out = {
        "provenance": provenance(SCRIPT, "kinetics.yaml laws converted to Aspen Plus LHHW input; test points from amcrax PFR "
                                         "(isothermal, no pressure drop, 100 kmol/h NH3)"),
        "status": "version 2 (complete set of implemented catalysts)",
        "how_to_use": [
            "Reaction set type LHHW, one reaction NH3 -> 0.5 N2 + 1.5 H2, vapour phase, rate basis Cat (wt).",
            "Enter k and E in the kinetic factor (T0 blank); driving-force term 1 and term 2 exponents and ln K = A + B/T + C lnT + D T;",
            "adsorption terms and adsorption exponent as listed. Units SI (kmol, kg, s, J/kmol, K; Pa or kmol/m3).",
            "RPlug: isothermal at T, no pressure drop, catalyst loading = W_cat_kg, bed voidage as listed, for cross-check with reference_test_points.",
            "Aspen equilibrium (PENG-ROB) differs slightly from the ideal-gas Kp used here; differences near equilibrium are expected.",
        ],
        "equilibrium_constant_fit": lnKp,
        "catalysts": specs,
        "not_included": {
            "Ni/CeO2, Ru/CeO2 (lucentini2019ceo2)": "no rate law, no Ea and no orders in the paper (conversion data only); not modellable",
            "Ru-K/CaO (sayas2020rukcao)": "full text not retrievable (publisher and repository blocked automated access); no k0 available",
        },
    }
    write_json(OUT / "aspen_kinetics_spec.json", out)
    for s in specs:
        e = s.get("native_form_error_vs_python") or s["best_native_approximation"]["conversion_error_vs_python_pfr"]
        print(s["catalyst_id"], s["aspen_native"], e, [round(p["X_python"], 4) for p in s["reference_test_points"]])
    print("lnKp fit max rel err", lnKp["max_rel_error_K"])


if __name__ == "__main__":
    main()
