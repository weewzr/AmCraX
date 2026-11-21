"""Compare Aspen Plus RGibbs equilibrium results with the independent AmCraX Python model.

    python scripts/validate_equilibrium.py [--aspen PATH] [--out-dir DIR] [--fig-dir DIR]

Input (produced by the coordinator from real Aspen Plus V15 runs - never fabricated):
  results/validation/equilibrium_aspen_grid.csv
  columns: T_C,P_bar,property_method,nh3_conversion,y_NH3,y_H2,y_N2,heat_duty_kJ_per_mol_NH3_fed
  (pure NH3 feed entering RGibbs at T, P; isothermal)
Outputs:
  results/validation/equilibrium_comparison.csv
  results/figures/equilibrium_parity_aspen_python.png
  results/figures/equilibrium_deviation_vs_pressure.png
Exit code 0 with a clear message when the Aspen file is missing (nothing is written).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from amcrax import paths  # noqa: E402
from amcrax.thermodynamics import isothermal_reactor_duty_kW, solve_equilibrium  # noqa: E402

REQUIRED = ["T_C", "P_bar", "property_method", "nh3_conversion", "y_NH3", "y_H2", "y_N2", "heat_duty_kJ_per_mol_NH3_fed"]
QUANT = ["nh3_conversion", "y_NH3", "y_H2", "y_N2", "heat_duty_kJ_per_mol_NH3_fed"]


def python_point(T_C: float, P: float, eos: str) -> dict:
    T = T_C + 273.15
    feed = {"NH3": 1.0}
    r = solve_equilibrium(T, P, feed, eos=eos)
    q = isothermal_reactor_duty_kW(feed, T, r.n_out, T, P_in_bar=P, P_out_bar=P, eos=eos) * 3.6
    return {"nh3_conversion": r.conversion, "y_NH3": r.y["NH3"], "y_H2": r.y["H2"], "y_N2": r.y["N2"],
            "heat_duty_kJ_per_mol_NH3_fed": q}


def _f(x: str) -> float:
    return float(x) if x not in ("", None) else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aspen", type=Path, default=paths.RESULTS_VALIDATION / "equilibrium_aspen_grid.csv")
    ap.add_argument("--out-dir", type=Path, default=paths.RESULTS_VALIDATION)
    ap.add_argument("--fig-dir", type=Path, default=paths.RESULTS_FIGURES)
    a = ap.parse_args(argv)

    if not a.aspen.exists():
        print(f"[validate_equilibrium] Aspen grid not found: {a.aspen}\n"
              "  Nothing to compare yet - the coordinator must first export real Aspen Plus RGibbs results "
              "to this file. No output written.")
        return 0
    with a.aspen.open(newline="") as f:
        rd = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (rd.fieldnames or [])]
        if missing:
            print(f"[validate_equilibrium] ERROR: {a.aspen} lacks columns {missing}")
            return 2
        aspen_rows = list(rd)
    if not aspen_rows:
        print(f"[validate_equilibrium] {a.aspen} has no data rows. No output written.")
        return 0

    out = []
    for row in aspen_rows:
        T_C, P = _f(row["T_C"]), _f(row["P_bar"])
        for eos in ("ideal", "pr"):
            py = python_point(T_C, P, eos)
            rec = {"T_C": T_C, "P_bar": P, "aspen_property_method": row["property_method"], "python_eos": eos}
            for q in QUANT:
                asp = _f(row[q])
                rec[f"{q}_aspen"] = asp
                rec[f"{q}_python"] = py[q]
                rec[f"{q}_abs_dev"] = py[q] - asp
                rec[f"{q}_rel_dev"] = (py[q] - asp) / asp if asp not in (0.0,) and np.isfinite(asp) else float("nan")
            rec["nh3_conversion_abs_dev_pp"] = 100 * rec["nh3_conversion_abs_dev"]
            out.append(rec)

    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.fig_dir.mkdir(parents=True, exist_ok=True)
    out_csv = a.out_dir / "equilibrium_comparison.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        for r in out:
            w.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v) for k, v in r.items()})

    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
                         "font.size": 10, "axes.grid": True, "grid.alpha": 0.3})
    # parity plot
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    marks = {"ideal": ("o", "#1f77b4"), "pr": ("s", "#d62728")}
    for eos, (m, c) in marks.items():
        sub = [r for r in out if r["python_eos"] == eos]
        axes[0].scatter([100 * r["nh3_conversion_aspen"] for r in sub], [100 * r["nh3_conversion_python"] for r in sub],
                        marker=m, s=18, facecolors="none", edgecolors=c, label=f"Python ({eos})")
        axes[1].scatter([r["heat_duty_kJ_per_mol_NH3_fed_aspen"] for r in sub],
                        [r["heat_duty_kJ_per_mol_NH3_fed_python"] for r in sub],
                        marker=m, s=18, facecolors="none", edgecolors=c, label=f"Python ({eos})")
    for ax, lab in ((axes[0], "NH$_3$ conversion (%)"), (axes[1], "Reactor duty (kJ per mol NH$_3$ fed)")):
        lo, hi = ax.get_xlim()
        lo2, hi2 = ax.get_ylim()
        lo, hi = min(lo, lo2), max(hi, hi2)
        ax.plot([lo, hi], [lo, hi], "k-", lw=0.8, label="y = x")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal", "box")
        ax.set_xlabel(f"Aspen Plus V15 RGibbs: {lab}"); ax.set_ylabel(f"AmCraX Python: {lab}")
        ax.legend(fontsize=8)
    pm = sorted({r["aspen_property_method"] for r in out})
    fig.suptitle(f"Equilibrium parity: Aspen Plus RGibbs ({', '.join(pm)}) vs independent Python model", fontsize=11)
    fig.tight_layout()
    fig.savefig(a.fig_dir / "equilibrium_parity_aspen_python.png", dpi=300); plt.close(fig)

    # deviation vs pressure
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    Ts = sorted({r["T_C"] for r in out})
    cols = plt.get_cmap("plasma")(np.linspace(0, 0.85, max(len(Ts), 1)))
    for c, T in zip(cols, Ts):
        for eos, ls in (("ideal", "-"), ("pr", "--")):
            sub = sorted([r for r in out if r["T_C"] == T and r["python_eos"] == eos], key=lambda r: r["P_bar"])
            ax.plot([r["P_bar"] for r in sub], [r["nh3_conversion_abs_dev_pp"] for r in sub], ls=ls, marker=".",
                    color=c, lw=1.2, label=f"{T:g} °C" if eos == "ideal" else None)
    ax.plot([], [], "k-", label="Python ideal"); ax.plot([], [], "k--", label="Python PR")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Pressure (bar)"); ax.set_ylabel("X$_{Python}$ − X$_{Aspen}$ (percentage points)")
    ax.set_title("Equilibrium conversion deviation vs pressure", fontsize=11)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(a.fig_dir / "equilibrium_deviation_vs_pressure.png", dpi=300); plt.close(fig)

    print(f"[validate_equilibrium] {len(aspen_rows)} Aspen points compared; wrote {out_csv}")
    for eos in ("ideal", "pr"):
        sub = [r for r in out if r["python_eos"] == eos]
        dX = np.array([abs(r["nh3_conversion_abs_dev_pp"]) for r in sub])
        dQ = np.array([abs(r["heat_duty_kJ_per_mol_NH3_fed_abs_dev"]) for r in sub])
        worst = sub[int(np.nanargmax(dX))]
        print(f"  Python({eos}) vs Aspen: max |dX| = {np.nanmax(dX):.4f} pp (at {worst['T_C']:g} C, {worst['P_bar']:g} bar), "
              f"mean |dX| = {np.nanmean(dX):.4f} pp; max |dQ| = {np.nanmax(dQ):.3f} kJ/mol NH3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
