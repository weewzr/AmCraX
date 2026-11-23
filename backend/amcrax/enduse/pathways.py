"""End-use pathways for imported ammonia in Singapore (workstream U).

Hydrogen pathways: functional unit 1 kg usable H2 at the stated purity.
Power pathways: functional unit 1 MWh of net electricity delivered.
Efficiency: product energy (H2 LHV or electricity) / total NH3 LHV including any NH3 burnt for heat.

Provenance labels: cracker activities per kg NH3 come from STORED ASPEN results ('aspen'); the partial-cracking
heat is the stored Aspen reactor + pre-heater duty scaled linearly with the cracked share (the stored temperature
scenarios give 500 C and 700 C duties for a sensitivity; the Python process model was not re-run). Turbine and
CCGT efficiencies are LITERATURE-CALIBRATED (Ahmad 2025); costs come from the Phase 2 unified reference scenario
(amcrax.economics.reference / amcrax.economics.singapore, data/reference_scenario.yaml). The legacy lcoh.py
correlation is no longer used here (superseded for research outputs).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from scipy.optimize import brentq

from amcrax.economics.lcoh import crf
from amcrax.economics.reference import reference_capex
from amcrax.economics.singapore import evaluate as sg_evaluate
from amcrax.environmental import lca
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, SimulationResult

from . import params as P

ROOT = Path(__file__).resolve().parents[3]
LHV_NH3_MOL = LHV_KJ_PER_MOL["NH3"]
LHV_H2_MOL = LHV_KJ_PER_MOL["H2"]
DH_CRACK_PER_MOL_NH3 = 1.5 * LHV_H2_MOL - LHV_NH3_MOL   # 45.94 kJ/mol NH3 (first-law, 25 C)


# --------------------------------------------------------------------------------------------------------
# stoichiometry of partially cracked fuel
# --------------------------------------------------------------------------------------------------------
def cracked_share_for_h2_fraction(y_h2: float, conversion: float = 1.0) -> float:
    """Share f of the NH3 sent through the cracker so the fuel gas has H2 mole fraction y (N2 counted).

    Per mol NH3 fed: cracked m = f X; gas = (1 - m) NH3 + 1.5 m H2 + 0.5 m N2, total 1 + m; y = 1.5 m / (1 + m)
    -> m = y / (1.5 - y). The maximum is y = 0.75 at m = 1 (fully cracked, unpurified).
    """
    if not 0 <= y_h2 < 0.75 + 1e-12:
        raise ValueError("H2 fraction must be in [0, 0.75] for unpurified cracked NH3")
    m = y_h2 / (1.5 - y_h2)
    f = m / conversion
    if f > 1 + 1e-9:
        raise ValueError("target H2 fraction not reachable at this conversion")
    return min(f, 1.0)


def h2_fraction_of_blend(f: float, conversion: float = 1.0) -> float:
    m = f * conversion
    return 1.5 * m / (1.0 + m)


def alpha_of_cracked_share(f: float, conversion: float) -> float:
    """Ahmad's alpha = NH3 / (NH3 + H2), N2 not counted."""
    m = f * conversion
    return (1.0 - m) / (1.0 - m + 1.5 * m)


def fuel_lhv_mj_per_kg_nh3_fed(f: float, conversion: float) -> float:
    """LHV (MJ) of the gas from 1 kg NH3 of which a share f is cracked at conversion X."""
    m = f * conversion
    per_mol = (1.0 - m) * LHV_NH3_MOL + 1.5 * m * LHV_H2_MOL
    return per_mol / MOLAR_MASS["NH3"]


