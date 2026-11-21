"""Decompose the Aspen Plus RGibbs vs AmCraX Python equilibrium discrepancy into its causes.

    python scripts/analyse_equilibrium_discrepancy.py

Nothing is adjusted to force agreement: the script only *explains* the difference.

Inputs (never fabricated; produced by real Aspen Plus V15 runs and by amcrax.thermodynamics):
  results/validation/equilibrium_aspen_grid.csv     (Aspen RGibbs, PENG-ROB and IDEAL, pure NH3 feed)
  backend/amcrax/thermodynamics/reference/janaf.json (NIST-JANAF 4th ed., parsed tables)
Outputs:
  results/validation/equilibrium_discrepancy.csv
  results/validation/equilibrium_discrepancy_summary.json
  results/figures/validation_lnK_offset.png
  results/figures/validation_eos_effect.png
  results/figures/validation_parity_by_method.png

Method
------
(a) Thermochemical data. For each Aspen IDEAL point the equilibrium constant implied by the Aspen
    composition is  Kp = y_N2^0.5 y_H2^1.5 / y_NH3 * (P / 1 bar)  (ideal gas, NH3 <-> 0.5 N2 + 1.5 H2).
    d(lnK) = lnK_aspen - lnK_python;  equivalent Gibbs offset dG = -R T d(lnK)  [J/mol NH3].
    The same is done for NIST-JANAF (dG_rxn = -dGf(NH3), cubic spline of the tabulated 100 K grid).
    Reaction enthalpy: Aspen IDEAL heat duty / conversion (isothermal, feed at T => Q = X dH_r(T)),
    Python reaction_enthalpy_kJ_mol(T), JANAF -dHf(NH3).
(b) Equation of state: dX_EOS = X(PENG-ROB) - X(IDEAL) in Aspen vs X(pr) - X(ideal) in Python
    (Python PR uses k_ij = 0; Aspen uses databank PRKBV k_ij from EOS-LIT).
(c) Amplification: for an ideal gas with pure NH3 feed,
    lnK = ln(0.5^0.5 1.5^1.5) + 2 ln X - ln(1 - X^2) + ln P  =>  dX/dlnK = X (1 - X^2) / 2.
    The predicted conversion shift from the data offset is dX/dlnK * d(lnK). Because d(lnK) is back-calculated
    from Aspen's own composition, this reproduces the Aspen conversion by construction (the residual is the
    second-order Taylor term): it re-expresses the difference as an equivalent dG offset, it does not explain it.
(d) k_ij SENSITIVITY (not a calibration, used nowhere): the PR-vs-PR conversion gap at 250 C / 40 bar as a
    function of one Python k_ij at a time (NH3-H2, NH3-N2, H2-N2; illustrative range +/-0.3), and the single
    k_ij value that would close it ("what k_ij would be needed"). Stored in the summary JSON.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline

from amcrax import paths
from amcrax.plotstyle import (C_AMBER, C_GREY, C_HEAT, C_N2, C_NH3, C_PRIMARY, add_provenance, apply_style,
                              plt, save)
from amcrax.thermodynamics import (R_J_molK, reaction_enthalpy_kJ_mol, reaction_gibbs_kJ_mol,
                                   solve_equilibrium)

ASPEN_GRID = paths.RESULTS_VALIDATION / "equilibrium_aspen_grid.csv"
JANAF = paths.ROOT / "backend" / "amcrax" / "thermodynamics" / "reference" / "janaf.json"
OUT_CSV = paths.RESULTS_VALIDATION / "equilibrium_discrepancy.csv"
OUT_JSON = paths.RESULTS_VALIDATION / "equilibrium_discrepancy_summary.json"
C0 = 0.5 ** 0.5 * 1.5 ** 1.5


def janaf_reaction() -> tuple[CubicSpline, CubicSpline, tuple[float, float]]:
    """Cubic splines of dG_rxn(T), dH_rxn(T) (kJ/mol NH3) for NH3 -> 0.5 N2 + 1.5 H2 from JANAF dGf/dHf(NH3)."""
    d = json.loads(JANAF.read_text(encoding="utf-8"))
    cols = d["columns"]
    rows = d["species"]["NH3"]["rows"]
    iT, iG, iH = cols.index("T_K"), cols.index("dGf_kJ_mol"), cols.index("dHf_kJ_mol")
    T = np.array([r[iT] for r in rows], float)
    G = -np.array([r[iG] for r in rows], float)
    H = -np.array([r[iH] for r in rows], float)
    return CubicSpline(T, G), CubicSpline(T, H), (float(T.min()), float(T.max()))


def lnK_from_y(y_nh3: float, y_h2: float, y_n2: float, P_bar: float) -> float:
    return 0.5 * math.log(y_n2) + 1.5 * math.log(y_h2) - math.log(y_nh3) + math.log(P_bar)


def dX_dlnK(X: float) -> float:
    return X * (1.0 - X * X) / 2.0


def load_aspen() -> list[dict]:
    with ASPEN_GRID.open(newline="") as f:
        return [{k: (v if k == "property_method" else float(v)) for k, v in r.items()} for r in csv.DictReader(f)]


def analyse() -> tuple[list[dict], dict]:
    rows = load_aspen()
    gJ, hJ, (tmin, tmax) = janaf_reaction()
    by = {(r["T_C"], r["P_bar"], r["property_method"].upper()): r for r in rows}
    keys = sorted({(r["T_C"], r["P_bar"]) for r in rows})
    out = []
    for T_C, P in keys:
        a_id = by.get((T_C, P, "IDEAL"))
        a_pr = by.get((T_C, P, "PENG-ROB"))
        T = T_C + 273.15
        py_id = solve_equilibrium(T, P, {"NH3": 1.0}, eos="ideal")
        py_pr = solve_equilibrium(T, P, {"NH3": 1.0}, eos="pr")
        lnK_py = math.log(py_id.K_eq)
        rec = {"T_C": T_C, "T_K": T, "P_bar": P,
               "X_python_ideal": py_id.conversion, "X_python_pr": py_pr.conversion,
               "lnK_python": lnK_py,
               "dG_rxn_python_kJ_mol": reaction_gibbs_kJ_mol(T),
               "dH_rxn_python_kJ_mol": reaction_enthalpy_kJ_mol(T)}
        if tmin <= T <= tmax:
            gj = float(gJ(T))
            rec["dG_rxn_janaf_kJ_mol"] = gj
            rec["lnK_janaf"] = -gj * 1000.0 / (R_J_molK * T)
            rec["dH_rxn_janaf_kJ_mol"] = float(hJ(T))
        if a_id:
            lnK_a = lnK_from_y(a_id["y_NH3"], a_id["y_H2"], a_id["y_N2"], P)
            rec.update({"X_aspen_ideal": a_id["nh3_conversion"], "lnK_aspen_ideal": lnK_a,
                        "dG_rxn_aspen_implied_kJ_mol": -R_J_molK * T * lnK_a / 1000.0,
                        "dH_rxn_aspen_ideal_kJ_mol": a_id["heat_duty_kJ_per_mol_NH3_fed"] / a_id["nh3_conversion"]})
            rec["dlnK_aspen_minus_python"] = lnK_a - lnK_py
            rec["dG_offset_aspen_minus_python_J_mol"] = -R_J_molK * T * (lnK_a - lnK_py)
            rec["dH_aspen_minus_python_kJ_mol"] = rec["dH_rxn_aspen_ideal_kJ_mol"] - rec["dH_rxn_python_kJ_mol"]
            rec["dX_ideal_aspen_minus_python_pp"] = 100 * (a_id["nh3_conversion"] - py_id.conversion)
            rec["dXdlnK_python_ideal"] = dX_dlnK(py_id.conversion)
            rec["dX_predicted_from_dlnK_pp"] = 100 * dX_dlnK(py_id.conversion) * (lnK_a - lnK_py)
        if "lnK_janaf" in rec:
            rec["dG_offset_janaf_minus_python_J_mol"] = -R_J_molK * T * (rec["lnK_janaf"] - lnK_py)
            rec["dH_janaf_minus_python_kJ_mol"] = rec["dH_rxn_janaf_kJ_mol"] - rec["dH_rxn_python_kJ_mol"]
            if a_id:
                rec["dG_offset_aspen_minus_janaf_J_mol"] = -R_J_molK * T * (rec["lnK_aspen_ideal"] - rec["lnK_janaf"])
                rec["dH_aspen_minus_janaf_kJ_mol"] = rec["dH_rxn_aspen_ideal_kJ_mol"] - rec["dH_rxn_janaf_kJ_mol"]
        if a_pr:
            rec["X_aspen_pr"] = a_pr["nh3_conversion"]
            rec["dX_pr_aspen_minus_python_pp"] = 100 * (a_pr["nh3_conversion"] - py_pr.conversion)
            rec["dX_aspenPR_minus_pythonIdeal_pp"] = 100 * (a_pr["nh3_conversion"] - py_id.conversion)
        rec["eos_effect_python_pp"] = 100 * (py_pr.conversion - py_id.conversion)
        # sensitivity: Boston-Mathias alpha above Tc (what Aspen PENG-ROB applies to supercritical components)
        py_bm = solve_equilibrium(T, P, {"NH3": 1.0}, eos="pr", alpha="boston-mathias")
        rec["X_python_pr_boston_mathias"] = py_bm.conversion
        rec["eos_effect_python_bm_pp"] = 100 * (py_bm.conversion - py_id.conversion)
        if a_pr and a_id:
            rec["eos_effect_aspen_pp"] = 100 * (a_pr["nh3_conversion"] - a_id["nh3_conversion"])
            rec["eos_effect_diff_aspen_minus_python_pp"] = rec["eos_effect_aspen_pp"] - rec["eos_effect_python_pp"]
            # additive decomposition of the PR-vs-PR deviation (exact identity)
            rec["decomp_data_pp"] = rec["dX_ideal_aspen_minus_python_pp"]
            rec["decomp_eos_pp"] = rec["eos_effect_diff_aspen_minus_python_pp"]
            rec["eos_effect_diff_aspen_minus_python_bm_pp"] = rec["eos_effect_aspen_pp"] - rec["eos_effect_python_bm_pp"]
        out.append(rec)

    def stat(key, fn, sub=out):
        v = np.array([r[key] for r in sub if key in r and np.isfinite(r[key])], float)
        return float(fn(v)) if v.size else None

    def argmax_abs(key):
        sub = [r for r in out if key in r]
        if not sub:
            return None
        r = max(sub, key=lambda r: abs(r[key]))
        return {"T_C": r["T_C"], "P_bar": r["P_bar"], "value": r[key]}

    # dG offset is meaningful only where y_NH3 is resolved; flag points with X > 0.999 (y_NH3 < ~5e-4)
    resolved = [r for r in out if "X_aspen_ideal" in r and r["X_aspen_ideal"] < 0.999]
    summ = {
        "n_points": len(out),
        "dG_offset_aspen_minus_python_J_mol": {
            "mean": stat("dG_offset_aspen_minus_python_J_mol", np.mean, resolved),
            "min": stat("dG_offset_aspen_minus_python_J_mol", np.min, resolved),
            "max": stat("dG_offset_aspen_minus_python_J_mol", np.max, resolved),
            "std": stat("dG_offset_aspen_minus_python_J_mol", np.std, resolved),
            "n_resolved_points_X_lt_0.999": len(resolved)},
        "dG_offset_janaf_minus_python_J_mol": {
            "mean": stat("dG_offset_janaf_minus_python_J_mol", np.mean),
            "min": stat("dG_offset_janaf_minus_python_J_mol", np.min),
            "max": stat("dG_offset_janaf_minus_python_J_mol", np.max)},
        "dG_offset_aspen_minus_janaf_J_mol": {
            "mean": stat("dG_offset_aspen_minus_janaf_J_mol", np.mean, resolved),
            "min": stat("dG_offset_aspen_minus_janaf_J_mol", np.min, resolved),
            "max": stat("dG_offset_aspen_minus_janaf_J_mol", np.max, resolved)},
        "mean_abs_dG_vs_janaf_J_mol": {
            "aspen": stat("dG_offset_aspen_minus_janaf_J_mol", lambda v: np.mean(np.abs(v)), resolved),
            "python": stat("dG_offset_janaf_minus_python_J_mol", lambda v: np.mean(np.abs(v)), resolved)},
        "dH_aspen_minus_python_kJ_mol": {"mean": stat("dH_aspen_minus_python_kJ_mol", np.mean),
                                         "min": stat("dH_aspen_minus_python_kJ_mol", np.min),
                                         "max": stat("dH_aspen_minus_python_kJ_mol", np.max)},
        "mean_abs_dH_vs_janaf_kJ_mol": {
            "aspen": stat("dH_aspen_minus_janaf_kJ_mol", lambda v: np.mean(np.abs(v))),
            "python": stat("dH_janaf_minus_python_kJ_mol", lambda v: np.mean(np.abs(v)))},
        "max_abs_dX_ideal_vs_ideal_pp": argmax_abs("dX_ideal_aspen_minus_python_pp"),
        "max_abs_dX_pr_vs_pr_pp": argmax_abs("dX_pr_aspen_minus_python_pp"),
        "max_abs_dX_aspenPR_vs_pythonIdeal_pp": argmax_abs("dX_aspenPR_minus_pythonIdeal_pp"),
        "mean_abs_dX_ideal_vs_ideal_pp": stat("dX_ideal_aspen_minus_python_pp", lambda v: np.mean(np.abs(v))),
        "mean_abs_dX_pr_vs_pr_pp": stat("dX_pr_aspen_minus_python_pp", lambda v: np.mean(np.abs(v))),
        "mean_abs_dX_aspenPR_vs_pythonIdeal_pp": stat("dX_aspenPR_minus_pythonIdeal_pp", lambda v: np.mean(np.abs(v))),
        "max_abs_eos_effect_aspen_pp": argmax_abs("eos_effect_aspen_pp"),
        "max_abs_eos_effect_python_pp": argmax_abs("eos_effect_python_pp"),
        "max_abs_eos_effect_diff_pp": argmax_abs("eos_effect_diff_aspen_minus_python_pp"),
        "max_abs_eos_effect_diff_with_boston_mathias_pp": argmax_abs("eos_effect_diff_aspen_minus_python_bm_pp"),
        "aspen_ideal_duty_anomalies": [
            {"T_C": r["T_C"], "P_bar": r["P_bar"], "dH_aspen_minus_python_kJ_mol": r["dH_aspen_minus_python_kJ_mol"]}
            for r in out if abs(r.get("dH_aspen_minus_python_kJ_mol", 0.0)) > 0.2],
        "max_abs_residual_dX_ideal_minus_predicted_pp": None,
        "dG_offset_max_spread_over_P_at_fixed_T_J_mol": max(
            (lambda v: (max(v) - min(v)) if v else 0.0)(
                [r["dG_offset_aspen_minus_python_J_mol"] for r in resolved if r["T_C"] == t]) for t in
            {r["T_C"] for r in resolved}),
        "dH_aspen_minus_python_median_kJ_mol": stat("dH_aspen_minus_python_kJ_mol", np.median),
        "dXdlnK_range": [stat("dXdlnK_python_ideal", np.min), stat("dXdlnK_python_ideal", np.max)],
    }
    for r in out:
        if "dX_predicted_from_dlnK_pp" in r:
            r["_resid"] = r["dX_ideal_aspen_minus_python_pp"] - r["dX_predicted_from_dlnK_pp"]
    summ["max_abs_residual_dX_ideal_minus_predicted_pp"] = argmax_abs("_resid")
    for r in out:
        if "_resid" in r:
            r["dX_ideal_residual_after_dlnK_pp"] = r.pop("_resid")
    # the Aspen IDEAL - Python conversion difference expressed as an equivalent standard-Gibbs-energy offset
    # (resolved points only; this is a restatement of the difference, not an explanation of it)
    summ["dG_offset_max_abs_resolved_J_mol"] = stat("dG_offset_aspen_minus_python_J_mol",
                                                    lambda v: np.max(np.abs(v)), resolved)
    summ["kij_sensitivity_250C_40bar"] = kij_sensitivity(by)
    return out, summ


# ------------------------------------------------------------------ k_ij SENSITIVITY (not a calibration)
KIJ_SCAN = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)
KIJ_NOTE = ("SENSITIVITY ONLY - not a calibration and not used anywhere in AmCraX (every model keeps k_ij = 0). "
            "Range +/-0.3 is illustrative: research/ holds no sourced Peng-Robinson k_ij for NH3-H2 or NH3-N2 "
            "(mehr2026highcapacity only states 'default binary interaction parameters'), and Aspen's EOS-LIT PRKBV "
            "values could not be read (aspen_binary_parameters.json). The 'needed' k_ij is the single value of one pair "
            "(the other pairs at 0) that would make Python PR reproduce Aspen PENG-ROB at this point.")


def kij_sensitivity(by: dict, T_C: float = 250.0, P_bar: float = 40.0) -> dict:
    """PR-vs-PR conversion gap at (T_C, P_bar) as a function of one k_ij at a time; the k_ij that would close it."""
    from scipy.optimize import brentq

    a_pr = by.get((T_C, P_bar, "PENG-ROB"))
    if a_pr is None:
        return {"note": KIJ_NOTE, "status": f"no Aspen PENG-ROB point at {T_C} C / {P_bar} bar"}
    T = T_C + 273.15
    X_a = a_pr["nh3_conversion"]

    def X(pair, k):
        return solve_equilibrium(T, P_bar, {"NH3": 1.0}, eos="pr", kij={pair: k}).conversion

    res = {"note": KIJ_NOTE, "T_C": T_C, "P_bar": P_bar, "X_aspen_peng_rob": X_a,
           "X_python_pr_kij0": X(("NH3", "H2"), 0.0), "pairs": {}}
    res["gap_kij0_aspen_minus_python_pp"] = 100 * (X_a - res["X_python_pr_kij0"])
    for pair in (("NH3", "H2"), ("NH3", "N2"), ("H2", "N2")):
        scan = {f"{k:+.1f}": 100 * (X_a - X(pair, k)) for k in KIJ_SCAN}
        needed = None
        try:  # wide bracket on purpose: the answer may lie far outside any physical range
            needed = brentq(lambda k: X(pair, k) - X_a, -2.0, 3.0, xtol=1e-6)
        except (ValueError, RuntimeError):
            pass
        res["pairs"]["-".join(pair)] = {"gap_aspen_minus_python_pp_vs_kij": scan,
                                       "kij_needed_to_close_gap": needed,
                                       "needed_within_illustrative_range": (needed is not None
                                                                            and abs(needed) <= max(KIJ_SCAN)),
                                       "dX_dkij_pp_per_0p1": 100 * (X(pair, 0.05) - X(pair, -0.05))}

    def X_all(k):
        return solve_equilibrium(T, P_bar, {"NH3": 1.0}, eos="pr",
                                 kij={("NH3", "H2"): k, ("NH3", "N2"): k, ("H2", "N2"): k}).conversion
    res["all_three_pairs_equal_kij"] = {f"{k:+.1f}": 100 * (X_a - X_all(k)) for k in KIJ_SCAN}
    best = max(abs(res["gap_kij0_aspen_minus_python_pp"]) - abs(v) for v in res["all_three_pairs_equal_kij"].values())
    res["max_gap_reduction_within_range_pp"] = best
    return res


def write_csv(out: list[dict]) -> None:
    cols: list[str] = []
    for r in out:
        for k in r:
            if k not in cols:
                cols.append(k)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v) for k, v in r.items()})


def figures(out: list[dict]) -> None:
    apply_style()
    Ts = sorted({r["T_C"] for r in out})
    Ps = sorted({r["P_bar"] for r in out})
    # ---- lnK offset + dH
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for P, mk in zip(Ps, "os^vDP"):
        sub = [r for r in out if r["P_bar"] == P and "dG_offset_aspen_minus_python_J_mol" in r
               and r["X_aspen_ideal"] < 0.999]
        ax[0].plot([r["T_C"] for r in sub], [r["dG_offset_aspen_minus_python_J_mol"] for r in sub], marker=mk,
                   ls="none", mfc="none", color=C_PRIMARY, label=f"Aspen IDEAL - Python, {P:g} bar")
    tj = np.linspace(250, 900, 131)
    jv = [r for r in out if "dG_offset_janaf_minus_python_J_mol" in r and r["P_bar"] == Ps[0]]
    ax[0].plot([r["T_C"] for r in jv], [r["dG_offset_janaf_minus_python_J_mol"] for r in jv], color=C_HEAT,
               lw=1.6, label="NIST-JANAF - Python")
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xlabel("Temperature (°C)")
    ax[0].set_ylabel("Equivalent ΔG° offset  −RT·Δln K  (J/mol NH$_3$)")
    ax[0].set_title("(a) Equilibrium-constant offset vs Python (GRI-Mech/NASA-7)")
    ax[0].legend(fontsize=7)
    sub = sorted([r for r in out if "dH_rxn_aspen_ideal_kJ_mol" in r and r["P_bar"] == Ps[0]], key=lambda r: r["T_C"])
    ax[1].plot([r["T_C"] for r in sub], [r["dH_rxn_aspen_ideal_kJ_mol"] for r in sub], "o", mfc="none",
               color=C_PRIMARY, label="Aspen IDEAL (duty / conversion, 1 bar)")
    pyT = sorted({r["T_C"] for r in out})
    ax[1].plot(pyT, [reaction_enthalpy_kJ_mol(t + 273.15) for t in pyT], color=C_NH3, label="Python (NASA-7)")
    jT = [r for r in out if "dH_rxn_janaf_kJ_mol" in r and r["P_bar"] == Ps[0]]
    ax[1].plot([r["T_C"] for r in jT], [r["dH_rxn_janaf_kJ_mol"] for r in jT], "--", color=C_HEAT, label="NIST-JANAF")
    ax[1].set_xlabel("Temperature (°C)")
    ax[1].set_ylabel("ΔH$_r$ (kJ/mol NH$_3$)")
    ax[1].set_title("(b) Reaction enthalpy NH$_3$ → ½N$_2$ + 1.5H$_2$")
    ax[1].legend(fontsize=7.5)
    add_provenance(fig, "Aspen IDEAL RGibbs grid; points with X > 0.999 omitted in (a) (y_NH3 not resolved)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "validation_lnK_offset")

    # ---- EOS effect
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2))
    cmap = plt.get_cmap("viridis")(np.linspace(0, 0.9, len(Ts)))
    for c, T in zip(cmap, Ts):
        sub = sorted([r for r in out if r["T_C"] == T and "eos_effect_aspen_pp" in r], key=lambda r: r["P_bar"])
        if not sub:
            continue
        ax[0].plot([r["P_bar"] for r in sub], [r["eos_effect_aspen_pp"] for r in sub], "-o", color=c, ms=3,
                   label=f"{T:g} °C" if T in Ts[::2] else None)
        ax[0].plot([r["P_bar"] for r in sub], [r["eos_effect_python_pp"] for r in sub], "--", color=c, lw=1.1)
        ax[1].plot([r["P_bar"] for r in sub], [r["eos_effect_diff_aspen_minus_python_pp"] for r in sub], "-o",
                   color=c, ms=3)
    ax[0].plot([], [], "k-o", ms=3, label="Aspen PENG-ROB − IDEAL")
    ax[0].plot([], [], "k--", label="Python pr − ideal (k$_{ij}$ = 0)")
    for a in ax:
        a.axhline(0, color="k", lw=0.6)
        a.set_xlabel("Pressure (bar)")
    ax[0].set_ylabel("ΔX from fugacity coefficients (pp)")
    ax[0].set_title("(a) Equation-of-state effect on conversion")
    ax[0].legend(fontsize=7, ncol=2)
    ax[1].set_ylabel("EOS effect: Aspen − Python (pp)")
    ax[1].set_title("(b) Difference of the EOS effects (k$_{ij}$, α-function)")
    add_provenance(fig, "pure NH3 feed, isothermal RGibbs")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "validation_eos_effect")

    # ---- parity by method
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    pairs = [("X_aspen_ideal", "X_python_ideal", "Aspen IDEAL vs Python ideal", C_PRIMARY),
             ("X_aspen_pr", "X_python_pr", "Aspen PENG-ROB vs Python pr", C_HEAT),
             ("X_aspen_pr", "X_python_ideal", "Aspen PENG-ROB vs Python ideal", C_AMBER)]
    for k, (ka, kp, lab, c) in enumerate(pairs):
        sub = [r for r in out if ka in r]
        ax[0].scatter([100 * r[ka] for r in sub], [100 * r[kp] for r in sub], s=14, facecolors="none",
                      edgecolors=c, label=lab)
    lo = min(100 * r["X_python_pr"] for r in out) - 2
    ax[0].plot([lo, 100], [lo, 100], "k-", lw=0.7)
    ax[0].set_xlabel("Aspen Plus V15 conversion (%)")
    ax[0].set_ylabel("Python conversion (%)")
    ax[0].set_title("(a) Parity")
    ax[0].legend(fontsize=7)
    for P, mk in zip(Ps, "os^vDP"):
        sub = sorted([r for r in out if r["P_bar"] == P and "dX_ideal_aspen_minus_python_pp" in r], key=lambda r: r["T_C"])
        ax[1].plot([r["T_C"] for r in sub], [r["dX_ideal_aspen_minus_python_pp"] for r in sub], marker=mk, ls="-",
                   lw=0.8, ms=3.5, color=C_PRIMARY, alpha=0.4 + 0.1 * Ps.index(P), label=f"{P:g} bar")
        ax[1].plot([r["T_C"] for r in sub], [r["dX_predicted_from_dlnK_pp"] for r in sub], ls=":", color=C_GREY, lw=0.9)
        sub = sorted([r for r in out if r["P_bar"] == P and "dX_pr_aspen_minus_python_pp" in r], key=lambda r: r["T_C"])
        ax[2].plot([r["T_C"] for r in sub], [r["dX_pr_aspen_minus_python_pp"] for r in sub], marker=mk, ls="-",
                   lw=0.8, ms=3.5, color=C_HEAT, alpha=0.4 + 0.1 * Ps.index(P), label=f"{P:g} bar")
    ax[1].plot([], [], ls=":", color=C_GREY, label="predicted: (dX/dlnK)·Δln K")
    ax[1].set_title("(b) X$_{Aspen}$ − X$_{Python}$, ideal gas (pp)")
    ax[2].set_title("(c) X$_{Aspen}$ − X$_{Python}$, Peng-Robinson (pp)")
    for a in ax[1:]:
        a.axhline(0, color="k", lw=0.6)
        a.set_xlabel("Temperature (°C)")
        a.legend(fontsize=7)
    add_provenance(fig, "AmCraX Python: amcrax.thermodynamics")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "validation_parity_by_method")


def main() -> int:
    if not ASPEN_GRID.exists():
        print(f"[analyse_equilibrium_discrepancy] missing {ASPEN_GRID}; nothing written")
        return 0
    out, summ = analyse()
    write_csv(out)
    OUT_JSON.write_text(json.dumps(summ, indent=2), encoding="utf-8")
    figures(out)
    print(json.dumps(summ, indent=1))
    print(f"wrote {OUT_CSV}, {OUT_JSON} and 3 figures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
