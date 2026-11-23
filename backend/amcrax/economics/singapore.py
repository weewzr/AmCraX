"""Singapore techno-economic framework for an ammonia cracker (workstream E; additive to lcoh.py).

PUBLIC FUNCTION (stable, for other workstreams)
    from amcrax.economics.singapore import evaluate
    out = evaluate(result_or_summary, scenario="grey", overrides=None)

    result_or_summary : an amcrax SimulationResult, a stored result dict (results/simulations/*.json), or a
                        summary dict with keys h2_kg_h, nh3_feed_kmol_h, heat_deficit_kW, cooling_kW, pump_kW,
                        h2_cracked_kmol_h, psa_recovery, tailgas_lhv_kW, tailgas_heat_kW (see extract_summary).
    scenario          : "grey" | "blue" | "green_current" | "green_2030" | "green_2050" (ammonia delivered-price
                        SCENARIOS from data/singapore.yaml, not Singapore transaction prices), or a number
                        (USD/t NH3).
    overrides         : flat dict. Keys of EconomicAssumptions (discount_rate, plant_life_yr, catalyst,
                        catalyst_price_USD_per_kg, catalyst_lifetime_yr, operating_hours_h_per_yr,
                        capex_multiplier, ...) or of SGParams (see below), e.g. electricity_price_USD_per_kWh,
                        carbon_tax_SGD_per_t, heat_fuel ("ammonia" | "natural_gas"), capacity_scale,
                        psa_recovery, capex_mode ("equipment" | "legacy"), h2_price_USD_per_kg, transport_USD_per_kg_H2.
    returns (dict, all USD):
        lcoh_USD_per_kg            levelised cost WITH ammonia feed (feed NH3 + all conversion costs)
        rec_USD_per_kg             reconversion cost = LCOH minus feed-NH3 cost (Cho et al. 2026 Eq. 23);
                                   supplementary NH3 fuel, capital, opex, catalyst, carbon tax stay in REC
        breakdown_USD_per_kg       capex, fixed_opex, ammonia_feed, heat_fuel, electricity, cooling_water,
                                   catalyst, carbon_tax (sums to LCOH; no item is counted twice)
        purification_memo_USD_per_kg  PSA+adsorber capital and fixed charges: a SUB-ALLOCATION of capex and
                                   fixed_opex, NOT an additional cost
        landed_cost_USD_per_kg     LCOH + transport_USD_per_kg_H2 if supplied, else None (no sourced figure)
        npv_USD, irr, payback_yr   at h2_price_USD_per_kg (default scenario in singapore.yaml)
        capex, annual, notes, assumptions

METRIC BOUNDARIES
    LCOH   : cracker plant gate, hydrogen at PSA outlet pressure (no product compression, no storage, no H2
             distribution), ammonia bought delivered to the plant gate at the scenario price.
    REC    : LCOH minus the cost of the contained feed NH3 (same boundary otherwise).
    Landed : only when a sourced transport/distribution cost is supplied.
    NPV/IRR/payback: pre-tax, constant prices, no depreciation, no working capital, construction time 0,
             cash flow = revenue - (fixed opex + variable opex + feed + fuel + carbon tax) from year 1 to
             plant_life_yr, investment = total capital investment in year 0, catalyst replacement smoothed as an
             annual cost. NPV at the discount rate equals (price - LCOH) * annual H2 / CRF.

CARBON TAX TREATMENT
    Applied only to direct (Scope 1) CO2e of the facility, only if the facility total reaches the
    25,000 tCO2e/yr threshold (NEA). Heat from NH3 combustion emits no CO2 (the AmCraX FEED has no carbon).
    Heat from natural gas (heat_fuel="natural_gas") emits 56.1 kg CO2/GJ (IPCC 2006). Upstream or overseas
    emissions of the ammonia are NOT taxed. N2O from ammonia combustion is a covered gas but is NOT quantified
    (no primary-source emission factor available); n2o_tCO2e_per_yr can be supplied by the caller.

REFERENCE SCENARIO (Phase 2): defaults (electricity, FX, carbon tax, H2 selling price, discount rate, plant life,
    operating hours, fixed-opex factors, NH3 scenarios) and the default CAPEX method (capex_mode "reference" =
    cho2026_itemised_v1) come from data/reference_scenario.yaml via amcrax.economics.reference. capex_mode
    "equipment" (Phase 1 Farokhi feed-scaled estimate, LCOH 3.61) and "legacy" (lcoh.py correlation, LCOH 3.92)
    remain selectable for comparison only; both are superseded for research outputs.

LIMITS (Phase 1 'equipment' mode): capex is a screening estimate (Farokhi PEC point scaled per equipment with exponent 0.8 and TCI/PEC
5.93; cost year not stated); no Singapore location factor (none sourced); heat-exchanger capital does not
respond to the heat-integration choice (no sourced cost per area), heat integration acts through fuel/cooling.
"""
from __future__ import annotations

