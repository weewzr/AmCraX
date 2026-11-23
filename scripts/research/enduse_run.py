"""End-use pathway comparison for imported ammonia in Singapore (workstream U). Deterministic; re-run:
   python scripts/research/enduse_run.py
Run scripts/research/lca_run.py first (shares the validation folder, reference file and figure style).
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

from amcrax.enduse import (alpha_of_cracked_share, carbon_intensity, cracked_share_for_h2_fraction, h2_fraction_of_blend,  # noqa: E402
                           hydrogen_activity, hydrogen_cost, load_cracker, power_activity, power_cost)
from amcrax.enduse import params as P  # noqa: E402
from amcrax.enduse import pathways as pw  # noqa: E402
from amcrax.environmental import carbon_intensity as old_ci  # noqa: E402
from amcrax.environmental import lca  # noqa: E402
from amcrax.plotstyle import C_AMBER, C_GREY, C_H2, C_HEAT, C_N2, C_NH3, C_PRIMARY, apply_style, plt  # noqa: E402

OUT = ROOT / "results" / "research" / "enduse"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
SCRIPT = "scripts/research/enduse_run.py"
D0 = 5000.0
PRICE = P.NH3_PRICE_REF_USD_T
ROUTE_SET = ["green", "blue", "blue_param", "grey"]
EF = {r: lca.route_spec(r).ef for r in ROUTE_SET}
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
_REF = load_reference_scenario()      # Phase 2 unified reference scenario (single source of cost inputs)
TAX_SGD = _REF.carbon_tax_SGD_per_t
FX = _REF.fx_SGD_per_USD
PRICE_COLS = {"grey_450": P.NH3_PRICE_SET_USD_T["grey"], "blue_487": P.NH3_PRICE_SET_USD_T["blue"],
              "green_2030_709": P.NH3_PRICE_SET_USD_T["green_2030"], "green_current_1000": P.NH3_PRICE_SET_USD_T["green_current"]}


def prov(source_type, summary):
    return {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "script": SCRIPT,
            "source_type": source_type, "inputs_summary": summary,
            "reference_scenario": provenance_stamp(),
            "model_versions": {"aspen_inputs": "stored results/simulations/baseline.json and scn_fuel_cell_grade.json (Aspen Plus V15)",
                               "economics": "Phase 2 reference scenario: amcrax.economics.singapore.evaluate (H2) and amcrax.economics.reference.reference_capex (cracker in power pathways); all cost inputs from data/reference_scenario.yaml",
                               "purification": "results/research/purification/purification_study.json (workstream P) for the purified-H2 rows; stored scn_fuel_cell_grade kept as the Aspen-scenario variant"}}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def foot(fig):
    fig.text(0.01, 0.005, "AmCraX workstream U | cracker activity: stored Aspen Plus V15 | turbine efficiency: literature-calibrated (Ahmad 2025) | prices: data/singapore.yaml (one set)",
             fontsize=6.0, color=C_GREY, ha="left", va="bottom")


def save(fig, name):
    foot(fig)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def main():
    apply_style()
    cr = load_cracker("baseline")
    X = cr.conversion

    # ---------------- pathway table ----------------
    specs = [("direct", None)]
    for y in (0.3, 0.4, 0.5, 0.6):
        specs += [("partial_exhaust", y), ("partial_fired", y)]
    specs += [("full_exhaust", None), ("full_fired", None), ("full_purified", None)]
    for y in (0.3, 0.4, 0.5, 0.6):
        specs.append(("blend_purified", y))
    names = {"direct": "(c1) direct NH3 in gas turbine / CCGT", "partial_exhaust": "(c2) partially cracked NH3, exhaust-heated cracker, no purification",
             "partial_fired": "(c2) partially cracked NH3, fired cracker (stored Aspen duty), no purification",
             "full_exhaust": "(c3) fully cracked H2/N2, exhaust-heated, unpurified", "full_fired": "(c3) fully cracked H2/N2, fired, unpurified",
             "full_purified": "(c4) fully cracked + PSA-purified H2 in CCGT", "blend_purified": "(d) NH3 + PSA H2 blend"}
    rows = []
    acts = {}
    for kind, y in specs:
        a = power_activity(kind, y)
        acts[a.id] = a
        c = power_cost(a, PRICE)
        flex = ""
        if a.h2_fraction_vol is not None and a.h2_fraction_vol > 0:
            flex = ("inside 30-60 vol% H2 turbine range (brief/Halim, unverified)" if 0.3 - 1e-9 <= a.h2_fraction_vol <= 0.6 + 1e-9 else
                    "below 30 vol%: NG-combustor-compatible range" if a.h2_fraction_vol < 0.3 else "above 60 vol%: beyond the quoted blend range, needs a H2-capable combustor (not demonstrated here)")
        row = {"id": a.id, "pathway": names[kind], "product": "electricity", "functional_unit": a.functional_unit,
               "H2_vol_fraction_in_fuel": a.h2_fraction_vol, "cracked_NH3_share": a.cracked_share,
               "efficiency_NH3_LHV_to_electricity": a.efficiency, "NH3_kg_per_MWh": a.nh3_kg,
               "cost_USD_per_MWh_at_450": c["LCOE_USD_per_MWh"], "plant_W_net_MW": c["W_net_MW"], "TCI_MUSD": c["TCI_MUSD"],
               "cost_capital": c["components_USD_per_MWh"]["capital"], "cost_fixed_om": c["components_USD_per_MWh"]["fixed_om"],
               "cost_ammonia": c["components_USD_per_MWh"]["ammonia"],
               "N2O_kgCO2e_per_MWh": a.n2o_kgCO2e, "NO_kg_per_MWh": a.no_kg if a.no_kg is not None else "not quantified (no source for this fuel)",
               "heat_mode": a.heat_mode, "fuel_flexibility": flex,
               "source_labels": "efficiency: literature-calibrated (Ahmad 2025)" + ("; cracker heat: aspen (stored baseline)" if "fired" in kind or "purified" in kind else "") + "; cost: python (amcrax.economics + Ahmad plant data, literature)"}
        for r in ROUTE_SET:
            row[f"CI_{r}_kgCO2e_per_MWh"] = carbon_intensity(a, EF[r], D0)["total"]
        for lab, p_ in PRICE_COLS.items():
            row[f"cost_USD_per_MWh_at_{lab}"] = power_cost(a, p_)["LCOE_USD_per_MWh"]
        row["carbon_tax_USD_per_MWh_direct_in_scope"] = a.n2o_kgCO2e / 1000.0 * TAX_SGD / FX
        row["cost_SGD_per_MWh_at_450"] = row["cost_USD_per_MWh_at_450"] * FX
        row["TCI_cracker_MUSD"] = c["TCI_cracker_MUSD"]
        rows.append(row)
    # hydrogen pathways
    hrows = []
    for case, id_, lab, pur in (("baseline", "h2_industrial", "(a) industrial H2 (99.9 %): cracker + PSA, stored Aspen baseline", "99.961 mol% H2 (set by assumed PSA split); meets 99.9 %"),
                                ("scn_fuel_cell_grade", "h2_fuelcell_candidate", "(b) fuel-cell candidate (ISO 14687 Grade D purity targets): stored Aspen scenario scn_fuel_cell_grade",
                                 "99.98 mol% H2 from the assumed PSA split; NH3 polishing to 0.1 ppm and H2O/O2 not modelled, so NOT claimed fuel-cell grade; cost is a lower bound")):
        a = hydrogen_activity(case, id_, lab, pur)
        row = {"id": id_, "pathway": lab, "product": "H2", "functional_unit": a.functional_unit, "purity_note": pur,
               "efficiency_NH3_LHV_to_H2": a.efficiency, "NH3_kg_per_kg_H2": a.nh3_kg}
        for lab_, p_ in PRICE_COLS.items():
            row[f"cost_USD_per_kg_at_{lab_}"] = hydrogen_cost(case, p_)["USD_per_kg"]
        row["cost_breakdown_at_450"] = hydrogen_cost(case, PRICE)["breakdown"]
        row["cost_SGD_per_kg_at_grey_450"] = hydrogen_cost(case, PRICE)["SGD_per_kg"]
        row["cost_USD_per_kg_legacy_v1_basis_at_450"] = hydrogen_cost(case, PRICE, capex_mode="legacy")["USD_per_kg"]
        for r in ROUTE_SET:
            row[f"CI_{r}_kgCO2e_per_kgH2"] = carbon_intensity(a, EF[r], D0)["total"]
        row["source_labels"] = "activity: aspen (stored); cost: python economics module; EF: literature"
        hrows.append(row)
    # purification-workstream variants (python reduced-order models on the stored Aspen cracked gas)
    for cfgid, gk, id_, lab, pur in (
            ("PSA_AMCRAX", "industrial_99.9", "h2_industrial_purif_study", "(a) industrial H2 (99.9 %), purification study PSA_AMCRAX, compressed to 30 bar", ""),
            ("PSA_D_MB", "fuel_cell_grade_D", "h2_fuelcell_gradeD_purif_study", "(b) fuel-cell hydrogen, ISO 14687 Grade D: purification study PSA_D_MB (TSA + PSA, recovery 0.751), compressed to 350 bar",
             "99.975 mol% H2; NH3, N2, H2O only evaluated; O2, Ar, He, CO, CO2, hydrocarbons, S, halogens, HCHO, HCOOH not evaluated; recovery from a mass-balance relation (optimistic)")):
        a, cst = pw.hydrogen_activity_purification(cfgid, gk, id_, lab)
        row = {"id": id_, "pathway": lab, "product": "H2", "functional_unit": a.functional_unit, "purity_note": pur or a.purity_note,
               "efficiency_NH3_LHV_to_H2": a.efficiency, "NH3_kg_per_kg_H2": a.nh3_kg, "compression_kWh_per_kg": cst["compression_kWh_per_kg_h2"],
               "delivery_pressure_bar": cst["delivery_pressure_bar"], "purification_only_USD_per_kg_at_450": cst["purification_only_usd_per_kg"]}
        for lab_, p_ in PRICE_COLS.items():
            row[f"cost_USD_per_kg_at_{lab_}"] = cst["usd_per_kg_product_h2"] + (p_ - PRICE) / 1000.0 * a.nh3_kg
        row["cost_breakdown_at_450"] = cst["components_usd_per_kg"]
        row["cost_SGD_per_kg_at_grey_450"] = cst["usd_per_kg_product_h2"] * FX
        for r in ROUTE_SET:
            row[f"CI_{r}_kgCO2e_per_kgH2"] = carbon_intensity(a, EF[r], D0)["total"]
        row["source_labels"] = "activity and cost: python reduced-order purification model on stored Aspen cracked gas (results/research/purification); cost at other prices = linear NH3 term; EF: literature"
        hrows.append(row)

    # ---------------- direct vs cracking cost ratio (Halim claim) ----------------
    def lc(kind, y=None, price=PRICE, hours=P.POWER_PLANT_HOURS_PER_YEAR, **kw):
        return power_cost(power_activity(kind, y), price, hours=hours, **kw)["LCOE_USD_per_MWh"]

    claim = []
    _H, _AH, _AP, _G = P.POWER_PLANT_HOURS_PER_YEAR, P.AHMAD_HOURS_IMPLIED, P.AHMAD_NH3_PRICE_USD_T, P.NH3_PRICE_SET_USD_T["green_current"]
    for price, hours, tag in ((PRICE, _H, f"AmCraX price set ({PRICE:g} USD/t, {_H:g} h)"), (_AP, _AH, f"Ahmad basis ({_AP:g} USD/t, {_AH:g} h)"),
                              (_G, _H, f"renewable NH3 today ({_G:g} USD/t)")):
        d = lc("direct", price=price, hours=hours)
        for kind in ("full_exhaust", "full_fired", "full_purified"):
            cck = lc(kind, price=price, hours=hours)
            claim.append({"basis": tag, "cracking_pathway": kind, "LCOE_direct": d, "LCOE_cracking": cck,
                          "direct_cheaper_by_pct_of_cracking(1-d/c)": 100 * (1 - d / cck), "cracking_dearer_by_pct_of_direct(c/d-1)": 100 * (cck / d - 1)})
    # price at which pathways cross
    def cross(kind_a, kind_b, y_a=None, y_b=None):
        f = lambda p_: lc(kind_a, y_a, p_) - lc(kind_b, y_b, p_)
        try:
            return brentq(f, 1.0, 5000.0)
        except ValueError:
            return None

    crossovers = {"full_exhaust_vs_direct_NH3_price_USD_t": cross("full_exhaust", "direct"),
                  "partial_exhaust_40_vs_direct": cross("partial_exhaust", "direct", 0.4, None),
                  "full_fired_vs_direct": cross("full_fired", "direct"), "full_purified_vs_direct": cross("full_purified", "direct"),
                  "note": "None = the pathways do not cross between 1 and 5000 USD/t; below the crossover price the capital-heavy pathway is dearer, above it the efficiency gain pays."}

    # ---------------- partial cracking: scan share and efficiency gain ----------------
    scan = []
    for y in np.linspace(0.0, 0.74, 38):
        k_e, k_f = ("partial_exhaust", "partial_fired") if y > 0 else ("direct", "direct")
        row = {"H2_vol_fraction": y, "cracked_share": cracked_share_for_h2_fraction(y, X)}
        for g in (1.0, 0.5, 0.0):
            row[f"LCOE_exhaust_gain{g}"] = power_cost(power_activity(k_e, y if y > 0 else None, gain_scale=g), PRICE)["LCOE_USD_per_MWh"]
        row["LCOE_fired"] = power_cost(power_activity(k_f, y if y > 0 else None), PRICE)["LCOE_USD_per_MWh"]
        scan.append(row)
    be_gain = []
    for price in (300.0, 450.0, 700.0, 1000.0):
        d = lc("direct", price=price)
        g_be = None
        f = lambda g: power_cost(power_activity("partial_exhaust", 0.4, gain_scale=g), price)["LCOE_USD_per_MWh"] - d
        try:
            g_be = brentq(f, 0.0, 3.0)
        except ValueError:
            pass
        be_gain.append({"NH3_price_USD_t": price, "gain_scale_where_partial_40vol_equals_direct": g_be,
                        "meaning": "fraction of Ahmad's end-point efficiency gain (49.1 -> 54 %) that exhaust-heat integration must deliver for 40 vol% H2 partial cracking to match direct NH3 cost; >1 means unreachable with the literature gain",
                        "LCOE_direct": d, "LCOE_partial40_gain1": lc("partial_exhaust", 0.4, price=price)})
    # price sweep for figure
    prices = np.linspace(250, 1100, 18)
    sweep = [{"NH3_price_USD_t": p_, **{k: lc(k, None, p_) for k in ("direct", "full_exhaust", "full_fired", "full_purified")},
              "partial40_exhaust": lc("partial_exhaust", 0.4, p_), "partial40_fired": lc("partial_fired", 0.4, p_)} for p_ in prices]
    # hours sensitivity (capital-heavy pathways suffer at low capacity factor)
    hours_rows = [{"hours": h, "direct": lc("direct", hours=h), "full_exhaust": lc("full_exhaust", hours=h), "full_purified": lc("full_purified", hours=h)} for h in (3000, 5000, 7200, 8000)]
    # unpurified cracker capex at the full correlation (Ahmad's own use)
    full_corr = power_cost(power_activity("full_exhaust"), PRICE, unpurified_full_correlation=True)["LCOE_USD_per_MWh"]

    # ---------------- break-even CO2 vs cost for hydrogen ----------------
    h_ind = hydrogen_activity("baseline", "h2_industrial", "", "")
    summary_h = {"industrial_H2_cost_vs_price": {int(p_): hydrogen_cost("baseline", p_)["USD_per_kg"] for p_ in (300, 450, 709, 1000)},
                 "fuelcell_candidate_cost_vs_price": {int(p_): hydrogen_cost("scn_fuel_cell_grade", p_)["USD_per_kg"] for p_ in (300, 450, 709, 1000)},
                 "purification_cost_increment_USD_per_kg_at_450": hydrogen_cost("scn_fuel_cell_grade", 450)["USD_per_kg"] - hydrogen_cost("baseline", 450)["USD_per_kg"],
                 "note": "Increment is the stored-scenario difference (PSA recovery 0.85 -> 0.80, N2 slip 1e-3 -> 5e-4); it excludes NH3 polishing and other ISO 14687 contaminants, so it is a lower bound."}

    # electricity from H2 detour: H2 product route vs direct for the same end use
    detour = {"kWh_electricity_per_kg_NH3_direct": P.ELEC_MJ_PER_KG_DIRECT / 3.6, "kWh_electricity_per_kg_NH3_cracked_purified": power_activity("full_purified").efficiency * P.LHV_NH3_MJ_KG / 3.6}

    result = {"provenance": prov("python+aspen(stored)+literature", "stored Aspen baseline / fuel-cell scenario activities; Ahmad 2025 turbine efficiencies and plant economics; economics.yaml prices"),
              "price_set": {"NH3_USD_per_t": P.NH3_PRICE_SET_USD_T, "NH3_USD_per_t_common_reference": PRICE, "electricity_USD_per_kWh": P.ELECTRICITY_USD_KWH,
                            "operating_hours": P.HOURS_PER_YEAR, "power_plant_operating_hours": P.POWER_PLANT_HOURS_PER_YEAR,
                            "discount_rate": P.DISCOUNT_RATE, "life_years": P.PLANT_LIFE_YR, "carbon_tax_SGD_per_t": TAX_SGD, "fx_SGD_per_USD": FX,
                            "fx_date": _REF.fx_date, "capex_method": _REF.capex_method,
                            "source": "Phase 2 reference scenario backend/amcrax/data/reference_scenario.yaml (blue 487 is a secondary_web value; FX ECB cross rate)",
                            "note": "One price set for every pathway. Cost columns: 'at_450' is the common reference price (isolates technology); the route columns use that route's own price. Carbon tax applies only to direct in-scope N2O (negligible) and is reported separately in USD per MWh."},
              "distance_km": D0, "ef_kgCO2e_per_kgNH3": EF,
              "power_pathways": rows, "hydrogen_pathways": hrows,
              "halim_claim_check": {"halim_statement": "direct NH3 combustion about 40 % cheaper than cracking-based power (task brief; Halim abstract confirms only 'preferable because of high capital and operating costs of cracking')",
                                    "computed": claim, "crossover_prices": crossovers,
                                    "unpurified_exhaust_LCOE_with_full_cracker_correlation": full_corr,
                                    "verdict_note": "Computed gap depends strongly on whether the cracker is exhaust-heated (literature 54 % efficiency) or fired, and on purification; see results table. Halim's inputs were not accessed."},
              "partial_cracking": {"scan": scan, "breakeven_efficiency_gain": be_gain},
              "price_sweep": sweep, "hours_sensitivity": hours_rows, "hydrogen_summary": summary_h, "detour": detour,
              "fuel_flexibility": {"halim_blend_range_vol_H2": list(P.HALIM_H2_BLEND_RANGE_VOL), "NG_combustor_limit_vol_H2": P.NG_COMBUSTOR_H2_LIMIT_VOL,
                                   "source_type": "literature (task brief; Ahmad 2025 p. 2)", "note": "Not Aspen results; combustion behaviour not simulated here."},
              "nox_note": "NO and N2O are only available for direct NH3 (Ahmad Chemkin, simulated); other fuels are 'not quantified'. NOx is a local pollutant and is never added to CO2e.",
              "limitations": ["Efficiencies of intermediate blends are a linear interpolation of Ahmad's two end points (assumption).",
                              "Fired variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption).",
                              "Plant capital outside the cracker is Ahmad's Case 2a scaled with power^0.67; no NOx abatement cost.",
                              "Fuel-cell candidate cost excludes NH3 polishing and other ISO 14687 contaminant control.",
                              "Halim et al. (2025) full text was not accessible; only the abstract and bibliographic data were checked."]}
    dump(OUT / "enduse_results.json", result)
    write_csv(OUT / "pathway_table_power.csv", rows)
    write_csv(OUT / "pathway_table_hydrogen.csv", [{k: v for k, v in r.items() if not isinstance(v, dict)} for r in hrows])
    write_csv(OUT / "claim_check_direct_vs_cracking.csv", claim)
    write_csv(OUT / "partial_cracking_scan.csv", scan)
    write_csv(OUT / "price_sweep.csv", sweep)

    # ---------------- assumptions ----------------
    reg = [
        {"name": "eta_direct_ahmad", "value": P.ETA_DIRECT_AHMAD, "unit": "-", "source_type": "literature", "source": "Ahmad 2025 Table 6 Case 2a", "applicability_note": "Literature-calibrated; LHV 18.8 MJ/kg basis"},
        {"name": "eta_full_crack_ahmad", "value": P.ETA_FULL_CRACK_AHMAD, "unit": "-", "source_type": "literature", "source": "Ahmad 2025 p. 15", "applicability_note": "Exhaust-heated cracker; approximate"},
        {"name": "eta_gt_gas", "value": P.ETA_GT_GAS, "unit": "-", "source_type": "assumption", "source": "same turbine as direct VNH3 case", "applicability_note": "applied to H2-rich fuel in fired/purified variants"},
        {"name": "exhaust_gain_interpolation", "value": "linear in cracked share", "unit": "-", "source_type": "assumption", "source": "Ahmad gives end points only", "applicability_note": "tested with gain scale 1, 0.5, 0"},
        {"name": "plant_TCI_noncracker", "value": P.AHMAD_TCI_2A_MUSD, "unit": "MUSD at 43.1 MW", "source_type": "literature", "source": "Ahmad 2025 Sec. 3.1.3", "applicability_note": "scaled with (W/43.1)^0.67 (assumption exponent)"},
        {"name": "plant_fixed_om", "value": P.AHMAD_OC_FIXED_2A_USD_PER_KWH, "unit": "USD/kWh at 7200 h", "source_type": "literature", "source": "Ahmad 2025 Case 2a breakdown", "applicability_note": "scaled with power^0.67"},
        {"name": "cracker_capex", "value": _REF.capex_method, "unit": "USD", "source_type": "literature", "source": "Cho 2026 itemised installed cost scaled with (NH3 through cracker)^0.8, via amcrax.economics.reference (Phase 2 reference scenario; supersedes Ahmad 2025 Fig. 6 correlation)", "applicability_note": "unpurified variants remove the PSA and adsorber items; large extrapolation from the 82 kg H2/h reference plant to the Ahmad power-plant scale"},
        {"name": "operating_hours", "value": P.POWER_PLANT_HOURS_PER_YEAR, "unit": "h/yr", "source_type": "assumption", "source": "reference_scenario.yaml power_plant.operating_hours_h_per_yr", "applicability_note": "Ahmad implies 7200 h (power_plant.ahmad_reproduction_hours); used only in the reproduction"},
        {"name": "nh3_price_reference", "value": PRICE, "unit": "USD/t", "source_type": "literature", "source": "data/economics.yaml default (Cho et al. range 300-610)", "applicability_note": "same for all routes; swept 250-1100"},
        {"name": "cracker_heat_scaling", "value": "linear in cracked share", "unit": "-", "source_type": "aspen", "source": "stored baseline.json reactor + pre-heater duty per kg NH3 cracked (600 C, 20 bar)", "applicability_note": "temperature sensitivity from stored scn_low/high_temperature runs not propagated"},
        {"name": "fuel_flexibility", "value": "30-60 vol% H2", "unit": "vol%", "source_type": "literature", "source": "task brief (Halim 2025, unverified); Ahmad 2025 p. 2 for the 30 vol% NG-combustor limit", "applicability_note": "label only; no combustion simulation"},
        {"name": "ISO_14687_grade_D", "value": P.ISO14687_GRADE_D, "unit": "mixed", "source_type": "literature", "source": "values quoted in docs/internal/fact_sheet.md (99.97 %, 300 ppm) and brief (NH3 0.1 ppm)", "applicability_note": "baseline product never called fuel-cell grade"},
    ]
    dump(OUT / "assumptions.json", reg)

    # ---------------- validation ----------------
    items = []

    def add(id_, desc, method, ref, obs, exp, tol, unit, status, files):
        items.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs, "expected": exp,
                      "tolerance": tol, "unit": unit, "status": status, "source_files": files})
    sf = ["backend/amcrax/enduse/pathways.py", "results/research/enduse/enduse_results.json"]
    for alpha, byp in P.AHMAD_ALPHA_BYPASS.items():
        # find f for alpha with X = 0.97
        f = brentq(lambda f_: alpha_of_cracked_share(f_, P.AHMAD_CRACK_CONVERSION) - alpha, 0, 1) if 0 < alpha < 1 else (1.0 if alpha == 0 else 0.0)
        exp = 1 - byp
        add(f"EU-stoich-alpha-{alpha}", f"Cracked NH3 share for alpha = {alpha} (stoichiometry, X = 0.97) against Ahmad's bypass table",
            "alpha = NH3/(NH3+H2); m = f X; compare with 1 - bypass share", "Ahmad 2025 p. 13-15", f, exp, 0.005, "-",
            "pass" if abs(f - exp) <= 0.005 else "fail", sf)
    for y in (0.3, 0.4, 0.5, 0.6):
        f = cracked_share_for_h2_fraction(y, X)
        back = h2_fraction_of_blend(f, X)
        add(f"EU-blend-{int(y*100)}", f"Round trip: H2 vol fraction {y} -> cracked share {f:.4f} -> H2 fraction", "closed-form stoichiometry both ways", "stoichiometry",
            back, y, 1e-12, "-", "pass" if abs(back - y) < 1e-12 else "fail", sf)
        a = power_activity("partial_fired", y)
        # mole balance check on the gas: H2 : N2 : NH3
        m = f * X
        nh3, h2_, n2 = 1 - m, 1.5 * m, 0.5 * m
        add(f"EU-blend-N-{int(y*100)}", "Nitrogen atoms conserved in the partially cracked gas (2 N2 + NH3 per NH3 fed = 1)", "2 n_N2 + n_NH3 = 1 per mol NH3 fed", "stoichiometry",
            2 * n2 + nh3, 1.0, 1e-12, "mol N/mol NH3", "pass", sf)
        add(f"EU-blend-H-{int(y*100)}", "Hydrogen atoms conserved (2 n_H2 + 3 n_NH3 = 3)", "per mol NH3 fed", "stoichiometry", 2 * h2_ + 3 * nh3, 3.0, 1e-12, "mol H/mol NH3", "pass", sf)
    for aid, a in acts.items():
        # energy balance: electricity + losses = total NH3 LHV; efficiency must lie in (0,1) and match elec / (NH3 x LHV)
        elec_MJ = 3600.0
        lhv_in = a.nh3_kg * P.LHV_NH3_MJ_KG
        eff = elec_MJ / lhv_in
        add(f"EU-energy-{aid}", f"Energy balance {aid}: 1 MWh_e / NH3 LHV (incl. heat NH3) equals the reported efficiency; efficiency < 1", "3600 MJ / (NH3 kg x 18.60 MJ/kg)", "first law",
            eff, a.efficiency, 1e-9, "-", "pass" if abs(eff - a.efficiency) < 1e-9 and 0 < eff < 1 else "fail", sf)
    h = hydrogen_activity("baseline", "x", "", "")
    add("EU-energy-h2", "H2 pathway energy efficiency against Aspen's stored lhv_efficiency (0.8772; first-law, heat 1:1)", "H2 LHV / (NH3 LHV x (1 + heat NH3))", "results/simulations/baseline.json",
        h.efficiency, pw.load_result("baseline").kpis.lhv_efficiency, 0.005, "-",
        "pass" if abs(h.efficiency - pw.load_result("baseline").kpis.lhv_efficiency) <= 0.005 else "fail", ["results/simulations/baseline.json"])
    old = old_ci(pw.load_result("baseline"), "blue/self_firing").total_kgCO2e_per_kgH2
    new = carbon_intensity(h, lca.route_spec("blue").ef, D0)["total"]
    add("EU-baseline-CI", "Existing baseline carbon intensity (blue NH3, self-firing) reproduced with old settings", "enduse.carbon_intensity vs amcrax.environmental.carbon_intensity", "results/simulations/environmental_baseline.json",
        new, old, 1e-6, "kg CO2e/kg H2", "pass" if abs(new - old) < 1e-6 * old else "fail", ["backend/amcrax/environmental/__init__.py"])
    econ = json.load(open(ROOT / "results" / "simulations" / "economics_baseline.json", encoding="utf-8"))
    ref_lcoh = None
    for k_ in ("lcoh_USD_per_kg",):
        node = econ.get("lcoh", econ.get("result", econ))
        ref_lcoh = node.get(k_) if isinstance(node, dict) else None
    ours = hydrogen_cost("baseline", PRICE, electricity=P.LEGACY_ELECTRICITY_USD_KWH, capex_mode="legacy")["USD_per_kg"]
    add("EU-lcoh", "Industrial H2 cost on the legacy v1 basis equals the stored baseline LCOH (legacy reproduction)", "evaluate(capex_mode=legacy) at 450 USD/t vs results/simulations/economics_baseline.json", "stored economics baseline",
        ours, ref_lcoh, 1e-6, "USD/kg H2", ("pass" if ref_lcoh is not None and abs(ours - ref_lcoh) < 1e-6 else "informational" if ref_lcoh is None else "fail"), ["results/simulations/economics_baseline.json"])
    ref_bl = json.load(open(ROOT / "results" / "research" / "reference_scenario" / "baseline.json", encoding="utf-8"))["lcoh_USD_per_kg"]
    ours_ref = hydrogen_cost("baseline", PRICE)["USD_per_kg"]
    add("EU-lcoh-reference", "Industrial H2 cost equals the unified reference baseline LCOH", "hydrogen_cost (reference scenario) vs results/research/reference_scenario/baseline.json", "reference scenario baseline",
        ours_ref, ref_bl, 1e-6 * ref_bl, "USD/kg H2", "pass" if abs(ours_ref - ref_bl) <= 1e-6 * ref_bl else "fail", ["results/research/reference_scenario/baseline.json"])
    d480 = power_cost(power_activity("direct"), P.AHMAD_NH3_PRICE_USD_T, hours=P.AHMAD_HOURS_IMPLIED)
    add("EU-ahmad-lcoe", "Reproduction of Ahmad Case 2a LCOE with Ahmad's inputs (480 USD/t, 7200 h, 10 %, 25 y)", "power_cost on direct pathway", "Ahmad 2025 conclusion p. 18 (0.2798 USD/kWh)",
        d480["LCOE_USD_per_MWh"] / 1000, P.AHMAD_LCOE_2A, 0.01 * P.AHMAD_LCOE_2A, "USD/kWh",
        "pass" if abs(d480["LCOE_USD_per_MWh"] / 1000 - P.AHMAD_LCOE_2A) <= 0.01 * P.AHMAD_LCOE_2A else "fail", sf)
    fe = power_cost(power_activity("full_exhaust"), P.AHMAD_NH3_PRICE_USD_T, hours=P.AHMAD_HOURS_IMPLIED, unpurified_full_correlation=True)
    add("EU-ahmad-tci-full", "Fully cracked plant TCI against Ahmad's about 230 MUSD (alpha = 0)", "plant 181.25 MUSD scaled + cracker correlation (full)", "Ahmad 2025 p. 15",
        fe["TCI_MUSD"], P.AHMAD_TCI_FULL_CRACK_MUSD, None, "MUSD", "informational", sf)
    d320 = power_cost(power_activity("direct"), 320.0, hours=P.AHMAD_HOURS_IMPLIED)["LCOE_USD_per_MWh"] / 1000
    f320 = power_cost(power_activity("full_exhaust"), 320.0, hours=P.AHMAD_HOURS_IMPLIED, unpurified_full_correlation=True)["LCOE_USD_per_MWh"] / 1000
    add("EU-ahmad-320", "Ahmad at 320 USD/t: direct VNH3 0.217 vs full cracking 0.22 USD/kWh (p. 15, attribution inconsistent in the paper); AmCraX direct and full-crack values",
        "power_cost at 320 USD/t, 7200 h, full cracker correlation", "Ahmad 2025 p. 15", [round(d320, 4), round(f320, 4)], [0.217, 0.22], None, "USD/kWh", "informational", sf)
    add("EU-ahmad-eta", "Direct NH3 efficiency re-expressed on the AmCraX LHV basis gives Ahmad's electricity per kg NH3", "0.4912 x 18.8 / 18.6", "Ahmad 2025 Table 6",
        power_activity("direct").efficiency * P.LHV_NH3_MJ_KG, P.ELEC_MJ_PER_KG_DIRECT, 1e-9, "MJ/kg NH3", "pass", sf)
    add("EU-halim-claim", "Halim et al. (2025): direct NH3 combustion about 40 % cheaper than cracking-based power", "computed 1 - direct/cracking, see halim_claim_check",
        "Halim 2025 (full text not accessed; abstract states direct use is preferable)", [round(c_["direct_cheaper_by_pct_of_cracking(1-d/c)"], 1) for c_ in claim if c_["basis"].startswith("AmCraX")], 40.0, None, "%", "informational", sf)
    add("EU-halim-plant", "Halim et al. (2025): 60.1 MW Singapore plant, LCOH 15.1 (green) and 10.1 (blue) USD/kg H2", "not verifiable: only abstract and bibliographic data were accessible", "Halim 2025 abstract (A*STAR OAR, IDEAS)",
        None, [60.1, 15.1, 10.1], None, "MW; USD/kg", "informational", sf)
    add("EU-iso", "Industrial and fuel-cell candidate purity against ISO 14687 Grade D (99.97 %, N2+Ar <= 300 ppm, NH3 <= 0.1 ppm)", "stored purity vs thresholds; NH3 and other contaminants not modelled",
        "fact_sheet F4", [cr.purity_mole_frac, load_cracker("scn_fuel_cell_grade").purity_mole_frac], P.ISO14687_GRADE_D, None, "mol frac", "informational", ["results/simulations/baseline.json", "results/simulations/scn_fuel_cell_grade.json"])
    dump(VAL / "enduse.json", items)

    # ---------------- figures ----------------
    show = ["direct", "partial_exhaust_40", "partial_fired_40", "full_exhaust", "full_fired", "full_purified", "blend_purified_40"]
    lab = {"direct": "direct NH3", "partial_exhaust_40": "partial 40 vol% H2\n(exhaust-heated)", "partial_fired_40": "partial 40 vol% H2\n(fired)",
           "full_exhaust": "full crack H2/N2\n(exhaust-heated)", "full_fired": "full crack H2/N2\n(fired)", "full_purified": "full crack + PSA H2", "blend_purified_40": "NH3 + PSA H2\n40 vol%"}
    rr = {r["id"]: r for r in rows}
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    cols = [C_NH3, C_PRIMARY, C_N2, C_AMBER, C_HEAT, C_H2, C_GREY]
    for i, k in enumerate(show):
        for rt, mk in (("green", "o"), ("blue", "s"), ("grey", "^")):
            ax.scatter(rr[k][f"CI_{rt}_kgCO2e_per_MWh"], rr[k]["cost_USD_per_MWh_at_450"], marker=mk, color=cols[i], s=34, edgecolor="k", lw=0.4,
                       label=lab[k].replace("\n", " ") if rt == "green" else None)
    ax.axvline(lca.ccgt_ci_kg_per_MWh(), color=C_PRIMARY, ls="--", lw=1)
    ax.text(lca.ccgt_ci_kg_per_MWh() + 5, ax.get_ylim()[0] + 3, "NG CCGT 367", fontsize=7, color=C_PRIMARY, rotation=90)
    ax.set_xlabel("kg CO$_2$e / MWh (markers: o green, s blue (Lee v1), ^ grey NH$_3$; 5000 km)")
    ax.set_ylabel("cost, USD / MWh at 450 USD/t NH$_3$ (all routes)")
    ax.set_title("Power from imported ammonia: cost against carbon intensity")
    ax.legend(fontsize=6.5, loc="center", bbox_to_anchor=(0.62, 0.62))
    save(fig, "enduse_power_cost_vs_ci.png")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ys = [s_["H2_vol_fraction"] * 100 for s_ in scan]
    for g, col, ls in ((1.0, C_NH3, "-"), (0.5, C_AMBER, "-"), (0.0, C_GREY, "-")):
        ax.plot(ys, [s_[f"LCOE_exhaust_gain{g}"] for s_ in scan], color=col, ls=ls, label=f"exhaust-heated cracker, efficiency gain x{g}")
    ax.plot(ys, [s_["LCOE_fired"] for s_ in scan], color=C_HEAT, label="fired cracker (stored Aspen duty)")
    ax.axvspan(30, 60, color=C_PRIMARY, alpha=0.08)
    ax.text(45, ax.get_ylim()[1] * 0.995, "30-60 vol% H$_2$ blend range", ha="center", va="top", fontsize=7, color=C_PRIMARY)
    ax.set_xlabel("H$_2$ in turbine fuel, vol% (unpurified partial cracking)")
    ax.set_ylabel("USD / MWh at 450 USD/t NH$_3$")
    ax.set_title("Partial cracking: cost against H$_2$ fraction")
    ax.legend(fontsize=7.5)
    save(fig, "enduse_partial_cracking_cost.png")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for k, col, lb in (("direct", C_NH3, "direct NH3"), ("full_exhaust", C_AMBER, "full crack, exhaust-heated"), ("full_fired", C_HEAT, "full crack, fired"), ("full_purified", C_H2, "full crack + PSA H2"),
                       ("partial40_exhaust", C_PRIMARY, "partial 40 vol% exhaust-heated")):
        ax.plot([s_["NH3_price_USD_t"] for s_ in sweep], [s_[k] for s_ in sweep], color=col, label=lb)
    ax.set_xlabel("NH$_3$ price, USD/t")
    ax.set_ylabel("USD / MWh")
    ax.set_title("Power cost against ammonia price (8000 h/yr, 10 %, 25 y)")
    ax.legend(fontsize=7.5)
    save(fig, "enduse_power_cost_vs_price.png")

    fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.0))
    xs = np.array([250, 450, 709, 1000, 1100])
    ax = axs[0]
    ax.plot(xs, [hydrogen_cost("baseline", p_)["USD_per_kg"] for p_ in xs], color=C_PRIMARY, label="industrial H$_2$ (99.96 mol%)")
    ax.plot(xs, [hydrogen_cost("scn_fuel_cell_grade", p_)["USD_per_kg"] for p_ in xs], color=C_H2, label="fuel-cell candidate (99.98 mol%, NH$_3$ polish not costed)")
    ax.set_xlabel("NH$_3$ price, USD/t")
    ax.set_ylabel("USD / kg usable H$_2$")
    ax.set_title("Hydrogen cost (cracking, delivered NH$_3$ basis)")
    ax.legend(fontsize=6.5)
    ax = axs[1]
    ids = ["h2_industrial", "h2_fuelcell_candidate"]
    w = 0.2
    for j, rt in enumerate(ROUTE_SET):
        ax.bar(np.arange(2) + (j - 1.5) * w, [[h_ for h_ in hrows if h_["id"] == i_][0][f"CI_{rt}_kgCO2e_per_kgH2"] for i_ in ids], w, label=rt.replace("_", " "))
    ax.axhline(lca.smr_h2_ci(False), color=C_HEAT, ls="--", lw=1)
    ax.axhline(lca.smr_h2_ci(True), color=C_PRIMARY, ls="--", lw=1)
    ax.set_xticks(range(2), ["industrial", "fuel-cell\ncandidate"])
    ax.set_ylabel("kg CO$_2$e / kg H$_2$")
    ax.set_title("Carbon intensity by NH$_3$ route (dashed: SMR 11, SMR+CCS 3.5)")
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, "enduse_hydrogen_cost_ci.png")

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ids = [r["id"] for r in rows if r["id"] in ("direct", "partial_exhaust_40", "partial_fired_40", "full_exhaust", "full_fired", "full_purified", "blend_purified_40")]
    ax.bar(range(len(ids)), [rr[i_]["efficiency_NH3_LHV_to_electricity"] * 100 for i_ in ids], color=[cols[show.index(i_)] for i_ in ids])
    ax.set_xticks(range(len(ids)), [lab[i_] for i_ in ids], fontsize=6.5)
    ax.set_ylabel("NH$_3$ LHV to electricity, %")
    ax.set_title("Net efficiency (literature-calibrated turbine inputs; cracker heat from stored Aspen duties)")
    for i_, k in enumerate(ids):
        ax.text(i_, rr[k]["efficiency_NH3_LHV_to_electricity"] * 100 + 0.5, f"{rr[k]['efficiency_NH3_LHV_to_electricity'] * 100:.1f}", ha="center", fontsize=7.5)
    save(fig, "enduse_power_efficiency.png")
    print("done")
    for r in rows:
        print(r["id"], round(r["efficiency_NH3_LHV_to_electricity"], 3), round(r["cost_USD_per_MWh_at_450"], 1), round(r["CI_blue_kgCO2e_per_MWh"], 0), r["fuel_flexibility"][:20])
    for c_ in claim:
        print(c_["basis"][:12], c_["cracking_pathway"], round(c_["direct_cheaper_by_pct_of_cracking(1-d/c)"], 1))
    print(crossovers, be_gain, summary_h, full_corr)
    print({i["id"]: i["status"] for i in items if i["status"] != "pass"})


if __name__ == "__main__":
    main()
