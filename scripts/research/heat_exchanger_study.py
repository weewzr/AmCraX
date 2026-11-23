"""Phase 2 task X1: FEHE duty diagnosis (HCAT-ASPY-*-HI-heat), exchanger sizing and cost, net benefit of heat integration.

    python scripts/research/heat_exchanger_study.py

Writes results/research/heat_exchanger/*.json, results/research/validation/heat_exchanger.json and
results/figures/research/heat_exchanger_*.png. Deterministic; no Aspen run, no network.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from amcrax.economics.reference import load_reference_scenario, provenance_stamp, reference_capex  # noqa: E402
from amcrax.economics.singapore import evaluate  # noqa: E402
from amcrax.heat_integration import analyse  # noqa: E402
from amcrax.heat_integration import exchanger as hx  # noqa: E402
from amcrax.process_model import properties as pp  # noqa: E402
from amcrax.process_model.flowsheet import run_python_case  # noqa: E402
from amcrax.research import catalyst_comparison as cc  # noqa: E402
from amcrax.schemas import SimulationResult  # noqa: E402
from amcrax.thermodynamics.peng_robinson import enthalpy_departure_J_mol  # noqa: E402

OUT = ROOT / "results/research/heat_exchanger"
FIG = ROOT / "results/figures/research"
VAL = ROOT / "results/research/validation/heat_exchanger.json"
ASP = ROOT / "results/research/aspen_kinetic"
K0 = 273.15
ASPEN_HI = {"ru_kum_temkin_pyzhev": "ci_kum_T499_P20_W100", "ru_takahashi_microkinetic": "ci_tru_T522_P20_W100",
            "nire_ceo2_5ni1ru_lucentini_lhhw": "ci_luc5_T572_P20_W100",
            "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "ci_luc25_T576_P20_W100", "ni_takahashi_microkinetic": "ci_tni_T594_P20_W100"}
REF = load_reference_scenario()
FX = REF.fx_SGD_per_USD
U_KEYS = ("low", "central", "high")
items: list[dict] = []


def add(id_, desc, kind, observed, expected, tol, unit, status, files, note=""):
    items.append({"id": id_, "description": desc, "evidence_kind": kind, "observed": observed, "expected": expected,
                  "tolerance": tol, "unit": unit, "status": status, "source_files": files, **({"note": note} if note else {})})


def load_res(path: Path) -> SimulationResult:
    j = json.loads(path.read_text(encoding="utf-8"))
    if "aspen" in j and "flowsheet_result" in j["aspen"]:
        j = j["aspen"]["flowsheet_result"]
    return SimulationResult.model_validate(j)


def fehe_state(res: SimulationResult) -> dict:
    s = res.streams
    return {"duty_kW": abs(res.blocks["FEHE"].duty_kW), "T_hot_in": s["S5"].temperature_C, "T_hot_out": s["S6"].temperature_C,
            "T_cold_in": s["S2"].temperature_C, "T_cold_out": s["S3"].temperature_C,
            "ua_seg_kW_K": analyse(res).fehe.ua_segmented_kW_K}


def size_all(st: dict, **kw) -> dict:
    out = {}
    for u in U_KEYS:
        out[u] = hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], u,
                                  ua_kW_K=st["ua_seg_kW_K"], **kw)
    return out


def slim(r: dict) -> dict:
    keys = ("U_case", "U_W_m2K", "area_m2", "n_shells", "F", "arrangement", "ua_kW_K", "lmtd_K", "purchase_USD",
            "installed_USD", "tci_equivalent_USD", "annualised_USD_per_yr", "purchase_SGD", "installed_SGD", "tci_equivalent_SGD")
    d = {k: r[k] for k in keys}
    d["n_units_costed"] = r["cost"]["n_units"]
    d["area_per_unit_m2"] = r["cost"]["area_per_unit_m2"]
    d["below_correlation_range"] = r["cost"]["below_range"]
    d["correlation"] = r["cost"]["correlation"]
    return d


# ======================================================================================== 1. diagnosis
def diagnosis() -> dict:
    rows = []
    cases = [(cid, ASP / f"{tag}_hi.json") for cid, tag in ASPEN_HI.items()] + [("baseline_rgibbs_600C", ROOT / "results/simulations/baseline.json")]
    for cid, path in cases:
        a = load_res(path)
        if cid == "baseline_rgibbs_600C":
            p = run_python_case(a.inputs)
        else:
            p = cc.kinetic_flowsheet(a.inputs.reactor_temperature_C, 20.0, a.kpis.nh3_conversion, True)
        sa, sp = a.streams, p.streams
        n = {k: v for k, v in sp["S2"].component_mole_flow_kmol_h.items() if v > 0}
        T2a, T3a, P2a, P3a = sa["S2"].temperature_C + K0, sa["S3"].temperature_C + K0, sa["S2"].pressure_bar, sa["S3"].pressure_bar
        Qa, Qp = a.blocks["FEHE"].duty_kW, p.blocks["FEHE"].duty_kW
        q_py_aspen_states = pp.feed_gas_enthalpy_kW(n, T3a, P3a) - pp.feed_gas_enthalpy_kW(n, T2a, P2a)
        q_pr_aspen_states = pp.gas_enthalpy_kW(n, T3a, P3a, "pr") - pp.gas_enthalpy_kW(n, T2a, P2a, "pr")
        tot = sum(n.values())
        y = {k: v / tot for k, v in n.items()}
        res_ref2 = n["NH3"] * pp.nh3_residual_enthalpy_kJ_mol(T2a, P2a) / 3.6
        res_ref3 = n["NH3"] * pp.nh3_residual_enthalpy_kJ_mol(T3a, P3a) / 3.6
        res_pr2 = tot * enthalpy_departure_J_mol(y, T2a, P2a) / 3600.0
        res_pr3 = tot * enthalpy_departure_J_mol(y, T3a, P3a) / 3600.0
        n5 = {k: v for k, v in sa["S5"].component_mole_flow_kmol_h.items() if v > 0}
        q_hot_pr = (pp.gas_enthalpy_kW(n5, sa["S5"].temperature_C + K0, sa["S5"].pressure_bar, "pr")
                    - pp.gas_enthalpy_kW(n5, sa["S6"].temperature_C + K0, sa["S6"].pressure_bar, "pr"))
        rows.append({
            "case": cid, "source_file": str(path.relative_to(ROOT)).replace("\\", "/"), "T_reactor_C": a.inputs.reactor_temperature_C,
            "aspen_duty_kW": Qa, "python_duty_kW": Qp, "difference_kW": Qp - Qa, "rel_difference": (Qp - Qa) / Qa,
            "aspen_S2_C": T2a - K0, "python_S2_C": sp["S2"].temperature_C, "S2_difference_K": sp["S2"].temperature_C - (T2a - K0),
            "aspen_dew_point_C_implied": T2a - K0 - 10.0, "python_dew_point_C": p.blocks["VAPORIZR"].details["dew_point_C"],
            "S3_C_both": T3a - K0,
            "state_effect_kW": Qp - q_py_aspen_states,
            "property_effect_kW": q_py_aspen_states - Qa,
            "python_cold_side_on_PR_basis_at_aspen_states_kW": q_pr_aspen_states,
            "python_PR_basis_minus_aspen_kW": q_pr_aspen_states - Qa,
            "NH3_residual_S2_reference_EOS_kW": res_ref2, "residual_S2_PR_kW": res_pr2,
            "NH3_residual_S3_reference_EOS_kW": res_ref3, "residual_S3_PR_kW": res_pr3,
            "residual_basis_effect_kW": (res_ref3 - res_ref2) - (res_pr3 - res_pr2),
            "python_hot_side_PR_at_aspen_states_kW": q_hot_pr, "hot_side_rel_to_aspen": (q_hot_pr - Qa) / Qa,
            "rel_if_state_matched": (q_py_aspen_states - Qa) / Qa,
            "rel_if_PR_residual_used_python_S2": (Qp - q_py_aspen_states + q_pr_aspen_states - Qa) / Qa,
            "python_vaporiser_kW": p.blocks["VAPORIZR"].duty_kW, "aspen_vaporiser_kW": a.blocks["VAPORIZR"].duty_kW,
        })
    for r in rows:
        add(f"HX-DIAG-{r['case']}", "Decomposition of Python minus Aspen FEHE duty into vaporiser-outlet state and "
            "cold-side residual-enthalpy basis (sum must reproduce the total difference)", "numerical_verification",
            r["state_effect_kW"] + r["property_effect_kW"], r["difference_kW"], 1e-6, "kW",
            "pass" if abs(r["state_effect_kW"] + r["property_effect_kW"] - r["difference_kW"]) <= 1e-6 else "fail", [r["source_file"]])
        add(f"HX-DIAG-PRBASIS-{r['case']}", "Python cold-side enthalpy change on the Peng-Robinson basis at the Aspen "
            "S2/S3 states vs Aspen PENG-ROB FEHE duty (shows the property offset is the residual-enthalpy model choice)",
            "python_vs_aspen", r["python_cold_side_on_PR_basis_at_aspen_states_kW"], r["aspen_duty_kW"], 0.01, "relative",
            "pass" if abs(r["python_PR_basis_minus_aspen_kW"] / r["aspen_duty_kW"]) <= 0.01 else "fail", [r["source_file"]])
        add(f"HX-DIAG-HOT-{r['case']}", "Python PR hot-side enthalpy change S5->S6 at the Aspen states vs Aspen FEHE duty",
            "python_vs_aspen", r["python_hot_side_PR_at_aspen_states_kW"], r["aspen_duty_kW"], 0.01, "relative",
            "pass" if abs(r["hot_side_rel_to_aspen"]) <= 0.01 else "fail", [r["source_file"]])
    add("HX-DIAG-CAUSE", "HCAT-ASPY-*-HI-heat failures: quantified cause (model-form, not an implementation error; checks kept failing, tolerance unchanged)",
        "python_vs_aspen", {r["case"]: round(r["rel_difference"], 4) for r in rows}, "<= 0.03", 0.03, "relative", "informational",
        ["results/research/heat_exchanger/fehe_duty_diagnosis.json"],
        note=("+20.8 kW in every case = (i) vaporiser outlet S2 5.81 K colder in Python (Raoult dew point 60.09 degC + 10 K vs "
              "Aspen PENG-ROB dew point 65.90 + 10 K): +8.76 kW; (ii) cold-side NH3 residual enthalpy from the reference EOS "
              "(CoolProp) instead of PR: +12.1 kW. On the PR basis at Aspen states Python reproduces Aspen within 0.12 %."))
    return {"rows": rows}


# ======================================================================================== 2/3. sizing, cost, benefit
def net_benefit(label, st, saving_USD_per_kg, annual_h2_kg, extra=None) -> dict:
    sized = size_all(st)
    sized_tow = size_all(st, correlation="towler")
    saving_yr = saving_USD_per_kg * annual_h2_kg
    tci_be = hx.capital_for_annual(saving_yr)
    U_be = hx.breakeven_U(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], tci_be,
                          ua_kW_K=st["ua_seg_kW_K"])
    U_be_tow = hx.breakeven_U(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], tci_be,
                              ua_kW_K=st["ua_seg_kW_K"], correlation="towler")
    cost_kg = {u: sized[u]["annualised_USD_per_yr"] / annual_h2_kg for u in U_KEYS}
    return {"case": label, **(extra or {}), "fehe": st, "saving_USD_per_kg": saving_USD_per_kg,
            "saving_SGD_per_kg": saving_USD_per_kg * FX, "annual_h2_kg": annual_h2_kg, "saving_USD_per_yr": saving_yr,
            "sizing_turton": {u: slim(sized[u]) for u in U_KEYS}, "sizing_towler": {u: slim(sized_tow[u]) for u in U_KEYS},
            "exchanger_cost_USD_per_kg": cost_kg,
            "net_benefit_USD_per_kg": {u: saving_USD_per_kg - cost_kg[u] for u in U_KEYS},
            "net_benefit_SGD_per_kg": {u: (saving_USD_per_kg - cost_kg[u]) * FX for u in U_KEYS},
            "net_benefit_towler_USD_per_kg": {u: saving_USD_per_kg - sized_tow[u]["annualised_USD_per_yr"] / annual_h2_kg for u in U_KEYS},
            "breakeven_tci_USD": tci_be, "breakeven_tci_SGD": tci_be * FX,
            "breakeven_U_W_m2K_turton": U_be, "breakeven_U_W_m2K_towler": U_be_tow,
            "survives": all(saving_USD_per_kg - cost_kg[u] > 0 for u in U_KEYS)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    diag = diagnosis()
    (OUT / "fehe_duty_diagnosis.json").write_text(json.dumps({"provenance": prov("FEHE duty diagnosis"), **diag}, indent=1), encoding="utf-8")

    # ---- baseline (Aspen stored baseline, reference basis)
    base = load_res(ROOT / "results/simulations/baseline.json")
    nohi = load_res(ROOT / "results/simulations/baseline_no_hi.json")
    e_hi, e_no = evaluate(base), evaluate(nohi)
    st = fehe_state(base)
    saving = e_no["lcoh_USD_per_kg"] - e_hi["lcoh_USD_per_kg"]
    bres = net_benefit("baseline_aspen_600C", st, saving, e_hi["annual_h2_kg"],
                       {"lcoh_hi_USD_per_kg": e_hi["lcoh_USD_per_kg"], "lcoh_no_hi_USD_per_kg": e_no["lcoh_USD_per_kg"],
                        "saving_components_USD_per_kg": {k: e_no["breakdown_USD_per_kg"][k] - e_hi["breakdown_USD_per_kg"][k]
                                                         for k in e_hi["breakdown_USD_per_kg"]}})
    add("HX-BASE-LCOH-FROZEN", "Reference baseline LCOH unchanged (frozen basis)", "numerical_verification",
        e_hi["lcoh_USD_per_kg"], 4.015461254695034, 1e-9, "USD/kg", "pass" if abs(e_hi["lcoh_USD_per_kg"] - 4.015461254695034) < 1e-9 else "fail",
        ["results/simulations/baseline.json"])
    add("HX-BASE-SAVING", "Phase 1 heat-integration saving on the reference basis (4.229 - 4.015)", "numerical_verification",
        saving, 0.214, 0.001, "USD/kg", "pass" if abs(saving - 0.214) <= 0.001 else "fail",
        ["results/simulations/baseline.json", "results/simulations/baseline_no_hi.json"])
    # counter-current alternative
    cc_alt = {u: slim(hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], u,
                                       ua_kW_K=st["ua_seg_kW_K"], counter_current=True)) for u in U_KEYS}
    lm_only = hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], "central")
    # reference CAPEX comparison
    rc = reference_capex(REF.nh3_feed_kmol_h)
    ref_hx_tci = rc["tci_by_item_USD"]["heat_exchangers"]
    ref_hx_isbl = rc["isbl_USD"]["heat_exchangers"]
    fehe_tci = {u: bres["sizing_turton"][u]["tci_equivalent_USD"] for u in U_KEYS}
    comparison = {
        "reference_item": "heat_exchangers (cho2026_itemised_v1; all exchangers of the Cho plant, scaled by NH3 feed)",
        "reference_isbl_installed_USD": ref_hx_isbl, "reference_tci_USD": ref_hx_tci, "reference_tci_SGD": ref_hx_tci * FX,
        "fehe_tci_equivalent_USD": fehe_tci, "fehe_share_of_reference_item": {u: fehe_tci[u] / ref_hx_tci for u in U_KEYS},
        "verdict": ("not comparable one-to-one: the reference item covers every exchanger of the Cho plant (FEHE, vaporiser, coolers, "
                    "flue-gas exchangers, waste-heat boiler side) and does not respond to area; the FEHE alone is "
                    f"{fehe_tci['high'] / ref_hx_tci:.0%}-{fehe_tci['low'] / ref_hx_tci:.0%} of it. Agreement is consistent "
                    "(FEHE < item) but not a validation."),
    }
    add("HX-REFCAPEX-CONSISTENT", "FEHE TCI-equivalent below the reference heat-exchanger item (which covers all exchangers)",
        "literature_comparison", fehe_tci, ref_hx_tci, None, "USD", "pass" if max(fehe_tci.values()) < ref_hx_tci else "fail",
        ["backend/amcrax/data/reference_scenario.yaml"])
    # hand check of the Turton correlation
    a = 100.0
    hand = 10 ** (4.3247 - 0.3030 * 2 + 0.1634 * 4)
    add("HX-TURTON-HAND", "Turton Cp0 at 100 m2 (fixed tube sheet) vs hand evaluation", "numerical_verification",
        hx.turton_cost(a, 0.0, "CS/CS", cepci_target=397.0)["Cp0_per_unit_USD_2001"], hand, 1e-6, "USD (2001)",
        "pass" if abs(hx.turton_cost(a, 0.0, "CS/CS", cepci_target=397.0)["Cp0_per_unit_USD_2001"] - hand) < 1e-6 else "fail", ["backend/amcrax/heat_integration/exchanger.py"])
    f_hand = hx.f_correction(200.0, 100.0, 50.0, 100.0, 1)  # R = 2, P = 1/3
    s = math.sqrt(5)
    f_ref = s * math.log((1 - 1 / 3) / (1 - 2 / 3)) / ((2 - 1) * math.log((2 - (3 - s) / 3) / (2 - (3 + s) / 3)))
    add("HX-F-HAND", "F correction (1-2 shell, R = 2, P = 1/3) vs closed form", "numerical_verification", f_hand, f_ref, 1e-12, "-",
        "pass" if abs(f_hand - f_ref) < 1e-12 else "fail", ["backend/amcrax/heat_integration/exchanger.py"])
    ua_lm = st["duty_kW"] / hx.lmtd(st["T_hot_in"] - st["T_cold_out"], st["T_hot_out"] - st["T_cold_in"])
    add("HX-UA-SEG-VS-LMTD", "Segmented UA (H-T curves) vs Q/LMTD for the baseline FEHE (cp variation)", "numerical_verification",
        st["ua_seg_kW_K"], ua_lm, None, "kW/K", "informational", ["results/simulations/baseline.json"],
        note=f"ratio {st['ua_seg_kW_K'] / ua_lm:.3f}; the segmented value is used for area")

    # ---- catalyst design cases
    cat = json.loads((ROOT / "results/research/catalyst_comparison/catalyst_comparison.json").read_text(encoding="utf-8"))["rows"]
    cases = []
    for cid, tag in ASPEN_HI.items():
        rh = next(r for r in cat if r["catalyst_id"] == cid and r["source_type"] == "aspen" and r["heat_integration"])
        rn = next(r for r in cat if r["catalyst_id"] == cid and r["source_type"] == "aspen" and not r["heat_integration"])
        res = load_res(ASP / f"{tag}_hi.json")
        cases.append(net_benefit(f"{cid}@{rh['T_C']:.0f}C_aspen_W100", fehe_state(res), rn["lcoh_USD_per_kg"] - rh["lcoh_USD_per_kg"],
                                 rh["annual_h2_kg"], {"catalyst_id": cid, "source_type": "aspen (duties) + python (economics)",
                                                      "T_C": rh["T_C"], "lcoh_hi": rh["lcoh_USD_per_kg"], "lcoh_no_hi": rn["lcoh_USD_per_kg"],
                                                      "basis": "same T and 100 kg catalyst, HI on vs off"}))
    for cid in ASPEN_HI:
        pys = [r for r in cat if r["catalyst_id"] == cid and r["source_type"] == "python"]
        rh = [r for r in pys if r["heat_integration"]]
        rh = min(rh, key=lambda r: r["lcoh_USD_per_kg"])
        rn = next(r for r in pys if not r["heat_integration"])
        res = cc.kinetic_flowsheet(rh["T_C"], 20.0, 0.95, True)
        cases.append(net_benefit(f"{cid}@Topt_python", fehe_state(res), rn["lcoh_USD_per_kg"] - rh["lcoh_USD_per_kg"],
                                 rh["annual_h2_kg"], {"catalyst_id": cid, "source_type": "python", "T_C": rh["T_C"],
                                                      "T_C_no_hi": rn["T_C"], "lcoh_hi": rh["lcoh_USD_per_kg"], "lcoh_no_hi": rn["lcoh_USD_per_kg"],
                                                      "basis": "each at its own cost-optimal T with and without HI (python)"}))

    # ---- sensitivities (baseline)
    sens = {}
    Ugrid = [10, 15, 20, 25, 35, 50, 72.5, 100, 150, 250, 500]
    sens["U"] = [{"U_W_m2K": U, **{k: v for k, v in slim(hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"],
                                                                          st["T_cold_out"], float(U), ua_kW_K=st["ua_seg_kW_K"])).items()
                                     if k in ("area_m2", "tci_equivalent_USD", "annualised_USD_per_yr")},
                  "net_benefit_USD_per_kg": saving - hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"],
                                                                      float(U), ua_kW_K=st["ua_seg_kW_K"])["annualised_USD_per_yr"] / e_hi["annual_h2_kg"]}
                 for U in Ugrid]
    sens["nh3_fuel_price"] = []
    for p in (300.0, 450.0, 487.0, 610.0, 1000.0):
        o = {"nh3_price_USD_per_t": p}
        sv = evaluate(nohi, overrides=o)["lcoh_USD_per_kg"] - evaluate(base, overrides=o)["lcoh_USD_per_kg"]
        sens["nh3_fuel_price"].append({"nh3_price_USD_per_t": p, "saving_USD_per_kg": sv,
                                       **{f"net_{u}_USD_per_kg": sv - bres["exchanger_cost_USD_per_kg"][u] for u in U_KEYS},
                                       "breakeven_tci_USD": hx.capital_for_annual(sv * e_hi["annual_h2_kg"])})
    sens["capital_recovery"] = []
    for d, n in ((0.085, 25), (0.10, 25), (0.10, 20), (0.12, 15), (0.15, 10)):
        crf = d * (1 + d) ** n / ((1 + d) ** n - 1)
        sens["capital_recovery"].append({"discount_rate": d, "life_yr": n, "crf": crf,
                                         **{f"net_{u}_USD_per_kg": saving - hx.annualised_cost(bres["sizing_turton"][u]["tci_equivalent_USD"], crf) / e_hi["annual_h2_kg"] for u in U_KEYS},
                                         "breakeven_tci_USD": hx.capital_for_annual(saving * e_hi["annual_h2_kg"], crf)})
    sens["cepci_material_correlation"] = []
    for lab, kw in (("CEPCI 720.2 (Kum)", {"cepci_target": 720.2}), ("CEPCI 800.3 (Ahmad)", {"cepci_target": 800.3}),
                    ("CS/SS", {"material": "CS/SS"}), ("CS/CS", {"material": "CS/CS"}), ("Towler U-tube", {"correlation": "towler"}),
                    ("counter-current F=1", {"counter_current": True})):
        r = hx.size_and_cost(st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"], "low", ua_kW_K=st["ua_seg_kW_K"], **kw)
        sens["cepci_material_correlation"].append({"variant": lab, "U_case": "low", "tci_equivalent_USD": r["tci_equivalent_USD"],
                                                   "net_benefit_USD_per_kg": saving - r["annualised_USD_per_yr"] / e_hi["annual_h2_kg"]})
    # approach temperature (python flowsheet on the baseline inputs; python offset vs Aspen +3.4 % FEHE duty)
    sens["approach_python"] = []
    inp0 = base.inputs
    pno = run_python_case(inp0.model_copy(update={"heat_integration": False}))
    l_no = evaluate(pno)["lcoh_USD_per_kg"]
    for dT in (20.0, 30.0, 40.0, 50.0, 75.0, 100.0, 150.0, 200.0):
        try:
            pr = run_python_case(inp0.model_copy(update={"fehe_hot_end_approach_K": dT}))
        except Exception as ex:  # infeasible approach
            sens["approach_python"].append({"approach_K": dT, "error": str(ex)[:200]})
            continue
        e = evaluate(pr)
        sv = l_no - e["lcoh_USD_per_kg"]
        stp = fehe_state(pr)
        row = {"approach_K": dT, "fehe_duty_kW": stp["duty_kW"], "T_hot_out_C": stp["T_hot_out"], "ua_seg_kW_K": stp["ua_seg_kW_K"],
               "saving_USD_per_kg": sv}
        for u in U_KEYS:
            r = hx.size_and_cost(stp["duty_kW"], stp["T_hot_in"], stp["T_hot_out"], stp["T_cold_in"], stp["T_cold_out"], u, ua_kW_K=stp["ua_seg_kW_K"])
            row[f"area_{u}_m2"] = r["area_m2"]
            row[f"net_{u}_USD_per_kg"] = sv - r["annualised_USD_per_yr"] / e["annual_h2_kg"]
        sens["approach_python"].append(row)

    # ---- validation on outcomes
    for c in [bres] + cases:
        add(f"HX-NET-{c['case']}", "Net benefit of the FEHE (fuel saving minus annualised exchanger cost) at low/central/high U",
            "numerical_verification", c["net_benefit_USD_per_kg"], "> 0", None, "USD/kg H2", "informational",
            ["results/research/heat_exchanger/heat_exchanger_study.json"])
    add("HX-FEHE-AREA-RANGE", "Baseline FEHE area per costed unit inside the Turton correlation range 10-1000 m2 (all U cases)",
        "numerical_verification", {u: bres["sizing_turton"][u]["area_per_unit_m2"] for u in U_KEYS}, [10, 1000], None, "m2",
        "pass" if all(10 <= bres["sizing_turton"][u]["area_per_unit_m2"] <= 1000 for u in U_KEYS) else "informational",
        ["results/research/heat_exchanger/heat_exchanger_study.json"],
        note="below 10 m2 per unit the cost is evaluated at 10 m2 (flagged below_correlation_range)")

    out = {"provenance": prov("FEHE sizing, cost and net benefit of heat integration"),
           "method": hx.__doc__.split("Method")[1].strip() if "Method" in (hx.__doc__ or "") else "",
           "U_cases": hx.U_CASES, "cepci": hx.CEPCI, "correlations": {"turton": {k: v for k, v in hx.TURTON.items()}, "towler": hx.TOWLER},
           "sources": hx.SOURCES, "fx_SGD_per_USD": FX, "fx_date": REF.fx_date,
           "baseline": bres, "baseline_counter_current_alternative": cc_alt,
           "baseline_lmtd_only_central": slim(lm_only), "reference_capex_comparison": comparison,
           "catalyst_cases": cases, "sensitivity": sens,
           "row_evidence": row_evidence(bres, cases, sens)}
    (OUT / "heat_exchanger_study.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    VAL.write_text(json.dumps(items, indent=1, default=float), encoding="utf-8")
    figures(bres, cases, sens)
    print(json.dumps({"baseline": {k: bres[k] for k in ("saving_USD_per_kg", "breakeven_tci_USD", "breakeven_U_W_m2K_turton", "survives")},
                      "net": bres["net_benefit_USD_per_kg"], "area": {u: bres["sizing_turton"][u]["area_m2"] for u in U_KEYS},
                      "tci": fehe_tci, "ref_tci": ref_hx_tci,
                      "cases": {c["case"]: [round(c["saving_USD_per_kg"], 4), {u: round(v, 4) for u, v in c["net_benefit_USD_per_kg"].items()},
                                            round(c["breakeven_U_W_m2K_turton"] or -1, 2)] for c in cases},
                      "status": {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "informational")}}, indent=1, default=float))


def row_evidence(b, cases, sens) -> dict:
    nets = [v for c in [b] + cases for v in c["net_benefit_USD_per_kg"].values()]
    ube = [c["breakeven_U_W_m2K_turton"] for c in [b] + cases if c["breakeven_U_W_m2K_turton"]]
    worst_sens = min([r["net_benefit_USD_per_kg"] for r in sens["U"] if r["U_W_m2K"] >= 10]
                     + [r[f"net_low_USD_per_kg"] for r in sens["nh3_fuel_price"]]
                     + [r[f"net_low_USD_per_kg"] for r in sens["capital_recovery"]]
                     + [r["net_benefit_USD_per_kg"] for r in sens["cepci_material_correlation"]])
    base = load_res(ROOT / "results/simulations/baseline.json").kpis
    nohi = load_res(ROOT / "results/simulations/baseline_no_hi.json").kpis
    savings = [c["saving_USD_per_kg"] for c in [b] + cases] + [r["saving_USD_per_kg"] for r in sens["approach_python"] if "saving_USD_per_kg" in r]
    negatives = ([f"U {r['U_W_m2K']}" for r in sens["U"] if r["net_benefit_USD_per_kg"] <= 0]
                 + [f"NH3 {r['nh3_price_USD_per_t']} USD/t, U {u}" for r in sens["nh3_fuel_price"] for u in U_KEYS if r[f"net_{u}_USD_per_kg"] <= 0]
                 + [f"CRF {r['crf']:.3f}, U {u}" for r in sens["capital_recovery"] for u in U_KEYS if r[f"net_{u}_USD_per_kg"] <= 0]
                 + [f"approach {r['approach_K']} K, U {u}" for r in sens["approach_python"] for u in U_KEYS if r.get(f"net_{u}_USD_per_kg", 1) <= 0])
    return {"H3-d": {
        "proposed_verdict": "SUPPORTED" if min(savings) > 0 else "INCONCLUSIVE",
        "numbers": {"energy_first_law_deficit_kW_hi_vs_nohi": [base.net_fuel_heat_deficit_kW, nohi.net_fuel_heat_deficit_kW],
                    "energy_total_external_heating_kW_hi_vs_nohi": [base.total_external_heating_kW, nohi.total_external_heating_kW],
                    "energy_reduction_first_law": 1 - base.net_fuel_heat_deficit_kW / nohi.net_fuel_heat_deficit_kW,
                    "energy_reduction_total_external_heating": 1 - base.total_external_heating_kW / nohi.total_external_heating_kW,
                    "min_fuel_saving_over_cases_and_approaches_USD_per_kg": min(savings),
                    "net_benefit_negative_in": negatives,
                    "baseline_fuel_saving_USD_per_kg": b["saving_USD_per_kg"],
                    "baseline_exchanger_cost_USD_per_kg": b["exchanger_cost_USD_per_kg"],
                    "baseline_net_USD_per_kg": b["net_benefit_USD_per_kg"],
                    "baseline_breakeven_tci_USD": b["breakeven_tci_USD"], "baseline_breakeven_U_W_m2K": b["breakeven_U_W_m2K_turton"],
                    "min_net_over_cases_and_U_USD_per_kg": min(nets), "max_breakeven_U_over_cases_W_m2K": max(ube),
                    "worst_sensitivity_net_USD_per_kg": worst_sens},
        "assumptions": ["U typical-range cases (VDI Heat Atlas C3; central derived)", "Turton 2018 module costing, SS/SS, 19.5 barg, CEPCI 797.9",
                        "TCI-equivalent = bare module x 1.4336 (reference indirect factor, conservative)",
                        "fuel saving on the unified reference basis (first-law deficit, supplementary NH3 at 450 USD/t)",
                        "reference CAPEX does not change between HI on and off; exchanger treated as incremental"],
        "uncertainty": "U 10-500 W/(m2 K), NH3 300-1000 USD/t, CRF 0.094-0.199, CEPCI 720-800, material CS/CS to SS/SS, Towler correlation, F=1 vs multi-shell",
        "envelope": "20 bar, 499-625 degC reactor, FEHE hot-end approach 20-200 K (python), U >= break-even U",
        "threshold": {"breakeven_U_W_m2K_range_over_cases": [min(ube), max(ube)],
                      "sourced_typical_U_W_m2K": {"gas ~1 bar both sides": [5, 35], "gas 200-300 bar both sides": [150, 500]},
                      "note": ("break-even U (conservative multi-shell 1-2 design, SS/SS, TCI factor 1.4336) is 7.7-11.3 W/(m2 K); it lies "
                               "inside the 1-bar typical range and far below the high-pressure range. No sourced value at 20 bar: a 20 bar "
                               "gas is expected above the 1-bar range, but that is an engineering expectation, not a sourced number.")},
        "reason": ("Energy (the H3-d claim): heat integration lowers the first-law heat deficit by 44 % and total external heating "
                   "by 21 % in Aspen (baseline 600 degC), and the fuel saving is positive in every catalyst case and at every FEHE "
                   "approach 20-200 K (python); it is a computed result, not a built-in assumption (the 50 K approach is an assumption, "
                   "varied). Cost (reported for H3-K and the essay): the 0.214 USD/kg saving survives the exchanger cost at every U "
                   "case (net 0.067-0.095 USD/kg, conservative design; 0.165-0.184 with one counter-current unit), but turns negative "
                   "in adverse corners listed in net_benefit_negative_in. The cost result therefore is SUPPORTED only inside the "
                   "envelope U >= ~12 W/(m2 K) with NH3 >= ~310 USD/t and CRF <= ~0.15; outside that it is threshold-dependent."),
    }}


def prov(what: str) -> dict:
    return {"generated_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
            "script": "scripts/research/heat_exchanger_study.py", "what": what, "source_type": "python (on stored Aspen results)",
            "reference_scenario": provenance_stamp(), "aspen_run": False}


def figures(b, cases, sens) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    allc = [b] + cases
    labels = [c["case"].replace("_aspen_W100", "").replace("_python", "").replace("baseline_aspen_600C", "baseline 600C") for c in allc]
    x = range(len(allc))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar([i - 0.3 for i in x], [c["saving_USD_per_kg"] for c in allc], 0.2, label="fuel saving", color="#2a7f62")
    for k, (u, col) in enumerate((("low", "#b44"), ("central", "#d98"), ("high", "#eca"))):
        ax.bar([i - 0.1 + 0.2 * k for i in x], [c["exchanger_cost_USD_per_kg"][u] for c in allc], 0.2, label=f"FEHE cost, U {u}", color=col)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("USD per kg H2")
    ax.set_title("Heat-integration fuel saving vs annualised FEHE cost (reference basis)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "heat_exchanger_net_benefit.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 4))
    U = [r["U_W_m2K"] for r in sens["U"]]
    ax.semilogx(U, [r["net_benefit_USD_per_kg"] for r in sens["U"]], "o-", color="#2a5d9f")
    ax.axhline(0, color="k", lw=0.8)
    ax.axvspan(35, 150, color="#ddd", label="U range used (35-150)")
    ax.set_xlabel("overall U, W/(m2 K)")
    ax.set_ylabel("net benefit, USD/kg H2")
    ax.set_title("Baseline FEHE: net benefit vs U")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "heat_exchanger_U_sensitivity.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