# --------------------------------------------------------------------------------------------------------
# stored Aspen cracker activities
# --------------------------------------------------------------------------------------------------------
@dataclass
class Cracker:
    case_id: str
    source: str
    conversion: float
    nh3_kg_h: float
    h2_cracked_kg_h: float
    h2_product_kg_h: float
    purity_mole_frac: float
    recovery: float
    cracker_heat_kW: float        # reactor + pre-heater duty (external, after feed/effluent exchanger)
    vaporiser_kW: float
    deficit_kW: float             # net fuel heat deficit after tail-gas firing
    pump_kW: float

    @property
    def crack_heat_MJ_per_kg_nh3(self) -> float:
        return self.cracker_heat_kW * 3.6 / self.nh3_kg_h

    @property
    def deficit_MJ_per_kg_nh3(self) -> float:
        return self.deficit_kW * 3.6 / self.nh3_kg_h

    @property
    def h2_product_per_kg_nh3(self) -> float:
        return self.h2_product_kg_h / self.nh3_kg_h

    @property
    def pump_kWh_per_kg_nh3(self) -> float:
        return self.pump_kW / self.nh3_kg_h


@lru_cache(maxsize=8)
def load_result(case: str) -> SimulationResult:
    with open(ROOT / "results" / "simulations" / f"{case}.json", encoding="utf-8") as fh:
        return SimulationResult.model_validate(json.load(fh))


def load_cracker(case: str = "baseline") -> Cracker:
    r = load_result(case)
    k = r.kpis
    nh3_kmol = r.streams["FEED"].component_mole_flow_kmol_h["NH3"]
    rec = r.inputs.psa_h2_recovery
    return Cracker(case, r.source.value, k.nh3_conversion, nh3_kmol * MOLAR_MASS["NH3"],
                   k.h2_in_cracked_gas_kmol_h * MOLAR_MASS["H2"], k.h2_product_kg_h, k.h2_purity_mole_frac, rec,
                   k.reactor_duty_kW + k.preheat_duty_kW, k.vaporiser_duty_kW, k.net_fuel_heat_deficit_kW,
                   k.pump_power_kW or 0.0)


# --------------------------------------------------------------------------------------------------------
# emissions of one pathway activity set
# --------------------------------------------------------------------------------------------------------
@dataclass
class Activity:
    """Per functional unit. nh3_kg includes NH3 burnt for heat."""
    id: str
    label: str
    product: str                 # 'H2' or 'electricity'
    functional_unit: str
    nh3_kg: float
    aux_kWh: float
    efficiency: float            # product energy / total NH3 LHV
    n2o_kgCO2e: float = 0.0
    no_kg: float | None = None   # NO (local pollutant), reported separately; None = not quantified
    cracker_h2_kg_h: float = 0.0  # cracker size basis (kg H2/h in cracked gas) at plant scale, for capex
    capex_kind: str = "none"     # none | unpurified | purified
    h2_fraction_vol: float | None = None
    cracked_share: float | None = None
    purity_note: str = ""
    heat_mode: str = ""
    cracker_nh3_kg_h: float = 0.0  # NH3 through the cracker at plant scale (reference CAPEX size driver)


def carbon_intensity(a: Activity, route_ef: float, distance_km: float, grid: float | None = None,
                     boil_off: float | None = None, ship_ef: float | None = None) -> dict:
    """kg CO2e per functional unit; NOx is NOT included."""
    g = lca.f("grid_ef_singapore_2024") if grid is None else grid
    ship = lca.ship_kg_per_kg_nh3(distance_km, ship_ef)
    bo = lca.f("boil_off_fraction") if boil_off is None else boil_off
    up = a.nh3_kg * route_ef / (1.0 - bo)
    tr = a.nh3_kg * ship / (1.0 - bo)
    el = a.aux_kWh * g
    tot = up + tr + el + a.n2o_kgCO2e
    return {"upstream_ammonia": up, "shipping": tr, "electricity": el, "direct_n2o": a.n2o_kgCO2e, "total": tot}