import numbers

from dataclasses import dataclass, field, fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

from .lcoh import EconomicAssumptions, crf, estimate_capex
from .reference import load_reference_scenario, provenance_stamp, reference_capex

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "singapore.yaml"
H2_LHV_KJ_PER_MOL = LHV_KJ_PER_MOL["H2"]

SCENARIOS = ("grey", "blue", "green_current", "green_2030", "green_2050")
EQUIP_KEYS = ("cracker", "psa", "adsorber", "heat_exchangers")


@lru_cache(maxsize=1)
def load_singapore_data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _sg() -> dict:
    return load_singapore_data()


def default_electricity_USD_per_kWh() -> float:
    d = _sg()
    e = d["electricity"]
    usep = e["usep_2025_monthly_SGD_per_MWh"]["value"]
    sgd = sum(usep) / len(usep) / 1000.0 + e["network_cost_SGD_per_kWh"]["value"] + e["fees_SGD_per_kWh"]["value"]
    return sgd / load_reference_scenario().fx_SGD_per_USD


@dataclass
class SGParams:
    nh3_price_USD_per_t: float = 450.0
    electricity_price_USD_per_kWh: float = field(default_factory=lambda: load_reference_scenario().electricity_USD_per_kWh)
    heat_fuel: str = "ammonia"                      # "ammonia" | "natural_gas"
    gas_heat_price_USD_per_kJ: Optional[float] = None  # None -> EconomicAssumptions.fired_heat_price (Kum 2026)
    fuel_efficiency: Optional[float] = None         # None -> EconomicAssumptions.ammonia_fuel_heat_efficiency
    carbon_tax_SGD_per_t: float = field(default_factory=lambda: load_reference_scenario().carbon_tax_SGD_per_t)
    apply_threshold: bool = True
    other_facility_emissions_tCO2e: float = 0.0
    n2o_tCO2e_per_yr: float = 0.0                   # not quantified by default
    capex_mode: str = "reference"                   # "reference" (cho2026_itemised_v1) | "equipment" (Phase 1) | "legacy" (lcoh.py)
    capacity_scale: float = 1.0                     # multiplier on NH3 feed (and all flows)
    psa_recovery: Optional[float] = None            # None -> value in the stored result
    h2_price_USD_per_kg: float = field(default_factory=lambda: load_reference_scenario().h2_selling_price_USD_per_kg)
    transport_USD_per_kg_H2: Optional[float] = None
    labour_scales_with_capacity: bool = False
    capex_scaling_exponent: Optional[float] = None  # None -> 0.8 (Chopra 2026 Eq. 5); 0.7451 = Ahmad 2025 Fig. 6
    reactor_size_driver: Optional[str] = None       # reference mode: None -> yaml ('nh3_feed'); 'catalyst_mass'
    item_size_ratio: Optional[dict] = None          # reference mode: caller size ratio per CAPEX item (e.g. area)


