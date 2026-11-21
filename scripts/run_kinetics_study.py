"""Kinetics validation + Ni vs Ru packed-bed PFR study (AmCraX P3.1/P3.2).

Writes
  results/validation/kinetics_validation.csv, results/figures/kinetics_validation.png
  results/simulations/pfr_baseline.json, results/sensitivity/pfr_temperature_sweep.csv
  results/figures/pfr_profiles_<catalyst>.png, results/figures/pfr_catalyst_mass_vs_T.png

All PFR outputs are python_model results built on literature kinetics (extrapolated to 20 bar; see
amcrax.reactor.pfr docstring). Literature data points are labelled 'literature'.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import brentq

from amcrax import paths
from amcrax.kinetics import get_catalyst, list_catalysts, takahashi_constants
from amcrax.kinetics.rate_laws import _registry
from amcrax.plotstyle import apply_style
from amcrax.reactor import BASELINE_FEED_kmol_h, DEFAULT_BED_SOURCE, catalyst_mass_for_conversion, simulate_pfr
from amcrax.thermodynamics import solve_equilibrium

import matplotlib.pyplot as plt  # noqa: E402  (backend set by plotstyle)

P_ATM_BAR = 1.01325
NORMAL_MOLAR_VOLUME_L = 22.414   # L/mol at 0 degC, 1 atm (ideal gas; convention for 'NmL')
CATS = ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "ru_kum_temkin_pyzhev"]
SHORT = {"ni_takahashi_microkinetic": "Ni/MgO (Takahashi)", "ru_takahashi_microkinetic": "Ru/MgO (Takahashi)",
         "ru_kum_temkin_pyzhev": "Ru/Al2O3 (Kum T-P)"}
# Baseline bed cross-section: Kum tube ID 0.126 m (Table 1); number of parallel tubes is an AmCraX ASSUMPTION
# chosen so the Ergun pressure drop at the 99 %-of-equilibrium Ru catalyst mass stays well below 1 bar.
N_TUBES = 40


def _lab(F_tot_mol_s: float, W_over_F: float, T_C: float, y: dict[str, float], approach: bool | None, cid: str,
         keq_basis: str = "amcrax_thermo") -> float:
    """Isothermal 1 atm lab PFR without pressure drop; y = feed mole fractions; returns conversion."""
    feed = {k: v * F_tot_mol_s * 3.6 for k, v in y.items() if v > 0}
    r = simulate_pfr(cid, W_over_F * F_tot_mol_s, T_in_C=T_C, P_in_bar=P_ATM_BAR, feed_kmol_h=feed,
                     pressure_drop=False, approach_factor=approach, keq_basis=keq_basis, n_points=2)
    return r.outlet["conversion"]


def validation() -> list[dict]:
    reg = _registry()
    V = reg["validation"]
    rows: list[dict] = []
    # (a) Table 2 rate constants at 500 degC from Table 1 parameters
    for cid in CATS[:2]:
        ref = reg["catalysts"][cid]["reference_values_773K"]
        calc = takahashi_constants(cid, 773.15)
        for k in ("k_minus1", "k2", "k3", "k4", "k_minus4", "K4"):
            rows.append(dict(dataset=f"{cid}:Table2", catalyst=cid, condition=f"{k} at 773.15 K", x=773.15,
                             literature=ref[k], model=calc[k], model_af_on="", deviation=calc[k] / ref[k] - 1,
                             deviation_unit="relative", basis="direct (no reactor)",
                             source="takahashi2016kinetic p.5 Table 2"))
    # (b) Takahashi conversion data. Catalyst mass and bed density are not reported, so W/F_total cannot be
    # reproduced from the paper. ONE anchor point per catalyst is used to infer W/F_total (published form, no
    # approach factor); all other points (same SV 15000 h^-1 => same total flow) are predictions.
    anchors = {"ni_takahashi_microkinetic": ("takahashi_ni_fig3a", 0), "ru_takahashi_microkinetic": ("takahashi_ru_fig4a", 0)}
    inferred = {}
    for cid, (ds, idx) in anchors.items():
        d = V[ds]
        T0, X0 = d["T_C"][idx], d["X_pct"][idx] / 100
        f = lambda wf: _lab(1.0, wf, T0, {"NH3": 1.0}, False, cid) - X0  # noqa: E731
        wf = brentq(f, 1e-6, 1e3, xtol=1e-9, rtol=1e-8)
        inferred[cid] = wf
        rho_implied = wf * (d["SV_h_inv"] / 3600.0) / (NORMAL_MOLAR_VOLUME_L / 1000.0)
        print(f"{cid}: inferred W/F_total = {wf*1000:.3f} g s/mol (anchor {ds} {T0} C X={X0:.3f}); "
              f"implied bed density at SV 15000 h^-1 (normal basis) = {rho_implied:.0f} kg/m3")
    for cid, sets in (("ni_takahashi_microkinetic", ["takahashi_ni_fig3a", "takahashi_ni_fig3b", "takahashi_ni_fig5a"]),
                      ("ru_takahashi_microkinetic", ["takahashi_ru_fig4a", "takahashi_ru_fig4b", "takahashi_ru_fig5b"])):
        wf = inferred[cid]
        for ds in sets:
            d = V[ds]
            pts = []
            if "P_atm" in d:
                pts = [(T, {"NH3": 1.0}, X, f"T={T} C, pure NH3", T) for T, X in zip(d["T_C"], d["X_pct"])]
            elif "p_H2_atm" in d:
                pts = [(d["T_C"], {"NH3": d["p_NH3_atm"], "H2": h, "Ar": 1 - d["p_NH3_atm"] - h}, X,
                        f"T={d['T_C']} C, pNH3={d['p_NH3_atm']} atm, pH2={h} atm", h) for h, X in zip(d["p_H2_atm"], d["X_pct"])]
            else:
                pts = [(d["T_C"], {"NH3": p, "Ar": 1 - p}, X, f"T={d['T_C']} C, pNH3={p} atm", p)
                       for p, X in zip(d["p_NH3_atm"], d["X_pct"])]
            for i, (T, y, X, cond, xval) in enumerate(pts):
                m_off = _lab(1.0, wf, T, y, False, cid)
                m_on = _lab(1.0, wf, T, y, True, cid)
                is_anchor = anchors[cid] == (ds, i)
                rows.append(dict(dataset=ds, catalyst=cid, condition=cond, x=xval, literature=X / 100, model=m_off,
                                 model_af_on=m_on, deviation=m_off - X / 100, deviation_unit="absolute conversion",
                                 basis=("ANCHOR (used to infer W/F, not a validation point)" if is_anchor else
                                        f"prediction with inferred W/F_total={wf*1000:.3f} g s/mol (assumption)"),
                                 source=f"{d['citekey']} p.{d['page']} {d['locator']}"))
    # (c) Kum T-P vs Di Carlo commercial Ru/Al2O3, 500 degC, 286 NmL/(gcat h) -> W/F_NH3 fully specified
    d = V["dicarlo_ru_al2o3_500C"]
    F_per_g = d["WHSV_NmL_per_gcat_h"] / 1000.0 / NORMAL_MOLAR_VOLUME_L / 3600.0     # mol NH3 /(g s)
    wf_kum = 1.0 / F_per_g / 1000.0                                                      # kg s / mol
    for P, X in zip(d["P_bar"], d["X_pct"]):
        res = {}
        for kb in ("published", "amcrax_thermo"):
            r = simulate_pfr("ru_kum_temkin_pyzhev", wf_kum * 1.0, T_in_C=d["T_C"], P_in_bar=float(P),
                             feed_kmol_h={"NH3": 3.6}, pressure_drop=False, keq_basis=kb, n_points=2)
            res[kb] = r.outlet["conversion"]
        Xe = solve_equilibrium(d["T_C"] + 273.15, float(P), {"NH3": 1.0}).conversion
        rows.append(dict(dataset="dicarlo_ru_al2o3_500C", catalyst="ru_kum_temkin_pyzhev",
                         condition=f"T=500 C, P={P} bar, pure NH3, 286 NmL/(gcat h); X_eq(AmCraX)={Xe:.4f}", x=P,
                         literature=X / 100, model=res["published"], model_af_on=res["amcrax_thermo"],
                         deviation=res["published"] - X / 100, deviation_unit="absolute conversion",
                         basis=f"W/F_NH3={wf_kum:.1f} kg s/mol from WHSV; model=Keq Eq.4 (published reading), "
                               "model_af_on column = Keq amcrax_thermo; rate law fitted to these data (not independent); 773 K > 723 K fit range",
                         source=f"{d['citekey']} p.{d['page']} {d['locator']}"))
    return rows, inferred, wf_kum


def write_validation(rows, inferred, wf_kum):
    paths.ensure_dirs()
    out = paths.RESULTS_VALIDATION / "kinetics_validation.csv"
    keys = ["dataset", "catalyst", "condition", "x", "literature", "model", "model_af_on", "deviation",
            "deviation_unit", "basis", "source"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    apply_style()
    fig, axs = plt.subplots(2, 3, figsize=(12, 7))
    panels = [("takahashi_ni_fig3a", "T [degC]", "Ni/MgO 1 atm pure NH3 (Fig. 3a)"),
              ("takahashi_ni_fig3b", "p_NH3 [atm]", "Ni/MgO 500 degC (Fig. 3b)"),
              ("takahashi_ni_fig5a", "p_H2 [atm]", "Ni/MgO 500 degC, pNH3 0.3 atm (Fig. 5a)"),
              ("takahashi_ru_fig4a", "T [degC]", "Ru/MgO 1 atm pure NH3 (Fig. 4a)"),
              ("takahashi_ru_fig4b", "p_NH3 [atm]", "Ru/MgO 450 degC (Fig. 4b)"),
              ("takahashi_ru_fig5b", "p_H2 [atm]", "Ru/MgO 450 degC, pNH3 0.3 atm (Fig. 5b)")]
    for ax, (ds, xl, tt) in zip(axs.flat, panels):
        sel = [r for r in rows if r["dataset"] == ds]
        x = [r["x"] for r in sel]
        ax.plot(x, [100 * r["literature"] for r in sel], "o", color="#33415f", label="literature (read from figure)")
        ax.plot(x, [100 * r["model"] for r in sel], "-s", label="model, published form")
        ax.plot(x, [100 * r["model_af_on"] for r in sel], "--^", label="model + AmCraX (1-Q/K)")
        for r in sel:
            if r["basis"].startswith("ANCHOR"):
                ax.annotate("anchor", (r["x"], 100 * r["literature"]), textcoords="offset points", xytext=(6, -10), fontsize=8)
        ax.set_xlabel(xl)
        ax.set_ylabel("NH3 conversion [%]")
        ax.set_title(tt)
    axs.flat[0].legend(loc="lower right")
    fig.suptitle("Takahashi 2016 microkinetics vs paper data. W/F inferred from one anchor point per catalyst "
                 f"(Ni {inferred['ni_takahashi_microkinetic']*1e3:.2f}, Ru {inferred['ru_takahashi_microkinetic']*1e3:.2f} g s/mol) - "
                 "catalyst mass not reported in source", fontsize=9)
    fig.text(0.01, 0.005, "Literature: takahashi2016kinetic Figs. 3-5 (p. 5). Model: AmCraX python_model.", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(paths.RESULTS_FIGURES / "kinetics_validation.png", dpi=150)
    plt.close(fig)
    return out


def study():
    feed = dict(BASELINE_FEED_kmol_h)
    common = dict(P_in_bar=20.0, feed_kmol_h=feed, n_tubes=N_TUBES)
    out: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "python_model",
        "description": "Packed-bed PFR (amcrax.reactor) with literature kinetics (amcrax.kinetics); NOT Aspen results",
        "assumptions": [
            f"bed properties: {DEFAULT_BED_SOURCE}; same bed used for Takahashi powders (assumption)",
            f"n_tubes = {N_TUBES} parallel tubes of 0.126 m ID (assumption, keeps Ergun dP < 1 bar at Ru W99)",
            "Takahashi kinetics measured at 1 atm on powders; 20 bar use is extrapolation (mole-fraction basis)",
            "Takahashi: AmCraX equilibrium approach factor (1-Q/K) ON",
            "Kum T-P fit range 623-723 K, 1-10 bar; 20 bar / 873 K is extrapolation; Keq basis amcrax_thermo",
            "effectiveness factor 1, no radial gradients, no axial dispersion",
        ],
        "catalysts": {c.id: {"label": c.label, "composition": c.composition, "source": c.source,
                             "validity": c.validity} for c in list_catalysts()},
        "cases": {},
    }
    apply_style()
    cases = [(cid, 600.0) for cid in CATS] + [("ru_kum_temkin_pyzhev", 450.0), ("ru_kum_temkin_pyzhev", 500.0),
                                              ("ru_takahashi_microkinetic", 450.0), ("ru_takahashi_microkinetic", 500.0)]
    for cid, T in cases:
        key = f"{cid}@{T:.0f}C"
        Xe = solve_equilibrium(T + 273.15, 20.0, feed).conversion
        w95 = catalyst_mass_for_conversion(cid, fraction_of_equilibrium=0.95, T_in_C=T, **common)
        w99 = catalyst_mass_for_conversion(cid, fraction_of_equilibrium=0.99, T_in_C=T, **common)
        Wp = 2.0 * w99 if math.isfinite(w99) else 1000.0
        r = simulate_pfr(cid, Wp, T_in_C=T, **common)
        r99 = simulate_pfr(cid, w99, T_in_C=T, n_points=2, **common) if math.isfinite(w99) else None
        out["cases"][key] = {
            "catalyst_id": cid, "T_C": T, "P_in_bar": 20.0, "feed_kmol_h": feed, "mode": "isothermal",
            "X_eq": Xe, "W_95pct_eq_kg": w95, "W_99pct_eq_kg": w99,
            "at_W99": None if r99 is None else {k: r99.outlet[k] for k in ("conversion", "pressure_drop_bar", "heat_input_kW",
                                                                            "residence_time_s", "H2_kmol_h")}
                      | {"GHSV_h_inv": r99.GHSV_h_inv, "W_over_F_kg_s_per_mol_NH3": r99.W_over_F_kg_s_per_mol_NH3},
            "profile": {"W_kg": r.W_kg, "conversion": r.conversion, "T_K": r.T_K, "P_bar": r.P_bar,
                        "y": r.y, "rate_mol_per_kgcat_s": r.rate_mol_per_kgcat_s,
                        "approach_to_equilibrium": r.approach_to_equilibrium, "residence_time_s": r.residence_time_s},
            "assumptions": r.assumptions,
        }
        print(f"{key}: X_eq={Xe:.4f} W95={w95:.3g} kg W99={w99:.3g} kg"
              + ("" if r99 is None else f" dP@W99={r99.outlet['pressure_drop_bar']:.3f} bar GHSV@W99={r99.GHSV_h_inv:.0f} 1/h"))
    # adiabatic and externally heated illustrations at baseline for the Kum Ru law (assumption-labelled inputs)
    W_ref = out["cases"]["ru_kum_temkin_pyzhev@600C"]["W_99pct_eq_kg"]
    for mode, extra in (("adiabatic", {}), ("external", {"T_wall_C": 650.0, "U_W_m2K": 60.0})):
        r = simulate_pfr("ru_kum_temkin_pyzhev", 20 * W_ref, T_in_C=600.0, mode=mode, **common, **extra)
        out["cases"][f"ru_kum_temkin_pyzhev@600C_{mode}"] = {
            "catalyst_id": "ru_kum_temkin_pyzhev", "mode": mode, "W_kg": 20 * W_ref, **extra,
            "note": ("ILLUSTRATIVE. U = 60 W/m2/K is richard2024technoeconomic p.6 Table 1 gas/gas HX value (not a "
                     "furnace-tube value); T_wall 650 degC is an assumption." if mode == "external" else
                     "ILLUSTRATIVE adiabatic bed from 600 degC"),
            "outlet": r.outlet,
            "profile": {"W_kg": r.W_kg, "conversion": r.conversion, "T_K": r.T_K, "X_eq_local": r.X_eq_local},
        }
        print(f"Kum 600C {mode}: X_out={r.outlet['conversion']:.4f} T_out={r.outlet['T_C']:.1f} C Q={r.outlet['heat_input_kW']:.1f} kW")
    paths.ensure_dirs()
    with open(paths.RESULTS_SIMULATIONS / "pfr_baseline.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda o: None if (isinstance(o, float) and not math.isfinite(o)) else o)

    # profiles figure per catalyst (600 degC baseline)
    for cid in CATS:
        c = out["cases"][f"{cid}@600C"]
        p = c["profile"]
        fig, axs = plt.subplots(1, 3, figsize=(12, 3.6))
        axs[0].plot(p["W_kg"], np.array(p["conversion"]) * 100, label="X")
        axs[0].axhline(c["X_eq"] * 100, ls="--", color="#5b6788", label="X_eq (AmCraX thermo)")
        axs[0].set_ylabel("NH3 conversion [%]")
        axs[0].legend()
        for s, col in (("NH3", "#15803d"), ("H2", "#be185d"), ("N2", "#4f46e5")):
            axs[1].plot(p["W_kg"], p["y"][s], color=col, label=s)
        axs[1].set_ylabel("mole fraction [-]")
        axs[1].legend()
        axs[2].semilogy(p["W_kg"], np.maximum(np.array(p["rate_mol_per_kgcat_s"], dtype=float), 1e-12))
        axs[2].set_ylabel("rate [mol NH3 /(kg_cat s)]")
        for a in axs:
            a.set_xlabel("catalyst mass W [kg]")
        fig.suptitle(f"{SHORT[cid]}: isothermal PFR 600 degC, 20 bar, 100 kmol/h, {N_TUBES} x 0.126 m tubes "
                     "(python_model; kinetics extrapolated beyond fitted range)", fontsize=9)
        fig.tight_layout()
        fig.savefig(paths.RESULTS_FIGURES / f"pfr_profiles_{cid}.png", dpi=150)
        plt.close(fig)

    # temperature sweep
    rows = []
    for T in range(400, 751, 25):
        Xe = solve_equilibrium(T + 273.15, 20.0, feed).conversion
        for cid in CATS:
            w95 = catalyst_mass_for_conversion(cid, fraction_of_equilibrium=0.95, T_in_C=float(T), **common)
            w99 = catalyst_mass_for_conversion(cid, fraction_of_equilibrium=0.99, T_in_C=float(T), **common)
            x100 = simulate_pfr(cid, 100.0, T_in_C=float(T), n_points=2, **common).outlet["conversion"]
            k = get_catalyst(cid).validity
            rows.append(dict(T_C=T, P_bar=20.0, catalyst_id=cid, X_eq=Xe, W_95pct_eq_kg=w95, W_99pct_eq_kg=w99,
                             X_at_100kg=x100, within_fitted_T_range=k["T_min_K"] <= T + 273.15 <= k["T_max_K"],
                             within_fitted_P_range=k["P_min_bar"] <= 20.0 <= k["P_max_bar"], source="python_model"))
        print(f"sweep T={T} done")
    with open(paths.RESULTS_SENSITIVITY / "pfr_temperature_sweep.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for cid in CATS:
        sel = [r for r in rows if r["catalyst_id"] == cid]
        ax.semilogy([r["T_C"] for r in sel], [r["W_99pct_eq_kg"] for r in sel], "-o", label=f"{SHORT[cid]} 99 % of X_eq")
        ax.semilogy([r["T_C"] for r in sel], [r["W_95pct_eq_kg"] for r in sel], ":", label=f"{SHORT[cid]} 95 % of X_eq")
    ax.set_xlabel("isothermal bed temperature [degC]")
    ax.set_ylabel("catalyst mass [kg] for 100 kmol/h feed")
    ax.set_title("Catalyst mass vs T at 20 bar (python_model, extrapolated kinetics)", fontsize=9.5)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(paths.RESULTS_FIGURES / "pfr_catalyst_mass_vs_T.png", dpi=150)
    plt.close(fig)


def main(argv):
    rows, inferred, wf_kum = validation()
    write_validation(rows, inferred, wf_kum)
    for r in rows:
        print(f"{r['dataset']:28s} {r['condition'][:48]:48s} lit={r['literature']:.4g} model={r['model']:.4g} "
              f"dev={r['deviation']:+.3f} ({r['deviation_unit']})")
    if "--validation-only" not in argv:
        study()


if __name__ == "__main__":
    main(sys.argv[1:])
