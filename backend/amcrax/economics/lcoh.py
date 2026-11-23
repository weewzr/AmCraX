"""Levelised cost of hydrogen (LCOH) for an AmCraX SimulationResult.

LEGACY CORRELATION, SUPERSEDED FOR RESEARCH OUTPUTS BY THE REFERENCE SCENARIO. This module is the version 1 basis
of the core stored results (results/simulations/economics_*.json, LCOH 3.918842 USD/kg for the baseline) and is
kept unchanged for backwards compatibility. Research outputs (results/research/**) use the unified reference
scenario instead: backend/amcrax/data/reference_scenario.yaml via amcrax.economics.reference and
amcrax.economics.singapore.evaluate (CAPEX method cho2026_itemised_v1). See docs/research/unified_baseline.md.

LCOH = (CAPEX * CRF + fixed OPEX + variable OPEX) / annual H2 product      [cho2026nickel p.7 Eqs. 15-17]
CRF  = i (1+i)^n / ((1+i)^n - 1)

CAPEX is a preliminary capacity-factored estimate (C2 = C1 (S2/S1)^n) from literature plant-level data
(data/economics.yaml, capex_references). No CEPCI escalation is applied (conflicting 2024 CEPCI values in the
library); costs stay in their source cost year and the result is labelled accordingly.
"""
from __future__ import annotations

from typing import Iterable, Optional

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, DataSource, SimulationResult

from .models import (
    CapexDetail,
    CapexReferenceEstimate,
    EconomicAssumptions,
    InputProvenance,
    LCOHResult,
    TornadoBar,
    load_economics_data,
)

#: 2 NH3 -> N2 + 3 H2 at 100 % conversion and recovery: kg NH3 per kg H2 (= 5.63).
STOICHIOMETRIC_KG_NH3_PER_KG_H2: float = 2.0 * MOLAR_MASS["NH3"] / (3.0 * MOLAR_MASS["H2"])

CATEGORIES = ("capex", "fixed_opex", "ammonia_feed", "imported_heat", "electricity", "cooling_water", "catalyst")


def crf(discount_rate: float, life_yr: float) -> float:
    """Capital recovery factor; 1/n for a zero discount rate."""
    i, n = float(discount_rate), float(life_yr)
    if n <= 0:
        raise ValueError("life_yr must be > 0")
    if i == 0.0:
        return 1.0 / n
    f = (1.0 + i) ** n
    return i * f / (f - 1.0)


# ----------------------------------------------------------------------------------------------- CAPEX
def _capex_references(capacity_kg_h: float, a: EconomicAssumptions) -> dict[str, CapexReferenceEstimate]:
    ref = load_economics_data()["capex_references"]
    out: dict[str, CapexReferenceEstimate] = {}

    r = ref["ahmad2025_correlation"]
    s_t_h = capacity_kg_h / 1000.0
    lo, hi = r["range_t_H2_per_h"]
    adj = [] if lo <= s_t_h <= hi else [f"capacity {s_t_h:.4g} t/h outside fit range {lo}-{hi} t/h (extrapolation)"]
    out["ahmad2025_correlation"] = CapexReferenceEstimate(
        method="ahmad2025_correlation", scaled_capex_USD=1e6 * r["a_MUSD"] * s_t_h ** r["b"], exponent=r["b"],
        cost_year=str(r["cost_year"]), citekey=r["citekey"], page=str(r["page"]), locator=r["locator"], adjustments=adj)

    n = a.capacity_exponent
    r = ref["chopra2026_point"]
    c1 = r["capex_MUSD"] * 1e6
    adj = []
    if a.chopra_exclude_compressor:
        c1 *= 1.0 - r["compressor_share_of_TCI"]["value"]
        adj.append(f"350 bar compressor share {r['compressor_share_of_TCI']['value']:.0%} removed (derived)")
    if a.chopra_remove_location_factor:
        c1 /= r["location_factor_india"]["value"]
        adj.append(f"India location factor {r['location_factor_india']['value']} removed (derived)")
    s1 = r["capacity_kg_H2_per_d"] / 24.0
    out["chopra2026_point"] = CapexReferenceEstimate(
        method="chopra2026_point", reference_capacity_kg_H2_h=s1, reference_capex_USD=c1,
        scaled_capex_USD=c1 * (capacity_kg_h / s1) ** n, exponent=n, cost_year=str(r["cost_year"]),
        citekey=r["citekey"], page=str(r["page"]), locator=r["locator"], adjustments=adj)

    r = ref["farokhi2025_point"]
    s1 = r["h2_kg_per_kg_nh3"] * r["nh3_feed_kmol_h"] * MOLAR_MASS["NH3"]
    c1 = r["tci_kUSD"] * 1e3
    out["farokhi2025_point"] = CapexReferenceEstimate(
        method="farokhi2025_point", reference_capacity_kg_H2_h=s1, reference_capex_USD=c1,
        scaled_capex_USD=c1 * (capacity_kg_h / s1) ** n, exponent=n, cost_year=str(r["cost_year"]),
        citekey=r["citekey"], page=str(r["page"]), locator=r["locator"],
        adjustments=["reference H2 capacity derived as 0.128 kg/kg x 500 kmol/h x M_NH3", "kUSD unit inferred"])
    return out