def scenario_price(scenario: Any) -> float:
    if isinstance(scenario, numbers.Real) and not isinstance(scenario, bool):
        return float(scenario)
    return float(load_reference_scenario().nh3_prices_USD_per_t[scenario])


# ------------------------------------------------------------------------------------------ input extraction
def extract_summary(res: Any) -> dict:
    """Reduce a SimulationResult / stored dict / summary dict to the numbers the model needs."""
    if isinstance(res, dict) and "h2_kg_h" in res:
        return dict(res)
    d = res if isinstance(res, dict) else res.model_dump(mode="json")
    k = d["kpis"]
    feed = (d.get("streams") or {}).get("FEED") or {}
    nh3 = (feed.get("component_mole_flow_kmol_h") or {}).get("NH3")
    if not nh3:
        i = d["inputs"]
        nh3 = i["feed_total_kmol_h"] * (1 - i["feed_h2o_mole_frac"])
    pump = k.get("pump_power_kW")
    if pump is None:
        pump = (d.get("blocks", {}).get("PUMP") or {}).get("power_kW") or 0.0
    return {
        "case_id": d.get("case_id"), "source": d.get("source"),
        "heat_integration": d.get("inputs", {}).get("heat_integration"),
        "h2_kg_h": float(k["h2_product_kg_h"]), "nh3_feed_kmol_h": float(nh3),
        "heat_deficit_kW": float(k["net_fuel_heat_deficit_kW"]), "cooling_kW": abs(float(k["cooling_duty_kW"])),
        "pump_kW": float(pump), "h2_cracked_kmol_h": k.get("h2_in_cracked_gas_kmol_h"),
        "psa_recovery": d.get("inputs", {}).get("psa_h2_recovery"),
        "tailgas_lhv_kW": k.get("tailgas_lhv_kW"), "tailgas_heat_kW": k.get("tailgas_combustion_heat_kW"),
    }


def _split_overrides(overrides: Optional[dict]) -> tuple[dict, dict]:
    econ_f = set(EconomicAssumptions.model_fields)
    sg_f = {f.name for f in fields(SGParams)}
    eo, so = {}, {}
    for k, v in (overrides or {}).items():
        if k in sg_f:
            so[k] = v
        elif k in econ_f:
            eo[k] = v
        else:
            raise KeyError(f"unknown override '{k}'")
    return eo, so


# ------------------------------------------------------------------------------------------ equipment CAPEX
def equipment_capex(nh3_feed_kmol_h: float, a: EconomicAssumptions, location_factor: Optional[float] = None,
                    exponent: Optional[float] = None) -> dict:
    c = _sg()["capex_equipment"]
    shares = c["equipment_shares_pct"]["value"]
    s = sum(shares.values())
    pec_ref = c["pec_reference_kUSD"]["value"] * 1e3
    ratio = nh3_feed_kmol_h / c["reference_feed_kmol_h"]["value"]
    n = c["scaling_exponent"]["value"] if exponent is None else exponent
    lf = c["singapore_location_factor"]["value"] if location_factor is None else location_factor
    pec = {k: pec_ref * v / s * ratio ** n * lf for k, v in shares.items()}
    pec_tot = sum(pec.values())
    f = c["tci_over_pec"]["value"]
    tci = pec_tot * f * a.capex_multiplier
    return {"pec_USD": pec, "pec_total_USD": pec_tot, "tci_over_pec": f, "scaling_exponent": n,
            "location_factor": lf, "capex_multiplier": a.capex_multiplier, "total_capex_USD": tci,
            "tci_by_equipment_USD": {k: v * f * a.capex_multiplier for k, v in pec.items()},
            "basis": "Farokhi 2025 PEC point (500 kmol/h) split by Chopra 2026 shares, scaled by feed^0.8, x TCI/PEC 5.93"}


