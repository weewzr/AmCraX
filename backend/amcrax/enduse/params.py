"""Literature-calibrated and assumed scenario inputs of the end-use comparison (workstream U).

NOTHING here is an Aspen Plus result. Turbine/CCGT efficiency, fuel-flexibility limits and NOx behaviour are
LITERATURE-CALIBRATED scenario inputs. Aspen results enter only through the stored cracker activities
(results/simulations/baseline.json and scn_fuel_cell_grade.json), read in ``pathways.load_cracker``.
"""
from __future__ import annotations

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

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
AHMAD_NH3_PRICE_USD_T = 480.0
AHMAD_MASS_FLOW_KG_S = 4.667
AHMAD_HOURS_IMPLIED = 7200.0    # implied: TCI x CRF(10 %, 25 y) / (0.06433 USD/kWh x 43.1 MW) = 7201 h
AHMAD_TCI_FULL_CRACK_MUSD = 230.0
PLANT_SCALE_EXPONENT = 0.67     # assumption: typical Ahmad Table 4 exponent for the ST/HRSG/BOP items

# ---- Fuel flexibility (literature, as stated in the task brief and Ahmad 2025) ----------------------------
HALIM_H2_BLEND_RANGE_VOL = (0.30, 0.60)   # task brief: H-25 turbine takes 30-60 vol% H2 in NH3-H2 blends (Halim not accessed)
NG_COMBUSTOR_H2_LIMIT_VOL = 0.30          # Ahmad (2025) p. 2: NG combustors limited to about 30 vol% H2 without modification

# ---- Price set (one consistent set for every pathway; economics.yaml defaults unless stated) -------------
HOURS_PER_YEAR = 8000.0          # data/economics.yaml operating_hours_h_per_yr
from amcrax.economics.singapore import default_electricity_USD_per_kWh, scenario_price  # noqa: E402

# One price set = the Singapore economics workstream (amcrax.economics.singapore / data/singapore.yaml)
NH3_PRICE_SET_USD_T = {k: scenario_price(k) for k in ("grey", "blue", "green_2050", "green_2030", "green_current")}
NH3_PRICE_REF_USD_T = NH3_PRICE_SET_USD_T["grey"]          # 450: common reference price for technology comparison
NH3_PRICE_GREEN_USD_T = (NH3_PRICE_SET_USD_T["green_2030"], NH3_PRICE_SET_USD_T["green_current"])
ELECTRICITY_USD_KWH = default_electricity_USD_per_kWh()    # singapore.yaml derived industrial price (USEP + network + fees)

# Singapore end-use anchors (literature)
ISO14687_GRADE_D = {"H2_min_mol_pct": 99.97, "N2_plus_Ar_max_ppm": 300.0, "NH3_max_ppm": 0.1}
