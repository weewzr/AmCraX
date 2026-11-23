"""Task U1 / T2a: propagation of the published Lucentini et al. (2021) Table 3 parameter intervals.

Deterministic (seed 20261123); run from the project root:  python scripts/research/uq_kinetic_propagation.py
Writes results/research/uq/kinetic_param_propagation.json, kinetic_param_propagation_samples.csv and
results/figures/research/uq_kinetic_T_required.png. Uses the existing PFR (amcrax.reactor.pfr) through the additive
param_overrides hook (amcrax.uq.kinetic_hook). Runs in parallel worker processes (one PFR per process).
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm, qmc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts" / "research"))

from amcrax.kinetics import rate_laws  # noqa: E402
from amcrax.reactor.pfr import _eq_conversion  # noqa: E402
from amcrax.uq import LABEL, SEED  # noqa: E402
from amcrax.uq.kinetic_hook import mass_with, simulate_with  # noqa: E402

OUT = ROOT / "results" / "research" / "uq"
FIG = ROOT / "results" / "figures" / "research"
SCRIPT = "scripts/research/uq_kinetic_propagation.py"
N_DRAWS = int(os.environ.get("AMCRAX_UQ_T2A_N", "4000"))
R = rate_laws.R_KIN_J_molK
T_REF_K = 748.15      # 475 degC, middle of the 350-600 degC fitted range (assumption, spec T2a.2)
ATM = 1.01325
FEED = {"NH3": 100.0}  # study basis of results/research/kinetics/study_*.json (100 kmol/h pure NH3)
BED = {"eps_b": 0.36, "rho_particle_kg_m3": 1651.8}  # same as scripts/research/kinetics_studies.py BED for Lucentini
# Lab reactor: identical to scripts/research/kinetics_validation.py (validation_*.json experimental_conditions)
LAB_W_KG, LAB_ML_MIN, LAB_AR, VM = 1e-4, 25.0, 1.2, 22.414
CATS = {
    "nire_ceo2_5ni1ru_lucentini_lhhw": {"short": "5Ni1Ru_CeO2", "T_C": [400, 450, 500], "X": [0.365, 0.861, 0.996]},
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": {"short": "2p5Ni0p5Ru_CeO2", "T_C": [400, 450, 500], "X": [0.497, 0.887, 0.992]},
}
TARGETS = [(P, W, X) for P in (ATM, 20.0) for W in (100.0, 1000.0) for X in (0.95, 0.99)]
T_LO, T_HI = 350.0, 900.0


def lab_feed():
    n = LAB_ML_MIN * 1e-3 * 60.0 / VM / 1000.0
    return {"NH3": n / (1 + LAB_AR), "Ar": n * LAB_AR / (1 + LAB_AR)}


def nominal(cid):
    reg = rate_laws._all_cats()[cid]["parameters"]
    return {k: float(reg[k]["value"]) for k in ("k0", "Ek", "K1", "K4")}, {k: float(reg[k]["uncertainty"]) for k in ("k0", "Ek", "K1", "K4")}


def lab_X(cid, ov):
    return [float(simulate_with(cid, ov, LAB_W_KG, T_in_C=float(T), P_in_bar=ATM, feed_kmol_h=lab_feed(), mode="isothermal",
                                pressure_drop=False, n_points=3).outlet["conversion"]) for T in CATS[cid]["T_C"]]


def X_at(cid, ov, W, T, P):
    return float(simulate_with(cid, ov, W, T_in_C=T, P_in_bar=P, feed_kmol_h=FEED, mode="isothermal", pressure_drop=False,
                               eps_b=BED["eps_b"], rho_particle_kg_m3=BED["rho_particle_kg_m3"], n_points=2).outlet["conversion"])


def T_required(cid, ov, W, X_t, P, lo=T_LO):
    if _eq_conversion(T_HI + 273.15, P, FEED) < X_t:
        return None, "X_eq below target at 900 degC"
    g = lambda T: X_at(cid, ov, W, T, P) - X_t  # noqa: E731
    try:
        glo, ghi = g(lo), g(T_HI)
    except Exception as ex:  # noqa: BLE001
        return None, f"solver error {ex}"
    if glo >= 0:
        return (None, "target reached at 350 degC (below bracket)") if lo == T_LO else (lo, "")
    if ghi < 0:
        return None, "target not reached between 350 and 900 degC"
    return float(brentq(g, lo, T_HI, xtol=0.02)), ""


def mass(cid, ov, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = mass_with(cid, ov, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, mode="isothermal", pressure_drop=False,
                      eps_b=BED["eps_b"], rho_particle_kg_m3=BED["rho_particle_kg_m3"], W_max_kg=1e7, return_details=True, **kw)
    return (d["W_kg"] if d["reachable"] else None), d


def run_draw(args):
    cid, ov, skip_abs99 = args
    out = {"X_lab": lab_X(cid, ov)}
    Tr = {}
    for P, W, X in TARGETS:
        lo = T_LO
        prev = Tr.get((P, W, 0.95)) if X == 0.99 else None
        if prev and prev[0] is not None:
            lo = prev[0]
        Tr[(P, W, X)] = T_required(cid, ov, W, X, P, lo=lo)
    out["T_req"] = {f"P{P:g}_W{W:g}_X{X:g}": v for (P, W, X), v in Tr.items()}
    out["m_frac99"] = mass(cid, ov, fraction_of_equilibrium=0.99)[0]
    out["m_abs99"] = None if skip_abs99 else mass(cid, ov, target_conversion=0.99)[0]
    return out


def draws(cid, case, n, rng_seed):
    nom, unc = nominal(cid)
    u = qmc.LatinHypercube(d=4, seed=rng_seed).random(n)
    z = norm.ppf(u)
    s_rel = {k: unc[k] / nom[k] / 1.96 for k in ("k0", "K1", "K4")}
    sEk = unc["Ek"] / 1.96
    Ek = nom["Ek"] + sEk * z[:, 1]
    K1 = np.exp(np.log(nom["K1"]) + s_rel["K1"] * z[:, 2])
    K4 = np.exp(np.log(nom["K4"]) + s_rel["K4"] * z[:, 3])
    if case == "C1":
        k0 = np.exp(np.log(nom["k0"]) + s_rel["k0"] * z[:, 0])
    else:  # C2 centred at T_ref: ln k_ref ~ N, Ek independent of k_ref
        kref_nom = nom["k0"] * math.exp(-nom["Ek"] * 1e3 / (R * T_REF_K))
        kref = np.exp(np.log(kref_nom) + s_rel["k0"] * z[:, 0])
        k0 = kref * np.exp(Ek * 1e3 / (R * T_REF_K))
    return [{"k0": float(a), "Ek": float(b), "K1": float(c), "K4": float(d)} for a, b, c, d in zip(k0, Ek, K1, K4)]


def summ(vals):
    v = np.array([x for x in vals if x is not None and np.isfinite(x)], float)
    n_nr = sum(1 for x in vals if x is None or not np.isfinite(x))
    if v.size == 0:
        return {"n": 0, "n_not_reached": n_nr}
    return {"n": int(v.size), "n_not_reached": n_nr, "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "p5": float(np.percentile(v, 5)), "p50": float(np.percentile(v, 50)), "p95": float(np.percentile(v, 95))}


def main():
    sys.path.insert(0, str(ROOT / "backend"))
    from amcrax.economics.reference import provenance_stamp
    from amcrax.economics.singapore import evaluate, extract_summary
    OUT.mkdir(parents=True, exist_ok=True)
    S_HI = extract_summary(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    plant_scale = S_HI["nh3_feed_kmol_h"] / FEED["NH3"]
    base_eval = evaluate(S_HI, "grey")
    stored_T = json.loads((ROOT / "results/research/kinetics/study_temperature_for_target_conversion.json").read_text(encoding="utf-8"))["rows"]
    stored_M = json.loads((ROOT / "results/research/kinetics/study_mass_for_fraction_of_equilibrium.json").read_text(encoding="utf-8"))["rows"]
    xe_600_20 = _eq_conversion(873.15, 20.0, FEED)
    skip_abs99 = xe_600_20 < 0.99
    result = {"catalysts": {}}
    checks = []
    csv_rows = []
    nproc = int(os.environ.get("AMCRAX_UQ_NPROC", max(1, (os.cpu_count() or 2) - 1)))
    with Pool(nproc) as pool:
        for cid, meta in CATS.items():
            nom, unc = nominal(cid)
            # ---- nominal reproduction
            nom_out = run_draw((cid, None, skip_abs99))
            xval = json.loads((ROOT / f"results/research/kinetics/validation_{meta['short']}.json").read_text(encoding="utf-8"))
            xp = [p["X_python"] for p in xval["points"]]
            d_lab = max(abs(a - b) for a, b in zip(nom_out["X_lab"], xp))
            checks.append({"id": f"T2A-NOM-LAB-{meta['short']}", "description": "nominal parameters reproduce X_python of the validation file (Table 1 points)",
                           "value": d_lab, "tolerance": 1e-6, "status": "pass" if d_lab <= 1e-6 else "fail"})
            dT = []
            for P, W, X in TARGETS:
                srow = [r for r in stored_T if r["catalyst_id"] == cid and abs(r["P_bar"] - P) < 1e-9 and r["W_cat_kg"] == W and r["X_target"] == X]
                mine = nom_out["T_req"][f"P{P:g}_W{W:g}_X{X:g}"][0]
                if srow and srow[0]["T_required_C"] == srow[0]["T_required_C"] and mine is not None:
                    dT.append(abs(mine - srow[0]["T_required_C"]))
            checks.append({"id": f"T2A-NOM-TREQ-{meta['short']}", "description": "nominal T_required equals the stored study (study_temperature_for_target_conversion.json)",
                           "value": max(dT) if dT else None, "n_compared": len(dT), "tolerance_K": 0.1,
                           "status": "pass" if dT and max(dT) <= 0.1 else "fail"})
            srow = [r for r in stored_M if r["catalyst_id"] == cid and r["T_C"] == 600 and r["fraction_of_equilibrium"] == 0.99]
            dm = abs(nom_out["m_frac99"] / srow[0]["W_cat_kg"] - 1.0) if srow and nom_out["m_frac99"] else None
            checks.append({"id": f"T2A-NOM-MASS-{meta['short']}", "description": "nominal catalyst mass for 99 % of equilibrium at 600 degC, 20 bar equals the stored study",
                           "value_rel": dm, "tolerance_rel": 1e-3, "status": "pass" if dm is not None and dm <= 1e-3 else "fail"})
            cres = {"nominal_parameters": nom, "published_half_widths": unc, "nominal_outputs": nom_out, "cases": {}}
            outs_by_case = {}
            for ci, case in enumerate(("C1", "C2")):
                ds = draws(cid, case, N_DRAWS, SEED)
                outs = pool.map(run_draw, [(cid, d, skip_abs99) for d in ds], chunksize=8)
                outs_by_case[case] = (ds, outs)
            # C3: C1 draws accepted by the +/-10 % parity band on all three Table 1 points
            ds1, outs1 = outs_by_case["C1"]
            acc = [all(abs(x / xo - 1.0) <= 0.10 for x, xo in zip(o["X_lab"], meta["X"])) for o in outs1]
            rate = sum(acc) / len(acc)
            outs_by_case["C3"] = ([d for d, a in zip(ds1, acc) if a], [o for o, a in zip(outs1, acc) if a])
            cres["C3_acceptance_rate"] = rate
            cres["C3_status"] = "used" if rate >= 0.02 else "acceptance below 2 %: C3 not used, rely on C2"
            for case, (ds, outs) in outs_by_case.items():
                if case == "C3" and rate < 0.02:
                    continue
                cs = {"n_draws": len(ds)}
                for k in ("k0", "Ek", "K1", "K4"):
                    cs[f"param_{k}"] = summ([d[k] for d in ds])
                for j, T in enumerate(meta["T_C"]):
                    cs[f"X_lab_{T}C"] = summ([o["X_lab"][j] for o in outs]) | {"X_published": meta["X"][j], "fitting_data": True}
                for key in outs[0]["T_req"]:
                    P = float(key.split("_")[0][1:])
                    cs[f"T_required_C_{key}"] = summ([o["T_req"][key][0] for o in outs]) | {"extrapolation": P > ATM + 1e-9,
                                                                                         "P_bar": P}
                mf = [o["m_frac99"] for o in outs]
                cs["catalyst_mass_kg_per_100kmolh_frac_eq99_600C_20bar"] = summ(mf) | {"extrapolation": True, "P_bar": 20.0}
                cs["catalyst_mass_kg_per_100kmolh_X0.99_600C_20bar"] = ({"not_reached": True, "reason": f"X_eq(600 degC, 20 bar) = {xe_600_20:.4f} < 0.99",
                                                                         "extrapolation": True} if skip_abs99 else summ([o["m_abs99"] for o in outs]) | {"extrapolation": True})
                # LCOH via the catalyst inventory only (stored Aspen conversion unchanged)
                for metal, price in (("Ni_proxy", 33.4), ("Ru_proxy", 542.0)):
                    L = [evaluate(S_HI, "grey", {"catalyst_mass_kg": m * plant_scale, "catalyst_price_USD_per_kg": price})["lcoh_USD_per_kg"]
                         if m else None for m in mf]
                    cs[f"lcoh_USD_per_kg_grey_HIon_{metal}"] = summ(L) | {"extrapolation": True, "catalyst_price_USD_per_kg": price}
                    cs[f"lcoh_SGD_per_kg_grey_HIon_{metal}"] = summ([x * base_eval["fx_SGD_per_USD"] if x else None for x in L])
                m50 = cs["catalyst_mass_kg_per_100kmolh_frac_eq99_600C_20bar"].get("p50")
                if m50:
                    e1 = evaluate(S_HI, "grey", {"catalyst_mass_kg": m50 * plant_scale, "catalyst_price_USD_per_kg": 100.0})["lcoh_USD_per_kg"]
                    e2 = evaluate(S_HI, "grey", {"catalyst_mass_kg": m50 * plant_scale, "catalyst_price_USD_per_kg": 101.0})["lcoh_USD_per_kg"]
                    cs["dLCOH_dcatalyst_price_at_p50_mass_USD_per_kgH2_per_USD_per_kgcat"] = e2 - e1
                if case == "C1":
                    from scipy.stats import spearmanr
                    key = "P1.01325_W1000_X0.99"
                    pairs = [(d["k0"], o["T_req"][key][0]) for d, o in zip(ds, outs) if o["T_req"][key][0] is not None]
                    rho = float(spearmanr([a for a, _ in pairs], [b for _, b in pairs])[0]) if len(pairs) > 10 else None
                    cs["spearman_k0_vs_T_required_1atm_W1000_X0.99"] = rho
                    checks.append({"id": f"T2A-MONO-{meta['short']}", "description": "T_required decreases as k0 increases (C1), rank correlation < -0.5 (informational)",
                                   "value": rho, "threshold": -0.5, "status": "informational"})
                    for k in ("k0", "K1", "K4"):
                        lv = np.log([d[k] for d in ds])
                        okm = abs(lv.mean() - math.log(nom[k])) <= 0.02 * abs(math.log(nom[k])) and abs(lv.std(ddof=1) / (unc[k] / nom[k] / 1.96) - 1) <= 0.02
                        checks.append({"id": f"T2A-MOM-{meta['short']}-ln{k}", "description": f"sample mean and sd of ln {k} within 2 % of the specified values",
                                       "mean": float(lv.mean()), "sd": float(lv.std(ddof=1)), "spec_mean": math.log(nom[k]),
                                       "spec_sd": unc[k] / nom[k] / 1.96, "status": "pass" if okm else "fail"})
                    ev = np.array([d["Ek"] for d in ds])
                    okm = abs(ev.mean() / nom["Ek"] - 1) <= 0.02 and abs(ev.std(ddof=1) / (unc["Ek"] / 1.96) - 1) <= 0.02
                    checks.append({"id": f"T2A-MOM-{meta['short']}-Ek", "description": "sample mean and sd of Ek within 2 % of the specified values",
                                   "mean": float(ev.mean()), "sd": float(ev.std(ddof=1)), "spec_mean": nom["Ek"], "spec_sd": unc["Ek"] / 1.96,
                                   "status": "pass" if okm else "fail"})
                cres["cases"][case] = cs
                for i, (d, o) in enumerate(zip(ds, outs)):
                    csv_rows.append([cid, case, i, d["k0"], d["Ek"], d["K1"], d["K4"], *o["X_lab"],
                                     *[o["T_req"][k][0] if o["T_req"][k][0] is not None else "not_reached" for k in o["T_req"]],
                                     o["m_frac99"] if o["m_frac99"] else "not_reached"])
            result["catalysts"][cid] = cres
    flagged = all(v.get("extrapolation") is True for c in result["catalysts"].values() for cs in c["cases"].values()
                  for k, v in cs.items() if isinstance(v, dict) and v.get("P_bar") == 20.0)
    checks.append({"id": "T2A-EXTRAP-FLAG", "description": "every 20 bar output carries extrapolation: true", "status": "pass" if flagged else "fail"})
    tkeys = [f"P{P:g}_W{W:g}_X{X:g}" for P, W, X in TARGETS]
    doc = {
        "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT, "source_type": "python",
                       "inputs_summary": "lucentini2021nirukinetic Table 3 (values and +/- intervals in backend/amcrax/data/kinetics.yaml); "
                                         "amcrax.reactor.pfr through amcrax.uq.kinetic_hook; grey scenario of the reference scenario",
                       "reference_scenario": provenance_stamp(), "seed": SEED, "n_draws_per_case": N_DRAWS},
        "evidence_kind": "numerical_verification", "analysis_kind": "uncertainty_propagation", "label": LABEL,
        "label_t2a": "reported parameter uncertainty of a 1 atm laboratory fit; every result above 1 atm is an extrapolation",
        "assumptions": [
            "assumption: Table 3 intervals are 95 % marginal intervals (MATLAB nlpredci default alpha 0.05): sigma = half-width / 1.96",
            "assumption: no covariance published; C1 independent (upper bound on spread), C2 centred at T_ref = 748.15 K with ln k_ref independent of Ek (correlation assumption, not a published covariance)",
            "assumption: C3 acceptance band from the paper's parity plot (+/-10 % relative on all three Table 1 points); ABC-style, Table 1 points are fitting data",
            "k0, K1, K4 lognormal with the relative sigma; Ek normal; Latin hypercube, seed 20261123 for both cases",
            "reactor: isothermal PFR, no pressure drop, pure NH3 100 kmol/h, bed as scripts/research/kinetics_studies.py (eps 0.36, rho_p 1651.8 kg/m3), approach factor ON (AmCraX extension)",
            "LCOH: catalyst mass for 99 % of equilibrium at 600 degC / 20 bar scaled to the stored baseline NH3 feed, passed as catalyst_mass_kg; affects catalyst replacement cost only (reactor CAPEX is feed-scaled in the reference method; stored Aspen conversion unchanged)",
            "catalyst price: no sourced Ni-Ru/CeO2 price; Ni 33.4 and Ru 542 USD/kg (Cho 2026 Table 4, economics.yaml) used as two bounding proxies",
        ],
        "temperature_targets": tkeys, "bisection_bracket_C": [T_LO, T_HI], "root_xtol_K": 0.02,
        "X_eq_600C_20bar_pure_NH3": xe_600_20, "plant_scale_factor_nh3_feed": plant_scale,
        "lcoh_base_grey_HIon_USD_per_kg": base_eval["lcoh_USD_per_kg"], "catalyst_mass_base_kg": base_eval["catalyst_mass_kg"],
        **result, "acceptance_checks": checks,
    }
    (OUT / "kinetic_param_propagation.json").write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    with open(OUT / "kinetic_param_propagation_samples.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["catalyst_id", "case", "draw", "k0", "Ek_kJ_mol", "K1", "K4", "X_lab_400C", "X_lab_450C", "X_lab_500C",
                    *[f"T_required_C_{k}" for k in tkeys], "catalyst_mass_kg_frac_eq99_600C_20bar"])
        w.writerows(csv_rows)
    # figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, cid in zip(axs, CATS):
        for case, col in (("C1", "#2a6f97"), ("C2", "#e07a5f")):
            rows = [r for r in csv_rows if r[0] == cid and r[1] == case]
            for P, ls, j in ((ATM, "-", 10 + tkeys.index("P1.01325_W1000_X0.99")), (20.0, "--", 10 + tkeys.index("P20_W1000_X0.99"))):
                v = [r[j] for r in rows if r[j] != "not_reached"]
                if v:
                    ax.hist(v, bins=40, histtype="step", ls=ls, color=col, label=f"{case}, {P:g} bar" + (" (extrapolation)" if P > 2 else ""))
        ax.set_title(f"{CATS[cid]['short']}: T for X = 0.99, W = 1000 kg per 100 kmol/h", fontsize=9)
        ax.set_xlabel("Temperature required (degC)")
        ax.legend(fontsize=7)
    axs[0].set_ylabel("Draws")
    fig.text(0.01, 0.005, "Source: python (amcrax PFR) with lucentini2021nirukinetic Table 3 intervals; propagated parameter uncertainty of a 1 atm fit, "
             "20 bar = extrapolation. Not experimental validation.", fontsize=6.5, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "uq_kinetic_T_required.png", dpi=150)
    plt.close(fig)
    print(json.dumps(checks, indent=1, default=float))


if __name__ == "__main__":
    main()