# --------------------------------------------------------------------------------------------------------
# hydrogen pathways (FU 1 kg usable H2)
# --------------------------------------------------------------------------------------------------------
def hydrogen_activity(case: str, id_: str, label: str, purity_note: str) -> Activity:
    c = load_cracker(case)
    heat_nh3 = c.deficit_MJ_per_kg_nh3 / P.LHV_NH3_MJ_KG        # kg extra NH3 per kg NH3 fed (efficiency 1, as AmCraX)
    per_h2 = 1.0 / c.h2_product_per_kg_nh3
    nh3 = per_h2 * (1.0 + heat_nh3)
    eff = P.LHV_H2_MJ_KG / (nh3 * P.LHV_NH3_MJ_KG)
    return Activity(id_, label, "H2", "1 kg H2 at stated purity", nh3, c.pump_kWh_per_kg_nh3 * per_h2, eff,
                    cracker_h2_kg_h=c.h2_product_kg_h, capex_kind="purified", purity_note=purity_note,
                    heat_mode="tail gas + extra NH3 (stored Aspen heat deficit)", cracker_nh3_kg_h=c.nh3_kg_h)


def hydrogen_activity_purification(config_id: str, grade_key: str, id_: str, label: str) -> tuple[Activity, dict]:
    """H2 pathway from the purification workstream (results/research/purification/purification_study.json).

    Returns the activity per kg usable H2 (NH3 feed + NH3 for the net heat deficit, compression electricity at the
    study's delivery pressure) and the study's cost record. Source type of the config: python (reduced-order model
    on the stored Aspen cracked gas)."""
    with open(ROOT / "results" / "research" / "purification" / "purification_study.json", encoding="utf-8") as fh:
        study = json.load(fh)
    case = study["cases"]["20bar_baseline"]
    cfg = {c["id"]: c for c in case["configs"]}[config_id]
    c0 = load_cracker("baseline")
    h2_kg_h = cfg["product_h2_kg_h"]
    heat_kW = cfg["net_heat_deficit_kW"]
    nh3 = c0.nh3_kg_h / h2_kg_h + heat_kW * 3.6 / P.LHV_NH3_MJ_KG / h2_kg_h
    cost = cfg["costs"][grade_key]
    el = c0.pump_kWh_per_kg_nh3 * c0.nh3_kg_h / h2_kg_h + cost["compression_kWh_per_kg_h2"]
    a = Activity(id_, label, "H2", "1 kg H2 at stated purity", nh3, el, P.LHV_H2_MJ_KG / (nh3 * P.LHV_NH3_MJ_KG),
                 cracker_h2_kg_h=h2_kg_h, capex_kind="purified", purity_note=f"{cfg['product_purity_h2_mole_frac'] * 100:.3f} mol% H2, recovery {cfg['h2_recovery']:.3f}",
                 heat_mode="tail gas + extra NH3", cracker_nh3_kg_h=c0.nh3_kg_h)
    return a, cost


def hydrogen_cost(case: str, nh3_price: float, hours: float = P.HOURS_PER_YEAR, electricity: float | None = None,
                  capex_mode: str = "reference") -> dict:
    """LCOH of a stored Aspen case on the reference scenario (amcrax.economics.singapore.evaluate)."""
    ov = {"operating_hours_h_per_yr": hours, "capex_mode": capex_mode,
          "electricity_price_USD_per_kWh": P.ELECTRICITY_USD_KWH if electricity is None else electricity}
    e = sg_evaluate(load_result(case), nh3_price, ov)
    return {"USD_per_kg": e["lcoh_USD_per_kg"], "breakdown": e["breakdown_USD_per_kg"],
            "SGD_per_kg": e["lcoh_SGD_per_kg"], "capex_total_USD": e["capex"]["total_capex_USD"]}


# --------------------------------------------------------------------------------------------------------
# power pathways (FU 1 MWh_e). Plant basis: Ahmad's 4.667 kg/s NH3 total mass flow.
# --------------------------------------------------------------------------------------------------------
def eta_exhaust_integrated(f: float) -> float:
    """Electricity per kg NH3 (MJ), linear in the cracked share between Ahmad's direct and fully cracked points.
    Linear interpolation is an ASSUMPTION (Ahmad gives only the end points in the main text)."""
    return P.ELEC_MJ_PER_KG_DIRECT + f * (P.ELEC_MJ_PER_KG_FULL - P.ELEC_MJ_PER_KG_DIRECT)


