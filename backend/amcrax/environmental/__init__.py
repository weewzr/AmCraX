"""Simplified carbon-intensity accounting of hydrogen from ammonia cracking (AmCraX P3.4).

This is NOT a life-cycle assessment. It is an activity x emission-factor bookkeeping of the
kg CO2e emitted per kg of H2 product at the PSA outlet of the simulated cracker, for four
contributions only:

* upstream ammonia   - NH3 feed x cradle-to-plant-gate factor of grey / blue / green NH3
* transport          - NH3 feed (t) x sea distance (km) x tanker factor (kg CO2e / t km)
* electricity        - process electricity (pump; electric heating if chosen) x grid factor
* external heat      - net heat deficit after tail-gas firing, supplied by imported natural gas
                       (combustion CO2), by burning extra NH3 (its upstream + transport
                       emissions; no CO2 at the burner) or by electric heating (booked under
                       electricity)

System boundary (stated in every result): cradle-to-gate of H2 at the cracker/PSA outlet.
Excluded: plant construction and equipment manufacture, catalyst / adsorbent manufacture,
N2O / NOx / NH3 slip from tail-gas or NH3 combustion, H2 leakage, H2 compression / storage /
delivery, NH3 boil-off, upstream natural-gas supply chain, CO2 transport & storage beyond what
the upstream NH3 factor includes. All emission factors live in ``amcrax/data/environmental.yaml``
with their sources.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, DataSource, SimulationResult

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "environmental.yaml"

NH3_ROUTES = ("green", "blue", "grey")
HEATING_OPTIONS = ("natural_gas", "self_firing", "electric")
HEATING_LABELS = {
    "natural_gas": "imported natural gas",
    "self_firing": "tail gas + extra NH3 self-firing",
    "electric": "electric heating",
}

METHOD_STATEMENT = (
    "Simplified carbon-intensity accounting (activity x emission factor); NOT a life-cycle assessment."
)
SYSTEM_BOUNDARY = (
    "Cradle-to-gate of H2 at the cracker/PSA outlet: upstream NH3 production, NH3 sea transport, "
    "process electricity, external heat supply. Excluded: plant construction and equipment "
    "manufacture, catalyst/adsorbent manufacture, N2O/NOx/NH3 slip from tail-gas or NH3 combustion, "
    "H2 leakage, H2 compression/storage/delivery, NH3 boil-off, upstream natural-gas supply chain."
)

KWH_PER_KJ = 1.0 / 3600.0


@lru_cache(maxsize=1)
def load_factors(path: str | None = None) -> dict:
    """Return the emission-factor registry (parsed ``environmental.yaml``)."""
    p = Path(path) if path else DATA_FILE
    with open(p, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ------------------------------------------------------------------------------------------------
class FactorUsed(BaseModel):
    name: str
    value: float
    unit: str
    provenance: DataSource
    source: Optional[str] = Field(None, description="citekey + page/locator, or None for an assumption")
    note: str = ""


class CIBreakdown(BaseModel):
    """kg CO2e per kg H2 product."""

    upstream_ammonia: float
    transport: float
    electricity: float
    external_heat: float


class ReferenceLine(BaseModel):
    label: str
    value_kgCO2e_per_kgH2: float
    source: str
    note: str = ""


class CarbonIntensityResult(BaseModel):
    case_id: str
    input_source: DataSource = Field(..., description="Provenance of the simulation result used")
    source: DataSource = DataSource.PYTHON
    method: str = METHOD_STATEMENT
    system_boundary: str = SYSTEM_BOUNDARY
    scenario: str
    nh3_route: str
    heating_option: str
    grid: str
    total_kgCO2e_per_kgH2: float
    breakdown_kgCO2e_per_kgH2: CIBreakdown
    # activities
    h2_product_kg_h: float
    nh3_feed_kg_h: float
    nh3_fuel_kg_h: float = Field(0.0, description="Extra NH3 burnt for heat (self-firing option)")
    kg_nh3_per_kg_h2: float = Field(..., description="(feed + fuel NH3) / H2 product")
    heat_deficit_kW: float = Field(..., description="Heat not covered by tail-gas firing (>= 0)")
    electricity_kW: float
    natural_gas_GJ_h: float = 0.0
    transport_distance_km: float
    factors: list[FactorUsed]
    reference_lines: list[ReferenceLine] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ScenarioRow(BaseModel):
    nh3_route: str
    heating_option: str
    heating_label: str
    total_kgCO2e_per_kgH2: float
    breakdown_kgCO2e_per_kgH2: CIBreakdown


class ScenarioComparison(BaseModel):
    case_id: str
    input_source: DataSource
    source: DataSource = DataSource.PYTHON
    method: str = METHOD_STATEMENT
    system_boundary: str = SYSTEM_BOUNDARY
    grid: str
    transport_distance_km: float
    rows: list[ScenarioRow]
    reference_lines: list[ReferenceLine]
    notes: list[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------------------------
def _src(entry: dict) -> Optional[str]:
    s = entry.get("source")
    if not s:
        return None
    parts = [str(s.get("citekey"))]
    if s.get("page") is not None:
        parts.append(f"p. {s['page']}")
    if s.get("locator"):
        parts.append(str(s["locator"]))
    return ", ".join(parts)


def _factor(name: str, entry: dict, value: float | None = None, overridden: bool = False) -> FactorUsed:
    prov = DataSource.ASSUMPTION if overridden else DataSource(entry.get("provenance", "assumption"))
    return FactorUsed(
        name=name,
        value=float(entry["value"]) if value is None else float(value),
        unit=str(entry.get("unit", "")),
        provenance=prov,
        source=None if overridden else _src(entry),
        note="user override" if overridden else str(entry.get("note", "")).strip(),
    )


def reference_lines(factors: dict | None = None) -> list[ReferenceLine]:
    """Regulatory / agency yardsticks (kg CO2e/kg H2), each with its citation."""
    f = factors or load_factors()
    rl = f["reference_lines"]
    eu = rl["eu_rfnbo"]
    lhv_MJ_per_kg = LHV_KJ_PER_MOL["H2"] / MOLAR_MASS["H2"]  # kJ/mol / (g/mol) = MJ/kg
    eu_val = eu["fossil_comparator_g_per_MJ"] * (1.0 - eu["required_saving"]) * lhv_MJ_per_kg / 1000.0
    iea = rl["iea_low_emission"]
    return [
        ReferenceLine(label="EU RFNBO threshold (70 % below 94 g CO2e/MJ)", value_kgCO2e_per_kgH2=eu_val,
                      source=_src(eu), note=str(eu["note"])),
        ReferenceLine(label="IEA low-emission H2 (as quoted by Kum et al.)", value_kgCO2e_per_kgH2=float(iea["value"]),
                      source=_src(iea), note=str(iea["note"])),
    ]


def _activities(result: SimulationResult) -> tuple[float, float, float, float]:
    """(H2 product kg/h, NH3 feed kg/h, heat deficit kW >= 0, pump power kW)."""
    k = result.kpis
    h2 = k.h2_product_kg_h
    if h2 is None:
        if k.h2_product_kmol_h is None:
            raise ValueError("SimulationResult has no H2 product flow (kpis.h2_product_kg_h)")
        h2 = k.h2_product_kmol_h * MOLAR_MASS["H2"]
    if not h2 > 0:
        raise ValueError("H2 product flow must be > 0 to compute a carbon intensity")
    feed = result.streams.get("FEED")
    if feed is not None and feed.component_mole_flow_kmol_h.get("NH3") is not None:
        nh3_kmol = feed.component_mole_flow_kmol_h["NH3"]
    else:
        nh3_kmol = result.inputs.feed_total_kmol_h * (1.0 - result.inputs.feed_h2o_mole_frac)
    nh3_kg = nh3_kmol * MOLAR_MASS["NH3"]
    deficit = k.net_fuel_heat_deficit_kW
    if deficit is None:
        if k.total_external_heating_kW is None or k.tailgas_combustion_heat_kW is None:
            raise ValueError("SimulationResult lacks net_fuel_heat_deficit_kW and its components")
        deficit = k.total_external_heating_kW - k.tailgas_combustion_heat_kW
    deficit = max(0.0, float(deficit))
    pump = float(k.pump_power_kW or 0.0)
    return float(h2), float(nh3_kg), deficit, pump


def parse_scenario(scenario: str) -> tuple[str, str]:
    """'grey' -> ('grey', 'natural_gas'); 'blue/self_firing' or 'blue:electric' -> (route, heating)."""
    s = scenario.strip().lower().replace(":", "/").replace("gray", "grey")
    route, _, heat = s.partition("/")
    heat = heat or "natural_gas"
    if route not in NH3_ROUTES and route not in load_factors()["upstream_ammonia"]:
        raise ValueError(f"unknown ammonia route {route!r}; use one of {NH3_ROUTES}")
    if heat not in HEATING_OPTIONS:
        raise ValueError(f"unknown heating option {heat!r}; use one of {HEATING_OPTIONS}")
    return route, heat


def carbon_intensity(
    result: SimulationResult,
    scenario: str = "grey",
    *,
    heating: str | None = None,
    grid: str = "singapore_2024",
    distance_km: float | None = None,
    nh3_ef_kg_per_kg: float | None = None,
    grid_ef_kg_per_kWh: float | None = None,
    ship_ef_kg_per_tkm: float | None = None,
    ng_ef_kg_per_TJ: float | None = None,
    fired_heater_efficiency: float | None = None,
    electric_heater_efficiency: float | None = None,
) -> CarbonIntensityResult:
    """Carbon intensity (kg CO2e / kg H2 product) of one scenario.

    Simplified carbon-intensity accounting - NOT a life-cycle assessment; see the module docstring
    for the system boundary. ``scenario`` is an NH3 route (``green`` | ``blue`` | ``grey``) optionally
    followed by ``/<heating>`` with heating in ``natural_gas`` | ``self_firing`` | ``electric``
    (default ``natural_gas``; ``heating=`` overrides). Any keyword factor override is recorded
    with provenance ``assumption``.
    """
    f = load_factors()
    route, heat = parse_scenario(scenario)
    if heating is not None:
        if heating not in HEATING_OPTIONS:
            raise ValueError(f"unknown heating option {heating!r}")
        heat = heating
    if grid not in f["electricity"]:
        raise ValueError(f"unknown grid {grid!r}; use one of {list(f['electricity'])}")

    h2_kg_h, nh3_kg_h, deficit_kW, pump_kW = _activities(result)

    e_nh3 = f["upstream_ammonia"][route]
    e_grid = f["electricity"][grid]
    e_ship = f["transport"]["ship_ef"]
    e_dist = f["transport"]["distance_km"]
    e_ng = f["heating"]["natural_gas_combustion"]
    e_eta_f = f["heating"]["fired_heater_efficiency_lhv"]
    e_eta_e = f["heating"]["electric_heater_efficiency"]

    def pick(override, entry):
        return (float(entry["value"]), False) if override is None else (float(override), True)

    ef_nh3, o1 = pick(nh3_ef_kg_per_kg, e_nh3)
    ef_grid, o2 = pick(grid_ef_kg_per_kWh, e_grid)
    ef_ship, o3 = pick(ship_ef_kg_per_tkm, e_ship)
    dist, o4 = pick(distance_km, e_dist)
    ef_ng, o5 = pick(ng_ef_kg_per_TJ, e_ng)
    eta_f, o6 = pick(fired_heater_efficiency, e_eta_f)
    eta_e, o7 = pick(electric_heater_efficiency, e_eta_e)
    for name, v in (("nh3 EF", ef_nh3), ("grid EF", ef_grid), ("ship EF", ef_ship), ("distance", dist), ("NG EF", ef_ng)):
        if v < 0 or not math.isfinite(v):
            raise ValueError(f"{name} must be finite and >= 0 (got {v})")
    if not (eta_f > 0 and eta_e > 0):
        raise ValueError("heater efficiencies must be > 0")

    used = [_factor(f"upstream_ammonia.{route}", e_nh3, ef_nh3, o1),
            _factor("transport.ship_ef", e_ship, ef_ship, o3),
            _factor("transport.distance_km", e_dist, dist, o4),
            _factor(f"electricity.{grid}", e_grid, ef_grid, o2)]

    # --- activities per hour ----------------------------------------------------------------
    nh3_fuel_kg_h = 0.0
    ng_GJ_h = 0.0
    elec_kW = pump_kW
    heat_kg_h = 0.0
    fuel_kW = deficit_kW / eta_f
    lhv_nh3_kJ_per_kg = LHV_KJ_PER_MOL["NH3"] / MOLAR_MASS["NH3"] * 1000.0
    ship_per_kg_nh3 = ef_ship * dist / 1000.0  # kg CO2e per kg NH3 (t km -> per kg)
    if heat == "natural_gas":
        ng_GJ_h = fuel_kW * 3600.0 / 1e6
        heat_kg_h = ng_GJ_h / 1000.0 * ef_ng
        used.append(_factor("heating.natural_gas_combustion", e_ng, ef_ng, o5))
        used.append(_factor("heating.fired_heater_efficiency_lhv", e_eta_f, eta_f, o6))
    elif heat == "self_firing":
        nh3_fuel_kg_h = fuel_kW * 3600.0 / lhv_nh3_kJ_per_kg
        heat_kg_h = nh3_fuel_kg_h * (ef_nh3 + ship_per_kg_nh3)
        used.append(_factor("heating.fired_heater_efficiency_lhv", e_eta_f, eta_f, o6))
    else:  # electric
        elec_kW += deficit_kW / eta_e
        used.append(_factor("heating.electric_heater_efficiency", e_eta_e, eta_e, o7))

    up_kg_h = nh3_kg_h * ef_nh3
    tr_kg_h = nh3_kg_h * ship_per_kg_nh3
    el_kg_h = elec_kW * ef_grid  # kW x 1 h = kWh per hour
    br = CIBreakdown(
        upstream_ammonia=up_kg_h / h2_kg_h,
        transport=tr_kg_h / h2_kg_h,
        electricity=el_kg_h / h2_kg_h,
        external_heat=heat_kg_h / h2_kg_h,
    )
    total = br.upstream_ammonia + br.transport + br.electricity + br.external_heat

    notes = [METHOD_STATEMENT, f"Input simulation source: {result.source.value}."]
    if heat == "self_firing":
        notes.append("Self-firing: extra NH3 burnt for the heat deficit; its upstream and transport emissions are "
                     "booked under external_heat. NH3/tail-gas combustion N2O and NOx are outside the model.")
    if heat == "natural_gas":
        notes.append("Natural gas: combustion CO2 only; upstream gas supply chain excluded (CI is a lower bound).")
    if route == "green":
        notes.append("Green NH3 factor is 0 under Lee et al. (2022) boundary (equipment manufacture excluded).")
    notes.append("Electricity covers the feed pump only (plus electric heating if chosen); PSA/compressor power is "
                 "not in the simulation result and is therefore not counted.")
    return CarbonIntensityResult(
        case_id=result.case_id,
        input_source=result.source,
        scenario=f"{route}/{heat}",
        nh3_route=route,
        heating_option=heat,
        grid=grid,
        total_kgCO2e_per_kgH2=total,
        breakdown_kgCO2e_per_kgH2=br,
        h2_product_kg_h=h2_kg_h,
        nh3_feed_kg_h=nh3_kg_h,
        nh3_fuel_kg_h=nh3_fuel_kg_h,
        kg_nh3_per_kg_h2=(nh3_kg_h + nh3_fuel_kg_h) / h2_kg_h,
        heat_deficit_kW=deficit_kW,
        electricity_kW=elec_kW,
        natural_gas_GJ_h=ng_GJ_h,
        transport_distance_km=dist,
        factors=used,
        reference_lines=reference_lines(f),
        notes=notes,
    )


def compare_scenarios(result: SimulationResult, **overrides) -> ScenarioComparison:
    """Green / blue / grey NH3 x {imported natural gas, self-firing, electric heating}.

    Simplified carbon-intensity accounting - NOT a life-cycle assessment. ``overrides`` are passed
    to :func:`carbon_intensity` (e.g. ``grid=``, ``distance_km=``); ``nh3_ef_kg_per_kg`` is not
    allowed here because each row uses its own route factor.
    """
    if "nh3_ef_kg_per_kg" in overrides:
        raise ValueError("nh3_ef_kg_per_kg cannot be overridden in a route comparison")
    rows: list[ScenarioRow] = []
    last: CarbonIntensityResult | None = None
    for route in NH3_ROUTES:
        for heat in HEATING_OPTIONS:
            r = carbon_intensity(result, f"{route}/{heat}", **overrides)
            last = r
            rows.append(ScenarioRow(nh3_route=route, heating_option=heat, heating_label=HEATING_LABELS[heat],
                                    total_kgCO2e_per_kgH2=r.total_kgCO2e_per_kgH2,
                                    breakdown_kgCO2e_per_kgH2=r.breakdown_kgCO2e_per_kgH2))
    assert last is not None
    return ScenarioComparison(
        case_id=result.case_id, input_source=result.source, grid=last.grid,
        transport_distance_km=last.transport_distance_km, rows=rows,
        reference_lines=last.reference_lines,
        notes=[METHOD_STATEMENT, f"Input simulation source: {result.source.value}.",
               f"Heat deficit {last.heat_deficit_kW:.1f} kW after tail-gas firing; "
               f"feed {last.nh3_feed_kg_h / last.h2_product_kg_h:.3f} kg NH3/kg H2."],
    )


__all__ = [
    "CarbonIntensityResult", "CIBreakdown", "FactorUsed", "ReferenceLine", "ScenarioRow", "ScenarioComparison",
    "carbon_intensity", "compare_scenarios", "reference_lines", "load_factors", "parse_scenario",
    "NH3_ROUTES", "HEATING_OPTIONS", "SYSTEM_BOUNDARY", "METHOD_STATEMENT", "DATA_FILE",
]
