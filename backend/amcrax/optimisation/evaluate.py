"""Common evaluator: one SimulationResult (Aspen or Python) -> dict of plain numbers.

The same function is applied to Aspen Plus V15 results and to the Python process model, so every
comparison (optimum vs baseline, Python vs Aspen re-solve) uses identical definitions.

LCOH        amcrax.economics.compute_lcoh with EconomicAssumptions() defaults (data/economics.yaml),
            except the heat-import pricing selected by ``heat_source`` and the cracked-gas compression
            electricity (below).
CI          amcrax.environmental.carbon_intensity (simplified carbon-intensity accounting, NOT an LCA)
            for ``<nh3_route>/<heating>``; heating follows ``heat_source`` so LCOH and CI book the same
            heat supply.  Default: ``grey/self_firing`` (economics default heat_import_mode is
            'ammonia_fuel', i.e. the heat deficit is covered by burning extra NH3; the environmental
            module's own default 'natural_gas' would be inconsistent with that LCOH).
Compression When the PSA feed pressure (stream S7) is below the literature PSA feed-pressure requirement
            (amcrax.separation params: psa.feed_pressure_requirement_bar.default = 7 bar, cho2026nickel
            p. 6 Table 3), the whole cracked gas S7 is compressed from P(S7) to the requirement at the
            S7 temperature with amcrax.separation.compression_power_kW (intercooled, eta 0.75,
            cho2026nickel p. 5 Table 2).  Its shaft power is added
              * to LCOH as electricity, through EconomicAssumptions.compression_power_kW (priced at
                electricity_price_USD_per_kWh), and
              * to CI as extra electricity: compression_kW x grid factor / H2 product (the
                environmental module counts only pump power, so it is added here, booked under the
                'electricity' breakdown entry).
            Compressor CAPEX is NOT added (the plant-level CAPEX correlation has no equipment term).
"""
from __future__ import annotations

from typing import Any, Optional

from amcrax.economics import EconomicAssumptions, compute_lcoh
from amcrax.environmental import carbon_intensity, load_factors
from amcrax.schemas import CaseInputs, SimulationResult
from amcrax.separation import compression_power_kW, params as sep_params

HEAT_SOURCES = ("ammonia", "natural_gas", "electric")
#: heat_source -> environmental heating option
CI_HEATING = {"ammonia": "self_firing", "natural_gas": "natural_gas", "electric": "electric"}

DEFAULT_HEAT_SOURCE = "ammonia"
DEFAULT_NH3_ROUTE = "grey"
DEFAULT_GRID = "singapore_2024"


def psa_feed_pressure_requirement_bar() -> float:
    return float(sep_params()["psa"]["feed_pressure_requirement_bar"]["default"])


def _economic_assumptions(heat_source: str, base: Optional[EconomicAssumptions], compression_kW: float,
                          nh3_price_USD_per_t: Optional[float]) -> EconomicAssumptions:
    a = (base or EconomicAssumptions()).model_copy()
    upd: dict[str, Any] = {"compression_power_kW": a.compression_power_kW + compression_kW}
    if heat_source == "ammonia":
        upd["heat_import_mode"] = "ammonia_fuel"
    elif heat_source == "natural_gas":
        # fired-heat utility price (kum2026heatintegrated p. 8 Table 5) - a generic fired-heat price
        upd["heat_import_mode"] = "fired_heat"
    elif heat_source == "electric":
        eta = float(load_factors()["heating"]["electric_heater_efficiency"]["value"])
        upd["heat_import_mode"] = "fired_heat"
        upd["fired_heat_price_USD_per_kJ"] = a.electricity_price_USD_per_kWh / 3600.0 / eta
    else:
        raise ValueError(f"unknown heat_source {heat_source!r}; use one of {HEAT_SOURCES}")
    if nh3_price_USD_per_t is not None:
        upd["nh3_price_USD_per_t"] = float(nh3_price_USD_per_t)
    return a.model_copy(update=upd)


def compression_requirement(result: SimulationResult, required_bar: Optional[float] = None) -> dict:
    """Cracked-gas compression needed to bring S7 to the PSA feed-pressure requirement."""
    req = psa_feed_pressure_requirement_bar() if required_bar is None else float(required_bar)
    s7 = result.streams.get("S7")
    if s7 is None or s7.pressure_bar is None:
        return {"psa_feed_pressure_bar": None, "required_bar": req, "power_kW": 0.0, "stages": 0,
                "note": "S7 not in result; no compression evaluated"}
    if s7.pressure_bar >= req:
        return {"psa_feed_pressure_bar": s7.pressure_bar, "required_bar": req, "power_kW": 0.0, "stages": 0,
                "note": "PSA feed pressure meets the requirement"}
    comp = {k: v for k, v in s7.component_mole_flow_kmol_h.items() if v and v > 0}
    n = sum(comp.values())
    c = compression_power_kW(n, comp, s7.temperature_C + 273.15, s7.pressure_bar, req)
    return {"psa_feed_pressure_bar": s7.pressure_bar, "required_bar": req, "power_kW": float(c["power_kW"]),
            "stages": int(c["stages"]), "note": "reduced-order intercooled compression of S7 (amcrax.separation)"}


