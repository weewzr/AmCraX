"""Literature-calibrated and assumed scenario inputs of the end-use comparison (workstream U).

NOTHING here is an Aspen Plus result. Turbine/CCGT efficiency, fuel-flexibility limits and NOx behaviour are
LITERATURE-CALIBRATED scenario inputs. Aspen results enter only through the stored cracker activities
(results/simulations/baseline.json and scn_fuel_cell_grade.json), read in ``pathways.load_cracker``.
"""
from __future__ import annotations

from amcrax.economics.reference import load_reference_scenario
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

_REF = load_reference_scenario()   # Phase 2 unified reference scenario (data/reference_scenario.yaml)

# ---- LHVs on the AmCraX basis (amcrax.schemas) -----------------------------------------------------------
LHV_NH3_MJ_KG = LHV_KJ_PER_MOL["NH3"] / MOLAR_MASS["NH3"]      # 18.60
LHV_H2_MJ_KG = LHV_KJ_PER_MOL["H2"] / MOLAR_MASS["H2"]          # 119.96
AHMAD_LHV_NH3 = 18.8                                            # MJ/kg used by Ahmad et al. (2025) Eq. 7

# ---- Ahmad et al. (2025), IJHE 173:151337 (literature-calibrated) ------------------------------------------
ETA_DIRECT_AHMAD = 0.4912       # Table 6, Case 2a (vaporised NH3, pressurised evaporator), on LHV 18.8 MJ/kg
ETA_FULL_CRACK_AHMAD = 0.54     # p. 15, alpha = 0 (H2/N2 fully cracked, exhaust-heated cracker, PR 8), approx.
# electricity per kg NH3, MJ (identical in both LHV bases): used as the anchor for every gas-turbine figure
ELEC_MJ_PER_KG_DIRECT = ETA_DIRECT_AHMAD * AHMAD_LHV_NH3
ELEC_MJ_PER_KG_FULL = ETA_FULL_CRACK_AHMAD * AHMAD_LHV_NH3
# turbine efficiency on gaseous fuel in the AmCraX LHV basis (assumption: same turbine as the direct VNH3 case)
ETA_GT_GAS = ELEC_MJ_PER_KG_DIRECT / LHV_NH3_MJ_KG
# Ahmad's bypass table (p. 13-15): alpha = NH3/(NH3+H2) molar -> NH3 bypass share; cracked share = 1 - bypass
AHMAD_ALPHA_BYPASS = {0.75: 0.8125, 0.5: 0.5876, 0.4: 0.4845, 0.3: 0.3724, 0.2: 0.2502, 0.1: 0.1165, 0.0: 0.0}
AHMAD_CRACK_CONVERSION = 0.97   # Hypermec 10010 at 10 bar, 500 C (p. 5)
# Ahmad economics (Sec. 2.4, Table 6, p. 11-13)
AHMAD_TCI_2A_MUSD = 181.25
AHMAD_W_NET_2A_MW = 43.1
AHMAD_OC_FIXED_2A_USD_PER_KWH = 0.02843
AHMAD_TCI_2A_USD_PER_KWH = 0.06433
AHMAD_LCOE_2A = 0.2798
AHMAD_NH3_PRICE_USD_T = _REF.power_value("ahmad_reproduction_nh3_price_USD_per_t")
AHMAD_MASS_FLOW_KG_S = 4.667
AHMAD_HOURS_IMPLIED = _REF.power_value("ahmad_reproduction_hours")   # 7200 h implied by Ahmad's LCOE (named field)
AHMAD_TCI_FULL_CRACK_MUSD = 230.0
PLANT_SCALE_EXPONENT = _REF.power_value("scale_exponent")   # assumption: typical Ahmad Table 4 exponent (ST/HRSG/BOP)
CRACKER_FIXED_OM_FRAC_TCI = _REF.power_value("cracker_fixed_om_frac_tci")   # Ahmad: maintenance 2.5 % + insurance 2 %

# ---- Fuel flexibility (literature, as stated in the task brief and Ahmad 2025) ----------------------------
HALIM_H2_BLEND_RANGE_VOL = (0.30, 0.60)   # H-25 turbine takes 30-60 vol% H2 in NH3-H2 blends: Halim et al. 2025 p. 3 (full text read 24 Nov 2026), relayed from trade press (vendor-claim grade)
NG_COMBUSTOR_H2_LIMIT_VOL = 0.30          # Ahmad (2025) p. 2: NG combustors limited to about 30 vol% H2 without modification

# ---- Price set (one consistent set for every pathway; economics.yaml defaults unless stated) -------------
HOURS_PER_YEAR = _REF.operating_hours_h_per_yr          # reference scenario (cracker)
POWER_PLANT_HOURS_PER_YEAR = _REF.power_value("operating_hours_h_per_yr")   # named field (same value, Phase 1 choice)
DISCOUNT_RATE = _REF.power_value("discount_rate")
PLANT_LIFE_YR = _REF.power_value("plant_life_yr")
FX_SGD_PER_USD = _REF.fx_SGD_per_USD
from amcrax.economics.singapore import scenario_price  # noqa: E402

# One price set = the Singapore economics workstream (amcrax.economics.singapore / data/singapore.yaml)
NH3_PRICE_SET_USD_T = {k: scenario_price(k) for k in ("grey", "blue", "green_2050", "green_2030", "green_current")}
NH3_PRICE_REF_USD_T = NH3_PRICE_SET_USD_T["grey"]          # 450: common reference price for technology comparison
NH3_PRICE_GREEN_USD_T = (NH3_PRICE_SET_USD_T["green_2030"], NH3_PRICE_SET_USD_T["green_current"])
ELECTRICITY_USD_KWH = _REF.electricity_USD_per_kWh    # reference scenario (USEP + network + fees, derived)
LEGACY_ELECTRICITY_USD_KWH = _REF.reproduction("legacy_v1")["electricity_price_USD_per_kWh"]  # only to reproduce v1

# N2O GWP for the Singapore carbon tax: Carbon Pricing Act 2018, First Schedule ("3. Nitrous oxide N2O 265"),
# research/data/carbon_policy_sg.json (accessed 2026-11-23). Life-cycle intensity keeps AR6 273 (amcrax.environmental.lca).
GWP_N2O_SG_CARBON_PRICING_ACT = 265.0

# Singapore end-use anchors (literature)
ISO14687_GRADE_D = {"H2_min_mol_pct": 99.97, "N2_plus_Ar_max_ppm": 300.0, "NH3_max_ppm": 0.1}
