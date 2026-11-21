"""Generate the Python equilibrium grid (CSV) and equilibrium figures (source = python_model).

    python scripts/generate_equilibrium_figures.py

Outputs
  results/validation/equilibrium_python_grid.csv
  results/figures/equilibrium_conversion_vs_T.png
  results/figures/equilibrium_composition_vs_T.png
  results/figures/equilibrium_K_and_dH_vs_T.png
  results/figures/equilibrium_pr_vs_ideal.png
Pure NH3 feed, isothermal: feed enters at T, leaves at equilibrium at T, P.
"""
from __future__ import annotations

import csv
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from amcrax import paths  # noqa: E402
from amcrax.thermodynamics import (  # noqa: E402
    equilibrium_constant,
    isothermal_reactor_duty_kW,
    reaction_enthalpy_kJ_mol,
    solve_equilibrium,
)

T_C = np.arange(250, 901, 25)
P_BAR = (1, 5, 10, 20, 30, 40)
EOS = ("ideal", "pr")
COLORS = plt.get_cmap("viridis")(np.linspace(0, 0.9, len(P_BAR)))
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
                     "font.size": 10, "axes.grid": True, "grid.alpha": 0.3})
NOTE = "AmCraX Python model (NASA-7 / GRI-Mech 3.0 thermo), pure NH$_3$ feed"


def point(T_c: float, P: float, eos: str) -> dict:
    T = T_c + 273.15
    feed = {"NH3": 1.0}  # kmol/h basis; duty / feed -> kJ/mol
    r = solve_equilibrium(T, P, feed, eos=eos)
    q_kW = isothermal_reactor_duty_kW(feed, T, r.n_out, T, P_in_bar=P, P_out_bar=P, eos=eos)
    return {
        "T_C": float(T_c), "P_bar": float(P), "eos": eos,
        "nh3_conversion": r.conversion, "y_NH3": r.y["NH3"], "y_H2": r.y["H2"], "y_N2": r.y["N2"],
        "K_eq": r.K_eq, "dH_rxn_kJ_per_mol_NH3": reaction_enthalpy_kJ_mol(T),
        "heat_duty_kJ_per_mol_NH3_fed": q_kW * 3600.0 / 1000.0 / feed["NH3"],
    }


def main() -> None:
    paths.ensure_dirs()
    rows = [point(t, p, e) for e in EOS for p in P_BAR for t in T_C]
    out_csv = paths.RESULTS_VALIDATION / "equilibrium_python_grid.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v) for k, v in r.items()})
    print("wrote", out_csv, len(rows), "rows")

    def sel(eos, P, key):
        return np.array([r[key] for r in rows if r["eos"] == eos and r["P_bar"] == P])

    fig_dir = paths.RESULTS_FIGURES

    # 1. conversion vs T
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for c, P in zip(COLORS, P_BAR):
        ax.plot(T_C, 100 * sel("ideal", P, "nh3_conversion"), color=c, lw=1.8, label=f"{P} bar")
        ax.plot(T_C, 100 * sel("pr", P, "nh3_conversion"), color=c, lw=1.0, ls="--")
    ax.plot([], [], "k-", label="ideal gas"); ax.plot([], [], "k--", lw=1.0, label="Peng-Robinson")
    ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("Equilibrium NH$_3$ conversion (%)")
    ax.set_title("Equilibrium NH$_3$ conversion vs temperature", fontsize=11)
    ax.set_xlim(250, 900); ax.set_ylim(0, 101)
    ax.legend(ncol=2, fontsize=8, loc="lower right"); fig.text(0.01, 0.005, NOTE, fontsize=6.5, color="0.4")
    fig.tight_layout(); fig.savefig(fig_dir / "equilibrium_conversion_vs_T.png", dpi=300); plt.close(fig)

    # 2. composition vs T (1 bar and 20 bar, ideal)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, P in zip(axes, (1, 20)):
        for key, lab, col in (("y_NH3", "NH$_3$", "#1f77b4"), ("y_H2", "H$_2$", "#d62728"), ("y_N2", "N$_2$", "#2ca02c")):
            ax.plot(T_C, sel("ideal", P, key), color=col, lw=1.8, label=lab)
            ax.plot(T_C, sel("pr", P, key), color=col, lw=1.0, ls="--")
        ax.set_title(f"{P} bar", fontsize=11); ax.set_xlabel("Temperature (°C)"); ax.set_xlim(250, 900)
    axes[0].set_ylabel("Equilibrium mole fraction (-)"); axes[0].set_ylim(0, 0.8)
    axes[0].plot([], [], "k--", lw=1.0, label="Peng-Robinson"); axes[0].legend(fontsize=8)
    fig.text(0.01, 0.005, NOTE + "; solid = ideal gas", fontsize=6.5, color="0.4")
    fig.tight_layout(); fig.savefig(fig_dir / "equilibrium_composition_vs_T.png", dpi=300); plt.close(fig)

    # 3. K and dH vs T
    Tf = np.linspace(250, 900, 131)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.semilogy(Tf, [equilibrium_constant(t + 273.15) for t in Tf], color="#1f77b4", lw=1.8)
    ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("K (-, p° = 1 bar), NH$_3$ ⇌ ½N$_2$ + 1.5H$_2$", color="#1f77b4")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(Tf, [reaction_enthalpy_kJ_mol(t + 273.15) for t in Tf], color="#d62728", lw=1.8)
    ax2.set_ylabel("ΔH$_{rxn}$ (kJ per mol NH$_3$)", color="#d62728")
    ax.set_title("Equilibrium constant and reaction enthalpy", fontsize=11)
    fig.text(0.01, 0.005, "AmCraX Python model, NASA-7 / GRI-Mech 3.0 thermo, standard state 1 bar", fontsize=6.5, color="0.4")
    fig.tight_layout(); fig.savefig(fig_dir / "equilibrium_K_and_dH_vs_T.png", dpi=300); plt.close(fig)

    # 4. PR minus ideal conversion (percentage points)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for c, P in zip(COLORS, P_BAR):
        ax.plot(T_C, 100 * (sel("pr", P, "nh3_conversion") - sel("ideal", P, "nh3_conversion")), color=c, lw=1.6, label=f"{P} bar")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("X$_{PR}$ − X$_{ideal}$ (percentage points)")
    ax.set_title("Non-ideality effect on equilibrium conversion (Peng-Robinson, k$_{ij}$ = 0)", fontsize=10)
    ax.legend(fontsize=8); fig.text(0.01, 0.005, NOTE, fontsize=6.5, color="0.4")
    fig.tight_layout(); fig.savefig(fig_dir / "equilibrium_pr_vs_ideal.png", dpi=300); plt.close(fig)
    print("wrote 4 figures to", fig_dir)

    for P in (1, 20):
        for t in (400, 500, 600):
            vals = {e: next(r for r in rows if r["eos"] == e and r["P_bar"] == P and r["T_C"] == t) for e in EOS}
            print(f"T={t} C P={P} bar: X_ideal={vals['ideal']['nh3_conversion']:.5f} X_pr={vals['pr']['nh3_conversion']:.5f} "
                  f"Q_ideal={vals['ideal']['heat_duty_kJ_per_mol_NH3_fed']:.3f} kJ/mol")
    assert not any(math.isnan(r["nh3_conversion"]) for r in rows)


if __name__ == "__main__":
    main()