def evaluate_result(result: SimulationResult, *, heat_source: str = DEFAULT_HEAT_SOURCE,
                    nh3_route: str = DEFAULT_NH3_ROUTE, grid: str = DEFAULT_GRID,
                    economic_assumptions: Optional[EconomicAssumptions] = None,
                    include_compression: bool = True, psa_feed_pressure_requirement: Optional[float] = None,
                    nh3_price_USD_per_t: Optional[float] = None) -> dict:
    """Evaluate any SimulationResult. Returns a flat dict of floats (plus the string keys
    ``source``, ``case_id``, ``ci_scenario``, ``heat_source``)."""
    k = result.kpis
    comp = compression_requirement(result, psa_feed_pressure_requirement) if include_compression else \
        {"psa_feed_pressure_bar": None, "required_bar": None, "power_kW": 0.0, "stages": 0}
    w_comp = float(comp["power_kW"])
    a = _economic_assumptions(heat_source, economic_assumptions, w_comp, nh3_price_USD_per_t)
    lc = compute_lcoh(result, a)
    heating = CI_HEATING[heat_source]
    ci = carbon_intensity(result, f"{nh3_route}/{heating}", grid=grid)
    grid_ef = float(load_factors()["electricity"][grid]["value"])
    ci_comp = w_comp * grid_ef / ci.h2_product_kg_h
    br = ci.breakdown_kgCO2e_per_kgH2
    s5 = result.streams.get("S5")
    y_nh3 = s5.mole_frac.get("NH3") if s5 is not None else None
    out: dict[str, Any] = {
        "case_id": result.case_id,
        "source": result.source.value,
        "heat_source": heat_source,
        "ci_scenario": f"{ci.nh3_route}/{ci.heating_option} grid={grid} (simplified carbon-intensity accounting, not an LCA)",
        "lcoh_USD_per_kg": float(lc.lcoh_USD_per_kg),
        "carbon_intensity_kgCO2e_per_kgH2": float(ci.total_kgCO2e_per_kgH2 + ci_comp),
        "lhv_efficiency": k.lhv_efficiency,
        "nh3_conversion": k.nh3_conversion,
        "h2_yield_overall": k.h2_yield_overall,
        "h2_product_kg_h": k.h2_product_kg_h,
        "h2_purity_mole_frac": k.h2_purity_mole_frac,
        "nh3_feed_kg_per_kgH2": float(lc.kg_nh3_feed_per_kg_h2),
        "nh3_total_kg_per_kgH2": float(lc.kg_nh3_feed_per_kg_h2 + lc.kg_nh3_fuel_per_kg_h2),
        "total_external_heating_kW": k.total_external_heating_kW,
        "net_fuel_heat_deficit_kW": k.net_fuel_heat_deficit_kW,
        "specific_heat_demand_kWh_per_kgH2": k.specific_heat_demand_kWh_per_kgH2,
        "cracked_gas_nh3_mole_frac": y_nh3,
        "psa_feed_pressure_bar": comp["psa_feed_pressure_bar"],
        "psa_feed_pressure_requirement_bar": comp["required_bar"],
        "compression_power_kW": w_comp,
        "pump_power_kW": k.pump_power_kW,
        "recovered_heat_kW": k.recovered_heat_kW,
    }
    for c, v in lc.breakdown_USD_per_kg.items():
        out[f"lcoh_{c}_USD_per_kg"] = float(v)
    out["ci_upstream_ammonia"] = float(br.upstream_ammonia)
    out["ci_transport"] = float(br.transport)
    out["ci_electricity"] = float(br.electricity + ci_comp)
    out["ci_external_heat"] = float(br.external_heat)
    fehe = result.blocks.get("FEHE")
    if fehe is not None and fehe.details.get("min_internal_dT_K") is not None:
        out["fehe_min_internal_dT_K"] = float(fehe.details["min_internal_dT_K"])
    return out


def evaluate_inputs(inputs: CaseInputs, **options) -> dict:
    """evaluate_result(run_python_case(inputs)). Raises FlowsheetSpecError for infeasible specs."""
    from amcrax.process_model import run_python_case

    return evaluate_result(run_python_case(inputs), **options)


__all__ = ["evaluate_result", "evaluate_inputs", "compression_requirement", "psa_feed_pressure_requirement_bar",
           "HEAT_SOURCES", "CI_HEATING", "DEFAULT_HEAT_SOURCE", "DEFAULT_NH3_ROUTE", "DEFAULT_GRID"]
