"""Workstream K, task 3: validate the Lucentini et al. (2021) LHHW laws against the paper's own Table 1 points.

Deterministic; run from the project root:  python scripts/research/kinetics_validation.py
Writes results/research/kinetics/validation_<catalyst>.json/.csv, results/research/validation/kinetics.json,
results/figures/research/kinetics_validation_lucentini.png (+ CSV of plotted data next to the JSON).

Experimental conditions (lucentini2021nirukinetic p. 6-7 Sec. 2.3 and Table 1 p. 10): 0.1 g catalyst, 1 atm,
Ar:NH3 = 1.2:1 (molar), total 25 mL min^-1 (F/W = 15.0 L g^-1 h^-1, GHSV 3660 h^-1), isothermal, 400/450/500 degC.
Reference state of mL min^-1 not stated: 0 degC, 1 atm assumed (25 degC run as sensitivity).
Note: the Table 1 points belong to the data set used for the fit (the paper fitted all its 1 atm experiments), so
this is a reproduction / consistency check of the published parameters, not an independent validation.
"""
from __future__ import annotations

import math
from pathlib import Path

from kinetics_common import (ATM_BAR, FIG, OUT, VAL, VM_0C_L_PER_MOL, VM_25C_L_PER_MOL, footer, parameter_override,
                             provenance, write_csv, write_json)

from amcrax.kinetics import get_catalyst
from amcrax.reactor.pfr import simulate_pfr

SCRIPT = "scripts/research/kinetics_validation.py"
TOL = 0.05  # absolute conversion, same tolerance as the existing KIN-* items (not weakened)

DATA = {
    "nire_ceo2_5ni1ru_lucentini_lhhw": {"T_C": [400, 450, 500], "X": [0.365, 0.861, 0.996], "short": "5Ni1Ru_CeO2"},
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": {"T_C": [400, 450, 500], "X": [0.497, 0.887, 0.992], "short": "2p5Ni0p5Ru_CeO2"},
}
SRC = "lucentini2021nirukinetic Table 1 (p. 10): x(%)NH3 at F/W 15.0 L gcat^-1 h^-1, 0.1 g, Ar:NH3 1.2:1, 1 atm"
W_KG = 1e-4
TOTAL_ML_MIN = 25.0
AR_TO_NH3 = 1.2


def feed(vm_L_mol: float) -> dict[str, float]:
    n_tot_kmol_h = TOTAL_ML_MIN * 1e-3 * 60.0 / vm_L_mol / 1000.0
    return {"NH3": n_tot_kmol_h / (1 + AR_TO_NH3), "Ar": n_tot_kmol_h * AR_TO_NH3 / (1 + AR_TO_NH3)}


def x_model(cid: str, T_C: float, vm=VM_0C_L_PER_MOL, approach_factor=None) -> float:
    r = simulate_pfr(cid, W_KG, T_in_C=T_C, P_in_bar=ATM_BAR, feed_kmol_h=feed(vm), mode="isothermal",
                     pressure_drop=False, approach_factor=approach_factor, n_points=3)
    return float(r.outlet["conversion"])


def stats(pred, obs):
    err = [p - o for p, o in zip(pred, obs)]
    return {"rmse": math.sqrt(sum(e * e for e in err) / len(err)), "max_abs_error": max(abs(e) for e in err),
            "mean_error": sum(err) / len(err)}


