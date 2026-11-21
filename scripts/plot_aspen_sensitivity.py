"""Publication figures of the Aspen Plus V15 sensitivity studies (results/sensitivity/aspen_*.csv)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax import plotstyle as ps  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

SENS = ROOT / "results" / "sensitivity"
FACTS: list[str] = []
DROPPED: dict[str, int] = {}


def fact(s: str) -> None:
    FACTS.append(s)
    print(s)


def load(study: str):
    p = SENS / f"aspen_{study}.csv"
    if not p.exists():
        print(f"[skip] missing {p.name}")
        return None
    df = pd.read_csv(p)
    n0 = len(df)
    conv = df["converged"].astype(str).str.lower().isin(["true", "1"])
    df = df[conv].copy()
    DROPPED[study] = n0 - len(df)
    if len(df) == 0:
        print(f"[skip] {p.name} has no converged rows")
        return None
    return df


def note(study: str) -> str:
    n = DROPPED.get(study, 0)
    return f"{n} non-converged row(s) dropped" if n else "all rows converged"


def finish(fig, name: str, study: str | list[str]) -> None:
    studies = [study] if isinstance(study, str) else study
    txt = "; ".join(dict.fromkeys(note(s) for s in studies))
    ps.add_provenance(fig, txt)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    ps.save(fig, name)
    print("wrote", name)


def base_mark(ax, x0, y0, label="Baseline (600 degC, 20 bar)"):
    ax.plot([x0], [y0], marker="*", ms=12, color="black", mfc="gold", mec="black", ls="none", zorder=6, label=label)


def at(df, col, val):
    i = (df[col] - val).abs().idxmin()
    return df.loc[i]


# ---------------------------------------------------------------- temperature
def fig_temperature():
    df = load("temperature")
    if df is None:
        return
    df = df.sort_values("reactor_temperature_C")
    T = df["reactor_temperature_C"]
    nat_p = SENS / "aspen_native_STEMP_baseline.csv"
    nat = pd.read_csv(nat_p) if nat_p.exists() else None

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(T, df["nh3_conversion"] * 100, "-o", color=ps.C_PRIMARY, label="Automated runs (COM, one case each)")
    if nat is not None:
        nat_in = nat[(nat["reactor_temperature_C"] >= T.min()) & (nat["reactor_temperature_C"] <= T.max())]
        ax.plot(nat_in["reactor_temperature_C"], nat_in["nh3_conversion"] * 100, "o", mfc="none", mec=ps.C_HEAT, ms=9,
                label="Aspen native Sensitivity block (STEMP)")
        m = df.merge(nat, on="reactor_temperature_C", suffixes=("", "_nat"))
        if len(m):
            d = {
                "conversion": (m["nh3_conversion"] - m["nh3_conversion_nat"]).abs().max(),
                "h2_product": (m["h2_product_kmol_h"] - m["h2_product_kmol_h_nat"]).abs().max(),
                "cracker_duty": (m["reactor_duty_kW"] - m["cracker_duty_kW"]).abs().max(),
                "heater_duty": (m["preheat_duty_kW"] - m["heater_duty_kW"]).abs().max(),
            }
            fact(f"Native STEMP vs automated runs over {len(m)} common temperatures: max |diff| NH3 conversion = {d['conversion']:.3e}, "
                 f"H2 product = {d['h2_product']:.3e} kmol/h, cracker duty = {d['cracker_duty']:.3e} kW, heater duty = {d['heater_duty']:.3e} kW.")
            ax.text(0.97, 0.06, f"max |diff| (conversion) = {d['conversion']:.1e}", transform=ax.transAxes, ha="right", fontsize=8)
        extra = nat[~nat["reactor_temperature_C"].isin(df["reactor_temperature_C"])]
        if len(extra):
            fact(f"Native STEMP points outside the automated range (not overlaid-compared): {sorted(extra['reactor_temperature_C'].tolist())} degC.")
    b = at(df, "reactor_temperature_C", 600)
    base_mark(ax, b["reactor_temperature_C"], b["nh3_conversion"] * 100)
    ax.set_xlabel("Cracker temperature (degC)")
    ax.set_ylabel("NH$_3$ conversion (%)")
    ax.set_title("NH$_3$ conversion vs cracker temperature (20 bar)")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 0.12))
    finish(fig, "aspen_conversion_vs_temperature", "temperature")
    lo, hi = df.iloc[0], df.iloc[-1]
    fact(f"Temperature sweep {lo['reactor_temperature_C']:.0f}-{hi['reactor_temperature_C']:.0f} degC at {b['reactor_pressure_bar']:.0f} bar: "
         f"NH3 conversion {lo['nh3_conversion']*100:.2f}% -> {hi['nh3_conversion']*100:.2f}%; at 600 degC {b['nh3_conversion']*100:.2f}%, "
         f"H2 product {b['h2_product_kmol_h']:.2f} kmol/h, cracker duty {b['reactor_duty_kW']:.0f} kW, trim heater {b['preheat_duty_kW']:.0f} kW, "
         f"FEHE recovered {b['recovered_heat_kW']:.0f} kW, total external heating {b['total_external_heating_kW']:.0f} kW, "
         f"LHV efficiency {b['lhv_efficiency']*100:.1f}%, specific heat demand {b['specific_heat_demand_kWh_per_kgH2']:.2f} kWh/kgH2.")

    # duties
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    series = [("vaporiser_duty_kW", "Vaporiser", ps.C_COLD), ("preheat_duty_kW", "Trim heater", ps.C_AMBER),
              ("reactor_duty_kW", "Cracker", ps.C_HEAT), ("recovered_heat_kW", "FEHE recovered", ps.C_NH3),
              ("cooling_duty_kW", "Cooler (magnitude)", ps.C_N2)]
    for c, l, col in series:
        ax.plot(T, df[c].abs(), "-o", ms=3.5, color=col, label=l)
    ax.plot(T, df["total_external_heating_kW"], "--", color="black", lw=1.3, label="Total external heating")
    ax.set_xlabel("Cracker temperature (degC)")
    ax.set_ylabel("Duty (kW), basis 100 kmol/h NH$_3$")
    ax.set_title("Heat duties vs cracker temperature (20 bar)")
    ax.set_ylim(0, df["total_external_heating_kW"].max() * 1.35)
    ax.legend(ncol=3, loc="upper left", fontsize=7.5)
    finish(fig, "aspen_duties_vs_temperature", "temperature")
    fact(f"Duties 400->800 degC (first/last row): cracker {lo['reactor_duty_kW']:.0f}->{hi['reactor_duty_kW']:.0f} kW, "
         f"FEHE recovered {lo['recovered_heat_kW']:.0f}->{hi['recovered_heat_kW']:.0f} kW, trim heater {lo['preheat_duty_kW']:.0f}->{hi['preheat_duty_kW']:.0f} kW, "
         f"cooler {abs(lo['cooling_duty_kW']):.0f}->{abs(hi['cooling_duty_kW']):.0f} kW.")


# ---------------------------------------------------------------- pressure
def fig_pressure():
    df = load("pressure")
    if df is None:
        return
    df = df.sort_values("reactor_pressure_bar")
    P = df["reactor_pressure_bar"]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(P, df["nh3_conversion"] * 100, "-o", color=ps.C_PRIMARY, label="NH$_3$ conversion")
    b = at(df, "reactor_pressure_bar", 20)
    base_mark(ax, b["reactor_pressure_bar"], b["nh3_conversion"] * 100)
    ax.set_xlabel("Cracker pressure (bar abs)")
    ax.set_ylabel("NH$_3$ conversion (%)")
    ax.set_title("NH$_3$ conversion vs pressure (600 degC)")
    ax.legend(loc="upper right")
    finish(fig, "aspen_conversion_vs_pressure", "pressure")

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(P, df["h2_product_kmol_h"], "-o", color=ps.C_H2, label="H$_2$ product")
    ax.set_xlabel("Cracker pressure (bar abs)")
    ax.set_ylabel("H$_2$ product (kmol/h)", color=ps.C_H2)
    ax2 = ax.twinx()
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.plot(P, df["lhv_efficiency"] * 100, "-s", color=ps.C_COLD, label="LHV efficiency")
    ax2.set_ylabel("LHV efficiency (%)", color=ps.C_COLD)
    ax.plot([b["reactor_pressure_bar"]], [b["h2_product_kmol_h"]], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (20 bar)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="center right")
    ax.set_title("H$_2$ product and LHV efficiency vs pressure (600 degC)")
    finish(fig, "aspen_h2_and_efficiency_vs_pressure", "pressure")
    lo, hi = df.iloc[0], df.iloc[-1]
    fact(f"Pressure sweep {lo['reactor_pressure_bar']:.0f}-{hi['reactor_pressure_bar']:.0f} bar at 600 degC: NH3 conversion "
         f"{lo['nh3_conversion']*100:.2f}% -> {hi['nh3_conversion']*100:.2f}%; H2 product {lo['h2_product_kmol_h']:.2f} -> {hi['h2_product_kmol_h']:.2f} kmol/h; "
         f"LHV efficiency {lo['lhv_efficiency']*100:.1f}% -> {hi['lhv_efficiency']*100:.1f}%; baseline 20 bar: conversion {b['nh3_conversion']*100:.2f}%, "
         f"H2 {b['h2_product_kmol_h']:.2f} kmol/h, efficiency {b['lhv_efficiency']*100:.1f}%.")


# ---------------------------------------------------------------- T-P map
def tp_map(df, col, scale, cbar, title, fname, fmt, cmap):
    piv = df.pivot_table(index="reactor_pressure_bar", columns="reactor_temperature_C", values=col) * scale
    Ts, Ps = piv.columns.values, piv.index.values
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    im = ax.pcolormesh(np.arange(len(Ts) + 1) - 0.5, np.arange(len(Ps) + 1) - 0.5, piv.values, cmap=cmap, shading="flat")
    ax.set_xticks(range(len(Ts)))
    ax.set_xticklabels([f"{t:.0f}" for t in Ts])
    ax.set_yticks(range(len(Ps)))
    ax.set_yticklabels([f"{p:.0f}" for p in Ps])
    ax.grid(False)
    vmin, vmax = np.nanmin(piv.values), np.nanmax(piv.values)
    for i in range(len(Ps)):
        for j in range(len(Ts)):
            v = piv.values[i, j]
            if np.isnan(v):
                continue
            dark = (v - vmin) / (vmax - vmin + 1e-12)
            ax.text(j, i, format(v, fmt), ha="center", va="center", fontsize=7.5, color="white" if (dark < 0.5 if cmap != "viridis_r" else dark > 0.5) else "black")
    # baseline cell if present
    if 600 in Ts and 20 in Ps:
        j, i = list(Ts).index(600), list(Ps).index(20)
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="gold", lw=2.5))
        ax.plot([], [], "s", mfc="none", mec="gold", mew=2, label="Baseline (600 degC, 20 bar)")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1)
    ax.set_xlabel("Cracker temperature (degC)")
    ax.set_ylabel("Cracker pressure (bar abs)")
    ax.set_title(title)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label(cbar)
    for s in ax.spines.values():
        s.set_visible(False)
    finish(fig, fname, "tp_map")
    return piv


def fig_tpmap():
    df = load("tp_map")
    if df is None:
        return
    p1 = tp_map(df, "nh3_conversion", 100, "NH$_3$ conversion (%)", "NH$_3$ conversion, temperature-pressure map",
                "aspen_tp_map_conversion", ".1f", "viridis")
    p2 = tp_map(df, "specific_heat_demand_kWh_per_kgH2", 1, "Specific heat demand (kWh per kg H$_2$)",
                "Specific heat demand, temperature-pressure map", "aspen_tp_map_specific_heat", ".2f", "viridis_r")
    for name, p, u in (("NH3 conversion", p1, "%"), ("specific heat demand", p2, "kWh/kgH2")):
        i, j = np.unravel_index(np.nanargmax(p.values), p.shape)
        k, l = np.unravel_index(np.nanargmin(p.values), p.shape)
        fact(f"T-P map {name}: max {p.values[i,j]:.2f} {u} at {p.columns[j]:.0f} degC / {p.index[i]:.0f} bar; "
             f"min {p.values[k,l]:.2f} {u} at {p.columns[l]:.0f} degC / {p.index[k]:.0f} bar ({p.shape[1]} T x {p.shape[0]} P grid).")


# ---------------------------------------------------------------- feed rate
def fig_feed_rate():
    df = load("feed_rate")
    if df is None:
        return
    df = df.sort_values("feed_total_kmol_h")
    F = df["feed_total_kmol_h"]
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axs[0]
    ax.plot(F, df["h2_product_kmol_h"], "-o", color=ps.C_H2, label="H$_2$ product")
    ax.set_xlabel("NH$_3$ feed (kmol/h)")
    ax.set_ylabel("H$_2$ product (kmol/h)")
    ax.set_title("H$_2$ product vs feed")
    b = at(df, "feed_total_kmol_h", 100)
    base_mark(ax, b["feed_total_kmol_h"], b["h2_product_kmol_h"], "Baseline (100 kmol/h)")
    ax.legend(loc="upper left")
    ax = axs[1]
    for c, l, col in (("total_external_heating_kW", "Total external heating", "black"), ("reactor_duty_kW", "Cracker", ps.C_HEAT),
                      ("preheat_duty_kW", "Trim heater", ps.C_AMBER), ("vaporiser_duty_kW", "Vaporiser", ps.C_COLD)):
        ax.plot(F, df[c], "-o", ms=3.5, color=col, label=l)
    ax.set_xlabel("NH$_3$ feed (kmol/h)")
    ax.set_ylabel("Heating duty (kW)")
    ax.set_title("Heating duty vs feed")
    ax.legend(loc="upper left")
    devs = {}
    for c in ("h2_product_kmol_h", "total_external_heating_kW", "reactor_duty_kW"):
        ratio = df[c] / F
        ref = ratio.loc[b.name]
        devs[c] = ((ratio / ref) - 1).abs().max()
    fact("Feed-rate proportionality (per-unit-feed value relative to baseline 100 kmol/h, max relative deviation): "
         + ", ".join(f"{k} {v:.2e}" for k, v in devs.items()) + f"; feed range {F.min():.0f}-{F.max():.0f} kmol/h.")
    axs[0].text(0.97, 0.08, f"max deviation from proportionality\n(H$_2$/feed): {devs['h2_product_kmol_h']:.1e}", transform=axs[0].transAxes,
                ha="right", fontsize=8)
    axs[1].text(0.97, 0.3, f"max dev. (total heating/feed): {devs['total_external_heating_kW']:.1e}", transform=axs[1].transAxes,
                ha="right", fontsize=8)
    finish(fig, "aspen_feed_rate_scaling", "feed_rate")


# ---------------------------------------------------------------- feed water
def fig_feed_water():
    df = load("feed_water")
    if df is None:
        return
    df = df.sort_values("feed_h2o_mole_frac")
    x = df["feed_h2o_mole_frac"] * 100
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axs[0]
    ax.plot(x, df["nh3_conversion"] * 100, "-o", color=ps.C_PRIMARY, label="NH$_3$ conversion")
    ax.set_ylabel("NH$_3$ conversion (%)", color=ps.C_PRIMARY)
    ax.set_xlabel("Water in NH$_3$ feed (mol%)")
    ax2 = ax.twinx()
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.plot(x, df["h2_product_kmol_h"], "-s", color=ps.C_H2, label="H$_2$ product")
    ax2.set_ylabel("H$_2$ product (kmol/h)", color=ps.C_H2)
    b = at(df, "feed_h2o_mole_frac", 0.002)
    ax.plot([b["feed_h2o_mole_frac"] * 100], [b["nh3_conversion"] * 100], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (0.2 mol%)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="best")
    ax.set_title("Conversion and H$_2$ product")
    ax = axs[1]
    ax.plot(x, df["total_external_heating_kW"], "-o", color=ps.C_HEAT, label="Total external heating")
    ax.set_xlabel("Water in NH$_3$ feed (mol%)")
    ax.set_ylabel("External heating (kW)", color=ps.C_HEAT)
    ax3 = ax.twinx()
    ax3.grid(False)
    ax3.spines["right"].set_visible(True)
    ax3.plot(x, df["specific_heat_demand_kWh_per_kgH2"], "-s", color=ps.C_N2, label="Specific heat demand")
    ax3.set_ylabel("Specific heat demand (kWh/kg H$_2$)", color=ps.C_N2)
    ax.plot([b["feed_h2o_mole_frac"] * 100], [b["total_external_heating_kW"]], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (0.2 mol%)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax3.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="best")
    ax.set_title("Heat demand")
    finish(fig, "aspen_feed_water_effect", "feed_water")
    lo, hi = df.iloc[0], df.iloc[-1]
    fact(f"Feed water {lo['feed_h2o_mole_frac']*100:.2f}-{hi['feed_h2o_mole_frac']*100:.2f} mol%: NH3 conversion {lo['nh3_conversion']*100:.2f}% -> {hi['nh3_conversion']*100:.2f}%; "
         f"H2 product {lo['h2_product_kmol_h']:.2f} -> {hi['h2_product_kmol_h']:.2f} kmol/h; total external heating {lo['total_external_heating_kW']:.0f} -> {hi['total_external_heating_kW']:.0f} kW; "
         f"specific heat {lo['specific_heat_demand_kWh_per_kgH2']:.2f} -> {hi['specific_heat_demand_kWh_per_kgH2']:.2f} kWh/kgH2.")


# ---------------------------------------------------------------- PSA recovery
def fig_psa():
    df = load("psa_recovery")
    if df is None:
        return
    df = df.sort_values("psa_h2_recovery")
    x = df["psa_h2_recovery"] * 100
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 4.1))
    ax = axs[0]
    ax.plot(x, df["h2_product_kmol_h"], "-o", color=ps.C_H2, label="H$_2$ product")
    ax.set_xlabel("PSA H$_2$ recovery (%)")
    ax.set_ylabel("H$_2$ product (kmol/h)")
    ax.set_title("H$_2$ product vs PSA recovery")
    b = at(df, "psa_h2_recovery", 0.85)
    ax.plot([b["psa_h2_recovery"] * 100], [b["h2_product_kmol_h"]], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (85 %)")
    ax.legend(loc="upper left")
    ax = axs[1]
    ax.plot(x, df["total_external_heating_kW"], "-o", color=ps.C_HEAT, label="Total external heat demand")
    ax.plot(x, df["tailgas_combustion_heat_kW"], "-s", color=ps.C_NH3, label="Tail-gas combustion heat")
    ax.plot(x, df["net_fuel_heat_deficit_kW"], "-^", color="black", label="Net fuel heat deficit")
    ax.axhline(0, color=ps.C_GREY, lw=1, ls=":")
    xs, ys = x.values, df["net_fuel_heat_deficit_kW"].values
    cross = None
    for i in range(len(xs) - 1):
        if ys[i] == 0 or ys[i] * ys[i + 1] < 0:
            cross = xs[i] if ys[i] == 0 else xs[i] + (0 - ys[i]) * (xs[i + 1] - xs[i]) / (ys[i + 1] - ys[i])
            break
    if cross is not None:
        ax.axvline(cross, color=ps.C_AMBER, ls="--", lw=1.2, label=f"Deficit = 0 at {cross:.1f} % (linear interp.)")
        ax.fill_between(x, 0, 1, where=x <= cross, transform=ax.get_xaxis_transform(), color=ps.C_AMBER, alpha=0.07)
    ax.plot([b["psa_h2_recovery"] * 100], [b["net_fuel_heat_deficit_kW"]], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (85 %)")
    ax.set_xlabel("PSA H$_2$ recovery (%)")
    ax.set_ylabel("Heat (kW)")
    ax.set_title("Tail-gas heat vs demand (600 degC, 20 bar)")
    ax.legend(loc="best", fontsize=7.5)
    finish(fig, "aspen_psa_recovery_tradeoff", "psa_recovery")
    lo, hi = df.iloc[0], df.iloc[-1]
    fact(f"PSA recovery {lo['psa_h2_recovery']*100:.0f}-{hi['psa_h2_recovery']*100:.0f}%: H2 product {lo['h2_product_kmol_h']:.2f} -> {hi['h2_product_kmol_h']:.2f} kmol/h; "
         f"tail-gas combustion heat {lo['tailgas_combustion_heat_kW']:.0f} -> {hi['tailgas_combustion_heat_kW']:.0f} kW; net fuel heat deficit {lo['net_fuel_heat_deficit_kW']:.0f} -> {hi['net_fuel_heat_deficit_kW']:.0f} kW "
         f"(positive = import needed); total external heating {b['total_external_heating_kW']:.0f} kW at 85% recovery; "
         + (f"deficit crosses zero at ~{cross:.1f}% recovery (linear interpolation between runs)." if cross is not None else "deficit does not cross zero in the swept range."))


# ---------------------------------------------------------------- FEHE approach
def fig_fehe():
    df = load("fehe_approach")
    if df is None:
        return
    df = df.sort_values("fehe_hot_end_approach_K")
    x = df["fehe_hot_end_approach_K"]
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axs[0]
    ax.plot(x, df["recovered_heat_kW"], "-o", color=ps.C_NH3, label="FEHE recovered heat")
    ax.plot(x, df["preheat_duty_kW"], "-s", color=ps.C_AMBER, label="Trim-heater duty")
    ax.set_xlabel("FEHE hot-end approach (K)")
    ax.set_ylabel("Duty (kW)")
    ax.set_title("Recovered heat and trim heater")
    b = at(df, "fehe_hot_end_approach_K", 50)
    base_mark(ax, b["fehe_hot_end_approach_K"], b["recovered_heat_kW"], "Baseline (50 K)")
    ax.legend(loc="best")
    ax = axs[1]
    ax.plot(x, df["fehe_hot_outlet_C"], "-o", color=ps.C_HEAT, label="FEHE hot outlet T")
    ax.set_xlabel("FEHE hot-end approach (K)")
    ax.set_ylabel("FEHE hot outlet temperature (degC)")
    ax.set_title("Effluent temperature leaving FEHE")
    ax.plot([b["fehe_hot_end_approach_K"]], [b["fehe_hot_outlet_C"]], marker="*", ms=12, mfc="gold", mec="black", ls="none", zorder=6,
            label="Baseline (50 K)")
    ax.legend(loc="best")
    finish(fig, "aspen_fehe_approach_effect", "fehe_approach")
    lo, hi = df.iloc[0], df.iloc[-1]
    fact(f"FEHE approach {lo['fehe_hot_end_approach_K']:.0f}-{hi['fehe_hot_end_approach_K']:.0f} K: recovered heat {lo['recovered_heat_kW']:.0f} -> {hi['recovered_heat_kW']:.0f} kW; "
         f"trim heater {lo['preheat_duty_kW']:.0f} -> {hi['preheat_duty_kW']:.0f} kW; FEHE hot outlet {lo['fehe_hot_outlet_C']:.1f} -> {hi['fehe_hot_outlet_C']:.1f} degC; "
         f"total external heating {lo['total_external_heating_kW']:.0f} -> {hi['total_external_heating_kW']:.0f} kW.")


# ---------------------------------------------------------------- heat integration vs none
def fig_hi():
    a = load("temperature")
    n = load("no_hi_temperature")
    if a is None or n is None:
        return
    a = a.sort_values("reactor_temperature_C")
    n = n.sort_values("reactor_temperature_C")
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axs[0]
    ax.plot(a["reactor_temperature_C"], a["total_external_heating_kW"], "-o", color=ps.C_NH3, label="With FEHE")
    ax.plot(n["reactor_temperature_C"], n["total_external_heating_kW"], "-s", color=ps.C_HEAT, label="Without FEHE")
    ax.set_xlabel("Cracker temperature (degC)")
    ax.set_ylabel("Total external heating (kW)")
    ax.set_title("External heating demand")
    ax.legend(loc="upper left")
    ax = axs[1]
    ax.plot(a["reactor_temperature_C"], a["lhv_efficiency"] * 100, "-o", color=ps.C_NH3, label="With FEHE")
    ax.plot(n["reactor_temperature_C"], n["lhv_efficiency"] * 100, "-s", color=ps.C_HEAT, label="Without FEHE")
    ba = at(a, "reactor_temperature_C", 600)
    base_mark(ax, ba["reactor_temperature_C"], ba["lhv_efficiency"] * 100, "Baseline (with FEHE, 600 degC)")
    ax.set_xlabel("Cracker temperature (degC)")
    ax.set_ylabel("LHV efficiency (%)")
    ax.set_title("LHV efficiency")
    ax.legend(loc="best")
    finish(fig, "aspen_heat_integration_vs_none", ["temperature", "no_hi_temperature"])
    m = a.merge(n, on="reactor_temperature_C", suffixes=("_hi", "_no"))
    if len(m):
        m["sav"] = m["total_external_heating_kW_no"] - m["total_external_heating_kW_hi"]
        m["savp"] = m["sav"] / m["total_external_heating_kW_no"] * 100
        m["de"] = (m["lhv_efficiency_hi"] - m["lhv_efficiency_no"]) * 100
        r6 = m.loc[(m["reactor_temperature_C"] - 600).abs().idxmin()]
        fact(f"Heat integration vs none over {len(m)} common temperatures: external heating saved {m['sav'].min():.0f}-{m['sav'].max():.0f} kW "
             f"({m['savp'].min():.1f}-{m['savp'].max():.1f}%); LHV efficiency gain {m['de'].min():.1f}-{m['de'].max():.1f} percentage points; "
             f"at {r6['reactor_temperature_C']:.0f} degC: {r6['total_external_heating_kW_hi']:.0f} kW with FEHE vs {r6['total_external_heating_kW_no']:.0f} kW without "
             f"({r6['savp']:.1f}% saving), efficiency {r6['lhv_efficiency_hi']*100:.1f}% vs {r6['lhv_efficiency_no']*100:.1f}%.")


def main():
    ps.apply_style()
    for f in (fig_temperature, fig_pressure, fig_tpmap, fig_feed_rate, fig_feed_water, fig_psa, fig_fehe, fig_hi):
        try:
            f()
        except Exception as e:  # report, do not hide
            import traceback
            traceback.print_exc()
            print(f"[ERROR] {f.__name__}: {e}")
    print("DROPPED non-converged rows:", DROPPED)


if __name__ == "__main__":
    main()