def _equipment_breakdown(total: float) -> tuple[dict[str, float], str]:
    eq = load_economics_data()["equipment_shares"]
    shares = {k: v for k, v in eq["shares_pct"].items() if k != "compressor"}
    s = sum(shares.values())
    return ({k: total * v / s for k, v in shares.items()},
            f"Indicative split only: {eq['basis']} ({eq['citekey']} p.{eq['page']} {eq['locator']})")


def estimate_capex(capacity_kg_H2_h: float, a: EconomicAssumptions) -> CapexDetail:
    refs = _capex_references(capacity_kg_H2_h, a)
    if a.capex_method == "fixed":
        if a.capex_fixed_USD is None:
            raise ValueError("capex_method 'fixed' requires capex_fixed_USD")
        sel = CapexReferenceEstimate(method="fixed", scaled_capex_USD=a.capex_fixed_USD, cost_year="caller supplied",
                                     source=DataSource.ASSUMPTION, adjustments=["caller-supplied CAPEX"])
    else:
        sel = refs[a.capex_method]
    total = sel.scaled_capex_USD * a.capex_multiplier
    br, note = _equipment_breakdown(total)
    return CapexDetail(method=sel.method, capacity_kg_H2_h=capacity_kg_H2_h, total_capex_USD=total,
                       capex_multiplier=a.capex_multiplier, cost_basis=load_economics_data()["cost_basis"],
                       selected=sel, alternatives=[v for k, v in refs.items() if k != sel.method],
                       equipment_breakdown_USD=br, equipment_breakdown_note=note)


# ----------------------------------------------------------------------------------------------- inputs
def _feed_mass_kg_h(res: SimulationResult) -> float:
    s = res.streams.get("FEED")
    if s is not None and s.mass_flow_kg_h:
        return float(s.mass_flow_kg_h)
    x = res.inputs.feed_h2o_mole_frac
    return res.inputs.feed_total_kmol_h * ((1 - x) * MOLAR_MASS["NH3"] + x * MOLAR_MASS["H2O"])


def _feed_nh3_kmol_h(res: SimulationResult) -> float:
    s = res.streams.get("FEED")
    if s is not None and s.component_mole_flow_kmol_h.get("NH3"):
        return float(s.component_mole_flow_kmol_h["NH3"])
    return res.inputs.feed_total_kmol_h * (1 - res.inputs.feed_h2o_mole_frac)


def _pump_power_kW(res: SimulationResult) -> float:
    if res.kpis.pump_power_kW is not None:
        return float(res.kpis.pump_power_kW)
    b = res.blocks.get("PUMP")
    if b is not None and b.power_kW is not None:
        return float(b.power_kW)
    raise ValueError("pump power not available in SimulationResult")


def _req(v: Optional[float], name: str) -> float:
    if v is None:
        raise ValueError(f"SimulationResult.kpis.{name} is None - LCOH cannot be computed without it")
    return float(v)