def _n2o_per_MWh(nh3_energy_share: float) -> float:
    return lca.n2o_noX_per_MWh()["N2O_kgCO2e_per_MWh"] * nh3_energy_share


def power_activity(kind: str, y_h2: float | None = None, case: str = "baseline", gain_scale: float = 1.0,
                   eta_h2_fuel: float | None = None) -> Activity:
    """kind: direct | partial_exhaust | partial_fired | full_exhaust | full_fired | full_purified | blend_purified.

    gain_scale scales the exhaust-integration efficiency gain (1 = Ahmad end points, 0 = no gain). The exhaust-heated
    kinds take their electricity per kg NH3 from Ahmad's system efficiencies (cracker heat internal); they do NOT use
    ETA_GT_GAS, so Ahmad's gain is counted once.
    eta_h2_fuel (Phase 2, optional): combined-cycle efficiency on the LHV of the H2-rich fuel actually fired, for the
    fired, purified and blend kinds. None keeps the Phase 1 assumption ETA_GT_GAS (copy of the direct-NH3 value).
    """
    eta_gas = P.ETA_GT_GAS if eta_h2_fuel is None else eta_h2_fuel
    c = load_cracker(case)
    X = c.conversion
    heat_nh3_per_kg_cracked = c.crack_heat_MJ_per_kg_nh3 / P.LHV_NH3_MJ_KG
    if kind == "direct":
        f = 0.0
    elif kind in ("full_exhaust", "full_fired"):
        f = 1.0
    elif kind in ("partial_exhaust", "partial_fired"):
        f = cracked_share_for_h2_fraction(y_h2, X)
    elif kind == "full_purified":
        f = 1.0
    elif kind == "blend_purified":
        f = None  # solved below
    else:
        raise ValueError(kind)

    # ---- electricity (MJ) and total NH3 (kg) per kg NH3 supplied to the GT-side system ----
    if kind in ("direct", "partial_exhaust", "full_exhaust"):
        elec = P.ELEC_MJ_PER_KG_DIRECT + gain_scale * (eta_exhaust_integrated(f) - P.ELEC_MJ_PER_KG_DIRECT)
        total_nh3 = 1.0
        h2f = h2_fraction_of_blend(f, X)
        nh3_energy_share = max(0.0, (1 - f * X) * P.LHV_NH3_MJ_KG / fuel_lhv_mj_per_kg_nh3_fed(f, X))
        cracked = f
        heat_mode = "exhaust-heated cracker (literature efficiency)" if f > 0 else "none"
        cap = "unpurified" if f > 0 else "none"
        pure = ""
    elif kind in ("partial_fired", "full_fired"):
        elec = eta_gas * fuel_lhv_mj_per_kg_nh3_fed(f, X)
        total_nh3 = 1.0 + f * heat_nh3_per_kg_cracked
        h2f = h2_fraction_of_blend(f, X)
        nh3_energy_share = max(0.0, (1 - f * X) * P.LHV_NH3_MJ_KG / fuel_lhv_mj_per_kg_nh3_fed(f, X))
        cracked = f
        heat_mode = "cracker heat from extra NH3 (stored Aspen reactor + pre-heater duty)"
        cap, pure = "unpurified", ""
    elif kind == "full_purified":
        h2p = c.h2_product_per_kg_nh3
        elec = eta_gas * h2p * P.LHV_H2_MJ_KG
        total_nh3 = 1.0 + c.deficit_MJ_per_kg_nh3 / P.LHV_NH3_MJ_KG
        h2f, nh3_energy_share, cracked = 1.0, 0.0, 1.0
        heat_mode = "tail gas + extra NH3 (stored Aspen heat deficit)"
        cap, pure = "purified", f"PSA product {c.purity_mole_frac * 100:.3f} mol% H2 (recovery {c.recovery})"
    else:  # blend_purified: share g of NH3 cracked and purified, rest NH3 direct; solve for H2 mole fraction y
        h2p = c.h2_product_per_kg_nh3

        def yfun(g):
            n_h2 = g * h2p / MOLAR_MASS["H2"]
            n_nh3 = (1 - g) / MOLAR_MASS["NH3"]
            return n_h2 / (n_h2 + n_nh3) - y_h2

        g = brentq(yfun, 1e-9, 1.0)
        elec = eta_gas * ((1 - g) * P.LHV_NH3_MJ_KG + g * h2p * P.LHV_H2_MJ_KG)
        total_nh3 = 1.0 + g * c.deficit_MJ_per_kg_nh3 / P.LHV_NH3_MJ_KG
        n_h2 = g * h2p / MOLAR_MASS["H2"]
        n_nh3 = (1 - g) / MOLAR_MASS["NH3"]
        h2f = n_h2 / (n_h2 + n_nh3)
        nh3_energy_share = (1 - g) * P.LHV_NH3_MJ_KG / ((1 - g) * P.LHV_NH3_MJ_KG + g * h2p * P.LHV_H2_MJ_KG)
        cracked = g
        heat_mode = "tail gas + extra NH3 (stored Aspen heat deficit)"
        cap = "purified"
        pure = f"blend of NH3 + PSA H2 ({c.purity_mole_frac * 100:.3f} mol%)"

    # electricity per kg of TOTAL NH3 (incl. NH3 burnt for heat); kg total NH3 per MWh
    elec_per_kg_total = elec / total_nh3
    nh3_per_MWh = 3600.0 / elec_per_kg_total
    eff = elec_per_kg_total / P.LHV_NH3_MJ_KG
    # cracker size at plant scale (Ahmad basis 4.667 kg/s NH3 total)
    m_total_h = P.AHMAD_MASS_FLOW_KG_S * 3600.0
    if kind in ("full_purified",):
        nh3_cracked_h = m_total_h / total_nh3
        cracker_h2 = nh3_cracked_h * c.h2_product_per_kg_nh3
    elif kind == "blend_purified":
        nh3_cracked_h = m_total_h / total_nh3 * cracked
        cracker_h2 = nh3_cracked_h * c.h2_product_per_kg_nh3
    else:
        nh3_cracked_h = m_total_h / total_nh3 * (cracked or 0.0)
        cracker_h2 = nh3_cracked_h * lca.KG_H2_PER_KG_NH3 * X
    n2o = _n2o_per_MWh(nh3_energy_share) if kind != "full_purified" else 0.0
    nh3_through_cracker = nh3_cracked_h if kind in ("full_purified", "blend_purified") else m_total_h / total_nh3 * (cracked or 0.0)
    return Activity(
        cracker_nh3_kg_h=nh3_through_cracker,
        id=f"{kind}" + (f"_{int(round(y_h2 * 100))}" if y_h2 is not None else ""),
        label=kind.replace("_", " "), product="electricity", functional_unit="1 MWh net electricity",
        nh3_kg=nh3_per_MWh, aux_kWh=c.pump_kWh_per_kg_nh3 * nh3_per_MWh * (cracked or 0.0), efficiency=eff,
        n2o_kgCO2e=n2o, no_kg=(lca.n2o_noX_per_MWh()["NO_kg_per_MWh"] if kind == "direct" else None),
        cracker_h2_kg_h=cracker_h2, capex_kind=cap, h2_fraction_vol=h2f, cracked_share=cracked,
        purity_note=pure, heat_mode=heat_mode)


