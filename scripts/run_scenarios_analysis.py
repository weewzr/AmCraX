"""AmCraX P2.6 scenario analysis: side-by-side comparison of the config/scenarios.json process scenarios
(stored Aspen Plus V15 results where converged, else Python model) with ammonia-origin / heat-source overlays.

Writes results/simulations/scenario_comparison.json, results/optimisation/scenario_comparison.csv and
results/figures/scenario_lcoh.png, scenario_ci.png, scenario_kpis.png.
"""
from __future__ import annotations

import csv
import json

import numpy as np

from amcrax import paths
from amcrax.scenarios import compare, flat_table


def main():
    paths.ensure_dirs()
    comp = compare()
    p = paths.RESULTS_SIMULATIONS / "scenario_comparison.json"
    p.write_text(json.dumps(comp, indent=1), encoding="utf-8")
    print("wrote", p)
    rows = flat_table(comp)
    p = paths.RESULTS_OPTIMISATION / "scenario_comparison.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", p)
    for r in comp["rows"]:
        m = r["metrics"]
        d = r["aspen_minus_python"] or {}
        print(f"{r['id']:22s} {r['source']:15s} LCOH {m['lcoh_USD_per_kg']:.3f} (A-P {d.get('lcoh_USD_per_kg', 0):+.4f}) "
              f"CI {m['carbon_intensity_kgCO2e_per_kgH2']:.2f} eff {m['lhv_efficiency']:.4f} X {m['nh3_conversion']:.4f}")
    figures(comp)


def figures(comp):
    import matplotlib.pyplot as plt
    from amcrax.plotstyle import C_GREY, PALETTE, apply_style, save

    apply_style()
    rows = comp["rows"]
    ids = [r["id"].replace("scn_", "") for r in rows]
    prov = ("Process data: Aspen Plus V15 stored results (per-row source); LCOH amcrax.economics; CI simplified accounting "
            "(not an LCA); grey NH3, heat deficit by burning NH3")
    x = np.arange(len(rows))
    # LCOH stacked
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    bottom = np.zeros(len(rows))
    parts = list(rows[0]["lcoh_breakdown_USD_per_kg"])
    for k, c in enumerate(parts):
        v = np.array([r["lcoh_breakdown_USD_per_kg"][c] for r in rows])
        ax.bar(x, v, bottom=bottom, label=c, color=(PALETTE + ["#64748b", "#94a3b8"])[k % 8])
        bottom += v
    ax.errorbar(x, bottom, yerr=[[0] * len(rows), [0] * len(rows)], fmt="none")
    for i, r in enumerate(rows):
        d = r["aspen_minus_python"]
        if d:
            ax.text(i, bottom[i] + 0.03, f"A-P {d['lcoh_USD_per_kg']:+.3f}", ha="center", fontsize=6.5, color=C_GREY)
    ax.set_xticks(x, ids, rotation=35, ha="right")
    ax.set_ylabel("LCOH (USD/kg H2)")
    ax.set_title("LCOH by scenario (A-P = Aspen minus Python model)")
    ax.legend(fontsize=7, ncol=4, loc="lower right")
    fig.text(0.01, -0.12, prov, fontsize=6.3, color=C_GREY)
    save(fig, "scenario_lcoh.png")
    # CI stacked + overlays
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.0), gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axs[0]
    bottom = np.zeros(len(rows))
    for k, c in enumerate(rows[0]["ci_breakdown_kgCO2e_per_kgH2"]):
        v = np.array([r["ci_breakdown_kgCO2e_per_kgH2"][c] for r in rows])
        ax.bar(x, v, bottom=bottom, label=c, color=PALETTE[k])
        bottom += v
    ax.set_xticks(x, ids, rotation=35, ha="right")
    ax.set_ylabel("kg CO2e / kg H2")
    ax.set_title("Carbon intensity by scenario (grey NH3, NH3 firing)")
    ax.legend(fontsize=7)
    ax = axs[1]
    base = next(r for r in rows if r["id"] == "baseline")
    labs, ci, lc = [], [], []
    for o in base["overlays"]:
        labs.append(f"{o['nh3_origin']}/{o['heat_source'].replace('tail_gas_plus_', '')}")
        ci.append(o["carbon_intensity_kgCO2e_per_kgH2"]); lc.append(o["lcoh_USD_per_kg"])
    for i, (l, c, v) in enumerate(zip(labs, ci, lc)):
        ax.scatter(v, c, color=PALETTE[i % 6], s=25)
        ax.annotate(l, (v, c), fontsize=6.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("LCOH (USD/kg H2)"); ax.set_ylabel("CI (kg CO2e/kg H2)")
    ax.set_title("Baseline overlays: NH3 origin x heat source", fontsize=9.5)
    fig.text(0.01, -0.12, prov + ". Green NH3 at 1000 USD/t (cho2026nickel Fig. 11); blue/grey at base 450 USD/t",
             fontsize=6.3, color=C_GREY)
    save(fig, "scenario_ci.png")
    # KPIs
    keys = [("lhv_efficiency", "LHV efficiency"), ("nh3_conversion", "NH3 conversion"),
            ("h2_yield_overall", "H2 yield"), ("specific_heat_demand_kWh_per_kgH2", "Ext. heating (kWh/kg H2)"),
            ("net_fuel_heat_deficit_kW", "Heat deficit (kW)"), ("compression_power_kW", "Compression (kW)")]
    fig, axs = plt.subplots(2, 3, figsize=(11, 5.5))
    for ax, (k, lab) in zip(axs.ravel(), keys):
        v = [r["metrics"][k] for r in rows]
        vp = [r["python_metrics"][k] for r in rows]
        ax.bar(x - 0.2, v, 0.4, label="scenario source (Aspen)", color=PALETTE[0])
        ax.bar(x + 0.2, vp, 0.4, label="Python model", color=PALETTE[1])
        ax.set_title(lab, fontsize=9)
        ax.set_xticks(x, ids, rotation=45, ha="right", fontsize=6.5)
        if k in ("lhv_efficiency", "nh3_conversion", "h2_yield_overall"):
            lo = min(v + vp)
            ax.set_ylim(lo - 0.05 * (1 - lo + 0.05), 1.0)
    axs[0, 0].legend(fontsize=6.5)
    fig.suptitle("Scenario KPIs: Aspen Plus V15 vs Python model", fontsize=10)
    fig.tight_layout()
    fig.text(0.01, -0.02, prov, fontsize=6.3, color=C_GREY)
    save(fig, "scenario_kpis.png")


if __name__ == "__main__":
    main()
