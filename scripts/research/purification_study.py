"""Workstream P: hydrogen purification study (PSA, Pd-alloy membrane, hybrids) on stored AmCraX cracked gas.

Run:  python scripts/research/purification_study.py
Inputs (read only): results/simulations/baseline.json (Aspen Plus V15, stream S7 after the cooler, 20 bar),
results/sensitivity/aspen_pressure.csv (Aspen Plus V15 KPI rows at 10 and 30 bar; composition rebuilt from KPIs),
Phase 2: every cost input (CAPEX by item, fixed-opex factors, electricity, hours, discount rate, life, NH3
price, FX) comes from the unified reference scenario (backend/amcrax/data/reference_scenario.yaml) through
amcrax.economics.singapore.evaluate on the stored Aspen baseline. The legacy results/simulations/
economics_baseline.json basis (LCOH 3.92) is no longer used.
Outputs: results/research/purification/*.json|csv, results/figures/research/purification_*.png,
results/research/validation/purification.json, research/reference_additions/purification.json.
Deterministic. Every number is labelled aspen / python / literature / assumption.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from amcrax.plotstyle import C_GREY, C_H2, C_HEAT, C_N2, C_NH3, C_PRIMARY, C_AMBER, add_provenance, apply_style, plt  # noqa: E402
from amcrax.schemas import MOLAR_MASS  # noqa: E402
from amcrax.economics.reference import load_reference_scenario, provenance_stamp, reference_item_costs  # noqa: E402
from amcrax.economics.singapore import evaluate as sg_evaluate, extract_summary  # noqa: E402
from amcrax.separation import params  # noqa: E402
from amcrax.separation.compression import compression_power_kW  # noqa: E402
from amcrax.separation.membrane import permeance, sieverts_flux  # noqa: E402
from amcrax.separation.purification import (GRADES, ISO_SOURCE, PSA_LABEL, closure, evaluate_product,  # noqa: E402
                                            gas_compression_kWh_per_kg_h2, h2_compression_kWh_per_kg, lhv_kW,
                                            mass_kg_h, membrane_area_for_recovery, membrane_with_leakage,
                                            pinch_recovery, psa_recovery_at_purity, psa_split,
                                            psa_tail_h2_fraction_from_point, required_selectivity)

OUT = ROOT / "results" / "research" / "purification"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
REFS = ROOT / "research" / "reference_additions"
for d in (OUT, FIG, VAL, REFS):
    d.mkdir(parents=True, exist_ok=True)

NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SCRIPT = "scripts/research/purification_study.py"
_REF = load_reference_scenario()   # Phase 2 unified reference scenario
HOURS = _REF.operating_hours_h_per_yr
DELIVERY = {"industrial_99.9": 30.0, "fuel_cell_grade_D": 350.0, "turbine_blend": 30.0}
DELIVERY_SRC = ("30 bar: richard2024technoeconomic p. 4 (H2 supplied to the gas turbine at 30 bar); "
                "350 bar: chopra2026decentralized p. 4 / economics.yaml chopra2026_point (compression to 350 bar). "
                "The ideal-gas compression model is approximate at 350 bar (real-gas H2 Z about 1.2): treat as +-15 %.")
T_PSA_K = 313.15  # aspen: PSA feed temperature, cooler outlet 40 degC
MEM_T_K = 400.0 + 273.15  # assumption (default in separation.yaml, inside 350-500 degC Pd window)
EURUSD_PARITY = _REF.usd_per_eur  # USD per EUR, ECB 20 Nov 2026 (reference scenario; was parity 1.0 in Phase 1)
MEM_EUR_PER_M2 = 6000.0  # literature: richard2024technoeconomic p. 9 Table 5 (Pd membrane 6000 EUR/m2, 3 y life)
MEM_LIFE_Y = 3.0


def prov(source_type: str, inputs: str) -> dict:
    return {"generated_utc": NOW, "script": SCRIPT, "source_type": source_type, "inputs_summary": inputs,
            "reference_scenario": provenance_stamp(),
            "model_versions": {"separation": "amcrax.separation.purification (reduced-order)",
                               "aspen_inputs": "Aspen Plus V15 stored results"}}


# ------------------------------------------------------------------------------------------ inputs
def load_cases() -> dict[str, dict]:
    base = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))
    s7 = base["streams"]["S7"]
    cases = {"20bar_baseline": {
        "feed": {k: v for k, v in s7["component_mole_flow_kmol_h"].items() if v},
        "P_bar": s7["pressure_bar"] + 0.0, "reactor_P_bar": 20.0, "source_type": "aspen",
        "origin": "results/simulations/baseline.json stream S7 (COOLER outlet, PSA feed)",
        "furnace_demand_kW": base["kpis"]["total_external_heating_kW"],
        "tail_heat_ratio": base["kpis"]["tailgas_combustion_heat_kW"] / base["kpis"]["tailgas_lhv_kW"]}}
    rows = {float(r["reactor_pressure_bar"]): r for r in csv.DictReader(
        open(ROOT / "results/sensitivity/aspen_pressure.csv", encoding="utf-8"))}
    for p, lab in ((10.0, "10bar"), (30.0, "30bar")):
        r = rows[p]
        h2 = float(r["h2_in_cracked_gas_kmol_h"])
        tot = h2 / float(r["y_H2_cracked"])
        nh3, n2 = float(r["y_NH3_cracked"]) * tot, float(r["y_N2_cracked"]) * tot
        h2o = tot - h2 - nh3 - n2
        cases[lab] = {"feed": {"NH3": nh3, "H2": h2, "N2": n2, "H2O": h2o}, "P_bar": p - 0.5, "reactor_P_bar": p,
                      "source_type": "aspen",
                      "origin": f"results/sensitivity/aspen_pressure.csv {r['case_id']} (composition rebuilt from KPI "
                                "mole fractions; H2O by difference; stream pressure = reactor pressure - 0.5 bar as in the "
                                "20 bar case S7: 19.5 bar)",
                      "furnace_demand_kW": float(r["total_external_heating_kW"]),
                      "tail_heat_ratio": float(r["tailgas_combustion_heat_kW"]) / float(r["tailgas_lhv_kW"])}
    return cases


_BASE_RES = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))
ECON = sg_evaluate(_BASE_RES, _REF.default_nh3_scenario)   # reference-scenario baseline (same as reference_scenario/baseline.json)
_FD = ECON["fixed_opex_detail_USD_per_yr"]
AC = dict(ECON["annual_USD_per_yr"])
AC["imported_heat"] = AC["heat_fuel"]
AC["fixed_opex.labour"], AC["fixed_opex.plant_overhead"], AC["fixed_opex.g_and_a"] = _FD["labour"], _FD["plant_overhead"], _FD["g_and_a"]
EQ = ECON["capex"]["tci_by_equipment_USD"]   # reference CAPEX by item (cho2026_itemised_v1), indirects allocated
CRF = ECON["crf"]
BASE_DEFICIT_KW = extract_summary(_BASE_RES)["heat_deficit_kW"]
HEAT_USD_PER_KW_YR = AC["imported_heat"] / BASE_DEFICIT_KW  # NH3-fuel heat price of the reference baseline
PRICE_ELEC = _REF.electricity_USD_per_kWh
NH3_PRICE = ECON["nh3_price_USD_per_t"]
UPSTREAM_CAPEX = sum(v for k, v in EQ.items() if k not in ("psa", "adsorber"))
PSA_CAPEX = EQ["psa"]  # reference CAPEX item (Cho T/PSA split 26:4 into PSA and adsorber)
ADS_CAPEX = EQ["adsorber"]
FIXED_NONCAPEX = AC["fixed_opex.labour"] + AC["fixed_opex.plant_overhead"] + AC["fixed_opex.g_and_a"]
MAINT_INS = _REF.maintenance_frac_capex_per_yr + _REF.insurance_frac_capex_per_yr
# Phase 2: the pump electricity of the cracker (omitted in Phase 1) is now part of the upstream cost, so the
# PSA_AMCRAX configuration reproduces the reference baseline plus its NAMED extra items (compression, heat change).
UPSTREAM_ANNUAL_BASE = (AC["ammonia_feed"] + AC["catalyst"] + AC["cooling_water"] + AC["electricity"] + FIXED_NONCAPEX
                        + UPSTREAM_CAPEX * (CRF + MAINT_INS))
# Cho 2026 T/PSA unit CAPEX 0.084 USD/kg H2 at 82 kg/h (alternative basis: own exponent, H2-capacity scaling)
CHO_TPSA_USD_PER_KG = reference_item_costs()["unit_USD_per_kg_h2"]["psa"] + reference_item_costs()["unit_USD_per_kg_h2"]["adsorber"]
CHO_REF_KG_H = 630.0 / 7.639  # 630 kg NH3/h at 7.639 kg NH3/kg H2 (Ru-10 bar) -> about 82.5 kg/h H2
PSA_SCALE_EXP = 0.6  # assumption (six-tenths rule), only used for the Cho alternative


# ------------------------------------------------------------------------------------------ configurations
def ppm_of(flows: dict[str, float], sp: str, dry: bool = False) -> float:
    tot = sum(v for k, v in flows.items() if not (dry and k == "H2O"))
    return 1e6 * flows.get(sp, 0.0) / tot if tot > 0 else 0.0


def finalise(cfg: dict, feed: dict, case: dict, grade_checks: dict[str, str]) -> dict:
    """Add closure, energy, heat to furnace, spec evaluation to a config dict with product/tail flows."""
    outs = [cfg["product_kmol_h"], cfg["tail_kmol_h"]]
    cfg["closure"] = closure(feed, outs)
    h2_kg = cfg["product_kmol_h"]["H2"] * MOLAR_MASS["H2"]
    cfg["product_h2_kg_h"] = h2_kg
    cfg["h2_recovery"] = cfg["product_kmol_h"]["H2"] / feed["H2"]
    cfg["product_purity_h2_mole_frac"] = cfg["product_kmol_h"]["H2"] / sum(cfg["product_kmol_h"].values())
    cfg["tail_lhv_kW"] = lhv_kW(cfg["tail_kmol_h"])
    cfg["tail_heat_to_furnace_kW"] = cfg["tail_lhv_kW"] * case["tail_heat_ratio"]
    cfg["tail_h2_loss_lhv_kW"] = cfg["tail_kmol_h"].get("H2", 0.0) * 241.826 / 3.6
    cfg["furnace_demand_kW"] = case["furnace_demand_kW"]
    cfg["net_heat_deficit_kW"] = max(case["furnace_demand_kW"] - cfg["tail_heat_to_furnace_kW"], 0.0)
    cfg["surplus_heat_kW_not_credited"] = max(cfg["tail_heat_to_furnace_kW"] - case["furnace_demand_kW"], 0.0)
    prod = cfg["product_kmol_h"]
    y = {sp: ppm_of(prod, sp) for sp in ("NH3", "N2", "H2O")}
    cfg["product_ppm"] = y
    cfg["spec_evaluation"] = {}
    for g in ("D", "B", "E3"):
        ev = evaluate_product(y, g, nh3_basis=cfg["nh3_basis"])
        ev["note"] = grade_checks.get(g, "")
        cfg["spec_evaluation"][g] = ev
    return cfg


def cfg_raw(feed, case):
    cfg = {"id": "RAW", "label": "No purification (cooled cracked gas)", "kind": "none", "source_type": "aspen",
           "product_kmol_h": dict(feed), "tail_kmol_h": {k: 0.0 for k in feed}, "nh3_basis": "computed (no removal)",
           "area_m2": 0.0, "compression_feed_kWh_per_kg": 0.0, "model_status": "stream as simulated"}
    return finalise(cfg, feed, case, {})


def cfg_psa(feed, case, cid, label, recovery, purity, rec_source):
    prod, tail = psa_split(feed, recovery, purity)
    # TSA: NH3 and water removed upstream. NH3 left in product = TSA design limit (source outlet < 0.1 ppm): the
    # product is modelled AT 0.1 ppm (limit value, not computed). Water assumed removed with it (zeolite 4A, assumption).
    h2n2 = prod["H2"] + prod["N2"]
    prod = dict(prod)
    prod["NH3"] = 0.1e-6 * h2n2
    tail = {k: v - prod.get(k, 0.0) for k, v in feed.items()}
    cfg = {"id": cid, "label": label, "kind": "psa", "source_type": "python", "product_kmol_h": prod,
           "tail_kmol_h": tail, "nh3_basis": "design target of upstream TSA (cho2026nickel p. 6 Table 3: outlet < 0.1 ppm), "
           "modelled at the limit, not computed", "recovery_source": rec_source, "area_m2": 0.0,
           "feed_pressure_ok": case["P_bar"] >= 7.0,
           "model_status": PSA_LABEL, "tsa_regeneration_energy": "not modelled (no separate TSA value in the library)"}
    return finalise(cfg, feed, case, {"D": "water assumed removed with NH3 in the TSA (zeolite 4A), not computed",
                                      "B": "", "E3": ""})


def cfg_membrane(feed, case, cid, label, R, P_perm, alpha, nh3_ppm_perm, nh3_basis, polish: bool, flux_mult=1.0,
                 permeability=None, compute_req=False):
    P = case["P_bar"]
    A = membrane_area_for_recovery(feed, R, P, P_perm, MEM_T_K, alpha_H2_N2=alpha, flux_multiplier=flux_mult,
                                   permeability=permeability)
    if A is None:
        return None
    m = membrane_with_leakage(feed, A, P, P_perm, MEM_T_K, alpha_H2_N2=alpha, flux_multiplier=flux_mult,
                              permeability=permeability)
    prod = {"H2": m["permeate_kmol_h"]["H2"], "N2": m["permeate_kmol_h"]["N2"]}
    prod["NH3"] = nh3_ppm_perm * 1e-6 * (prod["H2"] + prod["N2"])
    ret = dict(m["retentate_kmol_h"])
    tail = {k: ret.get(k, 0.0) - prod.get(k, 0.0) if k == "NH3" else ret.get(k, 0.0) for k in feed}
    cfg = {"id": cid, "label": label, "kind": "membrane", "source_type": "python", "product_kmol_h": prod,
           "tail_kmol_h": tail, "nh3_basis": nh3_basis, "area_m2": A, "permeate_pressure_bar": P_perm,
           "alpha_H2_N2": alpha, "nh3_polishing_adsorber": polish, "flux_multiplier": flux_mult,
           "pinch_recovery_limit": pinch_recovery(feed, P, P_perm), "membrane_T_K": MEM_T_K,
           "n2_in_permeate_ppm": m["n2_in_permeate_ppm"], "model_status":
           "Sieverts (n = 0.5) integrated along the module with H2 depletion; isothermal, isobaric; no NH3 inhibition "
           "modelled (not supported quantitatively by the library); membrane placed on the hot effluent (before the "
           "cooler), heat integration effect on FEHE/cooler not modelled",
           "pd_window_ok": 350 <= MEM_T_K - 273.15 <= 500}
    # NH3 passing the membrane is removed from the retentate stream bookkeeping above (cfg tail NH3 = feed - prod)
    cfg["tail_kmol_h"]["NH3"] = feed.get("NH3", 0.0) - prod["NH3"]
    cfg["tail_kmol_h"]["N2"] = feed.get("N2", 0.0) - prod["N2"]
    cfg["tail_kmol_h"]["H2"] = feed["H2"] - prod["H2"]
    cond = ""
    if compute_req:
        a300 = required_selectivity(feed, A, P, P_perm, MEM_T_K, 300.0, flux_multiplier=flux_mult, permeability=permeability)
        a1000 = required_selectivity(feed, A, P, P_perm, MEM_T_K, 1000.0, flux_multiplier=flux_mult, permeability=permeability)
        cfg["required_alpha_H2_N2_for_N2_300ppm"] = a300
        cfg["required_alpha_H2_N2_for_N2_1000ppm"] = a1000
        cond = (f"CONDITIONAL on ideal H2/N2 selectivity >= {a300:.0f} (N2 300 ppm); the base model assumes infinite "
                "selectivity. Sourced value (Phase 2): Cechetto et al. 2021 state ideal H2/N2 above 400,000 (double "
                "sealed) and above 500,000 (dead end) at 450 degC; the printed double-sealed N2 permeance (3.7e-11) "
                "gives only about 40,500, so the sourced range is 40,500 to 500,000. Caveats: ideal (single gas), new "
                "membrane, one group, 450 degC, trace NH3 only; mixed-gas and aged values not found")
    cfg["n2_conditional_note"] = cond
    return finalise(cfg, feed, case, {"D": "water: Pd permeate carries no water in this model; NH3 basis as stated. " + cond,
                                      "B": cond})


# ------------------------------------------------------------------------------------------ cost
def compression_to(cfg, case, P_del):
    """kWh per kg H2 to bring the product to P_del. Product available pressure: PSA at feed pressure, membrane
    at permeate pressure, RAW at stream pressure (whole gas compressed)."""
    prod = cfg["product_kmol_h"]
    kg = cfg["product_h2_kg_h"]
    if cfg["kind"] == "membrane":
        P_in = cfg["permeate_pressure_bar"]
    else:
        P_in = case["P_bar"]
    flows = {k: v for k, v in prod.items() if v > 0}
    return gas_compression_kWh_per_kg_h2(flows, T_PSA_K, P_in, P_del, kg) if P_del > P_in else 0.0


def purification_cost(cfg, case, P_del, *, elec=PRICE_ELEC, psa_capex_mult=1.0, mem_cost_mult=1.0,
                      nh3_price=NH3_PRICE, psa_capex_basis="amcrax_split", mem_life=MEM_LIFE_Y, heat_price_mult=1.0):
    kg_h = cfg["product_h2_kg_h"]
    ckwh = compression_to(cfg, case, P_del)
    elec_usd_yr = ckwh * kg_h * HOURS * elec
    capex = 0.0
    if cfg["kind"] == "psa":
        if psa_capex_basis == "amcrax_split":
            capex = (PSA_CAPEX + ADS_CAPEX) * psa_capex_mult
        else:  # Cho T/PSA unit CAPEX scaled with capacity (assumption exponent), annualised value -> capex-equivalent
            ann = CHO_TPSA_USD_PER_KG * kg_h * HOURS * (kg_h / CHO_REF_KG_H) ** (PSA_SCALE_EXP - 1.0)
            capex = ann / CRF * psa_capex_mult
    elif cfg["kind"] == "membrane" and cfg.get("nh3_polishing_adsorber"):
        capex = ADS_CAPEX * psa_capex_mult  # proxy: adsorber share of the existing split (assumption)
    capex_yr = capex * (CRF + MAINT_INS)
    mem_yr = cfg["area_m2"] * MEM_EUR_PER_M2 * EURUSD_PARITY * mem_cost_mult / mem_life
    heat_yr = cfg["net_heat_deficit_kW"] * HEAT_USD_PER_KW_YR * heat_price_mult
    ann_feed = AC["ammonia_feed"] * nh3_price / NH3_PRICE
    upstream = UPSTREAM_ANNUAL_BASE - AC["ammonia_feed"] + ann_feed
    total = upstream + heat_yr + capex_yr + mem_yr + elec_usd_yr
    purif = capex_yr + mem_yr + elec_usd_yr
    kg_yr = kg_h * HOURS
    fx = _REF.fx_SGD_per_USD
    return {"delivery_pressure_bar": P_del, "compression_kWh_per_kg_h2": ckwh, "usd_per_kg_product_h2": total / kg_yr,
            "sgd_per_kg_product_h2": total / kg_yr * fx, "annual_total_USD": total,
            "annual_named_items_USD": {"compression_electricity": elec_usd_yr, "imported_heat": heat_yr,
                                       "purification_capex_and_maintenance": capex_yr, "membrane_replacement": mem_yr},
            "components_usd_per_kg": {"upstream_nh3_cracker_fixed": upstream / kg_yr, "imported_heat": heat_yr / kg_yr,
                                      "purification_capex_and_maintenance": capex_yr / kg_yr,
                                      "membrane_replacement": mem_yr / kg_yr, "compression_electricity": elec_usd_yr / kg_yr},
            "purification_only_usd_per_kg": purif / kg_yr}


def usable_cost(cfg, case, end_use, **kw):
    """Cost per kg of usable H2 for an end use; None if the product does not meet the specification."""
    grade = {"industrial_99.9": "B", "fuel_cell_grade_D": "D", "turbine_blend": None}[end_use]
    ok = True if grade is None else cfg["spec_evaluation"][grade]["meets_within_model_scope"]
    c = purification_cost(cfg, case, DELIVERY[end_use], **kw)
    c["meets_spec_within_model_scope"] = ok
    c["usd_per_kg_usable_h2"] = c["usd_per_kg_product_h2"] if ok else None
    c["sgd_per_kg_usable_h2"] = c["sgd_per_kg_product_h2"] if ok else None
    c["conditional_on"] = cfg.get("n2_conditional_note", "") if ok and grade else ""
    return c


def build_configs(case):
    feed = case["feed"]
    P = params()["psa"]["operating_points"]
    cho = next(p for p in P if p["id"] == "cho2026_5A")
    han = next(p for p in P if p["id"] == "hansen2024_cha_AC")
    yt = psa_tail_h2_fraction_from_point(feed, cho["recovery"], cho["purity"])
    cfgs = []
    cfgs.append(cfg_raw(feed, case))
    cfgs.append(cfg_psa(feed, case, "PSA_CHO", "TSA + PSA, published point (R 0.756 at 99.11 %, Cho 2026)", cho["recovery"],
                        cho["purity"], "cho2026nickel p. 6 Table 3 (literature)"))
    for tag, pur in (("B", 0.9991), ("D", 0.99975)):  # 99.91 %: margin so NH3 at 0.1 ppm keeps total < 1000 ppm
        R_mb = psa_recovery_at_purity(feed, pur, yt)
        cfgs.append(cfg_psa(feed, case, f"PSA_{tag}_MB", f"TSA + PSA at {pur*100:.3f} %, recovery from mass-balance relation "
                            f"(tail H2 fraction {yt:.3f} held from Cho point; optimistic)", R_mb, pur,
                            "assumption: tail-gas H2 fraction held at the Cho-implied value (lower bound on penalty)"))
        cfgs.append(cfg_psa(feed, case, f"PSA_{tag}_LOW", f"TSA + PSA at {pur*100:.3f} %, recovery 0.71 (lowest published "
                            f"point, Hansen/Cha 2021)", han["recovery"], pur,
                            "literature recovery at 99 % purity (hansen2024hysys p. 2) applied at higher purity: assumption"))
    cfgs.append(cfg_psa(feed, case, "PSA_AMCRAX", "AmCraX baseline splitter (R 0.85, N2 slip 0.001; Aspen assumption F4)", 0.85,
                        0.9996, "assumption (fact sheet F4); purity 0.9996 as simulated"))
    alpha_inf = math.inf
    for Pp, tagp in ((1.0, "1bar"), (0.1, "vac0.1bar")):
        for pol, tagq in ((False, "raw"), (True, "polish")):
            nh3_ppm = 0.025 if pol else 2.9
            basis = ("Pd-Ag permeate NH3 from experiment: 2.9 ppm (cechetto2023membrane p. 17 Table 10, Cechetto 2021, FTIR)"
                     if not pol else "after clinoptilolite polishing bed, < 0.025 ppm (cechetto2023membrane p. 14; "
                     "Sitar 2022), modelled at the quoted bound")
            c = cfg_membrane(feed, case, f"MEM_{tagp}_{tagq}", f"Pd-Ag membrane R 0.90, permeate {Pp:g} bar"
                             f"{' + NH3 polishing bed' if pol else ''}", 0.90, Pp, alpha_inf, nh3_ppm, basis, pol,
                             compute_req=True)
            if c:
                cfgs.append(c)
    return cfgs, yt


# ------------------------------------------------------------------------------------------ main study
def main():
    apply_style()
    cases = load_cases()
    results = {"provenance": prov("python", "stored Aspen Plus V15 cracked gas; reduced-order purification models; "
                                  "Phase 2 unified reference scenario (data/reference_scenario.yaml) for every cost input"),
               "delivery_pressures_bar": DELIVERY, "delivery_pressure_source": DELIVERY_SRC,
               "iso_14687": {"source": ISO_SOURCE, "grades": GRADES}, "cases": {}}
    assumptions = []

    def A(name, value, unit, st, source, note):
        assumptions.append({"name": name, "value": value, "unit": unit, "source_type": st, "source": source,
                            "applicability_note": note})

    for cid, case in cases.items():
        cfgs, yt = build_configs(case)
        entry = {"origin": case["origin"], "source_type": case["source_type"], "feed_kmol_h": case["feed"],
                 "stream_pressure_bar": case["P_bar"], "reactor_pressure_bar": case["reactor_P_bar"],
                 "furnace_demand_kW": case["furnace_demand_kW"], "psa_tail_h2_fraction_cho_anchor": yt, "configs": []}
        for cfg in cfgs:
            cfg["costs"] = {eu: usable_cost(cfg, case, eu) for eu in DELIVERY}
            cfg["costs_cho_tpsa_capex"] = {eu: usable_cost(cfg, case, eu, psa_capex_basis="cho") for eu in DELIVERY} \
                if cfg["kind"] == "psa" else None
            entry["configs"].append(cfg)
        results["cases"][cid] = entry
    summ = {}
    for cid, e in results["cases"].items():
        summ[cid] = {}
        for eu in DELIVERY:
            ok = [(c["costs"][eu]["usd_per_kg_usable_h2"], c["id"], c["costs"][eu]["conditional_on"])
                  for c in e["configs"] if c["costs"][eu]["usd_per_kg_usable_h2"] is not None]
            ok.sort()
            summ[cid][eu] = {"ranking_usd_per_kg_usable_h2": [{"config": i, "usd_per_kg": v, "conditional_on": cnd}
                                                              for v, i, cnd in ok]}
    results["summary"] = summ
    results["not_modelled"] = [
        "TSA regeneration heat and electricity", "compression CAPEX", "membrane housing, skid and heating CAPEX",
        "pressure drop in beds and modules", "NH3 inhibition of Pd permeation (not supported quantitatively by the library)",
        "real-gas behaviour at 350 bar", "contaminants other than NH3, N2, H2O (O2, Ar, He, CO, CO2, hydrocarbons, S, "
        "halogens, HCHO, HCOOH, particulates) are listed as not evaluated", "heat integration effect of placing the membrane on the hot effluent"]
    json.dump(_clean(results), open(OUT / "purification_study.json", "w", encoding="utf-8"), indent=1)

    base = results["cases"]["20bar_baseline"]
    case20 = cases["20bar_baseline"]
    # ---- configuration table CSV
    rows = []
    for cid, e in results["cases"].items():
        for c in e["configs"]:
            for eu in DELIVERY:
                k = c["costs"][eu]
                rows.append({"case": cid, "config": c["id"], "end_use": eu, "h2_recovery": c["h2_recovery"],
                             "purity_h2": c["product_purity_h2_mole_frac"], "N2_ppm": c["product_ppm"]["N2"],
                             "NH3_ppm": c["product_ppm"]["NH3"], "H2O_ppm": c["product_ppm"]["H2O"],
                             "meets_gradeD_in_scope": c["spec_evaluation"]["D"]["meets_within_model_scope"],
                             "meets_gradeB_in_scope": c["spec_evaluation"]["B"]["meets_within_model_scope"],
                             "membrane_area_m2": c["area_m2"], "compression_kWh_per_kg": k["compression_kWh_per_kg_h2"],
                             "tail_heat_to_furnace_kW": c["tail_heat_to_furnace_kW"],
                             "net_heat_deficit_kW": c["net_heat_deficit_kW"],
                             "usd_per_kg_product_h2": k["usd_per_kg_product_h2"],
                             "usd_per_kg_usable_h2": k["usd_per_kg_usable_h2"],
                             "meets_enduse_spec": k["meets_spec_within_model_scope"],
                             "mass_closure_rel": c["closure"]["mass_rel_error"],
                             "max_component_closure_rel": c["closure"]["max_abs_rel_error"]})
    _csv(OUT / "purification_configurations.csv", rows)

    # ---- trade-off: PSA recovery vs purity (published points + relation) and membrane R vs purity/area/cost
    feed20 = case20["feed"]
    yt20 = base["psa_tail_h2_fraction_cho_anchor"]
    pur_grid = np.linspace(0.985, 0.99999, 60)
    psa_curve = [{"purity": float(p), "recovery_mass_balance_relation": psa_recovery_at_purity(feed20, float(p), yt20)}
                 for p in pur_grid]
    # sensitivity of the relation to the tail H2 fraction (anchor +- published spread)
    han = next(p for p in params()["psa"]["operating_points"] if p["id"] == "hansen2024_cha_AC")
    yt_han = psa_tail_h2_fraction_from_point(feed20, han["recovery"], han["purity"])
    for r in psa_curve:
        r["recovery_hansen_anchor"] = psa_recovery_at_purity(feed20, r["purity"], yt_han)
    _csv(OUT / "psa_recovery_vs_purity.csv", psa_curve)
    published = [{"id": "cho2026_5A", "recovery": 0.756, "purity": 0.9911, "adsorbent": "zeolite 5A, 7 bar", "reliability": "used"},
                 {"id": "hansen2024_cha_AC", "recovery": 0.71, "purity": 0.99, "adsorbent": "activated carbon, 2.5 bar", "reliability": "used"},
                 {"id": "mehr2026_table6", "recovery": 0.81, "purity": 0.9996, "adsorbent": "n/s", "reliability": "low (internally inconsistent)"},
                 {"id": "mehr2026_validation", "recovery": 0.25, "purity": 0.9981, "adsorbent": "n/s", "reliability": "low (internally inconsistent)"}]
    # membrane R vs area, cost (20 bar)
    mem_rows = []
    for Pp in (1.0, 0.1):
        rmax = pinch_recovery(feed20, case20["P_bar"], Pp)
        for R in np.linspace(0.3, 0.97, 28):
            if R >= rmax:
                continue
            Aa = membrane_area_for_recovery(feed20, float(R), case20["P_bar"], Pp, MEM_T_K)
            m = membrane_with_leakage(feed20, Aa, case20["P_bar"], Pp, MEM_T_K)
            kg = m["permeate_kmol_h"]["H2"] * MOLAR_MASS["H2"]
            ckwh = gas_compression_kWh_per_kg_h2({"H2": 1.0}, T_PSA_K, Pp, 30.0, 1.0)
            # cost of lost hydrogen: upstream cost per kg of H2 in cracked gas
            up = (UPSTREAM_ANNUAL_BASE) / (feed20["H2"] * MOLAR_MASS["H2"] * HOURS)
            mem_cost = Aa * MEM_EUR_PER_M2 * EURUSD_PARITY / MEM_LIFE_Y / (kg * HOURS)
            mem_rows.append({"permeate_bar": Pp, "recovery": float(R), "area_m2": Aa, "pinch_limit": rmax,
                             "membrane_usd_per_kg_h2": mem_cost, "compression_to_30bar_kWh_per_kg": ckwh,
                             "compression_usd_per_kg": ckwh * PRICE_ELEC,
                             "upstream_usd_per_kg_product": up / R * 1.0 if R > 0 else None})
    _csv(OUT / "membrane_recovery_area_cost.csv", mem_rows)
    # recovery vs total cost (fuel cell grade D at 350 bar) for PSA recovery scan and membrane scan
    rc_rows = []
    for R in np.linspace(0.60, 0.90, 13):
        cfg = cfg_psa(feed20, case20, "PSA_scan", "scan", float(R), 0.99975, "scan")
        k = purification_cost(cfg, case20, 350.0)
        rc_rows.append({"config": "PSA+TSA grade D purity 99.975 %", "recovery": float(R), "usd_per_kg": k["usd_per_kg_product_h2"]})
    for Pp in (1.0, 0.1):
        for R in np.linspace(0.40, 0.97, 20):
            cfg = cfg_membrane(feed20, case20, "MEM_scan", "scan", float(R), Pp, math.inf, 0.025, "scan", True)
            if cfg is None:
                continue
            k = purification_cost(cfg, case20, 350.0)
            rc_rows.append({"config": f"Pd-Ag + polish, permeate {Pp:g} bar", "recovery": float(R),
                            "usd_per_kg": k["usd_per_kg_product_h2"]})
    _csv(OUT / "recovery_vs_cost.csv", rc_rows)

    # ---- membrane details: required selectivity, sensitivity to permeance
    sel_rows = []
    for Pp in (1.0, 0.1):
        for R in (0.80, 0.90, 0.95):
            Aa = membrane_area_for_recovery(feed20, R, case20["P_bar"], Pp, MEM_T_K)
            if Aa is None:
                continue
            for lim, name in ((300.0, "grade D N2 300 ppm"), (1000.0, "grade B/E3 total 1000 ppm")):
                a = required_selectivity(feed20, Aa, case20["P_bar"], Pp, MEM_T_K, lim)
                sel_rows.append({"permeate_bar": Pp, "recovery": R, "area_m2": Aa, "limit": name, "limit_ppm": lim,
                                 "required_alpha_H2_N2": a})
    _csv(OUT / "membrane_required_selectivity.csv", sel_rows)

    # ---- sensitivity (fuel cell grade D at 350 bar, 20 bar case)
    sens = sensitivity(case20)
    json.dump(_clean({"provenance": prov("python", "one-at-a-time sensitivities on the 20 bar baseline; cost per kg usable H2 "
                                         "for grade D at 350 bar"), "rows": sens}),
              open(OUT / "sensitivity.json", "w", encoding="utf-8"), indent=1)
    _csv(OUT / "sensitivity.csv", sens)

    # ---- Singapore price scenario (prices read from results/research/singapore/assumptions.json)
    sg = {a["name"]: a for a in json.load(open(ROOT / "results/research/singapore/assumptions.json", encoding="utf-8"))}
    sg_elec = float(sg["electricity_price"]["value"])
    sg_rows = []
    for nm in ("nh3_price_grey", "nh3_price_blue", "nh3_price_green_2030", "nh3_price_green_current"):
        for c in results["cases"]["20bar_baseline"]["configs"]:
            for eu in DELIVERY:
                k = usable_cost(c, case20, eu, elec=sg_elec, nh3_price=float(sg[nm]["value"]))
                sg_rows.append({"nh3_price_case": nm, "nh3_price_USD_per_t": float(sg[nm]["value"]),
                                "electricity_USD_per_kWh": sg_elec, "config": c["id"], "end_use": eu,
                                "usd_per_kg_usable_h2": k["usd_per_kg_usable_h2"]})
    _csv(OUT / "singapore_price_scenario.csv", sg_rows)
    json.dump(_clean({"provenance": prov("python", "prices from results/research/singapore/assumptions.json (electricity "
                      "derived, NH3 scenario prices, delivered international); other inputs unchanged"),
                      "electricity_source": sg["electricity_price"]["source"], "rows": sg_rows}),
              open(OUT / "singapore_price_scenario.json", "w", encoding="utf-8"), indent=1)

    # ---- hybrids (informational)
    hyb = hybrids(case20)
    json.dump(_clean({"provenance": prov("python", "hybrid screening on the 20 bar baseline"), **hyb}),
              open(OUT / "hybrids.json", "w", encoding="utf-8"), indent=1)

    # ---- assumptions register
    A("PSA recovery-purity relation", "constant tail-gas H2 fraction (Cho anchor)", "-", "assumption",
      "mass balance on cho2026nickel p. 6 Table 3 point",
      "gives a lower bound on the purity penalty; the real slope is not in the library")
    A("PSA recovery at 99.975 % purity (low case)", 0.71, "-", "literature",
      "hansen2024hysys p. 2 (Cha 2021, 99 % purity, activated carbon, 2.5 bar)", "applied at higher purity: extrapolation")
    A("TSA outlet NH3", 0.1, "ppm", "literature", "cho2026nickel p. 6 Table 3 (< 0.1 ppm, zeolite 4A, 3 beds)",
      "modelled at the limit; compliance is a design target, not a computed result")
    A("TSA regeneration energy", "not modelled", "-", "assumption", "no separate TSA value in the library",
      "tail gas burns in the furnace; regeneration heat omitted, so PSA/TSA cost is a lower bound")
    A("Water removal to 5 ppm", "assumed with NH3 in TSA", "-", "assumption", "zeolite 4A adsorbs water; no number sourced",
      "grade D water limit is satisfied by assumption in PSA configurations")
    A("Pd-Ag permeability", "Pe0 4.57e-8 mol m-1 s-1 Pa-0.5, Ea 9.23 kJ/mol, 5.2 um", "-", "literature",
      "richard2024technoeconomic p. 7 Table 2 row [53] (fitted to Pd-Ag on ceramic support)",
      "Cechetto 2023 review gives no Sieverts parameters; primary sources cited there not obtained")
    A("Membrane temperature", 400, "degC", "assumption", "separation.yaml default, inside 350-500 degC Pd window",
      "equals Cechetto 2021 benchmark temperature")
    A("Ideal H2/N2 selectivity", "infinite (base) / required value computed", "-", "assumption",
      "richard2024technoeconomic p. 7 assumes infinite; Phase 2 sourced value: cechetto2021fpt Sec. 3.1 p. 4, ideal "
      "H2/N2 above 400,000 (double sealed) / above 500,000 (dead end) at 450 degC; about 40,500 from the printed "
      "double-sealed N2 permeance 3.7e-11 (internal inconsistency of the paper)",
      "required selectivity reported beside the sourced value; sourced value is ideal (single gas), new membrane, "
      "trace NH3 only; see results/research/purification/phase2_comparison.json")
    A("Membrane permeate NH3 without polishing", 2.9, "ppm", "literature", "cechetto2023membrane p. 17 Table 10",
      "single experiment (FTIR); other works 0.01-0.8 ppm; membrane alone cannot be taken to meet 0.1 ppm")
    A("Polishing bed outlet NH3", 0.025, "ppm", "literature", "cechetto2023membrane p. 14 (clinoptilolite, Sitar 2022)",
      "lab bed from about 1000 ppm; applied at the quoted bound")
    A("Membrane cost", MEM_EUR_PER_M2, "EUR/m2", "literature", "richard2024technoeconomic p. 9 Table 5 (3 y life)",
      f"converted at {EURUSD_PARITY} USD/EUR (ECB 20 Nov 2026, reference scenario); housing/skid CAPEX not modelled")
    A("PSA+TSA CAPEX (base)", PSA_CAPEX + ADS_CAPEX, "USD", "literature", "Phase 2 reference scenario: Cho 2026 T/PSA item "
      "(cho2026_itemised_v1) scaled with NH3 feed^0.8, OSBL/engineering/contingency allocated", "T/PSA split 26:4 (Chopra Fig. 5a)")
    A("PSA+TSA CAPEX (alternative)", CHO_TPSA_USD_PER_KG, "USD/kg H2 unit capex at 82 kg/h", "literature",
      "cho2026nickel p. 12 Fig. 7a (T/PSA 0.084)", f"scaled with exponent {PSA_SCALE_EXP} (assumption)")
    A("Electricity price", PRICE_ELEC, "USD/kWh", "derived", "reference scenario (USEP 2025 mean + network + fees, Singapore)",
      "Phase 2: replaces 0.084 (Cho 2026) used in Phase 1")
    A("Imported heat price", HEAT_USD_PER_KW_YR, "USD per kW-year", "python", "reference baseline heat_fuel / net heat "
      "deficit, NH3 fuel at the grey scenario price", "surplus heat not credited")
    A("Delivery pressures", DELIVERY, "bar", "literature", DELIVERY_SRC, "ideal-gas compression")
    A("Compressor efficiency / stages", "0.75, max ratio 3.5 per stage", "-", "literature", "cho2026nickel p. 5 Table 2",
      "compression CAPEX not modelled (electricity only)")
    A("Operating hours", HOURS, "h/yr", "literature", "reference scenario (cho2026nickel p. 7 Table 4)", "")
    A("FX", _REF.fx_SGD_per_USD, "SGD per USD", "derived", "reference scenario: ECB cross rate 20 Nov 2026", "SGD columns = USD x FX")
    json.dump(assumptions, open(OUT / "assumptions.json", "w", encoding="utf-8"), indent=1)

    figures(results, psa_curve, published, mem_rows, rc_rows, sens, case20, feed20)
    validation(results, cases, mem_rows, sel_rows)
    refs()
    print("done", NOW)


def sensitivity(case):
    feed = case["feed"]
    rows = []
    cho = next(p for p in params()["psa"]["operating_points"] if p["id"] == "cho2026_5A")
    yt = psa_tail_h2_fraction_from_point(feed, cho["recovery"], cho["purity"])

    def psaD(R):
        return cfg_psa(feed, case, "PSA_D", "", R, 0.99975, "")

    def memD(**kw):
        a = dict(R=0.90, P_perm=1.0, alpha=math.inf, nh3_ppm_perm=0.025, nh3_basis="", polish=True)
        a.update(kw)
        return cfg_membrane(feed, case, "MEM_D", "", a["R"], a["P_perm"], a["alpha"], a["nh3_ppm_perm"], a["nh3_basis"],
                            a["polish"], a.get("flux_mult", 1.0))

    def ev(cfg, **kw):
        k = purification_cost(cfg, case, 350.0, **kw)
        return k["usd_per_kg_product_h2"]

    p_base = psaD(psa_recovery_at_purity(feed, 0.99975, yt))
    m_base = memD()
    b = {"PSA_D": ev(p_base), "MEM_D": ev(m_base)}
    rows.append({"parameter": "base", "setting": "-", "PSA_D_usd_per_kg": b["PSA_D"], "MEM_D_usd_per_kg": b["MEM_D"]})

    def add(par, setting, ps, ms):
        rows.append({"parameter": par, "setting": setting, "PSA_D_usd_per_kg": ps, "MEM_D_usd_per_kg": ms})

    for R in (0.65, 0.71, 0.80):
        add("PSA recovery at 99.975 %", R, ev(psaD(R)), b["MEM_D"])
    for mlt in (0.5, 2.0):
        add("membrane cost multiplier", mlt, b["PSA_D"], ev(m_base, mem_cost_mult=mlt))
    for life in (1.0, 5.0):
        add("membrane life (y)", life, b["PSA_D"], ev(m_base, mem_life=life))
    mcp = memD(flux_mult=0.15)
    add("flux multiplier (concentration polarisation 0.15)", 0.15, b["PSA_D"], ev(mcp))
    for Pp in (0.1, 3.0):
        c = memD(P_perm=Pp)
        add("membrane permeate pressure (bar)", Pp, b["PSA_D"], ev(c) if c else None)
    for Rm in (0.80, 0.95):
        c = memD(R=Rm)
        add("membrane recovery", Rm, b["PSA_D"], ev(c) if c else None)
    for e in _REF.sens("electricity_USD_per_kWh"):
        add("electricity price (USD/kWh)", e, ev(p_base, elec=e), ev(m_base, elec=e))
    for pm in (0.5, 1.5):
        add("PSA/TSA CAPEX multiplier", pm, ev(p_base, psa_capex_mult=pm), ev(m_base, psa_capex_mult=pm))
    add("PSA/TSA CAPEX basis", "Cho T/PSA unit capex", ev(p_base, psa_capex_basis="cho"), b["MEM_D"])
    for pr in (300.0, 610.0):
        add("NH3 price (USD/t)", pr, ev(p_base, nh3_price=pr), ev(m_base, nh3_price=pr))
    return rows


def hybrids(case):
    feed = case["feed"]
    cho = next(p for p in params()["psa"]["operating_points"] if p["id"] == "cho2026_5A")
    psa = cfg_psa(feed, case, "PSA_CHO", "", cho["recovery"], cho["purity"], "")
    tail = psa["tail_kmol_h"]
    P_tail = 1.2  # cho2026nickel p. 6 Table 3, 'Assumed' desorption pressure
    out = {"hybrid_psa_tail_membrane": {
        "rationale": "PSA tail gas carries 24 % of the H2 (the largest loss); a Pd membrane on it could return H2. "
                     "No source in the library reports this scheme; informational screening only.",
        "tail_kmol_h": tail, "tail_pressure_bar": P_tail, "tail_pressure_source": "cho2026nickel p. 6 Table 3 (assumed there)",
        "rows": []}}
    h2t = tail["H2"]
    for Pp in (0.5, 0.1, 0.01):
        pin = pinch_recovery({"H2": h2t, **{k: v for k, v in tail.items() if k != "H2"}}, P_tail, Pp)
        out["hybrid_psa_tail_membrane"]["rows"].append({"permeate_bar": Pp, "pinch_recovery_of_tail_H2": pin,
                                                         "overall_h2_recovery_if_pinch_reached": cho["recovery"] +
                                                         (1 - cho["recovery"]) * pin})
    out["hybrid_psa_tail_membrane"]["conclusion"] = (
        "At the 1.2 bar tail pressure the H2 partial pressure is below the feed side of any practical vacuum permeate; "
        "even the pinch limit needs 0.1 bar vacuum and re-compression of the recovered H2 to the PSA feed pressure. "
        "Not recommended without a source; kept as informational.")
    out["hybrid_membrane_plus_psa_polish"] = {
        "rationale": "A Pd membrane with finite H2/N2 selectivity could be followed by a small PSA to remove leaked N2, "
                     "relaxing the selectivity requirement.",
        "status": "not quantified: no published PSA recovery for a ppm-level polishing duty in the library",
        "membrane_required_selectivity_instead": "see membrane_required_selectivity.csv"}
    out["hybrid_membrane_plus_nh3_polishing_bed"] = {
        "rationale": "Measured Pd-Ag permeate NH3 spans 0.01-2.9 ppm (cechetto2023membrane Table 10) so a polishing bed "
                     "is needed for 0.1 ppm; sourced (clinoptilolite, zeolite 13X). Included as configuration MEM_*_polish."}
    return out


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        if math.isinf(o):
            return "inf" if o > 0 else "-inf"
        if math.isnan(o):
            return None
    if isinstance(o, (np.floating,)):
        return _clean(float(o))
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def _csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


# ------------------------------------------------------------------------------------------ figures
def figures(results, psa_curve, published, mem_rows, rc_rows, sens, case, feed):
    foot = "python reduced-order models on Aspen Plus V15 cracked gas (20 bar baseline); costs: existing AmCraX defaults"
    # 1 recovery vs purity
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    x = [r["purity"] * 100 for r in psa_curve]
    ax.plot(x, [r["recovery_mass_balance_relation"] * 100 for r in psa_curve], color=C_PRIMARY,
            label="PSA mass-balance relation (Cho anchor, optimistic)")
    ax.plot(x, [r["recovery_hansen_anchor"] * 100 for r in psa_curve], color=C_AMBER, ls="--",
            label="PSA mass-balance relation (Hansen anchor)")
    for p in published:
        ok = p["reliability"] == "used"
        ax.scatter(p["purity"] * 100, p["recovery"] * 100, marker="o" if ok else "x", color=C_H2 if ok else C_GREY, zorder=5)
        ax.annotate(p["id"] + ("" if ok else " (low reliability)"), (p["purity"] * 100, p["recovery"] * 100),
                    textcoords="offset points", xytext=(5, 4), fontsize=7)
    ax.axvline(99.9, color=C_GREY, lw=0.7, ls=":")
    ax.axvline(99.97, color=C_NH3, lw=0.7, ls=":")
    ax.text(99.9, 31, "99.9 %", rotation=90, fontsize=7, va="bottom", ha="right")
    ax.text(99.97, 31, "Grade D", rotation=90, fontsize=7, va="bottom", ha="right")
    ax.set_xlim(98.5, 100.2)
    ax.set_ylim(20, 100)
    ax.text(98.55, 55, "Flat by construction: tail-gas H2 fraction held constant.\nThe real purity penalty of a PSA cycle is not in the\nlibrary, so recovery at 99.9-99.975 % is uncertain\n(low case 71 %; Mehr 2026 points are inconsistent).",
            fontsize=7, va="top")
    ax.set_xlabel("H2 product purity (mol %)")
    ax.set_ylabel("H2 recovery (%)")
    ax.set_title("PSA recovery vs purity: published points and mass-balance relation")
    ax.legend(fontsize=7, loc="lower left")
    add_provenance(fig, "literature points; python mass-balance relation (not a cycle simulation)")
    fig.savefig(FIG / "purification_recovery_purity.png", dpi=200)
    plt.close(fig)
    # 2 recovery vs cost
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    labs = sorted({r["config"] for r in rc_rows})
    cols = [C_PRIMARY, C_HEAT, C_NH3, C_N2]
    for lab, col in zip(labs, cols):
        rr = [r for r in rc_rows if r["config"] == lab]
        ax.plot([r["recovery"] * 100 for r in rr], [r["usd_per_kg"] for r in rr], color=col, label=lab)
    ax.set_xlabel("H2 recovery (%)")
    ax.set_ylabel("Cost per kg product H2, 350 bar (USD/kg)")
    ax.set_title("Recovery vs cost at Grade D purity (20 bar baseline)")
    ax.legend(fontsize=7)
    add_provenance(fig, "python; existing AmCraX costs + Richard 2024 membrane cost; PSA scan is parametric")
    fig.savefig(FIG / "purification_recovery_cost.png", dpi=200)
    plt.close(fig)
    # 3 config comparison per end use
    fig, axs = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
    base = results["cases"]["20bar_baseline"]["configs"]
    for ax, eu, ttl in zip(axs, DELIVERY, ("Industrial 99.9 % (30 bar)", "Fuel cell Grade D (350 bar)", "Turbine blend (30 bar)")):
        names, vals, cs = [], [], []
        for c in base:
            k = c["costs"][eu]
            names.append(c["id"])
            v = k["usd_per_kg_usable_h2"]
            vals.append(v if v is not None else 0.0)
            cs.append(C_PRIMARY if v is not None else C_GREY)
        y = np.arange(len(names))
        ax.barh(y, vals, color=cs)
        for yi, (c, v) in enumerate(zip(base, vals)):
            star = "*" if c["costs"][eu].get("conditional_on") else ""
            ax.text(v + 0.05, yi, f"{v:.2f}{star}" if c["costs"][eu]["usd_per_kg_usable_h2"] is not None else "fails spec",
                    va="center", fontsize=6.5)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=7)
        ax.set_title(ttl, fontsize=9)
        ax.set_xlabel("USD per kg usable H2")
        ax.invert_yaxis()
    fig.suptitle("Cost per kg of usable hydrogen by configuration and end use (20 bar baseline)", fontsize=10)
    add_provenance(fig, "python; * membrane N2 compliance conditional on selectivity; compression and housing CAPEX, TSA heat not modelled")
    fig.savefig(FIG / "purification_config_comparison.png", dpi=200)
    plt.close(fig)
    # 4 sensitivity
    fig, ax = plt.subplots(figsize=(8, 5.6))
    base_row = sens[0]
    labs, dps, dms = [], [], []
    for r in sens[1:]:
        labs.append(f"{r['parameter']} = {r['setting']}")
        dps.append((r["PSA_D_usd_per_kg"] - base_row["PSA_D_usd_per_kg"]) if r["PSA_D_usd_per_kg"] is not None else 0)
        dms.append((r["MEM_D_usd_per_kg"] - base_row["MEM_D_usd_per_kg"]) if r["MEM_D_usd_per_kg"] is not None else 0)
    y = np.arange(len(labs))
    ax.barh(y - 0.2, dps, 0.4, color=C_PRIMARY, label=f"PSA (base {base_row['PSA_D_usd_per_kg']:.2f} USD/kg)")
    ax.barh(y + 0.2, dms, 0.4, color=C_HEAT, label=f"Pd-Ag + polish (base {base_row['MEM_D_usd_per_kg']:.2f} USD/kg)")
    ax.set_yticks(y)
    ax.set_yticklabels(labs, fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("Change in cost per kg product H2 at 350 bar (USD/kg)")
    ax.set_title("Sensitivity of Grade D purification options, one parameter at a time")
    ax.legend(fontsize=7)
    add_provenance(fig, "python; ranges from assumptions.json")
    fig.savefig(FIG / "purification_sensitivity.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------------------ validation
def validation(results, cases, mem_rows, sel_rows):
    items = []

    def add(id_, desc, method, ref, obs, exp, tol, unit, status, files):
        items.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs,
                      "expected": exp, "tolerance": tol, "unit": unit, "status": status, "source_files": files})

    SF = ["results/research/purification/purification_study.json"]
    # 1 closure for every configuration
    worst, n = 0.0, 0
    bad = []
    for cid, e in results["cases"].items():
        for c in e["configs"]:
            n += 1
            m = c["closure"]["max_abs_rel_error"]
            worst = max(worst, m)
            if m > 1e-9 or abs(c["closure"]["mass_rel_error"]) > 1e-9:
                bad.append(f"{cid}/{c['id']}")
    add("P-MB-1", f"Component mole and total mass balance closure for all {n} configurations x 3 pressure cases",
        "sum of product and tail flows minus feed, per species, relative", "internal consistency (python)", worst, 0.0,
        1e-9, "relative", "pass" if not bad else "fail", SF)
    # 2 Sieverts hand calculation
    T = MEM_T_K
    Pe0, Ea, d = 4.57e-8, 9230.0, 5.2e-6
    perm_hand = Pe0 * math.exp(-Ea / (8.314462618 * T)) / d
    pret, pperm = 0.7 * 20e5, 1e5
    J_hand = perm_hand * (pret ** 0.5 - pperm ** 0.5)
    J_code = sieverts_flux(pret, pperm, permeance(T), 0.5, 1.0)
    add("P-SIEV-1", "Sieverts flux hand calculation at 673.15 K, p_H2,ret 14 bar, permeate 1 bar, Pe0 4.57e-8, Ea 9.23 kJ/mol, "
        "5.2 um", "flux = Pe0 exp(-Ea/RT)/d * (p_ret^0.5 - p_perm^0.5), computed separately with R = 8.314462618",
        "richard2024technoeconomic p. 7 Table 2 row [53], Eq. 1", J_code, J_hand, 1e-9 * J_hand, "mol m-2 s-1",
        "pass" if abs(J_code - J_hand) <= 1e-9 * J_hand else "fail", ["backend/amcrax/separation/purification.py"])
    # 3 pinch limit consistency: area -> large recovers pinch
    feed = cases["20bar_baseline"]["feed"]
    rmax = pinch_recovery(feed, 19.5, 1.0)
    m = membrane_with_leakage(feed, 1e6, 19.5, 1.0, MEM_T_K)
    add("P-PINCH-1", "Recovery at very large area approaches the partial-pressure pinch limit y_H2 P_feed = P_perm",
        "integrate with 1e6 m2 and compare with closed-form pinch", "thermodynamic limit (python)", m["h2_recovery"], rmax,
        1e-4, "-", "pass" if abs(m["h2_recovery"] - rmax) < 1e-4 else "fail", ["backend/amcrax/separation/purification.py"])
    # 4 PSA point reproduction (trivial)
    cfg = next(c for c in results["cases"]["20bar_baseline"]["configs"] if c["id"] == "PSA_CHO")
    add("P-PSA-1", "PSA published point reproduced when applied to the Aspen cracked gas: recovery 0.756 and purity (H2/(H2+N2), "
        "NH3 at 0.1 ppm) 0.9911", "psa_split with Cho recovery and purity; this reproduces the input by construction, so it is a "
        "bookkeeping check, not validation of PSA physics", "cho2026nickel p. 6 Table 3", cfg["h2_recovery"], 0.756, 1e-6, "-",
        "informational", SF)
    # 5 membrane vs measured purity: required selectivity vs literature purity
    req = [r for r in sel_rows if r["permeate_bar"] == 1.0 and r["recovery"] == 0.90 and r["limit_ppm"] == 300.0]
    obs = req[0]["required_alpha_H2_N2"] if req else None
    add("P-MEM-2", "H2/N2 selectivity needed for N2 <= 300 ppm in the permeate at R = 0.90, 1 bar permeate, 400 degC, "
        "20 bar baseline", "bisection on ideal selectivity; compared with measured Pd-Ag purity 99.995 % (50 ppm total "
        "impurities) at 450 degC, 4.61 um (a membrane reactor, different feed), and (Phase 2) with the sourced ideal "
        "H2/N2 of cechetto2021fpt Sec. 3.1 (stated above 400,000; about 40,500 from the printed double-sealed N2 "
        "permeance): see P2-SEL-1", "cechetto2023membrane p. 17 Table 10; cechetto2021fpt p. 4", obs,
        None, None, "-", "informational", ["results/research/purification/membrane_required_selectivity.csv"])
    # 6 like-for-like comparison with Cechetto not possible
    add("P-MEM-3", "Comparison with Cechetto 4 bar / 400 degC membrane reactor (X 99.3 %, R_H2 93.5 %)",
        "not performed: that is a reactor result (reaction plus separation, vacuum permeate, lab module) and the library gives "
        "neither the module area nor Sieverts parameters of that membrane; a separator model cannot be compared with it",
        "cechetto2023membrane p. 15 Table 8", None, None, None, "-", "informational", [])
    add("P-ISO-1", "ISO 14687:2019 grade D limits transcribed (H2 index 99.97 %, total 300, H2O 5, N2 300, NH3 0.1 umol/mol)",
        "values compared with the cited limits quoted in cechetto2023membrane p. 5 (NH3 0.1 ppm, N2 300 ppm)",
        "ISO 14687:2019 Table 2", [GRADES["D"]["limits_ppm"]["NH3"], GRADES["D"]["limits_ppm"]["N2"]], [0.1, 300.0], 0, "ppm",
        "pass", ["backend/amcrax/separation/purification.py"])
    # 7 AmCraX baseline splitter versus grade D
    ac = next(c for c in results["cases"]["20bar_baseline"]["configs"] if c["id"] == "PSA_AMCRAX")
    add("P-ISO-2", "Aspen baseline H2PROD stream (N2 0.0489 kmol/h, NH3 0) against grade D N2 limit: N2 ppm (Aspen stream)",
        "N2 / (H2 + N2) from results/simulations/baseline.json H2PROD, compared with 300 umol/mol", "ISO 14687:2019 Table 2",
        1e6 * 0.0489424371 / (124.803215 + 0.0489424371), 300.0, None, "umol/mol",
        "informational", ["results/simulations/baseline.json"])
    # Phase 2: every item names its kind of evidence (AmCraX has no experimental validation)
    kinds = {"P-MB-1": "numerical_verification", "P-SIEV-1": "numerical_verification",
             "P-PINCH-1": "numerical_verification", "P-PSA-1": "numerical_verification",
             "P-MEM-2": "literature_comparison", "P-MEM-3": "literature_comparison",
             "P-ISO-1": "literature_comparison", "P-ISO-2": "literature_comparison"}
    for it in items:
        it["evidence_kind"] = kinds[it["id"]]
    # Phase 2 items (P2-*) are appended by scripts/research/purification_phase2.py; keep them if present
    old = VAL / "purification.json"
    if old.exists():
        try:
            items += [i for i in json.loads(old.read_text(encoding="utf-8")) if str(i.get("id", "")).startswith("P2-")]
        except (ValueError, OSError):
            pass
    json.dump(_clean(items), open(VAL / "purification.json", "w", encoding="utf-8"), indent=1)


def refs():
    items = [
        {"key": "iso14687_2019", "apa": "International Organization for Standardization. (2019). Hydrogen fuel quality - Product "
         "specification (ISO 14687:2019). ISO.", "url": "https://www.iso.org/standard/69539.html",
         "access_date": "2026-11-23", "used_for": "Grade D, E category 3 and A/B hydrogen fuel index and contaminant limits "
         "(Tables 2-4). Text read from a public standards-body consultation reproduction "
         "(consultations.standards.govt.nz dz-14687.pdf), not from the ISO store.", "type": "standard"},
    ]
    json.dump(items, open(REFS / "purification.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
