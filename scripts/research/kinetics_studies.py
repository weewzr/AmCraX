"""Workstream K, task 4: kinetic versus equilibrium studies for every implemented catalyst at process conditions.

Deterministic; run from the project root:  python scripts/research/kinetics_studies.py
Basis: pure NH3, 100 kmol/h (baseline flowsheet basis), isothermal plug flow, no pressure drop (intrinsic-kinetics
comparison; effectiveness factor 1), AmCraX equilibrium approach factor ON for the irreversible published laws.
Baseline operating point of the flowsheet: 600 degC, 20 bar (amcrax.schemas CaseInputs defaults).
EVERY result outside a law's fitted range (kinetics.yaml validity) is an extrapolation and is flagged per row.
Writes results/research/kinetics/study_*.json/.csv, assumptions.json and results/figures/research/kinetics_*.png.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
from kinetics_common import (ALL_STUDY_CATALYSTS, FIG, OUT, footer, provenance, write_csv, write_json)
from scipy.optimize import brentq

from amcrax.kinetics import get_catalyst
from amcrax.reactor.pfr import _eq_conversion, catalyst_mass_for_conversion, simulate_pfr

SCRIPT = "scripts/research/kinetics_studies.py"
FEED = {"NH3": 100.0}
W_PRACTICAL = 1000.0       # kg catalyst for 100 kmol/h NH3 (assumption: illustrative practical loading, W/F = 36 kg s/mol)
P_BASE, T_BASE = 20.0, 600.0
# bed properties per catalyst (used for GHSV and residence time only; no pressure drop in these studies)
BED = {
    "ru_kum_temkin_pyzhev": {"eps_b": 0.36, "rho_particle_kg_m3": 980.0, "source": "kum2026heatintegrated Table 1"},
    "nire_ceo2_5ni1ru_lucentini_lhhw": {"eps_b": 0.36, "rho_particle_kg_m3": 1651.8,
                                        "source": "rho: lucentini2021nirukinetic Sec. 2.4; eps: assumption (Kum value)"},
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": {"eps_b": 0.36, "rho_particle_kg_m3": 1651.8,
                                            "source": "rho: lucentini2021nirukinetic Sec. 2.4; eps: assumption (Kum value)"},
    "ni_takahashi_microkinetic": {"eps_b": 0.36, "rho_particle_kg_m3": 980.0, "source": "assumption (pfr.py defaults, Kum values)"},
    "ru_takahashi_microkinetic": {"eps_b": 0.36, "rho_particle_kg_m3": 980.0, "source": "assumption (pfr.py defaults, Kum values)"},
}
SEED = {"ru_kum_temkin_pyzhev": "pfr x_seed 1e-6 (rate singular at p_H2 = 0)"}


def in_range(cid, T_C, P):
    v = get_catalyst(cid).validity
    T = T_C + 273.15
    return bool(v["T_min_K"] - 1e-6 <= T <= v["T_max_K"] + 1e-6 and v["P_min_bar"] - 1e-6 <= P <= v["P_max_bar"] + 1e-6)


def run(cid, W, T_C, P):
    b = BED[cid]
    return simulate_pfr(cid, W, T_in_C=T_C, P_in_bar=P, feed_kmol_h=FEED, mode="isothermal", pressure_drop=False,
                        eps_b=b["eps_b"], rho_particle_kg_m3=b["rho_particle_kg_m3"], n_points=2)


def row(cid, W, T_C, P, extra=None):
    r = run(cid, W, T_C, P)
    d = {"catalyst_id": cid, "T_C": T_C, "P_bar": P, "W_cat_kg": W, "W_over_F_kg_s_per_mol": r.W_over_F_kg_s_per_mol_NH3,
         "GHSV_h_inv": r.GHSV_h_inv, "X_kinetic": r.outlet["conversion"], "X_eq": r.outlet["X_eq_outlet"],
         "approach_to_equilibrium": r.outlet["approach_to_equilibrium"], "within_fitted_range": in_range(cid, T_C, P),
         "source_type": "python"}
    if extra:
        d.update(extra)
    return d


def main() -> None:
    import matplotlib.pyplot as plt
    from amcrax.plotstyle import PALETTE, apply_style
    apply_style()
    prov_common = ("pure NH3 100 kmol/h, isothermal PFR, no pressure drop, effectiveness factor 1, approach factor ON for "
                   "irreversible published laws; laws from backend/amcrax/data/kinetics.yaml")
    FOOT = "python (amcrax PFR) with literature rate laws; dashed = equilibrium; outside each law's fitted range = extrapolation"
    labels = {c: get_catalyst(c).label for c in ALL_STUDY_CATALYSTS}

    # 1) conversion vs temperature at the practical mass, 1 and 20 bar
    T_grid = list(range(350, 801, 25))
    rows_T = [row(c, W_PRACTICAL, T, P) for P in (1.01325, P_BASE) for c in ALL_STUDY_CATALYSTS for T in T_grid]
    write_csv(OUT / "study_conversion_vs_T.csv", rows_T)
    write_json(OUT / "study_conversion_vs_T.json", {"provenance": provenance(SCRIPT, prov_common + f"; W = {W_PRACTICAL} kg"), "rows": rows_T})
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, P in zip(axs, (1.01325, P_BASE)):
        for i, c in enumerate(ALL_STUDY_CATALYSTS):
            rr = [r for r in rows_T if r["catalyst_id"] == c and r["P_bar"] == P]
            ax.plot([r["T_C"] for r in rr], [100 * r["X_kinetic"] for r in rr], color=PALETTE[i], label=labels[c])
        rr = [r for r in rows_T if r["catalyst_id"] == ALL_STUDY_CATALYSTS[0] and r["P_bar"] == P]
        ax.plot([r["T_C"] for r in rr], [100 * r["X_eq"] for r in rr], "k--", lw=1.2, label="equilibrium")
        ax.set_title(f"{P:g} bar, W = {W_PRACTICAL:g} kg per 100 kmol/h NH3")
        ax.set_xlabel("Temperature (degC)")
    axs[0].set_ylabel("NH3 conversion (%)")
    axs[1].legend(fontsize=7)
    footer(fig, FOOT)
    fig.savefig(FIG / "kinetics_conversion_vs_T.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    # 2) conversion vs pressure at 500 and 600 degC
    P_grid = [1.01325, 2, 5, 10, 15, 20, 30, 40]
    rows_P = [row(c, W_PRACTICAL, T, P) for T in (500.0, T_BASE) for c in ALL_STUDY_CATALYSTS for P in P_grid]
    write_csv(OUT / "study_conversion_vs_P.csv", rows_P)
    write_json(OUT / "study_conversion_vs_P.json", {"provenance": provenance(SCRIPT, prov_common + f"; W = {W_PRACTICAL} kg"), "rows": rows_P})
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, T in zip(axs, (500.0, T_BASE)):
        for i, c in enumerate(ALL_STUDY_CATALYSTS):
            rr = [r for r in rows_P if r["catalyst_id"] == c and r["T_C"] == T]
            ax.plot([r["P_bar"] for r in rr], [100 * r["X_kinetic"] for r in rr], color=PALETTE[i], label=labels[c])
        rr = [r for r in rows_P if r["catalyst_id"] == ALL_STUDY_CATALYSTS[0] and r["T_C"] == T]
        ax.plot([r["P_bar"] for r in rr], [100 * r["X_eq"] for r in rr], "k--", lw=1.2, label="equilibrium")
        ax.set_title(f"{T:g} degC, W = {W_PRACTICAL:g} kg")
        ax.set_xlabel("Pressure (bar)")
    axs[0].set_ylabel("NH3 conversion (%)")
    axs[1].legend(fontsize=7)
    footer(fig, FOOT)
    fig.savefig(FIG / "kinetics_conversion_vs_P.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    # 3) conversion vs catalyst mass (W/F) and vs GHSV at 500 and 600 degC, 20 bar
    W_grid = [float(w) for w in np.logspace(0, 5, 21)]
    rows_W = [row(c, W, T, P_BASE) for T in (500.0, T_BASE) for c in ALL_STUDY_CATALYSTS for W in W_grid]
    write_csv(OUT / "study_conversion_vs_W_and_GHSV.csv", rows_W)
    write_json(OUT / "study_conversion_vs_W_and_GHSV.json", {"provenance": provenance(SCRIPT, prov_common + "; 20 bar; GHSV = normal (0 degC, 1 atm) feed / bed volume"), "rows": rows_W})
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for i, c in enumerate(ALL_STUDY_CATALYSTS):
        rr = [r for r in rows_W if r["catalyst_id"] == c and r["T_C"] == T_BASE]
        axs[0].semilogx([r["W_over_F_kg_s_per_mol"] for r in rr], [100 * r["X_kinetic"] for r in rr], color=PALETTE[i], label=labels[c])
        axs[1].semilogx([r["GHSV_h_inv"] for r in rr], [100 * r["X_kinetic"] for r in rr], color=PALETTE[i], label=labels[c])
    xe = 100 * rows_W[-1]["X_eq"]
    for ax in axs:
        ax.axhline(xe, color="k", ls="--", lw=1.2, label="equilibrium")
    axs[0].set_xlabel("W/F_NH3,0 (kg s/mol)")
    axs[1].set_xlabel("GHSV (1/h, normal basis)")
    axs[0].set_ylabel("NH3 conversion (%)")
    axs[0].set_title(f"{T_BASE:g} degC, {P_BASE:g} bar")
    axs[1].legend(fontsize=7)
    footer(fig, FOOT)
    fig.savefig(FIG / "kinetics_conversion_vs_W_GHSV.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    # 4) catalyst mass for 90/95/99 % of equilibrium conversion vs T (20 bar)
    rows_M = []
    for c in ALL_STUDY_CATALYSTS:
        b = BED[c]
        for T in range(400, 801, 50):
            for f in (0.90, 0.95, 0.99):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    d = catalyst_mass_for_conversion(c, fraction_of_equilibrium=f, T_in_C=float(T), P_in_bar=P_BASE,
                                                     feed_kmol_h=FEED, mode="isothermal", pressure_drop=False,
                                                     eps_b=b["eps_b"], rho_particle_kg_m3=b["rho_particle_kg_m3"],
                                                     W_max_kg=1e7, return_details=True)
                rows_M.append({"catalyst_id": c, "T_C": T, "P_bar": P_BASE, "fraction_of_equilibrium": f,
                               "X_target": d["target_conversion"], "W_cat_kg": d["W_kg"], "reachable_within_1e7_kg": d["reachable"],
                               "within_fitted_range": in_range(c, T, P_BASE), "source_type": "python"})
    write_csv(OUT / "study_mass_for_fraction_of_equilibrium.csv", rows_M)
    write_json(OUT / "study_mass_for_fraction_of_equilibrium.json", {"provenance": provenance(SCRIPT, prov_common + "; 20 bar; W_max 1e7 kg"), "rows": rows_M})
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, f in zip(axs, (0.90, 0.95, 0.99)):
        for i, c in enumerate(ALL_STUDY_CATALYSTS):
            rr = [r for r in rows_M if r["catalyst_id"] == c and r["fraction_of_equilibrium"] == f and r["reachable_within_1e7_kg"]]
            ax.semilogy([r["T_C"] for r in rr], [r["W_cat_kg"] for r in rr], "o-", color=PALETTE[i], label=labels[c])
        ax.set_title(f"{100 * f:g} % of equilibrium, {P_BASE:g} bar")
        ax.set_xlabel("Temperature (degC)")
    axs[0].set_ylabel("Catalyst mass for 100 kmol/h NH3 (kg)")
    axs[2].legend(fontsize=6.5)
    footer(fig, FOOT)
    fig.savefig(FIG / "kinetics_mass_for_equilibrium_fraction.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    # 5) temperature needed for 95 % and 99 % conversion at the practical mass (1 and 20 bar)
    rows_TT = []
    for P, Wfix, c, X_t in [(P, Wf, c, X) for P in (1.01325, P_BASE) for Wf in (100.0, W_PRACTICAL)
                            for c in ALL_STUDY_CATALYSTS for X in (0.95, 0.99)]:
        def g(T, c=c, Wfix=Wfix, P=P, X_t=X_t):
            return run(c, Wfix, T, P).outlet["conversion"] - X_t
        T_lo, T_hi = 300.0, 900.0
        try:
            ok = g(T_lo) < 0 < g(T_hi)
        except Exception:  # noqa: BLE001
            ok = False
        T_need = brentq(g, T_lo, T_hi, xtol=0.05) if ok else float("nan")
        # equilibrium-limited minimum temperature
        Te = brentq(lambda T: _eq_conversion(T + 273.15, P, FEED) - X_t, 150.0, 1100.0, xtol=0.05)
        rows_TT.append({"catalyst_id": c, "P_bar": P, "W_cat_kg": Wfix, "X_target": X_t,
                        "T_required_C": T_need, "T_equilibrium_min_C": Te,
                        "kinetic_penalty_K": T_need - Te if not math.isnan(T_need) else float("nan"),
                        "within_fitted_range": (in_range(c, T_need, P) if not math.isnan(T_need) else None),
                        "note": "" if ok else "target not reached between 300 and 900 degC",
                        "source_type": "python"})
    write_csv(OUT / "study_temperature_for_target_conversion.csv", rows_TT)
    write_json(OUT / "study_temperature_for_target_conversion.json", {"provenance": provenance(SCRIPT, prov_common + "; W = 100 and 1000 kg"), "rows": rows_TT})

    assumptions = [
        {"name": "feed", "value": "100 kmol/h pure NH3", "unit": "kmol/h", "source_type": "assumption",
         "source": "baseline flowsheet basis (config/flowsheet.json 100 kmol/h; 0.2 % H2O omitted for a pure-NH3 kinetic comparison)",
         "applicability_note": "scales linearly: W at other throughputs = W x (F/100 kmol/h)"},
        {"name": "practical catalyst mass", "value": W_PRACTICAL, "unit": "kg per 100 kmol/h NH3", "source_type": "assumption",
         "source": "illustrative choice (W/F = 36 kg s/mol)", "applicability_note": "used only for the fixed-mass studies"},
        {"name": "reactor model", "value": "isothermal PFR, no pressure drop, effectiveness factor 1", "unit": "-", "source_type": "assumption",
         "source": "amcrax.reactor.pfr", "applicability_note": "intrinsic-kinetics comparison; pellet diffusion and heat supply limits not included"},
        {"name": "equilibrium approach factor", "value": "ON for takahashi and lucentini laws", "unit": "-", "source_type": "assumption",
         "source": "kinetics.yaml equilibrium_approach_factor (AmCraX extension)", "applicability_note": "published laws are irreversible"},
        {"name": "flow reference state for Lucentini mL/min", "value": "0 degC, 1 atm", "unit": "-", "source_type": "assumption",
         "source": "not stated in lucentini2021nirukinetic", "applicability_note": "25 degC tested: conversions change by <= 0.03"},
        {"name": "Lucentini bed voidage for industrial bed", "value": 0.36, "unit": "-", "source_type": "assumption",
         "source": "kum2026heatintegrated Table 1 value reused", "applicability_note": "affects GHSV and residence time only"},
    ] + [{"name": f"bed {c}", "value": BED[c], "unit": "eps -, rho kg/m3", "source_type": "literature/assumption",
          "source": BED[c]["source"], "applicability_note": "GHSV conversion"} for c in ALL_STUDY_CATALYSTS]
    write_json(OUT / "assumptions.json", assumptions)

    for r in rows_TT:
        print(r["catalyst_id"], r["P_bar"], r["W_cat_kg"], r["X_target"], round(r["T_required_C"], 1), round(r["T_equilibrium_min_C"], 1))
    for r in rows_M:
        if r["T_C"] in (500, 600):
            print(r["catalyst_id"], r["T_C"], r["fraction_of_equilibrium"], round(r["W_cat_kg"], 1))


if __name__ == "__main__":
    main()