def catalyst_mass_kg(res: SimulationResult, a: EconomicAssumptions) -> float:
    if a.catalyst_mass_kg is not None:
        return a.catalyst_mass_kg
    mL_h = _feed_nh3_kmol_h(res) * 1000.0 * a.normal_molar_volume_L_per_mol * 1000.0
    return mL_h / a.catalyst_space_velocity_mL_NH3_per_gcat_h / 1000.0


# ----------------------------------------------------------------------------------------------- provenance
def _provenance(a: EconomicAssumptions) -> dict[str, InputProvenance]:
    d = load_economics_data()["defaults"]
    dflt = EconomicAssumptions()
    out: dict[str, InputProvenance] = {}
    for name, val in a.model_dump().items():
        entry = d.get(name)
        if name == "catalyst_price_USD_per_kg":
            entry = d[name][a.catalyst]
            val = a.resolved_catalyst_price_USD_per_kg()
            overridden = a.catalyst_price_USD_per_kg is not None and a.catalyst_price_USD_per_kg != entry["value"]
        else:
            overridden = val != getattr(dflt, name)
        if entry is None or overridden:
            out[name] = InputProvenance(value=val, source=DataSource.ASSUMPTION,
                                        note="caller-supplied value" if overridden else "AmCraX option (see economics.yaml)")
            continue
        src = DataSource.LITERATURE if entry.get("source") == "literature" else DataSource.ASSUMPTION
        out[name] = InputProvenance(value=val, unit=str(entry.get("unit", "")), source=src, citekey=entry.get("citekey"),
                                    page=None if entry.get("page") is None else str(entry.get("page")),
                                    locator=entry.get("locator"), note=entry.get("rationale") or entry.get("note"))
    return out