# ------------------------------------------------------------------------------------------ core
def evaluate(result_or_summary: Any, scenario: Any = "grey", overrides: Optional[dict] = None) -> dict:
    s = extract_summary(result_or_summary)
    eo, so = _split_overrides(overrides)
    ref = load_reference_scenario()
    if so.get("capex_mode", "reference") != "legacy":
        # reference scenario owns these EconomicAssumptions fields (caller overrides win)
        eo = {**{k: v for k, v in ref.economic_overrides().items() if k != "electricity_price_USD_per_kWh"}, **eo}
    a = EconomicAssumptions(**eo)
    so = dict(so)
    price = so.pop("nh3_price_USD_per_t", None)
    p = SGParams(nh3_price_USD_per_t=scenario_price(scenario) if price is None else float(price), **so)
    notes: list[str] = []
    sc = p.capacity_scale
    hours = a.operating_hours_h_per_yr

    h2_kg_h, nh3_kmol_h = s["h2_kg_h"], s["nh3_feed_kmol_h"]
    deficit, cooling, pump = s["heat_deficit_kW"], s["cooling_kW"], s["pump_kW"]
    rec = s.get("psa_recovery")
    if p.psa_recovery is not None and rec and s.get("h2_cracked_kmol_h"):
        # linearised re-scaling of the stored result (python, not re-simulated): H2 product ~ recovery;
        # the H2 lost to the tail gas is burnt, so the heat deficit falls by the extra tail-gas heat.
        h2c = float(s["h2_cracked_kmol_h"])
        eff = (s["tailgas_heat_kW"] / s["tailgas_lhv_kW"]) if s.get("tailgas_lhv_kW") else 1.0
        d_lost = h2c * (rec - p.psa_recovery) * 1000.0 / 3600.0 * H2_LHV_KJ_PER_MOL  # kW more H2 lost
        h2_kg_h = h2c * p.psa_recovery * MOLAR_MASS["H2"]
        deficit = deficit - eff * d_lost
        notes.append(f"PSA recovery {rec:g} -> {p.psa_recovery:g}: H2 and tail-gas heat rescaled linearly from the stored "
                     "result (not re-simulated; cooler/exchanger duties and PSA power held).")
        rec = p.psa_recovery
    h2_kg_h *= sc; nh3_kmol_h *= sc; deficit *= sc; cooling *= sc; pump *= sc
    if deficit < 0:
        notes.append(f"Heat surplus {-deficit:.1f} kW not credited.")
        deficit = 0.0
    annual_h2 = h2_kg_h * hours
    nh3_USD_kg = p.nh3_price_USD_per_t / 1000.0
    eff_f = p.fuel_efficiency if p.fuel_efficiency is not None else a.ammonia_fuel_heat_efficiency

    feed_kg_h = nh3_kmol_h * MOLAR_MASS["NH3"]
    fx = ref.fx_SGD_per_USD
    # heat / fuel and direct emissions
    co2_t_yr = 0.0
    if p.heat_fuel == "ammonia":
        fuel_nh3_kg_h = deficit / (LHV_KJ_PER_MOL["NH3"] * eff_f) * 3600.0 * MOLAR_MASS["NH3"] / 1000.0
        heat_USD_yr = fuel_nh3_kg_h * nh3_USD_kg * hours
    elif p.heat_fuel == "natural_gas":
        fuel_nh3_kg_h = 0.0
        price = p.gas_heat_price_USD_per_kJ if p.gas_heat_price_USD_per_kJ is not None else a.fired_heat_price_USD_per_kJ
        gj_yr = deficit / eff_f * 3600.0 / 1e6 * hours
        heat_USD_yr = gj_yr * 1e6 * price
        co2_t_yr = gj_yr * _sg()["gas_and_fuel"]["natural_gas_co2_factor_kg_per_GJ"]["value"] / 1000.0
    else:
        raise ValueError("heat_fuel must be 'ammonia' or 'natural_gas'")
    direct_t = co2_t_yr + p.n2o_tCO2e_per_yr
    thr = ref.carbon_threshold_tCO2e_per_yr
    liable = (not p.apply_threshold) or (direct_t + p.other_facility_emissions_tCO2e >= thr)
    tax_USD_yr = direct_t * p.carbon_tax_SGD_per_t / fx if liable else 0.0
    if direct_t == 0:
        notes.append("Direct CO2e = 0 (ammonia-fuelled heat, no carbon in the feed); N2O not quantified; carbon tax 0.")
    elif not liable:
        notes.append(f"Direct emissions {direct_t:.0f} tCO2e/yr below the {thr} t threshold: no tax liability.")

    elec_kW = pump
    elec_USD_yr = elec_kW * p.electricity_price_USD_per_kWh * hours
    cool_USD_yr = cooling * 3600.0 * a.cooling_water_price_USD_per_kJ * hours
    m_cat = nh3_kmol_h * 1000.0 * a.normal_molar_volume_L_per_mol * 1000.0 / a.catalyst_space_velocity_mL_NH3_per_gcat_h / 1000.0
    if a.catalyst_mass_kg is not None:
        m_cat = a.catalyst_mass_kg * sc
    cat_USD_yr = m_cat * a.resolved_catalyst_price_USD_per_kg() / a.catalyst_lifetime_yr

    # capital
    if p.capex_mode == "legacy":
        capex_USD = estimate_capex(h2_kg_h, a).total_capex_USD
        cap = {"total_capex_USD": capex_USD, "basis": "legacy plant-level correlation (lcoh.py)"}
        tci_eq = None
    elif p.capex_mode == "reference":
        cap = reference_capex(nh3_kmol_h, catalyst_mass_kg=m_cat, reactor_size_driver=p.reactor_size_driver,
                              item_size_ratio=p.item_size_ratio, exponent=p.capex_scaling_exponent,
                              capex_multiplier=a.capex_multiplier)
        capex_USD = cap["total_capex_USD"]
        tci_eq = cap["tci_by_equipment_USD"]
    elif p.capex_mode == "equipment":
        cap = equipment_capex(nh3_kmol_h, a, exponent=p.capex_scaling_exponent)
        capex_USD = cap["total_capex_USD"]
        tci_eq = cap["tci_by_equipment_USD"]
    else:
        raise ValueError("capex_mode must be 'reference', 'equipment' or 'legacy'")
    f = crf(a.discount_rate, a.plant_life_yr)
    maint = a.maintenance_frac_capex_per_yr * capex_USD
    ins = a.insurance_frac_capex_per_yr * capex_USD
    lab = a.labour_USD_per_yr * (sc if p.labour_scales_with_capacity else 1.0)
    overhead = a.plant_overhead_frac_labour_maint * (lab + maint)
    fixed_base = maint + ins + lab + overhead
    fixed_USD_yr = fixed_base * (1.0 + a.g_and_a_frac_fixed_opex)

    annual = {"capex": capex_USD * f, "fixed_opex": fixed_USD_yr, "ammonia_feed": feed_kg_h * nh3_USD_kg * hours,
              "heat_fuel": heat_USD_yr, "electricity": elec_USD_yr, "cooling_water": cool_USD_yr,
              "catalyst": cat_USD_yr, "carbon_tax": tax_USD_yr}
    breakdown = {k: v / annual_h2 for k, v in annual.items()}
    lcoh = sum(breakdown.values())
    rec_cost = lcoh - breakdown["ammonia_feed"]

    purification = None
    if tci_eq is not None:
        pur_tci = tci_eq["psa"] + tci_eq["adsorber"]
        # capital charge + maintenance and insurance (with G&A); labour and overhead not allocated
        pur_yr = pur_tci * (f + (a.maintenance_frac_capex_per_yr + a.insurance_frac_capex_per_yr)
                            * (1.0 + a.g_and_a_frac_fixed_opex))
        purification = pur_yr / annual_h2

    landed = None if p.transport_USD_per_kg_H2 is None else lcoh + p.transport_USD_per_kg_H2
    # NPV / IRR / payback
    opex_yr = sum(v for k, v in annual.items() if k != "capex")
    net = p.h2_price_USD_per_kg * annual_h2 - opex_yr
    n = int(round(a.plant_life_yr))
    npv = -capex_USD + net * (1.0 - (1.0 + a.discount_rate) ** -n) / a.discount_rate if a.discount_rate > 0 else -capex_USD + net * n
    irr = _irr(capex_USD, net, n)
    payback = capex_USD / net if net > 0 else None

    if p.capex_mode == "reference":
        notes.append("Reference CAPEX (cho2026_itemised_v1, 2024 USD) excludes product compression/storage, NOx "
                     "after-treatment, land and taxes; no Singapore location factor (none sourced).")
    elif tci_eq is not None:
        notes.append("Equipment-level CAPEX excludes NOx after-treatment, product compression/storage, land and taxes; "
                     "no Singapore location factor (none sourced).")
    notes.append("Ammonia price is a scenario (delivered, international basis), not a Singapore transaction price.")
    return {
        "case_id": s.get("case_id"), "input_source": s.get("source"), "scenario": scenario if isinstance(scenario, str) else "custom",
        "source_type": "python", "currency": "USD",
        "cost_basis": ref.raw["price_year_label"] if p.capex_mode == "reference" else _sg()["base_year_label"],
        "capex_mode": p.capex_mode, "fx_SGD_per_USD": fx, "reference_scenario": provenance_stamp(),
        "lcoh_SGD_per_kg": lcoh * fx, "rec_SGD_per_kg": rec_cost * fx,
        "breakdown_SGD_per_kg": {k: v * fx for k, v in breakdown.items()},
        "npv_SGD": npv * fx, "capex_total_SGD": capex_USD * fx,
        "fixed_opex_detail_USD_per_yr": {"maintenance": maint, "insurance": ins, "labour": lab, "plant_overhead": overhead,
                                         "g_and_a": fixed_base * a.g_and_a_frac_fixed_opex},
        "nh3_price_USD_per_t": p.nh3_price_USD_per_t, "h2_product_kg_h": h2_kg_h, "annual_h2_kg": annual_h2,
        "lcoh_USD_per_kg": lcoh, "rec_USD_per_kg": rec_cost, "breakdown_USD_per_kg": breakdown,
        "purification_memo_USD_per_kg": purification, "landed_cost_USD_per_kg": landed,
        "npv_USD": npv, "irr": irr, "payback_yr": payback, "h2_price_USD_per_kg": p.h2_price_USD_per_kg,
        "kg_nh3_feed_per_kg_h2": feed_kg_h / h2_kg_h, "kg_nh3_fuel_per_kg_h2": fuel_nh3_kg_h / h2_kg_h,
        "catalyst_mass_kg": m_cat, "direct_emissions_tCO2e_per_yr": direct_t, "carbon_tax_liable": liable,
        "crf": f, "capex": cap, "annual_USD_per_yr": annual, "notes": notes,
        "assumptions": {"economic": a.model_dump(), "singapore": p.__dict__},
    }


def _irr(capex: float, net: float, n: int) -> Optional[float]:
    if net <= 0 or net * n <= capex:
        return None
    lo, hi = 0.0, 10.0
    def npv(r: float) -> float:
        return -capex + net * (1.0 - (1.0 + r) ** -n) / r if r > 0 else -capex + net * n
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def breakeven_nh3_price(result_or_summary: Any, target_USD_per_kg: float, overrides: Optional[dict] = None,
                        metric: str = "lcoh_USD_per_kg") -> Optional[float]:
    """NH3 price (USD/t) at which the metric equals the target (LCOH is linear in the NH3 price)."""
    o = dict(overrides or {})
    l0 = evaluate(result_or_summary, 0.0, o)[metric]
    l1 = evaluate(result_or_summary, 1000.0, o)[metric]
    p = (target_USD_per_kg - l0) / ((l1 - l0) / 1000.0)
    return p if p >= 0 else None