def power_cost(a: Activity, nh3_price: float, hours: float = P.POWER_PLANT_HOURS_PER_YEAR,
               discount: float = P.DISCOUNT_RATE, life: float = P.PLANT_LIFE_YR,
               mass_basis_kg_s: float = P.AHMAD_MASS_FLOW_KG_S,
               electricity_price: float = P.ELECTRICITY_USD_KWH, unpurified_full_correlation: bool = False,
               cracker_capex_factor: float = 1.0, plant_capex_factor: float = 1.0,
               extra_capex_USD_per_kW: float = 0.0) -> dict:
    """LCOE (USD/MWh) of the reference plant (Ahmad basis: 4.667 kg/s total NH3).

    Non-cracker plant TCI = Ahmad Case 2a (181.25 MUSD at 43.1 MW) scaled with (W / 43.1)^0.67 (assumption);
    its fixed O&M = Ahmad's 0.02843 USD/kWh x 43.1 MW x 7200 h, scaled the same way. Cracker TCI from the
    reference-scenario CAPEX method (cho2026_itemised_v1, sized on the NH3 through the cracker; unpurified: PSA and
    adsorber items removed); maintenance + insurance 4.5 % of cracker TCI (Ahmad, named field of the reference
    scenario). Hours, discount and life come from the reference scenario (power_plant fields).

    Phase 2 optional sensitivity arguments (defaults reproduce the stored results): cracker_capex_factor multiplies the
    cracker TCI (and so its 4.5 % O&M); plant_capex_factor multiplies the non-cracker plant TCI only (its fixed O&M is
    kept); extra_capex_USD_per_kW adds a capital item per kW net (for example SCR), annualised with the same CRF and
    without O&M.
    """
    eff_MJ = 3600.0 / a.nh3_kg                       # MJ per kg total NH3
    W_MW = mass_basis_kg_s * eff_MJ                  # MW (kg/s x MJ/kg)
    scale = (W_MW / P.AHMAD_W_NET_2A_MW) ** P.PLANT_SCALE_EXPONENT
    tci_plant = P.AHMAD_TCI_2A_MUSD * 1e6 * scale * plant_capex_factor + extra_capex_USD_per_kW * W_MW * 1e3
    fixed_plant = P.AHMAD_OC_FIXED_2A_USD_PER_KWH * P.AHMAD_W_NET_2A_MW * 1e3 * P.AHMAD_HOURS_IMPLIED * scale
    tci_crk = 0.0
    if a.capex_kind != "none" and a.cracker_nh3_kg_h > 0:
        excl = ("psa", "adsorber") if (a.capex_kind == "unpurified" and not unpurified_full_correlation) else ()
        tci_crk = reference_capex(a.cracker_nh3_kg_h / MOLAR_MASS["NH3"], exclude=excl)["total_capex_USD"] * cracker_capex_factor
    k = crf(discount, life)
    mwh_y = W_MW * hours
    capital = (tci_plant + tci_crk) * k
    fixed = fixed_plant + P.CRACKER_FIXED_OM_FRAC_TCI * tci_crk
    fuel = mass_basis_kg_s * 3600.0 * hours * nh3_price / 1000.0
    elec = a.aux_kWh * mwh_y * electricity_price
    tot = capital + fixed + fuel + elec
    return {"LCOE_USD_per_MWh": tot / mwh_y, "W_net_MW": W_MW, "TCI_MUSD": (tci_plant + tci_crk) / 1e6,
            "TCI_cracker_MUSD": tci_crk / 1e6, "components_USD_per_MWh": {
                "capital": capital / mwh_y, "fixed_om": fixed / mwh_y, "ammonia": fuel / mwh_y, "aux_electricity": elec / mwh_y}}


def breakeven_ef(a: Activity, alt_ci: float, distance_km: float, grid: float | None = None) -> float:
    """NH3 gate emission factor (kg CO2e/kg NH3) at which the pathway equals the alternative's CI per FU."""
    zero = carbon_intensity(a, 0.0, distance_km, grid)["total"]
    return (alt_ci - zero) / a.nh3_kg