def main() -> None:
    import matplotlib.pyplot as plt
    from amcrax.plotstyle import apply_style, PALETTE
    apply_style()
    items = []
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    plot_rows = []
    for i, (cid, d) in enumerate(DATA.items()):
        cat = get_catalyst(cid)
        par = cat.parameters
        rows = []
        pred = [x_model(cid, T) for T in d["T_C"]]
        pred_pub = [x_model(cid, T, approach_factor=False) for T in d["T_C"]]
        pred_25 = [x_model(cid, T, vm=VM_25C_L_PER_MOL) for T in d["T_C"]]
        Ek, dEk = par["Ek"]["value"], par["Ek"]["uncertainty"]
        k0, dk0 = par["k0"]["value"], par["k0"]["uncertainty"]
        sens = {}
        for lab, kw in (("Ek_minus", {"Ek": Ek - dEk}), ("Ek_plus", {"Ek": Ek + dEk}),
                        ("k0_minus", {"k0": k0 - dk0}), ("k0_plus", {"k0": k0 + dk0})):
            with parameter_override(cid, **kw):
                sens[lab] = [x_model(cid, T) for T in d["T_C"]]
        for j, T in enumerate(d["T_C"]):
            rows.append({"catalyst_id": cid, "T_C": T, "P_bar": ATM_BAR, "W_g": 0.1, "F_over_W_L_g_h": 15.0,
                         "Ar_to_NH3": AR_TO_NH3, "X_published": d["X"][j], "X_python": pred[j],
                         "abs_error": pred[j] - d["X"][j],
                         "rel_error": (pred[j] - d["X"][j]) / d["X"][j],
                         "X_python_published_form_no_approach_factor": pred_pub[j],
                         "X_python_Vm_25C": pred_25[j],
                         "X_python_Ek_minus_CI": sens["Ek_minus"][j], "X_python_Ek_plus_CI": sens["Ek_plus"][j],
                         "X_python_k0_minus_CI": sens["k0_minus"][j], "X_python_k0_plus_CI": sens["k0_plus"][j],
                         "source_type_published": "literature", "source_type_python": "python"})
        st = stats(pred, d["X"])
        st_pub = stats(pred_pub, d["X"])
        st_25 = stats(pred_25, d["X"])
        res = {
            "provenance": provenance(SCRIPT, SRC + "; PFR isothermal, no pressure drop, 0.1 g, Vm 22.414 L/mol"),
            "catalyst_id": cid, "label": cat.label,
            "experimental_conditions": {"W_g": 0.1, "P_bar": ATM_BAR, "total_flow_mL_min": TOTAL_ML_MIN,
                                        "Ar_to_NH3_molar": AR_TO_NH3, "F_over_W_L_g_h": 15.0, "GHSV_h_inv": 3660,
                                        "bed_volume_cm3": 0.41, "reactor_inner_diameter_m": 0.004572,
                                        "source": "lucentini2021nirukinetic Sec. 2.3 (p. 6-7), Table 1 (p. 10)",
                                        "flow_reference_state": "assumption: 0 degC, 1 atm (not stated in source)"},
            "points": rows, "statistics": st,
            "statistics_published_form_no_approach_factor": st_pub,
            "statistics_flow_reference_25C": st_25,
            "sensitivity": {"basis": "reported confidence intervals of Table 3 (Ek +/- %g kJ/mol, k0 +/- %g mol/g/s), "
                                     "one parameter at a time" % (dEk, dk0),
                            "label": "reported uncertainty", "X_by_case": sens,
                            "caveat": "k0 and Ek are strongly correlated in an Arrhenius fit; moving Ek alone with k0 fixed "
                                      "overstates the joint uncertainty (no covariance is published)"},
            "nature_of_check": "reproduction of the fitting data (Table 1 points are part of the paper's 1 atm data set); not an independent validation",
            "applicability_limits": cat.validity,
            "source_type": "python vs literature",
        }
        short = d["short"]
        write_json(OUT / f"validation_{short}.json", res)
        write_csv(OUT / f"validation_{short}.csv", rows)
        items.append({
            "id": f"KINR-LUC-{short}", "description": f"{cat.label}: PFR reproduces Table 1 conversions (400-500 degC, 1 atm)",
            "method": "amcrax.reactor.pfr.simulate_pfr, isothermal, no pressure drop, the paper's conditions; max |X_python - X_published|",
            "reference_source": SRC, "observed": st["max_abs_error"], "expected": 0.0, "tolerance": TOL,
            "unit": "conversion (fraction)", "status": "pass" if st["max_abs_error"] <= TOL else "fail",
            "source_files": [f"results/research/kinetics/validation_{short}.json"],
            "note": "consistency check against the fitting data, not independent validation; RMSE %.4f" % st["rmse"]})
        c = PALETTE[i]
        Tg = [375 + 12.5 * j for j in range(13)]
        line = [x_model(cid, T) for T in Tg]
        with parameter_override(cid, Ek=Ek + dEk):
            lo = [x_model(cid, T) for T in Tg]
        with parameter_override(cid, Ek=Ek - dEk):
            hi = [x_model(cid, T) for T in Tg]
        ax.plot(Tg, [100 * x for x in line], "-", color=c, label=f"{short} python")
        ax.fill_between(Tg, [100 * x for x in lo], [100 * x for x in hi], color=c, alpha=0.12)
        ax.plot(d["T_C"], [100 * x for x in d["X"]], "o", color=c, label=f"{short} Table 1 (literature)")
        for r in rows:
            plot_rows.append({k: r[k] for k in ("catalyst_id", "T_C", "X_published", "X_python", "X_python_Ek_minus_CI", "X_python_Ek_plus_CI")})
    ax.set_xlabel("Temperature (degC)")
    ax.set_ylabel("NH3 conversion (%)")
    ax.set_title("Ni-Ru/CeO2 LHHW (Lucentini et al. 2021): Python PFR vs published points")
    ax.legend(fontsize=7.5)
    footer(fig, "python: amcrax PFR with lucentini2021nirukinetic Table 3; points: literature Table 1 (fit data); band: Ek +/- reported CI")
    fig.savefig(FIG / "kinetics_validation_lucentini.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    write_csv(OUT / "kinetics_validation_lucentini_plotdata.csv", plot_rows)

    # existing items stay visible: copy the status of the original KIN-* items (read only, not regenerated)
    import json
    from kinetics_common import ROOT
    vm = json.loads((ROOT / "results" / "validation" / "validation_matrix.json").read_text(encoding="utf-8"))
    vlist = vm if isinstance(vm, list) else vm.get("items", vm.get("checks", []))
    for it in vlist:
        if str(it.get("id", "")).startswith("KIN"):
            items.append({"id": "EXISTING-" + it["id"], "description": "existing item, unchanged (not re-run): " + str(it.get("expected_behaviour", "")),
                          "method": "read from results/validation/validation_matrix.json; " + str(it.get("validation_method", "")),
                          "reference_source": it.get("reference", ""),
                          "observed": it.get("value"), "expected": it.get("actual_result"), "tolerance": it.get("tolerance"),
                          "unit": it.get("metric", ""), "status": it.get("status"),
                          "root_cause_recorded": it.get("root_cause"),
                          "original_status": it.get("status"),
                          "source_files": ["results/validation/validation_matrix.json"]})
    # Aspen native representation vs Python law (from kinetics_aspen_spec.py output, if present)
    spec_p = OUT / "aspen_kinetics_spec.json"
    if spec_p.exists():
        spec = json.loads(spec_p.read_text(encoding="utf-8"))
        for c in spec["catalysts"]:
            if c["aspen_native"]:
                e = c["native_form_error_vs_python"]["max_rel_rate_error"]
                items.append({"id": f"KINR-ASPENFORM-{c['catalyst_id']}", "description": "Aspen LHHW parameter set reproduces the Python rate law",
                              "method": "rate from the Aspen LHHW parameters (SI) vs rate_mol_per_kgcat_s over " + c["native_form_error_vs_python"]["range"],
                              "reference_source": "python rate law (kinetics.yaml)", "observed": e, "expected": 0.0, "tolerance": 0.01,
                              "unit": "relative rate error (max)", "status": "pass" if e <= 0.01 else "fail",
                              "source_files": ["results/research/kinetics/aspen_kinetics_spec.json"]})
            else:
                e = c["best_native_approximation"]["conversion_error_vs_python_pfr"]["max_abs"]
                items.append({"id": f"KINR-ASPENAPPROX-{c['catalyst_id']}", "description": "fitted native LHHW approximation of the microkinetic law: PFR conversion error at the reference points",
                              "method": "isothermal PFR with the approximation vs simulate_pfr with the microkinetic law",
                              "reference_source": "python microkinetic law (takahashi2016kinetic Table 1)", "observed": e, "expected": 0.0,
                              "tolerance": 0.05, "unit": "conversion (fraction)", "status": "pass" if e <= 0.05 else "fail",
                              "source_files": ["results/research/kinetics/aspen_kinetics_spec.json"],
                              "note": "approximation fitted by AmCraX (python), not a literature law; max relative rate error %.2f" % c["best_native_approximation"]["rate_error_vs_python_law"]["max_rel"]})
    items.append({"id": "KINR-LIT-LUC2019", "description": "essay lead: Ru/CeO2 98 % vs Ni/CeO2 63 % at 450 degC (1 atm, GHSV 3067 1/h, Ar:NH3 1.3:1)",
                  "method": "read in the primary source text", "reference_source": "lucentini2019ceo2 p. 10-11 (postprint), Fig. 1",
                  "observed": "98 vs 63 % (text)", "expected": "98 vs 63 %", "tolerance": None, "unit": "%", "status": "informational",
                  "source_files": ["research/notes/lucentini2019ceo2.md"],
                  "note": "confirmed; the paper has no rate law, so Ni/CeO2 and Ru/CeO2 are not modelled"})
    items.append({"id": "KINR-LIT-SAYAS2020", "description": "essay lead: Ru-K/CaO Ea 96 -> 75 kJ/mol, H2 order -1.9 vs -1.2, about 80 % at 40 bar/550 degC",
                  "method": "primary-source read (main text read in full on 24 Nov 2026; supplementary information not obtained)",
                  "reference_source": "sayas2020rukcao p. 5033 Table 4; p. 5030-5031 text; Fig. 4A",
                  "observed": {"Ea_kJ_per_mol": [96, 75], "H2_order": [-1.9, -1.2], "X_550C_40bar": "around 80 % (text); about 84 % (figure)"},
                  "expected": {"Ea_kJ_per_mol": [96, 75], "H2_order": [-1.9, -1.2], "X_550C_40bar": "about 80 %"},
                  "tolerance": None, "unit": "-", "status": "informational",
                  "source_files": ["research/notes/sayas2020_full_text.md", "research/data/sayas2020_extract.json"],
                  "note": "VERIFIED in the main text (Table 4, 350 degC and 1 atm, differential experiments). No complete rate law: the "
                          "rate constant and equilibrium term are in the supplementary information (not obtained); no Ru-K/CaO law "
                          "implemented and nothing fitted"})
    write_json(VAL / "kinetics.json", items)
    # Phase 2 (task K1): evidence_kind on every item + the K1P2- items (scripts/research/kinetics_phase2_validation.py)
    import importlib.util
    _sp = importlib.util.spec_from_file_location("kinetics_phase2_validation",
                                                 Path(__file__).with_name("kinetics_phase2_validation.py"))
    _m = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(_m)
    _m.apply(("kinetics",))
    for it in items:
        print(it["id"], it["status"], it.get("original_status", ""), it["observed"])


if __name__ == "__main__":
    main()