# ----------------------------------------------------------------------------------------------- LCOH
def compute_lcoh(result: SimulationResult, assumptions: Optional[EconomicAssumptions] = None) -> LCOHResult:
    a = assumptions or EconomicAssumptions()
    k = result.kpis
    h2_kg_h = _req(k.h2_product_kg_h, "h2_product_kg_h")
    if h2_kg_h <= 0:
        raise ValueError("H2 product flow must be > 0")
    deficit_kW = _req(k.net_fuel_heat_deficit_kW, "net_fuel_heat_deficit_kW")
    cooling_kW = abs(_req(k.cooling_duty_kW, "cooling_duty_kW"))
    hours = a.operating_hours_h_per_yr
    annual_h2 = h2_kg_h * hours
    notes: list[str] = []

    # Ammonia is priced on its contained NH3 (the same basis as the environmental module and the
    # stoichiometric floor). The water carried in the feed (0.2 mol% by default) is not priced.
    # An earlier version priced the whole feed stream as ammonia, which overstated the feed cost
    # by the water mass fraction (0.2 %); found by the independent code review.
    feed_kg_h = _feed_nh3_kmol_h(result) * MOLAR_MASS["NH3"]
    feed_stream_kg_h = _feed_mass_kg_h(result)
    nh3_USD_per_kg = a.nh3_price_USD_per_t / 1000.0

    heat_kW = deficit_kW if (deficit_kW > 0 or a.credit_heat_surplus) else 0.0
    if deficit_kW < 0 and not a.credit_heat_surplus:
        notes.append(f"Heat surplus {-deficit_kW:.1f} kW not credited (credit_heat_surplus = False).")
    fuel_kg_h = 0.0
    if a.heat_import_mode == "ammonia_fuel":
        fuel_kg_h = heat_kW / (LHV_KJ_PER_MOL["NH3"] * a.ammonia_fuel_heat_efficiency) * 3600.0 * MOLAR_MASS["NH3"] / 1000.0
        heat_USD_h = fuel_kg_h * nh3_USD_per_kg
    else:
        heat_USD_h = heat_kW * 3600.0 * a.fired_heat_price_USD_per_kJ

    elec_kW = _pump_power_kW(result) + a.compression_power_kW
    m_cat = catalyst_mass_kg(result, a)
    cat_USD_yr = m_cat * a.resolved_catalyst_price_USD_per_kg() / a.catalyst_lifetime_yr

    cap = estimate_capex(h2_kg_h, a)
    f = crf(a.discount_rate, a.plant_life_yr)
    capex_yr = cap.total_capex_USD * f
    maint = a.maintenance_frac_capex_per_yr * cap.total_capex_USD
    ins = a.insurance_frac_capex_per_yr * cap.total_capex_USD
    overhead = a.plant_overhead_frac_labour_maint * (a.labour_USD_per_yr + maint)
    fixed_base = maint + ins + a.labour_USD_per_yr + overhead
    fixed_yr = fixed_base * (1.0 + a.g_and_a_frac_fixed_opex)

    annual = {
        "capex": capex_yr,
        "fixed_opex": fixed_yr,
        "ammonia_feed": feed_kg_h * nh3_USD_per_kg * hours,
        "imported_heat": heat_USD_h * hours,
        "electricity": elec_kW * a.electricity_price_USD_per_kWh * hours,
        "cooling_water": cooling_kW * 3600.0 * a.cooling_water_price_USD_per_kJ * hours,
        "catalyst": cat_USD_yr,
    }
    breakdown = {c: v / annual_h2 for c, v in annual.items()}
    total = sum(breakdown.values())
    annual_detail = dict(annual)
    annual_detail.update({"fixed_opex.maintenance": maint, "fixed_opex.insurance": ins,
                          "fixed_opex.labour": a.labour_USD_per_yr, "fixed_opex.plant_overhead": overhead,
                          "fixed_opex.g_and_a": fixed_base * a.g_and_a_frac_fixed_opex, "total": sum(annual.values())})

    if result.source != DataSource.ASPEN:
        notes.append(f"Process data source is '{result.source.value}', not Aspen Plus.")
    notes.append(f"Ammonia feed priced on contained NH3: {feed_kg_h:.2f} kg/h of the {feed_stream_kg_h:.2f} kg/h feed stream "
                 "(feed water is not priced).")
    notes.append("CAPEX is a plant-level correlation on hydrogen capacity: it does not respond to heat-integration "
                 "choices (exchanger area), PSA size or catalyst volume.")
    notes.append(f"Catalyst inventory {m_cat:.1f} kg ({a.catalyst}) sized from the cho2026nickel space velocity "
                 "(the AmCraX cracker is an equilibrium block).")
    notes.append(f"PSA H2 recovery {result.inputs.psa_h2_recovery:g} taken from the simulation inputs "
                 "(assumption; literature 0.71-0.81).")
    notes.append("Excluded: NOx after-treatment, TSA NH3 polishing, H2 compression/storage, land, taxes, "
                 "working capital beyond the source CAPEX basis.")

    prov = _provenance(a)
    prov["psa_h2_recovery"] = InputProvenance(value=result.inputs.psa_h2_recovery, source=DataSource.ASSUMPTION,
                                              note=load_economics_data()["defaults"]["psa_h2_recovery_note"]["rationale"])
    prov["process_data"] = InputProvenance(value=result.case_id, source=result.source, note="SimulationResult KPIs")

    return LCOHResult(
        case_id=result.case_id, input_source=result.source, lcoh_USD_per_kg=total,
        breakdown_USD_per_kg=breakdown, annual_costs_USD_per_yr=annual_detail, annual_h2_kg=annual_h2,
        h2_product_kg_h=h2_kg_h, crf=f, capex=cap,
        kg_nh3_feed_per_kg_h2=feed_kg_h / h2_kg_h, kg_nh3_fuel_per_kg_h2=fuel_kg_h / h2_kg_h,
        stoichiometric_floor_kg_nh3_per_kg_h2=STOICHIOMETRIC_KG_NH3_PER_KG_H2,
        reconversion_cost_USD_per_kg=total - breakdown["ammonia_feed"],
        cost_basis=load_economics_data()["cost_basis"], assumptions=a, provenance=prov, notes=notes)


