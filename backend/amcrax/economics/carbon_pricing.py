"""Carbon pricing of cracked hydrogen in Singapore: actual boundary (Mode A) and hypothetical life-cycle price (Mode B).

Phase 2, task C3. Additive: it calls amcrax.economics.singapore.evaluate and never changes its default output.

MODE A  "actual_sg" (default): the Singapore carbon tax as the Carbon Pricing Act 2018 (CPA) defines it.
    - Taxed quantity: direct (Scope 1) reckonable GHG emissions of the facility, in tCO2e with the CPA First Schedule
      GWPs (CO2 1, CH4 28, N2O 265).
    - Liability only if the facility emits at least the second emissions threshold, 25,000 tCO2e per year.
    - Rate: SGD 5 (emissions year 2023 or earlier), 25 (2024, 2025), 45 (2026 or any later year). The Act sets no
      step above 45; "SGD 50 to 80 by 2030" is a stated government aim, not legislation.
    - Upstream emissions of imported ammonia (production abroad, shipping) are outside the Act.
    - With ammonia self-firing (the reference case) the facility emits no CO2. N2O from burning the tail gas and the
      supplementary NH3 is a covered gas. AmCraX has no primary emission factor for it, so Mode A takes N2O = 0 by
      default and reports a threshold test (the N2O rate that would make the plant liable). A caller may pass an N2O
      rate; it is then charged at the legislated rate if the threshold is reached.
    Mode A is computed by amcrax.economics.singapore.evaluate (breakdown.carbon_tax), as in frontend/src/sim/carbon.ts.

MODE B  "hypothetical_lca": a user price P (SGD/tCO2e) applied to the full life-cycle carbon intensity CI
    (kg CO2e/kg H2) of the delivered hydrogen. It REPLACES the Mode A tax term (every emission is charged once):
        carbon_USD_per_kg = P * CI / 1000 / fx
        LCOH_B = LCOH_A - carbon_tax_A + carbon_USD_per_kg
    Every Mode B output carries HYPOTHETICAL_LABEL. Mode B is NOT Singapore law.

CARBON INTENSITY: same formula as frontend/src/sim/carbon.ts carbonIntensity (simplified carbon-intensity
    accounting, not a full LCA; factors from data/environmental.yaml), with the gate factor of the ammonia route
    taken from amcrax.environmental.lca.route_spec (central and range) unless given.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS

from . import singapore
from .reference import load_reference_scenario

MODES = ("actual_sg", "hypothetical_lca")
HYPOTHETICAL_LABEL = ("HYPOTHETICAL life-cycle carbon price, not Singapore law; replaces the actual tax term "
                      "(no double counting)")
ACTUAL_LABEL = ("Singapore carbon tax, actual boundary (Carbon Pricing Act 2018): direct reckonable facility "
                "emissions only, only at or above 25,000 tCO2e/yr")

# Facts from research/data/carbon_policy_sg.json (access date 2026-11-23). A test checks they match that file.
POLICY = {
    "rate_SGD_per_tCO2e": {"2023_or_earlier": 5.0, "2024_2025": 25.0, "2026_or_later": 45.0},
    "rate_source": "Carbon Pricing Act 2018, Third Schedule Part 1 para 1(a)-(c) (statute text, SSO, accessed 2026-11-23)",
    "threshold_tCO2e_per_yr": 25000.0,
    "threshold_source": "Carbon Pricing Act 2018, Second Schedule Part 1 ('The second emissions threshold is 25,000 tCO2e.')",
    "gwp": {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
    "gwp_source": "Carbon Pricing Act 2018, First Schedule",
    "aim_2030_SGD_per_tCO2e": (50.0, 80.0),
    "aim_2030_status": "stated government aim ('with a view of reaching $50 to $80 per tonne by 2030', NEA/NCCS pages); NOT in the Act",
    "eu_ets_EUR_per_tCO2": 90.0,
    "eu_ets_status": "secondary press report (GMK Center citing ICE, EUA Dec-2026 future EUR 90.2-90.5, 2-13 Nov 2026); context only, not Singapore law",
}


def legislated_rate_SGD(year: int = 2026) -> float:
    """CPA Third Schedule rate for an emissions year (no rate above 45 is legislated)."""
    r = POLICY["rate_SGD_per_tCO2e"]
    if year <= 2023:
        return r["2023_or_earlier"]
    if year <= 2025:
        return r["2024_2025"]
    return r["2026_or_later"]


def eu_ets_SGD_per_t() -> float:
    """EU ETS context level converted with the reference-scenario ECB rates (USD/EUR x SGD/USD)."""
    ref = load_reference_scenario()
    usd_per_eur = float(ref.raw["currency"]["usd_per_eur"]["value"])
    return POLICY["eu_ets_EUR_per_tCO2"] * usd_per_eur * ref.fx_SGD_per_USD


# ------------------------------------------------------------------------------------------ carbon intensity
@dataclass(frozen=True)
class CIFactors:
    ship_ef_kg_per_tkm: float
    distance_km: float
    grid_kg_per_kWh: float
    natural_gas_kg_per_TJ: float
    fired_heater_efficiency_lhv: float
    electric_heater_efficiency: float


def ci_factors(grid: str = "singapore_2024") -> CIFactors:
    from amcrax.environmental import load_factors
    f = load_factors()
    return CIFactors(
        ship_ef_kg_per_tkm=float(f["transport"]["ship_ef"]["value"]),
        distance_km=float(f["transport"]["distance_km"]["value"]),
        grid_kg_per_kWh=float(f["electricity"][grid]["value"]),
        natural_gas_kg_per_TJ=float(f["heating"]["natural_gas_combustion"]["value"]),
        fired_heater_efficiency_lhv=float(f["heating"]["fired_heater_efficiency_lhv"]["value"]),
        electric_heater_efficiency=float(f["heating"]["electric_heater_efficiency"]["value"]),
    )


def route_gate_ef(route: str) -> dict:
    """Gate emission factor (kg CO2e/kg NH3): central, low, high, from amcrax.environmental.lca.route_spec."""
    from amcrax.environmental import lca
    key = {"green_current": "green", "green_2030": "green", "green_2050": "green"}.get(route, route)
    s = lca.route_spec(key)
    return {"route_ef_key": key, "central": float(s.ef), "low": float(s.low), "high": float(s.high), "label": s.label}


def carbon_intensity_h2(inputs: dict, nh3_ef_kg_per_kg: float, heating: str = "self_firing",
                        distance_km: Optional[float] = None, factors: Optional[CIFactors] = None) -> dict:
    """kg CO2e per kg H2. Port target and twin of carbon.ts carbonIntensity.

    inputs: {h2_kg_h, nh3_feed_kg_h, heat_deficit_kW, pump_kW}.
    """
    fc = factors or ci_factors()
    dist = fc.distance_km if distance_km is None else float(distance_km)
    deficit = max(0.0, float(inputs["heat_deficit_kW"]))
    fuel_kW = deficit / fc.fired_heater_efficiency_lhv
    lhv_kg = LHV_KJ_PER_MOL["NH3"] / MOLAR_MASS["NH3"] * 1000.0
    ship = fc.ship_ef_kg_per_tkm * dist / 1000.0
    elec, heat, fuel_kg = float(inputs["pump_kW"]), 0.0, 0.0
    if heating == "natural_gas":
        heat = fuel_kW * 3600.0 / 1e6 / 1000.0 * fc.natural_gas_kg_per_TJ
    elif heating == "self_firing":
        fuel_kg = fuel_kW * 3600.0 / lhv_kg
        heat = fuel_kg * (nh3_ef_kg_per_kg + ship)
    elif heating == "electric":
        elec += deficit / fc.electric_heater_efficiency
    else:
        raise ValueError("heating must be natural_gas | self_firing | electric")
    h2 = float(inputs["h2_kg_h"])
    br = {"upstream_ammonia": inputs["nh3_feed_kg_h"] * nh3_ef_kg_per_kg / h2,
          "transport": inputs["nh3_feed_kg_h"] * ship / h2,
          "electricity": elec * fc.grid_kg_per_kWh / h2,
          "external_heat": heat / h2}
    return {"total_kgCO2e_per_kgH2": sum(br.values()), "breakdown_kgCO2e_per_kgH2": br, "nh3_fuel_kg_h": fuel_kg,
            "heating": heating, "statement": "simplified carbon-intensity accounting, not a life-cycle assessment"}


def ci_inputs_from_result(result_or_summary: Any) -> dict:
    s = singapore.extract_summary(result_or_summary)
    return {"h2_kg_h": s["h2_kg_h"], "nh3_feed_kg_h": s["nh3_feed_kmol_h"] * MOLAR_MASS["NH3"],
            "heat_deficit_kW": s["heat_deficit_kW"], "pump_kW": s["pump_kW"]}


# ------------------------------------------------------------------------------------------ carbon cost
def carbon_cost(econ: dict, ci_total_kgCO2e_per_kgH2: float, mode: str = "actual_sg",
                price_SGD_per_t: float = 0.0) -> dict:
    """Port target and twin of carbon.ts carbonCost. econ: output of singapore.evaluate."""
    fx = float(econ["fx_SGD_per_USD"])
    tax = float(econ["breakdown_USD_per_kg"]["carbon_tax"])
    if mode == "actual_sg":
        return {"mode": mode, "USD_per_kg_H2": tax, "SGD_per_kg_H2": tax * fx, "lcoh_USD_per_kg": econ["lcoh_USD_per_kg"],
                "lcoh_SGD_per_kg": econ["lcoh_USD_per_kg"] * fx, "hypothetical": False, "label": ACTUAL_LABEL}
    if mode != "hypothetical_lca":
        raise ValueError(f"mode must be one of {MODES}")
    if price_SGD_per_t < 0 or not math.isfinite(price_SGD_per_t):
        raise ValueError("price must be finite and >= 0")
    sgd = price_SGD_per_t * ci_total_kgCO2e_per_kgH2 / 1000.0
    usd = sgd / fx
    lcoh = econ["lcoh_USD_per_kg"] - tax + usd
    return {"mode": mode, "USD_per_kg_H2": usd, "SGD_per_kg_H2": sgd, "lcoh_USD_per_kg": lcoh, "lcoh_SGD_per_kg": lcoh * fx,
            "hypothetical": True, "label": HYPOTHETICAL_LABEL}


# ------------------------------------------------------------------------------------------ Mode A threshold test
def actual_boundary(result_or_summary: Any, scenario: Any = "grey", *, year: int = 2026,
                    n2o_kg_per_h: float = 0.0, overrides: Optional[dict] = None) -> dict:
    """Mode A with an explicit threshold test. N2O (kg/h) is converted with the CPA GWP 265."""
    o = dict(overrides or {})
    hours = load_reference_scenario().raw["operation"]["operating_hours_h_per_yr"]["value"]
    n2o_t = n2o_kg_per_h * float(o.get("operating_hours_h_per_yr", hours)) / 1000.0 * POLICY["gwp"]["N2O"]
    o.setdefault("carbon_tax_SGD_per_t", legislated_rate_SGD(year))
    o["n2o_tCO2e_per_yr"] = o.get("n2o_tCO2e_per_yr", 0.0) + n2o_t
    e = singapore.evaluate(result_or_summary, scenario, o)
    thr = POLICY["threshold_tCO2e_per_yr"]
    d = e["direct_emissions_tCO2e_per_yr"]
    return {"mode": "actual_sg", "label": ACTUAL_LABEL, "year": year, "rate_SGD_per_t": o["carbon_tax_SGD_per_t"],
            "direct_tCO2e_per_yr": d, "n2o_tCO2e_per_yr": n2o_t, "threshold_tCO2e_per_yr": thr,
            "threshold_fraction": d / thr, "liable": e["carbon_tax_liable"],
            "carbon_tax_USD_per_kg": e["breakdown_USD_per_kg"]["carbon_tax"], "lcoh_USD_per_kg": e["lcoh_USD_per_kg"],
            "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"], "upstream_emissions_taxed": False, "econ": e}


def n2o_threshold_test(result: dict, econ: dict) -> dict:
    """N2O emission that would make the reference plant liable, against the fuel nitrogen burnt and the flue gas.

    result: stored Aspen result dict (results/simulations/baseline.json). econ: singapore.evaluate output.
    The stored flowsheet burns only the tail gas; the supplementary NH3 fuel (heat deficit) is not simulated, so its
    flue gas is added by stoichiometry at the stored excess-O2 fraction (estimate).
    """
    thr = POLICY["threshold_tCO2e_per_yr"]
    hours = econ["assumptions"]["economic"]["operating_hours_h_per_yr"]
    n2o_t_yr = thr / POLICY["gwp"]["N2O"]
    n2o_kg_h = n2o_t_yr * 1000.0 / hours
    n2o_kmol_h = n2o_kg_h / 44.013
    tg = result["streams"]["TAILGAS"]["component_mole_flow_kmol_h"]
    fuel_nh3_kmol_h = econ["kg_nh3_fuel_per_kg_h2"] * econ["h2_product_kg_h"] / MOLAR_MASS["NH3"]
    fuel_n_kmol_h = float(tg.get("NH3", 0.0)) + fuel_nh3_kmol_h          # N atoms in burnt NH3 (N2 is inert)
    flue = result["streams"]["FLUE"]
    o2 = flue["mole_frac"]["O2"]
    # NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O, air 0.21 O2: added flue per kmol NH3 = 0.5 + 1.5 + 0.75*0.79/0.21, scaled for excess O2
    add_flue = fuel_nh3_kmol_h * (0.5 + 1.5 + 0.75 * 0.79 / 0.21) / (1.0 - o2 / 0.21)
    flue_kmol_h = float(flue["mole_flow_kmol_h"]) + add_flue
    return {
        "n2o_needed_t_per_yr": n2o_t_yr, "n2o_needed_kg_per_h": n2o_kg_h,
        "fuel_nitrogen_kmol_N_per_h": fuel_n_kmol_h,
        "fraction_of_fuel_N_to_N2O_needed": 2.0 * n2o_kmol_h / fuel_n_kmol_h,
        "flue_gas_kmol_h_estimate": flue_kmol_h,
        "n2o_ppmv_needed_in_flue": n2o_kmol_h / flue_kmol_h * 1e6,
        "basis": "threshold 25,000 tCO2e/yr / GWP 265; fuel N = tail-gas NH3 (Aspen) + supplementary NH3 (economics); "
                 "flue = stored FLUE + stoichiometric flue of the supplementary NH3 at the stored excess O2 (estimate)",
    }


def n2o_at_ppmv(ppmv: float, threshold_test: dict, hours: float) -> dict:
    kg_h = ppmv * 1e-6 * threshold_test["flue_gas_kmol_h_estimate"] * 44.013
    t = kg_h * hours / 1000.0 * POLICY["gwp"]["N2O"]
    return {"ppmv": ppmv, "n2o_kg_per_h": kg_h, "tCO2e_per_yr": t, "threshold_fraction": t / POLICY["threshold_tCO2e_per_yr"]}


# ------------------------------------------------------------------------------------------ route evaluation
def route_case(result_or_summary: Any, route: str, mode: str = "actual_sg", price_SGD_per_t: float = 0.0, *,
               ci_level: str = "central", nh3_ef_kg_per_kg: Optional[float] = None,
               benchmark_USD_per_kg: Optional[float] = None, benchmark_ci_kgCO2e_per_kgH2: float = 11.0,
               overrides: Optional[dict] = None) -> dict:
    """Cost of hydrogen from one ammonia route under one carbon mode.

    route: grey | blue | green_current | green_2030 | green_2050 (price scenario; green_* share the green CI).
    benchmark: hydrogen price for break-even and NPV (default: reference h2_selling_price 3.06 USD/kg, NE Asia SMR).
    Under Mode B the benchmark is also reported carbon-adjusted with its own CI (default 11 kg/kg, unabated SMR,
    IEA GHR 2024 10-12, as in amcrax.environmental.lca); under Mode A it is not (an imported-H2 marker pays no SG tax).
    """
    ref = load_reference_scenario()
    fx = ref.fx_SGD_per_USD
    o = dict(overrides or {})
    econ = singapore.evaluate(result_or_summary, route, o)
    ef = route_gate_ef(route)
    ef_val = ef[ci_level] if nh3_ef_kg_per_kg is None else float(nh3_ef_kg_per_kg)
    ci = carbon_intensity_h2(ci_inputs_from_result(result_or_summary), ef_val)
    cc = carbon_cost(econ, ci["total_kgCO2e_per_kgH2"], mode, price_SGD_per_t)
    bench = ref.h2_selling_price_USD_per_kg if benchmark_USD_per_kg is None else float(benchmark_USD_per_kg)
    hyp = mode == "hypothetical_lca"
    bench_adj = bench + (price_SGD_per_t * benchmark_ci_kgCO2e_per_kgH2 / 1000.0 / fx if hyp else 0.0)
    # LCOH is linear in the NH3 price (feed + supplementary fuel); the carbon term does not depend on it
    e0 = singapore.evaluate(result_or_summary, 0.0, o)
    e1 = singapore.evaluate(result_or_summary, 1000.0, o)
    slope = (e1["lcoh_USD_per_kg"] - e0["lcoh_USD_per_kg"]) / 1000.0
    base0 = e0["lcoh_USD_per_kg"] - e0["breakdown_USD_per_kg"]["carbon_tax"] + (cc["USD_per_kg_H2"] if hyp else e0["breakdown_USD_per_kg"]["carbon_tax"])
    be = (bench - base0) / slope
    be_adj = (bench_adj - base0) / slope
    a = econ["assumptions"]["economic"]
    r, n = a["discount_rate"], int(round(a["plant_life_yr"]))
    annuity = (1.0 - (1.0 + r) ** -n) / r
    d_carbon = cc["USD_per_kg_H2"] - econ["breakdown_USD_per_kg"]["carbon_tax"]
    # NPV = evaluate's NPV (at its h2 price) + revenue change at the benchmark - extra carbon cost, same annuity
    q = econ["annual_h2_kg"] * annuity
    npv = econ["npv_USD"] + (bench - econ["h2_price_USD_per_kg"]) * q - d_carbon * q
    npv_adj = npv + (bench_adj - bench) * q
    fc = ci_factors()
    ef_del = ef_val + fc.ship_ef_kg_per_tkm * fc.distance_km / 1000.0
    nh3_incl = econ["nh3_price_USD_per_t"] + (price_SGD_per_t * ef_del / fx if hyp else 0.0)
    out = {
        "route": route, "mode": mode, "hypothetical": hyp, "label": cc["label"],
        "carbon_price_SGD_per_tCO2e": price_SGD_per_t if hyp else float(econ["assumptions"]["singapore"]["carbon_tax_SGD_per_t"]),
        "ci_level": ci_level if nh3_ef_kg_per_kg is None else "custom", "nh3_gate_ef_kgCO2e_per_kgNH3": ef_val,
        "carbon_intensity_kgCO2e_per_kgH2": ci["total_kgCO2e_per_kgH2"],
        "nh3_price_USD_per_t": econ["nh3_price_USD_per_t"],
        "nh3_cost_incl_carbon_USD_per_t": nh3_incl, "nh3_cost_incl_carbon_SGD_per_t": nh3_incl * fx,
        "carbon_cost_USD_per_kg": cc["USD_per_kg_H2"], "carbon_cost_SGD_per_kg": cc["SGD_per_kg_H2"],
        "lcoh_USD_per_kg": cc["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": cc["lcoh_SGD_per_kg"],
        "benchmark_USD_per_kg": bench, "benchmark_carbon_adjusted_USD_per_kg": bench_adj,
        "breakeven_nh3_USD_per_t": be, "breakeven_nh3_vs_carbon_adjusted_benchmark_USD_per_t": be_adj,
        "npv_USD": npv, "npv_SGD": npv * fx, "npv_at_carbon_adjusted_benchmark_USD": npv_adj,
        "fx_SGD_per_USD": fx,
    }
    if not hyp:
        out["mode_a_note"] = ("Upstream and shipping emissions of imported NH3 are outside the Act; the CI is reported "
                              "for information and is not priced.")
    return out


def crossover_price(lcoh_a: float, ci_a: float, lcoh_b: float, ci_b: float, fx: float) -> Optional[float]:
    """Hypothetical price (SGD/tCO2e) at which route a (dearer at P=0) becomes as cheap as route b.

    Returns 0.0 if a is already not dearer, None if a never overtakes (CI_a >= CI_b while dearer).
    """
    if lcoh_a <= lcoh_b:
        return 0.0
    if ci_b <= ci_a:
        return None
    return (lcoh_a - lcoh_b) * fx * 1000.0 / (ci_b - ci_a)


__all__ = ["MODES", "HYPOTHETICAL_LABEL", "ACTUAL_LABEL", "POLICY", "legislated_rate_SGD", "eu_ets_SGD_per_t",
           "CIFactors", "ci_factors", "route_gate_ef", "carbon_intensity_h2", "ci_inputs_from_result", "carbon_cost",
           "actual_boundary", "n2o_threshold_test", "n2o_at_ppmv", "route_case", "crossover_price"]
