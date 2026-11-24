"""H1 end-use analysis, Phase 2 (task E2): turbine-efficiency thresholds, sensitivities, two-way map, NOx/N2O and
blend status, the 40 % figure and row evidence for H1-a..H1-d. Deterministic; re-run after enduse_run.py:
   python scripts/research/enduse_threshold.py

Every number is computed on the unified reference scenario (amcrax.economics.reference / singapore.evaluate defaults);
the defaults of amcrax.enduse are not changed, only optional arguments are used. Sourced literature values are read
from research/data/turbine_efficiency_literature.json and enduse_cost_literature.json; nothing is tuned.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from amcrax.economics.reference import load_reference_scenario, provenance_stamp, reference_capex  # noqa: E402
from amcrax.enduse import hydrogen_activity, hydrogen_cost, load_cracker, power_activity, power_cost  # noqa: E402
from amcrax.enduse import params as P  # noqa: E402
from amcrax.enduse import pathways as pw  # noqa: E402
from amcrax.environmental import lca  # noqa: E402
from amcrax.plotstyle import C_AMBER, C_GREY, C_H2, C_HEAT, C_N2, C_NH3, C_PRIMARY, apply_style, plt  # noqa: E402
from amcrax.schemas import MOLAR_MASS  # noqa: E402

OUT = ROOT / "results" / "research" / "enduse"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation" / "enduse.json"
SCRIPT = "scripts/research/enduse_threshold.py"
REF = load_reference_scenario()
FX = REF.fx_SGD_per_USD
USD_PER_EUR = REF.usd_per_eur
TAX_SGD = REF.carbon_tax_SGD_per_t
PRICE = P.NH3_PRICE_REF_USD_T
HOURS = P.POWER_PLANT_HOURS_PER_YEAR
ETA0 = P.ETA_GT_GAS
LIT_T = json.loads((ROOT / "research/data/turbine_efficiency_literature.json").read_text(encoding="utf-8"))
LIT_C = json.loads((ROOT / "research/data/enduse_cost_literature.json").read_text(encoding="utf-8"))
X = load_cracker("baseline").conversion
DSYS_AHMAD = (P.ELEC_MJ_PER_KG_FULL - P.ELEC_MJ_PER_KG_DIRECT) / P.LHV_NH3_MJ_KG   # system gain, AmCraX LHV basis
ALL = [("direct", None), ("partial_exhaust", 0.4), ("partial_fired", 0.4), ("full_exhaust", None), ("full_fired", None),
       ("full_purified", None), ("blend_purified", 0.4)]
CRK = ALL[1:]


def tag(kind, y):
    return kind + (f"_{int(round(y * 100))}" if y is not None else "")


def prov(summary):
    return {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "script": SCRIPT,
            "source_type": "python (stored Aspen cracker activities + literature-calibrated turbine inputs)",
            "inputs_summary": summary, "reference_scenario": provenance_stamp(),
            "literature_files": ["research/data/turbine_efficiency_literature.json", "research/data/enduse_cost_literature.json",
                                 "research/notes/enduse_turbine_literature.md", "research/data/carbon_policy_sg.json"]}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------------------------------------
# cost helpers
# ------------------------------------------------------------------------------------------------
def act(kind, y=None, eta=None, g=1.0, case="baseline"):
    if kind in ("direct", "partial_exhaust", "full_exhaust"):
        return power_activity(kind, y, case=case, gain_scale=g)
    return power_activity(kind, y, case=case, eta_h2_fuel=eta)


def ahmad_corr_factor(a):
    """Ahmad (2025) Fig. 6 cracker CAPEX correlation (18.171 x (t H2/h)^0.7451 MUSD, Cesaro 2021 data) as a factor on
    the reference cracker TCI of the same activity (sized on H2 in the cracked gas)."""
    if a.capex_kind == "none" or a.cracker_nh3_kg_h <= 0:
        return 1.0
    excl = ("psa", "adsorber") if a.capex_kind == "unpurified" else ()
    ref = reference_capex(a.cracker_nh3_kg_h / MOLAR_MASS["NH3"], exclude=excl)["total_capex_USD"]
    t_h2 = a.cracker_nh3_kg_h * lca.KG_H2_PER_KG_NH3 * X / 1000.0
    return 18.171e6 * t_h2 ** 0.7451 / ref


CAPEX_BASES = {
    "reference": {},
    "reference_with_psa_items": {"unpurified_full_correlation": True},
    "ahmad_fig6_correlation": "ahmad",
    "cracker_x0.5": {"cracker_capex_factor": 0.5},
    "cracker_x2": {"cracker_capex_factor": 2.0},
}


def cost(a, price=PRICE, hours=HOURS, basis="reference", **kw):
    b = CAPEX_BASES[basis]
    if b == "ahmad":
        kw = {**kw, "cracker_capex_factor": kw.get("cracker_capex_factor", 1.0) * ahmad_corr_factor(a)}
    else:
        kw = {**b, **kw}
    return power_cost(a, price, hours=hours, **kw)["LCOE_USD_per_MWh"]


def direct_lcoe(price=PRICE, hours=HOURS, **kw):
    kw = {k: v for k, v in kw.items() if k in ("plant_capex_factor", "extra_capex_USD_per_kW")}
    return power_cost(power_activity("direct"), price, hours=hours, **kw)["LCOE_USD_per_MWh"]


# ------------------------------------------------------------------------------------------------
# thresholds
# ------------------------------------------------------------------------------------------------
def threshold(kind, y, price=PRICE, hours=HOURS, basis="reference"):
    d = direct_lcoe(price, hours)
    if kind in ("partial_exhaust", "full_exhaust"):
        fn = lambda g: cost(act(kind, y, g=g), price, hours, basis) - d
        try:
            g = brentq(fn, -3.0, 8.0, xtol=1e-12)
        except ValueError:
            return None
        a = act(kind, y, g=g)
        f = a.cracked_share
        return {"parameter": "system efficiency on NH3 LHV supplied (exhaust-heated cracker, heat internal)",
                "gain_scale": g, "system_efficiency": a.efficiency,
                "delta_system_pp_vs_direct": (a.efficiency - ETA0) * 100,
                "delta_full_cracking_equivalent_pp": g * DSYS_AHMAD * 100,
                "implied_eta_on_fuel_gas_LHV": a.efficiency * a.nh3_kg * P.LHV_NH3_MJ_KG / (a.nh3_kg * pw.fuel_lhv_mj_per_kg_nh3_fed(f, X)),
                "cracked_share": f, "LCOE_check": cost(a, price, hours, basis), "LCOE_direct": d}
    fn = lambda e: cost(act(kind, y, eta=e), price, hours, basis) - d
    try:
        e = brentq(fn, 0.2, 0.99, xtol=1e-12)
    except ValueError:
        return None
    a = act(kind, y, eta=e)
    return {"parameter": "combined-cycle efficiency on the LHV of the H2-rich fuel fired (same basis as the direct-NH3 49.64 %)",
            "eta_h2_fuel": e, "delta_fuel_pp_vs_direct_turbine": (e - ETA0) * 100, "ratio_to_direct_turbine": e / ETA0,
            "system_efficiency_at_threshold": a.efficiency, "delta_system_pp_vs_direct": (a.efficiency - ETA0) * 100,
            "cracked_share": a.cracked_share, "LCOE_check": cost(a, price, hours, basis), "LCOE_direct": d}


HALIM_X = ROOT / "research" / "data" / "halim2025_extract.json"


def fuel_cost_gap_on_paper_basis():
    """H1-b on the paper's own basis (addendum of 24 November 2026). Halim et al. (2025) report 'about 40 %' as
    1 - LCOA/LCOH (39 % green, 44 % blue, p. 9): the cost of fuel delivered to the turbine per kg of hydrogen-equivalent
    fuel energy, power plant excluded. The same quantity on AmCraX boundaries: direct = NH3 bought at the scenario price
    for the same LHV as 1 kg H2 (no storage, vaporisation or compression item exists in AmCraX), cracked = the unified
    LCOH (singapore.evaluate on the stored Aspen baseline), heat integration on and off. The LCOE comparison of the
    essay's sentence about power (largest gap 16.6 %) is not changed."""
    from amcrax.economics.singapore import evaluate as sg_eval
    hx = {e["id"]: e for e in json.loads(HALIM_X.read_text(encoding="utf-8"))["entries"]}
    lhv_nh3, lhv_h2 = P.LHV_NH3_MJ_KG, P.LHV_H2_MJ_KG
    kg_eq = lhv_h2 / lhv_nh3                               # kg NH3 with the LHV of 1 kg H2
    hi = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))
    nohi = json.loads((ROOT / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8"))
    pr = hx["cost_nh3_prices"]["value"]
    prices = [(k, "reference scenario (backend/amcrax/data/reference_scenario.yaml)", v) for k, v in P.NH3_PRICE_SET_USD_T.items()]
    prices += [("halim_green_FOB", "Halim et al. 2025 Table 4 (Platts, July 2024)", pr["green_FOB_USD_per_t"]),
               ("halim_blue_FOB", "Halim et al. 2025 Table 4 (Platts, July 2024)", pr["blue_FOB_USD_per_t"])]
    cases = []
    for lab, src, p in prices:
        for hl, res in (("on", hi), ("off", nohi)):
            e = sg_eval(res, float(p))
            d = p / 1000.0 * kg_eq
            cases.append({"price_case": lab, "price_source": src, "NH3_USD_per_t": float(p), "heat_integration": hl,
                          "cracked_LCOH_USD_per_kg": e["lcoh_USD_per_kg"], "direct_fuel_cost_USD_per_kg_H2_equivalent": d,
                          "gap_pct_1_minus_direct_over_cracked": 100.0 * (1.0 - d / e["lcoh_USD_per_kg"])})
    # ---- reconciliation with the paper's printed and reader-derived quantities (heat integration on) ----
    wt = hx["cost_discount_life_cf"]["value"]
    retain = hx["eff_direct_equivalence"]["value"] / hx["eff_cracker_nh3_feed"]["value"]["kg_per_h_at_8760h"]   # 0.695
    fig5 = {"green": {"price": pr["green_FOB_USD_per_t"], "lcoh": hx["cost_lcoh_green"]["value"], "lcoa": hx["cost_lcoa_green"]["value"],
                      "lcoh_feed": 8.70, "lcoa_feed": 6.05, "paper_gap_pct": hx["cost_forty_percent"]["value"]["green_pct"]},
            "blue": {"price": pr["blue_FOB_USD_per_t"], "lcoh": hx["cost_lcoh_blue"]["value"], "lcoa": hx["cost_lcoa_blue"]["value"],
                     "lcoh_feed": 3.67, "lcoa_feed": 2.55, "paper_gap_pct": hx["cost_forty_percent"]["value"]["blue_pct"]}}
    hours_halim = 8760.0 * wt["capacity_factor"]
    rec = {}
    for k, z in fig5.items():
        p = z["price"] / 1000.0
        e0 = sg_eval(hi, z["price"])
        nh3_kg = e0["kg_nh3_feed_per_kg_h2"] + e0["kg_nh3_fuel_per_kg_h2"]
        non0 = e0["lcoh_USD_per_kg"] - (e0["breakdown_USD_per_kg"]["ammonia_feed"] + e0["breakdown_USD_per_kg"]["heat_fuel"])
        e2 = sg_eval(hi, z["price"], {"operating_hours_h_per_yr": hours_halim, "plant_life_yr": float(wt["life_years"])})
        non2 = e2["lcoh_USD_per_kg"] - (e2["breakdown_USD_per_kg"]["ammonia_feed"] + e2["breakdown_USD_per_kg"]["heat_fuel"])
        d0 = p * kg_eq
        nh3_halim = kg_eq / retain
        non_direct_halim = z["lcoa"] - z["lcoa_feed"]
        non_crack_halim = z["lcoh"] - z["lcoh_feed"]
        steps = [("0 AmCraX unified model at the paper's price, heat integration on", d0, e0["lcoh_USD_per_kg"]),
                 (f"1 cracked side: NH3 per kg H2 at the paper's energy retention {retain:.4f} (AmCraX {kg_eq / nh3_kg:.4f})",
                  d0, non0 + p * nh3_halim),
                 (f"2 also the paper's capacity factor {wt['capacity_factor']} ({hours_halim:.0f} h) and life {wt['life_years']} yr on AmCraX non-NH3 costs",
                  d0, non2 + p * nh3_halim),
                 (f"3 also the paper's cracked-side non-feed cost {non_crack_halim:.2f} USD/kg instead of AmCraX {non2:.3f} (storage tank, fired furnace, compressors, PSA, O&M; Fig. 5)",
                  d0, non_crack_halim + p * nh3_halim),
                 (f"4 also the paper's direct-use non-feed cost {non_direct_halim:.2f} USD/kg (mostly the same storage tank, plus vaporisation and compression; Fig. 5)",
                  d0 + non_direct_halim, non_crack_halim + p * nh3_halim)]
        rows = []
        for lab, dd, cc in steps:
            rows.append({"step": lab, "direct_USD_per_kg": dd, "cracked_USD_per_kg": cc, "gap_pct": 100.0 * (1.0 - dd / cc)})
        for i in range(1, len(rows)):
            rows[i]["change_pp"] = rows[i]["gap_pct"] - rows[i - 1]["gap_pct"]
        g0 = rows[0]["gap_pct"]
        one = {"energy_retention_only": 100.0 * (1.0 - d0 / (non0 + p * nh3_halim)) - g0,
               "hours_and_life_only": 100.0 * (1.0 - d0 / (non2 + p * nh3_kg)) - g0,
               "cracked_non_feed_cost_only": 100.0 * (1.0 - d0 / (non_crack_halim + p * nh3_kg)) - g0,
               "direct_non_feed_cost_only": 100.0 * (1.0 - (d0 + non_direct_halim) / e0["lcoh_USD_per_kg"]) - g0}
        rec[k] = {"NH3_USD_per_t": z["price"], "paper_gap_pct_printed": z["paper_gap_pct"],
                  "paper_gap_pct_from_printed_LCOA_LCOH": 100.0 * (1.0 - z["lcoa"] / z["lcoh"]),
                  "amcrax_nh3_kg_per_kg_h2_feed_plus_fuel": nh3_kg, "amcrax_energy_retained_as_h2": kg_eq / nh3_kg,
                  "paper_energy_retained_as_h2_derived": retain, "amcrax_non_nh3_cost_USD_per_kg": non0,
                  "amcrax_non_nh3_cost_at_paper_hours_and_life_USD_per_kg": non2,
                  "paper_non_feed_cost_cracked_USD_per_kg": non_crack_halim, "paper_non_feed_cost_direct_USD_per_kg": non_direct_halim,
                  "steps": rows, "one_at_a_time_change_pp_from_step_0": one,
                  "residual_pp_vs_printed": rows[-1]["gap_pct"] - z["paper_gap_pct"]}
    cap = hx["cost_capex"]["value"]
    h2_kg_h = hx["sys_fuel_flows"]["value"]["H2_kg_per_h"]
    e_ref = sg_eval(hi, "grey")
    capital = {"paper_TCI_USD_per_kg_h_H2": cap["TCI_USD"] / h2_kg_h,
               "paper_TCI_excluding_storage_tank_share_USD_per_kg_h_H2": cap["TCI_USD"] * (1.0 - cap["storage_tank_T100_USD"] / cap["PEIC_USD"]) / h2_kg_h,
               "paper_storage_tank_share_of_PEIC": cap["storage_tank_T100_USD"] / cap["PEIC_USD"],
               "paper_furnace_share_of_PEIC": cap["furnace_F100_USD"] / cap["PEIC_USD"],
               "amcrax_capex_USD_per_kg_h_H2": e_ref["capex"]["total_capex_USD"] / e_ref["h2_product_kg_h"],
               "note": "derived; the storage-tank exclusion assumes every capital-proportional item scales with PEIC (the paper's "
                       "factors are percentages of PEC); AmCraX has no ammonia storage item"}
    return {
        "description": fuel_cost_gap_on_paper_basis.__doc__.split("\n\n")[0].replace("\n", " ").replace("    ", " "),
        "quantity": "1 - direct NH3 fuel cost / cracked-hydrogen cost, both per kg of hydrogen-equivalent fuel energy (not a cost of electricity)",
        "lhv_MJ_per_kg": {"NH3": lhv_nh3, "H2": lhv_h2, "basis": "amcrax.schemas LHV_KJ_PER_MOL / MOLAR_MASS (the paper's implied NH3 LHV is 18.737)"},
        "kg_NH3_per_kg_H2_equivalent": kg_eq,
        "direct_side_boundary": "NH3 purchase only at the scenario price; AmCraX has no ammonia storage, vaporisation or compression item (the paper's LCOA includes them)",
        "cracked_side_boundary": "unified reference LCOH: plant gate, H2 at 19.5 bar, PSA recovery 0.85, supplementary NH3 fuel at 100 % of its LHV, no storage",
        "cases": cases,
        "paper_values": {k: {"NH3_USD_per_t": z["price"], "LCOH_USD_per_kg": z["lcoh"], "LCOA_USD_per_kg": z["lcoa"],
                             "gap_pct_printed": z["paper_gap_pct"]} for k, z in fig5.items()},
        "reconciliation": rec,
        "reconciliation_note": ("Sequential substitution of the paper's quantities into the AmCraX calculation, heat integration on; "
                                "each step keeps the previous ones, so the change per step depends on the order (one-at-a-time "
                                "changes from step 0 are given beside the steps). After step 4 the gap is rebuilt from the paper's "
                                "own numbers on the AmCraX LHV basis. Reading: the paper's larger gap comes from its lower energy "
                                "retention (0.695 against 0.877) and above all from its much larger non-feed cost of cracking "
                                "(6.40 against 0.70 USD/kg); its ammonia storage, vaporisation and compression cost on the direct "
                                "side (3.15 USD/kg) pulls the gap back down; hours and plant life change it by less than 0.1 point."),
        "capital_intensity": capital,
        "cannot_be_reconciled": [
            "how the paper's non-feed costs split between the storage tank, the fired furnace, the compressors and the PSA beyond "
            "the PEIC shares (the stream table and supplementary Tables A1-A2 were not available)",
            "the price year of the paper's capital costs (not stated; CEPCI 800) against the AmCraX 2024 USD basis",
            "the paper's NH3 LHV (18.737 MJ/kg implied) against AmCraX 18.60: about 0.7 % on every NH3 quantity",
            "AmCraX has no ammonia storage, vaporisation or compression cost on either side, so steps 3 and 4 import the paper's "
            "numbers rather than compute them",
            "the paper's plant buys grid electricity at 0.16 USD/kWh inside 'other variable' costs; AmCraX uses its own electricity price",
        ],
        "lcoe_comparison_unchanged": "forty_percent_figure/largest_computed_pct (cost of electricity on AmCraX boundaries) is unchanged; "
                                     "it tests the essay's sentence about power, which is not the paper's quantity",
        "source_type": "python (unified economics) + literature (Halim et al. 2025, research/data/halim2025_extract.json)",
    }


def side(th, lo, hi):
    if th is None:
        return "no threshold in range"
    if hi < th:
        return "all sourced values BELOW threshold: direct NH3 cheaper"
    if lo > th:
        return "all sourced values ABOVE threshold: cracking pathway cheaper"
    return "sourced values STRADDLE the threshold"


def main():
    apply_style()
    FIG.mkdir(parents=True, exist_ok=True)
    stored = {r["id"]: r for r in json.loads((OUT / "enduse_results.json").read_text(encoding="utf-8"))["power_pathways"]}
    base = {tag(k, y): cost(act(k, y)) for k, y in ALL}
    D = base["direct"]

    # ---------------- what each pathway assumes ----------------
    fe = act("full_exhaust")
    implied_fe = P.ELEC_MJ_PER_KG_FULL / pw.fuel_lhv_mj_per_kg_nh3_fed(1.0, X)
    assumes = {
        "direct": f"Ahmad Case 2a system efficiency 49.12 % on LHV 18.8 = {P.ELEC_MJ_PER_KG_DIRECT:.4f} MJ electricity per kg NH3 = {ETA0*100:.2f} % on the AmCraX LHV 18.60 MJ/kg.",
        "full_fired / partial_fired": f"Cracker heat = stored Aspen reactor + pre-heater duty ({load_cracker('baseline').crack_heat_MJ_per_kg_nh3:.3f} MJ per kg NH3 cracked) supplied by burning extra NH3 at 100 % heat-transfer efficiency (assumption, favourable to cracking). Combined cycle on the H2/N2(/NH3) fuel gas LHV at eta_h2_fuel = {ETA0*100:.2f} % (copy of the direct value; assumption eta_gt_gas).",
        "full_purified / blend_purified": f"Stored Aspen baseline cracker + PSA (recovery {load_cracker('baseline').recovery}); heat deficit after tail-gas firing from extra NH3; combined cycle on the H2 (or NH3 + H2 blend) LHV at eta_h2_fuel = {ETA0*100:.2f} % (assumption).",
        "full_exhaust / partial_exhaust": f"Electricity per kg NH3 from Ahmad's two system end points (49.12 % and about 54 % on LHV 18.8, i.e. {ETA0*100:.2f} % and {fe.efficiency*100:.2f} % on LHV 18.60, +{DSYS_AHMAD*100:.2f} pp), linear in the cracked share (assumption). No extra NH3 for cracker heat (exhaust supplies it) and ETA_GT_GAS is NOT used. The implied combined-cycle efficiency on cracked-gas LHV is {implied_fe*100:.2f} % (below 49.64 %, because exhaust heat goes to the cracker instead of the steam cycle).",
        "double_counting_check": "Ahmad's efficiency gain enters only the exhaust-heated kinds through eta_exhaust_integrated(); those kinds neither add cracker-heat NH3 nor apply ETA_GT_GAS, and the fired/purified kinds never use the Ahmad 54 % value. Nothing is counted twice (validation EU-P2-no-double-count).",
        "brief_correction": "The statement that all four stored power costs assume a 49.64 % hydrogen-rich turbine is true for fired cracking (280.1) and cracking + PSA (310.2) only. The exhaust-heated value (255.6) uses Ahmad's 54 % system efficiency.",
    }

    # ---------------- 1. statement of the computed result ----------------
    halim = json.loads((OUT / "enduse_results.json").read_text(encoding="utf-8"))["halim_claim_check"]["computed"]
    adv = {k: {"LCOE": base[k], "direct_cheaper_pct_of_cracking_1_minus_d_over_c": 100 * (1 - D / base[k]),
               "cracking_dearer_pct_of_direct_c_over_d_minus_1": 100 * (base[k] / D - 1)} for k in ("full_fired", "full_purified", "full_exhaust", "partial_exhaust_40", "partial_fired_40", "blend_purified_40")}
    statement = {
        "text": (f"On the unified reference scenario (grey NH3 {PRICE:g} USD/t, {HOURS:g} h/yr, 10 %, 25 y), direct NH3 combustion gives {D:.1f} USD/MWh. "
                 f"It is {adv['full_fired']['direct_cheaper_pct_of_cracking_1_minus_d_over_c']:.1f} % cheaper than a standalone fired cracker ({base['full_fired']:.1f}) and "
                 f"{adv['full_purified']['direct_cheaper_pct_of_cracking_1_minus_d_over_c']:.1f} % cheaper than cracking + PSA ({base['full_purified']:.1f}), as 1 - direct/cracking, "
                 f"ON THE ASSUMPTION that the turbine reaches the direct-NH3 efficiency ({ETA0*100:.2f} %) on the H2-rich fuel. "
                 f"Against an exhaust-heated cracker (Ahmad's +{DSYS_AHMAD*100:.2f} pp system gain) direct use is {-adv['full_exhaust']['direct_cheaper_pct_of_cracking_1_minus_d_over_c']:.1f} % dearer ({base['full_exhaust']:.1f})."),
        "old_pre_unification": {"fired_pct": 5.0, "purified_pct": 15.0, "exhaust_pct": -4.0, "source": "Phase 1 end-use results of the 23 November 2026 release (LCOE 259 / 273 / 304 / 248 USD/MWh), quoted as about 5 to 15 %"},
        "new_unified": adv,
    }

    # ---------------- 2. thresholds ----------------
    tr = LIT_T["key_deliverable_efficiency_difference"]
    ahm_lo, ahm_hi = 4.4 * P.AHMAD_LHV_NH3 / P.LHV_NH3_MJ_KG, 5.4 * P.AHMAD_LHV_NH3 / P.LHV_NH3_MJ_KG
    sourced = {
        "exhaust_heated_system_delta_pp": {
            "ahmad2025_like_for_like_AmCraX_basis": [ahm_lo, DSYS_AHMAD * 100, ahm_hi],
            "karpilov2025_maximum": [5.0, 5.5], "supported_range": [4.9, 5.5], "sensitivity_range": [0.0, 5.5],
            "basis": "combined-cycle system efficiency on NH3 LHV supplied, exhaust-heated cracker; Ahmad 4.4-5.4 pp on LHV 18.8 rescaled by 18.8/18.6; Karpilov unit and basis not stated ('up to', a maximum over TIT 800-1200 C)",
            "grade": "cycle_simulation (no measurement); small or idealised machines only; nothing for F/H class",
            "source": "research/data/turbine_efficiency_literature.json key_deliverable_efficiency_difference"},
        "fired_H2N2_fuel_delta_pp": {
            "sourced": None,
            "indirect_bracket": [(implied_fe - ETA0) * 100, 7.3],
            "basis": "nothing sourced for a turbine on H2/N2 from a standalone fired cracker. Bracket for orientation only: lower = Ahmad exhaust-heated implied efficiency on cracked-gas LHV (derived here, exhaust heat diverted to the cracker); upper = NETL 2023 vs 2024 pure H2 (steam-diluted) minus NH3, +7.3 pp, which the literature note says NOT to use for cracked gas.",
            "grade": "derived / not like-for-like"},
        "purified_H2_fuel_delta_pp": {
            "netl_absolute": 7.3, "netl_relative_on_AmCraX_turbine": (66.9 / 59.6 - 1) * ETA0 * 100,
            "basis": "NETL 2023 (66.9 %, 100 % H2 steam-diluted, Exhibit 4-9) minus NETL 2024 (59.6 %, 100 % NH3, Exhibit 4-6), same agency method and B32A baseline, H-class-like. Steam dilution inflates the H2 figure, so it is an UPPER bound for dry H2 firing. No lower-side source.",
            "grade": "cycle_simulation, not like-for-like (no cracker, steam diluent)"},
    }
    cases = [("full_fired", None, "fired_H2N2_fuel_delta_pp"), ("full_purified", None, "purified_H2_fuel_delta_pp"),
             ("blend_purified", 0.4, "purified_H2_fuel_delta_pp"), ("full_exhaust", None, "exhaust_heated_system_delta_pp")]
    for y in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        cases += [("partial_fired", y, "fired_H2N2_fuel_delta_pp"), ("partial_exhaust", y, "exhaust_heated_system_delta_pp")]
    bases = [("reference", PRICE, HOURS, "reference")] + [(f"capex_{b}", PRICE, HOURS, b) for b in CAPEX_BASES if b != "reference"] + \
            [(f"nh3_{p:g}", p, HOURS, "reference") for p in (300.0, 709.0, 1000.0)] + [("hours_5000", PRICE, 5000.0, "reference"),
             ("ahmad_basis_480_7200", P.AHMAD_NH3_PRICE_USD_T, P.AHMAD_HOURS_IMPLIED, "reference"),
             ("ahmad_basis_480_7200_ahmad_capex", P.AHMAD_NH3_PRICE_USD_T, P.AHMAD_HOURS_IMPLIED, "ahmad_fig6_correlation")]
    th_rows, th_json = [], {}
    for kind, y, cls in cases:
        k = tag(kind, y)
        entry = {"class": cls, "bases": {}}
        for bname, p_, h_, cb in bases:
            t = threshold(kind, y, p_, h_, cb)
            entry["bases"][bname] = t
            if t is None:
                continue
            key = "delta_fuel_pp_vs_direct_turbine" if "eta_h2_fuel" in t else "delta_system_pp_vs_direct"
            th_rows.append({"pathway": k, "basis": bname, "NH3_USD_t": p_, "hours": h_, "capex_basis": cb,
                            "threshold_parameter": "eta_h2_fuel" if "eta_h2_fuel" in t else "system_efficiency",
                            "threshold_efficiency": t.get("eta_h2_fuel", t.get("system_efficiency")),
                            "threshold_delta_pp": t[key], "threshold_full_cracking_equivalent_delta_pp": t.get("delta_full_cracking_equivalent_pp"),
                            "system_efficiency_at_threshold": t.get("system_efficiency_at_threshold", t.get("system_efficiency"))})
        ref_t = entry["bases"]["reference"]
        key = "delta_fuel_pp_vs_direct_turbine" if (ref_t and "eta_h2_fuel" in ref_t) else "delta_system_pp_vs_direct"
        vals = [b[key] for b in entry["bases"].values() if b]
        entry["threshold_delta_pp_reference"] = ref_t[key] if ref_t else None
        entry["threshold_delta_pp_range_over_bases"] = [min(vals), max(vals)] if vals else None
        if kind in ("full_exhaust", "partial_exhaust"):
            # compare the full-cracking-equivalent gain with the full-cracking literature (linear interpolation assumption)
            cmp_ref = ref_t["delta_full_cracking_equivalent_pp"] if ref_t else None
            cmp_all = [b["delta_full_cracking_equivalent_pp"] for b in entry["bases"].values() if b]
            s = sourced[cls]
            entry["compared_quantity"] = "full-cracking-equivalent system gain (pp); for partial cracking this uses the linear interpolation assumption"
            entry["vs_ahmad_like_for_like"] = side(cmp_ref, s["ahmad2025_like_for_like_AmCraX_basis"][0], s["ahmad2025_like_for_like_AmCraX_basis"][2])
            entry["vs_supported_range"] = side(cmp_ref, *s["supported_range"])
            entry["vs_sensitivity_range"] = side(cmp_ref, *s["sensitivity_range"])
            entry["vs_supported_range_all_bases"] = sorted({side(v, *s["supported_range"]) for v in cmp_all})
            entry["threshold_full_equiv_pp_reference"] = cmp_ref
            entry["threshold_full_equiv_pp_range_over_bases"] = [min(cmp_all), max(cmp_all)] if cmp_all else None
        elif cls == "fired_H2N2_fuel_delta_pp":
            entry["vs_sourced"] = "nothing sourced for a standalone fired cracker's turbine: threshold is the finding"
            entry["vs_indirect_bracket"] = side(entry["threshold_delta_pp_reference"], *sourced[cls]["indirect_bracket"])
        else:
            s = sourced[cls]
            entry["vs_netl_upper_bound_absolute"] = side(entry["threshold_delta_pp_reference"], -1e9, s["netl_absolute"])
            entry["vs_netl_upper_bound_relative"] = side(entry["threshold_delta_pp_reference"], -1e9, s["netl_relative_on_AmCraX_turbine"])
            entry["vs_netl_all_bases"] = sorted({side(v, -1e9, s["netl_absolute"]) for v in vals})
        th_json[k] = entry
    write_csv(OUT / "turbine_threshold.csv", th_rows)

    # ---------------- 2b. cracker-heat fuel efficiency (review C, finding M1) ----------------
    # The reference pathways burn the extra NH3 for cracker heat at 100 % of its LHV (optimistic, favourable to
    # cracking). Recompute the reference-basis thresholds with the heat delivered at the flowsheet's own tail-gas ratio
    # and at the H3 furnace efficiency. Defaults are not changed.
    bl = json.loads((ROOT / "results/research/reference_scenario/baseline.json").read_text(encoding="utf-8"))
    fe_eta_flow = round(bl["fuel_efficiency_sensitivity"]["flowsheet_tailgas_ratio_exact"], 4)
    fe_rows = []
    for eta_h in (1.0, fe_eta_flow, 0.85):
        row_ = {"heat_fuel_efficiency": eta_h}
        for k_ in ("full_fired", "full_purified"):
            a1 = power_activity(k_, heat_fuel_efficiency=eta_h)
            fn_ = lambda e_: cost(power_activity(k_, eta_h2_fuel=e_, heat_fuel_efficiency=eta_h)) - D
            e_ = brentq(fn_, 0.2, 0.99, xtol=1e-12)
            row_[k_] = {"LCOE_USD_per_MWh": cost(a1), "system_efficiency": a1.efficiency,
                        "threshold_eta_h2_fuel": e_, "threshold_delta_fuel_pp_vs_direct_turbine": (e_ - ETA0) * 100}
        fe_rows.append(row_)
    assert abs(fe_rows[0]["full_fired"]["threshold_delta_fuel_pp_vs_direct_turbine"] - th_json["full_fired"]["threshold_delta_pp_reference"]) < 1e-6
    fuel_eff = {
        "description": "Computed. Reference-basis turbine-efficiency thresholds (grey 450 USD/t, 8000 h, reference cracker CAPEX) "
                       "with the extra NH3 for cracker heat delivered at 100 % of its LHV (reference, optimistic), at the stored "
                       "flowsheet's tail-gas ratio and at the 0.85 H3 furnace efficiency. Direct NH3 is unaffected (no cracker heat). "
                       "The reference outputs above are at 1.0 and are not changed.",
        "cases": fe_rows,
        "fired_threshold_shift_pp": {str(r_["heat_fuel_efficiency"]): r_["full_fired"]["threshold_delta_fuel_pp_vs_direct_turbine"]
                                     - fe_rows[0]["full_fired"]["threshold_delta_fuel_pp_vs_direct_turbine"] for r_ in fe_rows},
        "purified_threshold_shift_pp": {str(r_["heat_fuel_efficiency"]): r_["full_purified"]["threshold_delta_fuel_pp_vs_direct_turbine"]
                                        - fe_rows[0]["full_purified"]["threshold_delta_fuel_pp_vs_direct_turbine"] for r_ in fe_rows},
        "source_type": "python"}

    # ---------------- 3. sensitivities ----------------
    def row_all(extra, **kw):
        """LCOE of every pathway + direct-minus-cracking (negative = direct cheaper)."""
        r = dict(extra)
        d = direct_lcoe(kw.get("price", PRICE), kw.get("hours", HOURS), **kw.get("dkw", {}))
        r["direct"] = d
        for k_, y_ in CRK:
            a = act(k_, y_, eta=kw.get("eta"), g=kw.get("g", 1.0), case=kw.get("case", "baseline"))
            v = cost(a, kw.get("price", PRICE), kw.get("hours", HOURS), kw.get("basis", "reference"), **kw.get("ckw", {}))
            r[tag(k_, y_)] = v
            r[f"direct_minus_{tag(k_, y_)}"] = d - v
        return r

    s_eta = [row_all({"delta_fuel_pp": dpp, "eta_h2_fuel": ETA0 + dpp / 100, "note": "eta applies to fired, purified and blend kinds; exhaust kinds at Ahmad central"}, eta=ETA0 + dpp / 100)
             for dpp in np.arange(-4.0, 12.01, 0.5)]
    write_csv(OUT / "sensitivity_turbine_efficiency.csv", s_eta)
    s_gain = [row_all({"delta_system_full_pp": dpp, "gain_scale": dpp / (DSYS_AHMAD * 100), "note": "gain applies to exhaust kinds; fired/purified at eta 49.64 %"}, g=dpp / (DSYS_AHMAD * 100))
              for dpp in np.arange(0.0, 6.01, 0.25)]
    write_csv(OUT / "sensitivity_heat_integration_exhaust.csv", s_gain)
    s_case = []
    for case, lab in (("baseline", "stored Aspen baseline (600 C, FEHE on)"), ("baseline_no_hi", "stored Aspen baseline, heat integration off"),
                      ("scn_low_temperature", "stored Aspen low-temperature scenario"), ("scn_high_temperature", "stored Aspen high-temperature scenario")):
        try:
            c_ = load_cracker(case)
            s_case.append(row_all({"case": case, "label": lab, "crack_heat_MJ_per_kg_NH3": c_.crack_heat_MJ_per_kg_nh3, "deficit_MJ_per_kg_NH3": c_.deficit_MJ_per_kg_nh3, "conversion": c_.conversion}, case=case))
        except Exception as exc:  # noqa: BLE001
            s_case.append({"case": case, "label": lab, "error": str(exc)})
    write_csv(OUT / "sensitivity_heat_integration_fired_cases.csv", s_case)
    s_price = [row_all({"NH3_USD_t": p_}, price=p_) for p_ in np.arange(200.0, 1101.0, 50.0)]
    write_csv(OUT / "sensitivity_nh3_price.csv", s_price)
    s_cf = [row_all({"hours": h_, "capacity_factor": h_ / 8760.0}, hours=h_) for h_ in (1000, 2000, 3000, 4000, 5000, 6000, 7000, 7200, 8000, 8760)]
    write_csv(OUT / "sensitivity_capacity_factor.csv", s_cf)
    ab = next(e for e in LIT_C["entries"] if e["id"] == "abuzayed_capex_uplift")["value"]
    h2_vs_nh3 = (1 + ab["hydrogen_cofiring_percent"] / 100) / (1 + ab["ammonia_percent"] / 100)
    scr_lo, scr_hi, scr_adv = 15 * USD_PER_EUR, 36 * USD_PER_EUR, 60 * USD_PER_EUR
    cap_specs = [("reference", {}, {}, "reference")]
    for fct in (0.5, 0.75, 1.5, 2.0, 3.0):
        cap_specs.append((f"cracker capex x{fct}", {"cracker_capex_factor": fct}, {}, "reference"))
    cap_specs += [
        ("cracker capex: Ahmad Fig. 6 correlation", {}, {}, "ahmad_fig6_correlation"),
        ("cracker capex: reference incl. PSA/adsorber items for unpurified", {}, {}, "reference_with_psa_items"),
        (f"plant capex: Abuzayed 2025 H2 vs NH3 uplift ratio {h2_vs_nh3:.4f} on cracking plants (assumption-grade source)", {"plant_capex_factor": h2_vs_nh3}, {}, "reference"),
        ("plant capex: NETL 2024 AFCC +12 % on direct, Abuzayed +7.98 % on cracking plants (mixed sources; Ahmad base read as NGCC-like)", {"plant_capex_factor": 1 + ab["hydrogen_cofiring_percent"] / 100}, {"plant_capex_factor": 1.12}, "reference"),
        ("plant capex: NETL 2024 AFCC +16 % on direct, Abuzayed +7.98 % on cracking plants (mixed sources)", {"plant_capex_factor": 1 + ab["hydrogen_cofiring_percent"] / 100}, {"plant_capex_factor": 1.16}, "reference"),
        (f"SCR standard 15 EUR/kW on all ({scr_lo:.1f} USD/kW at {USD_PER_EUR} USD/EUR; price year not stated)", {"extra_capex_USD_per_kW": scr_lo}, {"extra_capex_USD_per_kW": scr_lo}, "reference"),
        (f"SCR standard 36 EUR/kW on all ({scr_hi:.1f} USD/kW)", {"extra_capex_USD_per_kW": scr_hi}, {"extra_capex_USD_per_kW": scr_hi}, "reference"),
        ("SCR 36 + advanced 60 EUR/kW on direct only, 36 on cracking (worst case for direct; allocation not sourced)", {"extra_capex_USD_per_kW": scr_hi}, {"extra_capex_USD_per_kW": scr_hi + scr_adv}, "reference"),
        ("SCR 36 + advanced 60 EUR/kW on all", {"extra_capex_USD_per_kW": scr_hi + scr_adv}, {"extra_capex_USD_per_kW": scr_hi + scr_adv}, "reference"),
    ]
    s_cap = [row_all({"scenario": nm}, basis=cb, ckw=ck, dkw=dk) for nm, ck, dk, cb in cap_specs]
    write_csv(OUT / "sensitivity_capital.csv", s_cap)

    # ---------------- two-way map ----------------
    dps = np.arange(-2.0, 12.01, 0.5)
    dsys = np.arange(0.0, 6.01, 0.25)
    fcts = np.array([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0])
    grid = []
    for fct in fcts:
        d = direct_lcoe()
        for dpp in dps:
            v = {k_: cost(act(k_, None, eta=ETA0 + dpp / 100), cracker_capex_factor=fct) for k_ in ("full_fired", "full_purified")}
            v["direct"] = d
            grid.append({"panel": "A_fuel_efficiency", "cracker_capex_factor": fct, "delta_pp": dpp, **v, "cheapest": min(v, key=v.get)})
        for dpp in dsys:
            g = dpp / (DSYS_AHMAD * 100)
            v = {"full_exhaust": cost(act("full_exhaust", g=g), cracker_capex_factor=fct),
                 "partial_exhaust_40": cost(act("partial_exhaust", 0.4, g=g), cracker_capex_factor=fct), "direct": d}
            grid.append({"panel": "B_exhaust_system_gain", "cracker_capex_factor": fct, "delta_pp": dpp, **v, "cheapest": min(v, key=v.get)})
    write_csv(OUT / "twoway_map_efficiency_capital.csv", grid)
    # break-even line of panel B (full exhaust vs direct) per capex factor
    beB = []
    for fct in fcts:
        try:
            g = brentq(lambda g_: cost(act("full_exhaust", g=g_), cracker_capex_factor=fct) - direct_lcoe(), -3, 8)
            beB.append({"cracker_capex_factor": fct, "full_exhaust_threshold_delta_system_pp": g * DSYS_AHMAD * 100})
        except ValueError:
            beB.append({"cracker_capex_factor": fct, "full_exhaust_threshold_delta_system_pp": None})
    beA = []
    for fct in fcts:
        rr_ = {"cracker_capex_factor": fct}
        for k_ in ("full_fired", "full_purified"):
            try:
                e = brentq(lambda e_: cost(act(k_, eta=e_), cracker_capex_factor=fct) - direct_lcoe(), 0.2, 0.99)
                rr_[f"{k_}_threshold_delta_fuel_pp"] = (e - ETA0) * 100
            except ValueError:
                rr_[f"{k_}_threshold_delta_fuel_pp"] = None
        beA.append(rr_)
    # capex factor at which full exhaust (Ahmad gain) equals direct
    try:
        fct_be = brentq(lambda f_: cost(act("full_exhaust"), cracker_capex_factor=f_) - D, 0.01, 50)
    except ValueError:
        fct_be = None

    # ---------------- 4. blends, partial cracking, NOx, N2O ----------------
    nn = lca.n2o_noX_per_MWh()
    n2o_kg = nn["N2O_kg_per_MWh"]
    emis = {
        "provenance": prov("Ahmad 2025 Chemkin ppmv via amcrax.environmental.lca.n2o_noX_per_MWh; Carbon Pricing Act First Schedule GWP"),
        "direct_NH3": {"N2O_kg_per_MWh": n2o_kg, "N2O_kgCO2e_per_MWh_AR6_273_lifecycle": n2o_kg * lca.f("gwp100_n2o"),
                       "N2O_kgCO2e_per_MWh_CPA_265_tax": n2o_kg * P.GWP_N2O_SG_CARBON_PRICING_ACT,
                       "carbon_tax_SGD_per_MWh_at_CPA_265": n2o_kg * P.GWP_N2O_SG_CARBON_PRICING_ACT / 1000 * TAX_SGD,
                       "carbon_tax_USD_per_MWh_at_CPA_265": n2o_kg * P.GWP_N2O_SG_CARBON_PRICING_ACT / 1000 * TAX_SGD / FX,
                       "carbon_tax_rate_SGD_per_t": TAX_SGD,
                       "NO_kg_per_MWh": nn["NO_kg_per_MWh"],
                       "source": "Ahmad 2025 Chemkin reactor network (simulated): N2O 0.15 ppmv (vaporised NH3), NO 83.8-116 ppmv; the paper says Chemkin underestimates NO and cites AIST tests at 282 and 337 ppmv; exhaust-basis conversion is an AmCraX assumption",
                       "gwp_note": "Singapore carbon tax: GWP 265 (Carbon Pricing Act 2018, First Schedule). Life-cycle intensity: AR6 273 (lca.py). Both reported; the tax is negligible either way."},
        "blends_and_cracked_gas": {
            "N2O": "No source gives N2O for NH3-H2 blends or for cracked gas. pathway_table_power.csv scales the direct-NH3 N2O by the NH3 energy share of the fuel: this is an AmCraX assumption, not a sourced value.",
            "NOx": "No turbine NOx measurement or simulation for NH3-H2 blends or H2/N2 cracked gas was found (NO_kg_per_MWh = 'not quantified'). GE Vernova (vendor): NOx up to +35 % at 50 vol% H2 in natural gas, possibly double near 100 % H2; NETL 2023: N2-diluted H2 has higher NOx potential than steam-diluted. Qualitative only; not used in costs.",
            "blend_limits": "The essay's '30-60 vol% H2 for the H-25 in NH3-H2 blends' is printed in Halim et al. 2025 p. 3 (full text read 24 Nov 2026), relayed from a trade-press article: a vendor-claim grade statement, not tested in that paper. NETL 2022 states 30-60 % hydrogen for Baker Hughes turbines on hydrogen in natural gas (a different fuel); Ahmad 2025 p. 2 gives about 30 vol% for unmodified natural-gas combustors. No measured or simulated H2 limit for NH3-H2 blends exists in the library; the vol% labels in the tables are flags only.",
            "partial_cracking_efficiency": "Only Ahmad's two end points are sourced (alpha = 1 and 0). Intermediate efficiencies are a linear interpolation (assumption). Ahmad reports LCOE non-monotonic in the cracked fraction (not reproduced, Supplementary Material not available)."},
        "SCR": {"standard_EUR_per_kW": [15, 36], "advanced_additional_EUR_per_kW": 60, "USD_per_EUR": USD_PER_EUR,
                "source": "Abuzayed et al. 2025 (EPRG2520) citing their ref. 109 (secondary quote, price year not stated)",
                "use_here": "capital sensitivity only (sensitivity_capital.csv); which pathway needs the advanced SCR is not sourced; SCR reagent (NH3) demand not quantified in any source read; whether Ahmad's Case 2a TCI already includes SCR is not stated in the project note"},
    }
    dump(OUT / "nox_n2o_blends.json", emis)

    # ---------------- 5. the 40 % figure ----------------
    gaps = [c_["direct_cheaper_by_pct_of_cracking(1-d/c)"] for c_ in halim]
    def fct_for(kind, target):
        try:
            return brentq(lambda f_: 1 - D / cost(act(kind), cracker_capex_factor=f_) - target, 0.0, 200.0)
        except ValueError:
            return None
    forty = {
        "claim": "direct NH3 combustion about 40 % cheaper than cracking-based power (essay, attributed to Halim et al. 2025)",
        "computed_gaps_pct_1_minus_d_over_c": {f"{c_['basis']} | {c_['cracking_pathway']}": c_["direct_cheaper_by_pct_of_cracking(1-d/c)"] for c_ in halim},
        "largest_computed_pct": max(gaps), "smallest_computed_pct": min(gaps),
        "largest_in_sensitivities_pct": None,
        "cracker_capex_factor_for_40pct_fired": fct_for("full_fired", 0.40),
        "cracker_capex_factor_for_40pct_purified": fct_for("full_purified", 0.40),
        "halim_status": ("Full text read on 24 November 2026 (research/notes/halim2025_full_text.md; research/data/halim2025_extract.json). "
                         "All four quoted numbers are located: 60.1 MW (p. 3, p. 11; vendor rating of the Mitsubishi H-25); LCOH 15.1 and "
                         "10.1 USD/kg (Highlights, p. 9, Fig. 5, Table 5); 'about 40 %' (Highlights; 39 % green and 44 % blue on p. 9), which "
                         "is 1 - LCOA/LCOH, the cost of fuel delivered to the turbine per kg of hydrogen-equivalent energy for the 40 % "
                         "hydrogen share, with equal turbine efficiency and the power plant excluded, NOT a cost of electricity (the paper "
                         "computes no LCOE); and 30-60 vol% H2 for the H-25 (p. 3, relayed from trade press). The same quantity on AmCraX "
                         "boundaries is in fuel_cost_gap_on_paper_basis; the LCOE gaps above test the essay's sentence about power."),
        "halim_status_superseded_2026_11_23": "Full text not accessible (A*STAR repository: request a copy; abstract read; DOI resolves). The abstract supports only the direction (direct use preferable because cracking has high capital and operating cost). 40 %, 60.1 MW, LCOH 15.1 / 10.1 USD/kg and the 30-60 vol% H-25 range are not in the abstract and could not be located. No location can be given for any of them.",
        "fuel_cost_gap_on_paper_basis": fuel_cost_gap_on_paper_basis(),
    }
    sens_all = [r_ for tbl in (s_eta, s_gain, s_price, s_cf, s_cap) for r_ in tbl]
    forty["largest_in_sensitivities_pct"] = max(100 * (1 - r_["direct"] / r_[k_]) for r_ in sens_all for k_ in ("full_fired", "full_purified", "full_exhaust"))

    # ---------------- 6. H1-d evidence ----------------
    be = json.loads((ROOT / "results/research/singapore/breakeven_ammonia_price.json").read_text(encoding="utf-8"))["results"]["heat_integration_on"]
    h2c = {lab: hydrogen_cost("baseline", p_)["USD_per_kg"] for lab, p_ in P.NH3_PRICE_SET_USD_T.items()}
    hci = {r_: pw.carbon_intensity(hydrogen_activity("baseline", "h", "", ""), lca.route_spec(r_).ef, 5000.0)["total"] for r_ in ("green", "blue", "grey")}
    bench = {k_: {"USD_per_kg": v["h2_price_USD_per_kg"], "breakeven_NH3_USD_t": v["breakeven_nh3_USD_per_t"], "source": v["source"]} for k_, v in be.items()}
    kd = P.ELEC_MJ_PER_KG_DIRECT / 3.6
    kc_netl_abs = power_activity("full_purified", eta_h2_fuel=ETA0 + 0.073).efficiency * P.LHV_NH3_MJ_KG / 3.6
    kc_netl_rel = power_activity("full_purified", eta_h2_fuel=ETA0 * 66.9 / 59.6).efficiency * P.LHV_NH3_MJ_KG / 3.6
    h1d = {
        "efficiency_NH3_LHV_to_H2_aspen": pw.load_result("baseline").kpis.lhv_efficiency,
        "H2_cost_USD_per_kg_by_NH3_scenario": h2c, "H2_cost_SGD_per_kg_grey": h2c["grey"] * FX,
        "H2_CI_kgCO2e_per_kg_5000km": hci,
        "benchmarks_USD_per_kg": bench,
        "electricity_kWh_per_kg_NH3": {"direct": kd, "cracked_purified_at_eta_copy": power_activity("full_purified").efficiency * P.LHV_NH3_MJ_KG / 3.6,
                                       "cracked_purified_at_NETL_plus_7p3pp_absolute": kc_netl_abs, "cracked_purified_at_NETL_ratio_1p1225": kc_netl_rel},
        "evidence_beyond_definition": [
            f"Cost against alternatives: grey-NH3 cracked H2 {h2c['grey']:.3f} USD/kg ({h2c['grey']*FX:.3f} SGD/kg) is ABOVE the NE Asia SMR cost marker 3.06 (Argus, read from PDF) and the Singapore willingness to pay about 3.0 (S&P, search summary); break-even NH3 320 and 312 USD/t.",
            f"Green NH3 2030 ({P.NH3_PRICE_SET_USD_T['green_2030']:g} USD/t) gives {h2c['green_2030']:.2f} USD/kg, below the blue delivered East Asia midpoint 6.0 (ACE, search summary) and the 10 USD/kg low-carbon offer FOB Malaysia (S&P, search summary); green today ({P.NH3_PRICE_SET_USD_T['green_current']:g}) gives {h2c['green_current']:.2f}, above 6.0 and below 10.",
            f"Carbon intensity: green-NH3 H2 {hci['green']:.1f} kg CO2e/kg against SMR 10-12; blue {hci['blue']:.1f}; grey {hci['grey']:.1f} (lca workstream).",
            f"Energy: cracker + PSA keeps {pw.load_result('baseline').kpis.lhv_efficiency*100:.1f} % of NH3 LHV as H2 (stored Aspen). Not like-for-like with an electrical efficiency.",
        ],
        "what_does_not_exist": [
            "No Singapore hydrogen transaction price; three of four benchmarks are search-summary grade and differ in basis (production cost, willingness to pay, delivered, FOB).",
            "No AmCraX comparison with other H2 import carriers (liquid H2, LOHC) or with local electrolysis.",
            "No end-user (refinery, fuel-cell) cost or value of H2 purity in Singapore; Grade D cost is a lower bound (purification workstream).",
            "The 'loss is larger when H2 is an intermediate fuel' half: with the NETL +7.3 pp upper bound applied absolutely, the cracked + PSA route gives slightly MORE electricity per kg NH3 than direct; applied as a ratio it gives less. The energy ranking is not established independently of the turbine assumption.",
        ],
    }

    # ---------------- row evidence ----------------
    tf, tp, te = th_json["full_fired"], th_json["full_purified"], th_json["full_exhaust"]
    rng = lambda r_: f"{r_[0]:.2f} to {r_[1]:.2f}"
    row_evidence = {
        "H1-a": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"LCOE_direct": D, "LCOE_full_fired": base["full_fired"], "LCOE_full_purified": base["full_purified"],
                        "direct_cheaper_pct_fired": adv["full_fired"]["direct_cheaper_pct_of_cracking_1_minus_d_over_c"],
                        "direct_cheaper_pct_purified": adv["full_purified"]["direct_cheaper_pct_of_cracking_1_minus_d_over_c"],
                        "threshold_delta_fuel_pp_fired": tf["threshold_delta_pp_reference"], "threshold_delta_fuel_pp_purified": tp["threshold_delta_pp_reference"]},
            "assumptions": "eta_h2_fuel = 49.64 % (copy of direct) for fired and purified; fired cracker heat from NH3 at 100 % transfer efficiency; Cho-itemised cracker capex extrapolated about 30-fold; Ahmad plant capital scaled ^0.67; 8000 h (not sourced).",
            "uncertainty": f"fired threshold over bases {rng(tf['threshold_delta_pp_range_over_bases'])} pp; purified {rng(tp['threshold_delta_pp_range_over_bases'])} pp",
            "envelope": "AmCraX boundary, grey 450 USD/t (300-1000 checked), 5000-8000 h, capex x0.5-x2 and Ahmad correlation.",
            "threshold": {"fired": tf["threshold_delta_pp_reference"], "purified": tp["threshold_delta_pp_reference"],
                          "fired_vs_sources": tf["vs_sourced"] + "; indirect bracket: " + tf["vs_indirect_bracket"],
                          "purified_vs_sources": tp["vs_netl_upper_bound_absolute"] + " (NETL absolute); " + tp["vs_netl_upper_bound_relative"] + " (NETL ratio); all bases: " + "; ".join(tp["vs_netl_all_bases"])},
            "reason": "The purified sub-pathway passes the threshold test (the only sourced H2-turbine gain, an upper bound, lies below the threshold on every basis checked), but the fired sub-pathway has no sourced turbine efficiency and its threshold lies inside the indirect bracket. The row claims both, so it stays INCONCLUSIVE; the purified half alone would be SUPPORTED inside the stated envelope.",
        },
        "H1-b": {
            "proposed_verdict": "CONTRADICTED (secondary, does not vote)",
            "numbers": {"claim_pct": 40.0, "largest_computed_pct_stored_bases": max(gaps), "largest_in_all_sensitivities_pct": forty["largest_in_sensitivities_pct"],
                        "cracker_capex_factor_needed_for_40pct_purified": forty["cracker_capex_factor_for_40pct_purified"],
                        "cracker_capex_factor_needed_for_40pct_fired": forty["cracker_capex_factor_for_40pct_fired"]},
            "assumptions": "as H1-a; three price/hour bases",
            "uncertainty": ("The paper (full text read 24 Nov 2026) computes no cost of electricity: its 'about 40 %' is a fuel cost at the turbine "
                            "inlet (1 - LCOA/LCOH, 39 % green, 44 % blue). On that basis AmCraX gives "
                            + ", ".join(f"{c_['gap_pct_1_minus_direct_over_cracked']:.1f} % ({c_['price_case']}, HI {c_['heat_integration']})"
                                        for c_ in forty["fuel_cost_gap_on_paper_basis"]["cases"] if c_["price_case"].startswith("halim"))
                            + " (fuel_cost_gap_on_paper_basis)"),
            "envelope": "AmCraX boundaries; does not show Halim's own calculation is wrong",
            "threshold": "existing rule: CONTRADICTED if the largest computed gap is below half the claim (20 %)",
            "reason": ("Largest computed LCOE gap is below 20 % on every stored basis; reaching 40 % needs a cracker capital several times the "
                       "reference (see numbers). The row tests the essay's sentence about power; the paper's own 40 % is a different quantity "
                       "(fuel cost per kg of hydrogen-equivalent energy, located on p. 9), compared like for like in "
                       "forty_percent_figure/fuel_cost_gap_on_paper_basis."),
        },
        "H1-c": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"LCOE_full_exhaust": base["full_exhaust"], "LCOE_partial_exhaust_40": base["partial_exhaust_40"], "LCOE_partial_fired_40": base["partial_fired_40"], "LCOE_direct": D,
                        "threshold_delta_system_pp_full_exhaust": te["threshold_delta_pp_reference"],
                        "threshold_full_equiv_pp_partial": {y_: th_json[f"partial_exhaust_{int(y_*100)}"]["threshold_full_equiv_pp_reference"] for y_ in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)},
                        "ahmad_gain_AmCraX_basis_pp": DSYS_AHMAD * 100, "capex_factor_where_full_exhaust_equals_direct": fct_be},
            "assumptions": "Ahmad system end points (54 % 'about'), linear interpolation for partial cracking, reference cracker capex, 8000 h",
            "uncertainty": f"full-exhaust threshold over bases {rng(te['threshold_delta_pp_range_over_bases'])} pp",
            "envelope": "small or mid-size machines (Ahmad 43 MW class, PR 8); no F/H-class source",
            "threshold": {"full_exhaust_reference": te["threshold_delta_pp_reference"], "vs_ahmad": te["vs_ahmad_like_for_like"],
                          "vs_supported_range": te["vs_supported_range"], "vs_supported_range_all_bases": te["vs_supported_range_all_bases"],
                          "vs_sensitivity_range": te["vs_sensitivity_range"]},
            "reason": "The row says cracking in front of a turbine does not pay. The full-exhaust threshold lies below the like-for-like sourced gains on the reference basis, so on the reference basis the sourced values favour CRACKING (against the row and the essay), but by about 1 % of LCOE, the threshold moves across the supported range when the cracker capex basis or NH3 price changes, and the sensitivity range (0 to 5.5 pp) straddles it. Neither side is clear: INCONCLUSIVE, with the threshold as the finding. Fired partial cracking is dearer than direct at the copy efficiency, but that again follows from the assumption (see partial_fired thresholds).",
        },
        "H1-d": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"eta_H2_product": h1d["efficiency_NH3_LHV_to_H2_aspen"], "LCOH_grey_USD": h2c["grey"], "LCOH_grey_SGD": h2c["grey"] * FX,
                        "LCOH_green_2030": h2c["green_2030"], "LCOH_green_current": h2c["green_current"], "benchmarks": {k_: v["USD_per_kg"] for k_, v in bench.items()},
                        "kWh_per_kg_NH3": h1d["electricity_kWh_per_kg_NH3"]},
            "assumptions": "stored Aspen PSA split; reference capex; benchmarks of mixed basis and grade",
            "uncertainty": "benchmarks 3.0-10 USD/kg straddle the computed LCOH range 4.0-8.1",
            "envelope": "Jurong Island cracker, plant-gate 19.5 bar H2",
            "threshold": {"breakeven_NH3_vs_SMR_3p06": bench["ne_asia_smr_production_cost"]["breakeven_NH3_USD_t"], "breakeven_NH3_vs_WTP_3p0": bench["sg_low_carbon_willingness_to_pay"]["breakeven_NH3_USD_t"],
                          "breakeven_NH3_vs_blue_delivered_6": bench["blue_delivered_east_asia"]["breakeven_NH3_USD_t"], "breakeven_NH3_vs_offer_10": bench["low_carbon_offer_fob_malaysia"]["breakeven_NH3_USD_t"]},
            "reason": "Beyond the definition (H2 is the product, so some conversion is unavoidable) the evidence is a cost comparison against benchmarks that straddle the computed LCOH: cracked grey-NH3 H2 is dearer than NE Asia SMR H2 and the Singapore willingness to pay, cheaper than delivered low-carbon offers. The energy half depends on the turbine assumption (NETL bound applied absolutely reverses it). INCONCLUSIVE.",
        },
    }

    out = {
        "provenance": prov("stored Aspen baseline cracker; Ahmad 2025 turbine end points; reference scenario costs; literature ranges from research/data"),
        "what_each_pathway_assumes": assumes,
        "statement_of_result": statement,
        "sourced_values": sourced,
        "thresholds": th_json,
        "cracker_heat_fuel_efficiency_sensitivity": fuel_eff,
        "threshold_bases": {b[0]: {"NH3_USD_t": b[1], "hours": b[2], "capex_basis": b[3]} for b in bases},
        "twoway_map": {"file": "results/research/enduse/twoway_map_efficiency_capital.csv", "panelA_thresholds_by_capex": beA, "panelB_thresholds_by_capex": beB,
                       "cracker_capex_factor_where_full_exhaust_equals_direct_at_ahmad_gain": fct_be},
        "forty_percent_figure": forty,
        "h1d_evidence": h1d,
        "row_evidence": row_evidence,
        "files": ["turbine_threshold.csv", "sensitivity_turbine_efficiency.csv", "sensitivity_heat_integration_exhaust.csv", "sensitivity_heat_integration_fired_cases.csv",
                  "sensitivity_nh3_price.csv", "sensitivity_capacity_factor.csv", "sensitivity_capital.csv", "twoway_map_efficiency_capital.csv", "nox_n2o_blends.json"],
        "notes": ["Capacity factor: no sourced base value (NETL sensitivity starts at 10 %); 8000 h is the reference-scenario choice.",
                  "Thresholds do not change any default; defaults reproduce the stored pathway table (validation EU-P2-defaults)."],
    }
    dump(OUT / "turbine_threshold.json", out)

    # ---------------- validation ----------------
    items = [i for i in json.loads(VAL.read_text(encoding="utf-8")) if not i["id"].startswith("EU-P2-")]
    sf = ["backend/amcrax/enduse/pathways.py", "results/research/enduse/turbine_threshold.json"]

    def add(id_, desc, obs, exp, tol, unit, ok, kind="numerical_verification", ref="internal"):
        items.append({"id": id_, "description": desc, "method": "recomputation in scripts/research/enduse_threshold.py", "reference_source": ref,
                      "observed": obs, "expected": exp, "tolerance": tol, "unit": unit, "status": "pass" if ok else "fail",
                      "source_files": sf, "evidence_kind": kind})
    for k, y in ALL:
        st = stored[tag(k, y)]["cost_USD_per_MWh_at_450"]
        add(f"EU-P2-defaults-{tag(k, y)}", f"Default LCOE of {tag(k, y)} unchanged by the new optional arguments", base[tag(k, y)], st, 1e-9 * st, "USD/MWh", abs(base[tag(k, y)] - st) <= 1e-9 * st)
    for k, e in th_json.items():
        t = e["bases"]["reference"]
        if t:
            add(f"EU-P2-threshold-{k}", f"LCOE of {k} at its threshold equals direct NH3", t["LCOE_check"], t["LCOE_direct"], 1e-6, "USD/MWh", abs(t["LCOE_check"] - t["LCOE_direct"]) < 1e-6)
    e_fe = [power_activity("full_exhaust", eta_h2_fuel=v).efficiency for v in (0.4, 0.6)]
    add("EU-P2-no-double-count", "Exhaust-heated electricity per kg NH3 equals Ahmad's 0.54 x 18.8 MJ/kg and does not depend on eta_h2_fuel",
        [x_ * P.LHV_NH3_MJ_KG for x_ in e_fe], [0.54 * 18.8, 0.54 * 18.8], 1e-9, "MJ/kg NH3", all(abs(x_ * P.LHV_NH3_MJ_KG - 0.54 * 18.8) < 1e-9 for x_ in e_fe))
    add("EU-P2-eta-default", "eta_h2_fuel = ETA_GT_GAS reproduces the default fired efficiency", power_activity("full_fired", eta_h2_fuel=ETA0).efficiency,
        power_activity("full_fired").efficiency, 1e-12, "-", abs(power_activity("full_fired", eta_h2_fuel=ETA0).efficiency - power_activity("full_fired").efficiency) < 1e-12)
    lc_ref = json.loads((ROOT / "results/research/reference_scenario/baseline.json").read_text(encoding="utf-8"))["lcoh_USD_per_kg"]
    add("EU-P2-frozen-lcoh", "singapore.evaluate default LCOH unchanged (frozen 4.015 USD/kg)", h2c["grey"], lc_ref, 1e-6 * lc_ref, "USD/kg H2", abs(h2c["grey"] - lc_ref) <= 1e-6 * lc_ref)
    add("EU-P2-ahmad-gain", "Ahmad system gain on the AmCraX LHV basis equals (0.54 - 0.4912) x 18.8 / 18.6", DSYS_AHMAD * 100, (0.54 - 0.4912) * 18.8 / P.LHV_NH3_MJ_KG * 100, 1e-9, "pp", abs(DSYS_AHMAD * 100 - (0.54 - 0.4912) * 18.8 / P.LHV_NH3_MJ_KG * 100) < 1e-9)
    add("EU-P2-threshold-vs-literature", "Full exhaust-heated threshold system gain against the like-for-like literature gain (Ahmad 2025, 4.4-5.4 pp on LHV 18.8)",
        te["threshold_delta_pp_reference"], [ahm_lo, ahm_hi], None, "pp", True, kind="literature_comparison", ref="research/data/turbine_efficiency_literature.json")
    items[-1]["status"] = "informational"
    fb = forty["fuel_cost_gap_on_paper_basis"]
    gh = {c_["price_case"]: c_["gap_pct_1_minus_direct_over_cracked"] for c_ in fb["cases"] if c_["heat_integration"] == "on"}
    add("EU-P2-halim-fuel-basis", "Halim et al. 2025 'about 40 %' on the paper's own basis (1 - direct NH3 fuel cost / cracked H2 cost per kg "
        "of hydrogen-equivalent energy; not a cost of electricity): AmCraX unified model at the paper's green and blue NH3 prices, heat "
        "integration on, against the paper's 39 % and 44 %", [gh["halim_green_FOB"], gh["halim_blue_FOB"]],
        [fb["paper_values"]["green"]["gap_pct_printed"], fb["paper_values"]["blue"]["gap_pct_printed"]], None, "%", True,
        kind="literature_comparison", ref="research/data/halim2025_extract.json (p. 9; Table 4; Fig. 5)")
    items[-1]["status"] = "informational"
    items[-1]["note"] = ("same direction, smaller gap; reconciliation by sequential substitution of the paper's quantities in "
                         "forty_percent_figure/fuel_cost_gap_on_paper_basis/reconciliation. Different boundaries (no ammonia storage in "
                         "AmCraX; fired furnace and 25,000 t tank in the paper); not a validation")
    rr = [fb["reconciliation"][k]["steps"][-1]["gap_pct"] for k in ("green", "blue")]
    pp = [fb["reconciliation"][k]["paper_gap_pct_printed"] for k in ("green", "blue")]
    add("EU-P2-halim-reconcile", "The reconciliation closes: with the paper's energy retention, hours, life and non-feed costs substituted, "
        "the rebuilt gap equals the paper's printed 39 % and 44 % within 1 point (printed integers; NH3 LHV 18.60 against 18.737)",
        rr, pp, 1.0, "%", all(abs(a_ - b_) <= 1.0 for a_, b_ in zip(rr, pp)))
    add("EU-P2-n2o-gwp", "Carbon-tax N2O uses GWP 265 (Carbon Pricing Act First Schedule); ratio of tax CO2e to life-cycle CO2e = 265/273",
        emis["direct_NH3"]["N2O_kgCO2e_per_MWh_CPA_265_tax"] / emis["direct_NH3"]["N2O_kgCO2e_per_MWh_AR6_273_lifecycle"], 265 / 273, 1e-12, "-",
        abs(emis["direct_NH3"]["N2O_kgCO2e_per_MWh_CPA_265_tax"] / emis["direct_NH3"]["N2O_kgCO2e_per_MWh_AR6_273_lifecycle"] - 265 / 273) < 1e-12)
    dump(VAL, items)

    # ---------------- figures ----------------
    def foot(fig):
        fig.text(0.01, 0.005, "AmCraX H1 end use | cracker: stored Aspen Plus V15 | turbine: literature-calibrated (Ahmad 2025) | costs: Phase 2 reference scenario",
                 fontsize=6.0, color=C_GREY, ha="left", va="bottom")

    def save(fig, name):
        foot(fig)
        fig.savefig(FIG / name, dpi=300, bbox_inches="tight", pad_inches=0.12)
        plt.close(fig)

    cols = {"direct": C_NH3, "partial_exhaust_40": C_PRIMARY, "partial_fired_40": C_N2, "full_exhaust": C_AMBER, "full_fired": C_HEAT, "full_purified": C_H2, "blend_purified_40": C_GREY}
    labs = {"direct": "direct NH3", "partial_exhaust_40": "partial 40 vol% (exhaust)", "partial_fired_40": "partial 40 vol% (fired)", "full_exhaust": "full crack (exhaust)",
            "full_fired": "full crack (fired)", "full_purified": "full crack + PSA", "blend_purified_40": "NH3 + PSA H2 40 vol%"}

    # threshold chart
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.2))
    ax = axs[0]
    ks = ["full_fired"] + [f"partial_fired_{v}" for v in (20, 30, 40, 50, 60, 70)] + ["full_purified", "blend_purified_40"]
    for i, k in enumerate(ks):
        e = th_json[k]
        lo, hi = e["threshold_delta_pp_range_over_bases"]
        ax.plot([lo, hi], [i, i], color=C_GREY, lw=2)
        ax.plot(e["threshold_delta_pp_reference"], i, "o", color=C_HEAT if "fired" in k else C_H2, ms=7)
    ax.axvspan(-1e-9, 7.3, color=C_PRIMARY, alpha=0.06)
    ax.axvline(7.3, color=C_PRIMARY, ls="--", lw=1)
    ax.text(7.4, len(ks) - 0.6, "NETL pure H$_2$ +7.3\n(upper bound)", fontsize=6.5, color=C_PRIMARY, va="top")
    ax.axvline(0, color=C_GREY, lw=0.8)
    ax.set_yticks(range(len(ks)), [k.replace("_", " ") for k in ks], fontsize=7)
    ax.set_xlabel("threshold: H$_2$-rich fuel efficiency minus 49.64 %, pp\n(dot reference; bar range over capex/price/hours bases)")
    ax.set_title("Fired and purified: turbine efficiency gain\nneeded to match direct NH$_3$", fontsize=9)
    ax = axs[1]
    ks2 = ["full_exhaust"] + [f"partial_exhaust_{v}" for v in (20, 30, 40, 50, 60, 70)]
    for i, k in enumerate(ks2):
        e = th_json[k]
        lo, hi = e["threshold_full_equiv_pp_range_over_bases"]
        ax.plot([lo, hi], [i, i], color=C_GREY, lw=2)
        ax.plot(e["threshold_full_equiv_pp_reference"], i, "o", color=C_AMBER, ms=7)
    ax.axvspan(4.9, 5.5, color=C_NH3, alpha=0.15)
    ax.axvline(DSYS_AHMAD * 100, color=C_NH3, ls="--", lw=1)
    ax.text(5.55, 0, "sourced 4.9-5.5\n(Ahmad, Karpilov)", fontsize=6.5, color=C_NH3, va="center")
    ax.set_yticks(range(len(ks2)), [k.replace("_", " ") for k in ks2], fontsize=7)
    ax.set_xlabel("threshold: full-cracking system gain vs direct, pp\n(partial: linear interpolation assumed)")
    ax.set_title("Exhaust-heated: system gain needed\nto match direct NH$_3$", fontsize=9)
    fig.tight_layout()
    save(fig, "enduse_turbine_threshold.png")

    # turbine efficiency + exhaust gain sensitivity
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axs[0]
    xs = [r_["delta_fuel_pp"] for r_ in s_eta]
    for k in ("full_fired", "partial_fired_40", "full_purified", "blend_purified_40"):
        ax.plot(xs, [r_[k] for r_ in s_eta], color=cols[k], label=labs[k])
    ax.axhline(D, color=C_NH3, lw=2, label="direct NH3")
    ax.set_xlabel("H$_2$-rich fuel efficiency minus 49.64 %, pp")
    ax.set_ylabel("USD / MWh at 450 USD/t NH$_3$")
    ax.set_title("Turbine efficiency on H$_2$-rich fuel", fontsize=9)
    ax.legend(fontsize=6.5)
    ax = axs[1]
    xs = [r_["delta_system_full_pp"] for r_ in s_gain]
    for k in ("full_exhaust", "partial_exhaust_40"):
        ax.plot(xs, [r_[k] for r_ in s_gain], color=cols[k], label=labs[k])
    ax.axhline(D, color=C_NH3, lw=2, label="direct NH3")
    ax.axvspan(4.9, 5.5, color=C_NH3, alpha=0.12)
    ax.set_xlabel("exhaust-heat system gain at full cracking, pp")
    ax.set_title("Heat integration (exhaust-heated cracker)", fontsize=9)
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, "enduse_sensitivity_efficiency.png")

    # price and capacity factor (difference)
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    for ax, tbl, xk, xl in ((axs[0], s_price, "NH3_USD_t", "NH$_3$ price, USD/t"), (axs[1], s_cf, "capacity_factor", "capacity factor (8000 h = 0.913)")):
        for k, _ in [(tag(k_, y_), 0) for k_, y_ in CRK]:
            ax.plot([r_[xk] for r_ in tbl], [r_[f"direct_minus_{k}"] for r_ in tbl], color=cols[k], label=labs[k])
        ax.axhline(0, color=C_GREY, lw=0.8)
        ax.set_xlabel(xl)
    axs[0].set_ylabel("direct minus cracking, USD/MWh (<0: direct cheaper)")
    axs[0].legend(fontsize=6.0)
    axs[0].set_title("NH$_3$ price", fontsize=9)
    axs[1].set_title("Capacity factor (no sourced base value)", fontsize=9)
    fig.tight_layout()
    save(fig, "enduse_sensitivity_price_cf.png")

    # capital scenarios
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ks3 = ["full_exhaust", "partial_exhaust_40", "full_fired", "full_purified"]
    yy = np.arange(len(s_cap))
    w = 0.2
    for j, k in enumerate(ks3):
        ax.barh(yy + (j - 1.5) * w, [r_[f"direct_minus_{k}"] for r_ in s_cap], w, color=cols[k], label=labs[k])
    ax.axvline(0, color=C_GREY, lw=0.8)
    ax.set_yticks(yy, [r_["scenario"][:70] for r_ in s_cap], fontsize=5.6)
    ax.invert_yaxis()
    ax.set_xlabel("direct minus cracking, USD/MWh at 450 USD/t (<0: direct cheaper)")
    ax.set_title("Capital-cost sensitivity (cracker capex, sourced plant uplifts, SCR)", fontsize=9)
    ax.legend(fontsize=6.5, loc="lower left")
    save(fig, "enduse_sensitivity_capital.png")

    # two-way map
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 4.2))
    code = {"direct": 0, "full_fired": 1, "full_purified": 2, "full_exhaust": 3, "partial_exhaust_40": 4}
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([C_NH3, C_HEAT, C_H2, C_AMBER, C_PRIMARY])
    for ax, panel, xv, ttl, xl in ((axs[0], "A_fuel_efficiency", dps, "fired / purified vs direct", "H$_2$-rich fuel efficiency minus 49.64 %, pp"),
                                   (axs[1], "B_exhaust_system_gain", dsys, "exhaust-heated vs direct", "exhaust-heat system gain at full cracking, pp")):
        Z = np.array([[code[next(g for g in grid if g["panel"] == panel and g["cracker_capex_factor"] == fct and abs(g["delta_pp"] - dv) < 1e-9)["cheapest"]] for dv in xv] for fct in fcts])
        ax.pcolormesh(xv, np.arange(len(fcts)), Z, cmap=cmap, vmin=-0.5, vmax=4.5, shading="nearest")
        ax.set_yticks(range(len(fcts)), [f"x{v:g}" for v in fcts], fontsize=7)
        ax.set_xlabel(xl)
        ax.set_title(f"Cheapest pathway: {ttl}", fontsize=9)
    axs[0].set_ylabel("cracker capital, multiple of reference")
    axs[1].axvspan(4.9, 5.5, fill=False, edgecolor="k", ls="--", lw=0.8)
    axs[1].plot([b_["full_exhaust_threshold_delta_system_pp"] for b_ in beB], range(len(fcts)), "k-", lw=1)
    axs[0].axvline(7.3, color="k", ls="--", lw=0.8)
    axs[0].set_xlim(dps[0] - 0.25, dps[-1] + 0.25)
    axs[1].set_xlim(dsys[0] - 0.125, dsys[-1] + 0.125)
    axs[1].set_title("Cheapest pathway: exhaust-heated vs direct\n(line: break-even; dashed box: sourced 4.9-5.5 pp)", fontsize=9)
    axs[0].set_title("Cheapest pathway: fired / purified vs direct\n(dashed: NETL pure-H$_2$ +7.3 pp, upper bound)", fontsize=9)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=cmap(i), label=n) for n, i in (("direct NH3", 0), ("full crack, fired", 1), ("full crack + PSA", 2), ("full crack, exhaust", 3), ("partial 40 %, exhaust", 4))],
               loc="lower center", ncol=5, fontsize=7, bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    save(fig, "enduse_twoway_map.png")

    print(json.dumps({k: (v["threshold_delta_pp_reference"], v["threshold_delta_pp_range_over_bases"], v.get("threshold_full_equiv_pp_reference")) for k, v in th_json.items()}, default=float))
    print(json.dumps(statement["new_unified"], default=float))
    print(json.dumps({k: v["proposed_verdict"] for k, v in row_evidence.items()}))
    print(json.dumps({"te": te["vs_supported_range_all_bases"], "tp": tp["vs_netl_all_bases"], "tf": tf["vs_indirect_bracket"], "fct_be": fct_be, "forty": forty}, default=float))
    print({i["id"]: i["status"] for i in items if i["status"] not in ("pass", "informational")})


if __name__ == "__main__":
    main()