# ----------------------------------------------------------------------------------------------- sensitivity
def default_variations(a: Optional[EconomicAssumptions] = None) -> dict[str, tuple[float, float, str]]:
    """Literature-sourced low/high values for the tornado (parameter -> (low, high, source))."""
    a = a or EconomicAssumptions()
    cat = a.resolved_catalyst_price_USD_per_kg()
    return {
        "nh3_price_USD_per_t": (300.0, 610.0, "cho2026nickel p.7 Table 8"),
        "electricity_price_USD_per_kWh": (0.042, 0.126, "cho2026nickel p.7 Table 8"),
        "capex_multiplier": (0.5, 1.5, "cho2026nickel p.7 Table 8 (CAPEX -50 %/+50 %)"),
        "catalyst_price_USD_per_kg": (0.5 * cat, 2.0 * cat, "cho2026nickel p.7 Table 8 (-50 %/+100 %)"),
        "catalyst_lifetime_yr": (1.0, 4.0, "cho2026nickel p.7 Table 8"),
        "discount_rate": (0.085, 0.10, "library range: cho2026nickel 0.085 - kum/farokhi/chopra/ahmad 0.10"),
        "plant_life_yr": (20.0, 25.0, "library range: chopra2026decentralized/mehr 20 - cho/kum/farokhi 25"),
        "operating_hours_h_per_yr": (7000.0, 8000.0, "library range: kum2026heatintegrated 7000 - cho2026nickel 8000"),
        "maintenance_frac_capex_per_yr": (0.025, 0.05, "library range: richard 0.025 - kum 0.05"),
    }


def _with(a: EconomicAssumptions, **kw) -> EconomicAssumptions:
    return a.model_copy(update=kw)


def lcoh_sensitivity(result: SimulationResult, assumptions: Optional[EconomicAssumptions] = None,
                     variations: Optional[dict[str, tuple]] = None) -> list[TornadoBar]:
    """One-at-a-time sensitivity. Returns bars sorted by LCOH swing (largest first)."""
    a = assumptions or EconomicAssumptions()
    var = variations if variations is not None else default_variations(a)
    base = compute_lcoh(result, a).lcoh_USD_per_kg
    bars = []
    for p, spec in var.items():
        lo, hi = float(spec[0]), float(spec[1])
        src = spec[2] if len(spec) > 2 else "caller-supplied"
        bv = a.resolved_catalyst_price_USD_per_kg() if p == "catalyst_price_USD_per_kg" else float(getattr(a, p))
        bars.append(TornadoBar(parameter=p, base_value=bv, low_value=lo, high_value=hi, lcoh_base=base,
                               lcoh_at_low=compute_lcoh(result, _with(a, **{p: lo})).lcoh_USD_per_kg,
                               lcoh_at_high=compute_lcoh(result, _with(a, **{p: hi})).lcoh_USD_per_kg,
                               source_of_range=src))
    bars.sort(key=lambda b: b.swing, reverse=True)
    return bars


def lcoh_vs_ammonia_price(result: SimulationResult, assumptions: Optional[EconomicAssumptions],
                          prices_USD_per_t: Iterable[float]) -> list[tuple[float, float]]:
    a = assumptions or EconomicAssumptions()
    return [(float(p), compute_lcoh(result, _with(a, nh3_price_USD_per_t=float(p))).lcoh_USD_per_kg)
            for p in prices_USD_per_t]


def breakeven_ammonia_price(result: SimulationResult, assumptions: Optional[EconomicAssumptions],
                            target_lcoh_USD_per_kg: float) -> Optional[float]:
    """NH3 price (USD/t) at which LCOH equals the target. LCOH is linear in the NH3 price, so two evaluations
    give the exact answer. Returns None if the target is below the zero-NH3-price LCOH."""
    a = assumptions or EconomicAssumptions()
    l0 = compute_lcoh(result, _with(a, nh3_price_USD_per_t=0.0)).lcoh_USD_per_kg
    l1 = compute_lcoh(result, _with(a, nh3_price_USD_per_t=1000.0)).lcoh_USD_per_kg
    slope = (l1 - l0) / 1000.0
    p = (target_lcoh_USD_per_kg - l0) / slope
    return p if p >= 0 else None


def literature_benchmarks() -> list[dict]:
    """Literature LCOH values (labelled literature; never AmCraX results)."""
    return [dict(b, source=DataSource.LITERATURE.value) for b in load_economics_data()["literature_lcoh"]]
