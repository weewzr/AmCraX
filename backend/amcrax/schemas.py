"""Shared data contract for AmCraX (pydantic v2).

This module is the single source of truth for the structures exchanged between the
Aspen Plus automation layer, the independent Python models, the FastAPI backend and
the React frontend (``frontend/src/api/types.ts`` mirrors these classes).

Unit conventions (fixed across the whole code base)
---------------------------------------------------
* temperature      degC at interfaces (``*_C``), kelvin inside models (``*_K``)
* pressure         bar absolute (``*_bar``)
* molar flow       kmol/h
* mass flow        kg/h
* duty / power     kW  (positive duty = heat ADDED to the process stream)
* molar energy     kJ/mol
* compositions     mole or mass fractions in [0, 1]
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0"

#: Aspen Plus property methods accepted in a case specification (PENG-ROB is the validated default).
PROPERTY_METHODS: tuple[str, ...] = ("PENG-ROB", "RK-SOAVE", "RKS-BM", "PR-BM", "SRK", "IDEAL")

#: Component IDs used in the Aspen model and in every composition dictionary.
COMPONENTS: tuple[str, ...] = ("NH3", "H2", "N2", "H2O", "O2")

#: Molar masses, kg/kmol (IUPAC 2021 standard atomic weights, rounded).
MOLAR_MASS: dict[str, float] = {
    "NH3": 17.0305,
    "H2": 2.01588,
    "N2": 28.0134,
    "H2O": 18.01528,
    "O2": 31.9988,
}

#: Lower heating values, kJ/mol (derived from standard enthalpies of formation at 298.15 K,
#: gaseous water product): H2 241.826; NH3 316.8 (NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O(g)).
LHV_KJ_PER_MOL: dict[str, float] = {"H2": 241.826, "NH3": 316.80}


class DataSource(str, Enum):
    """Provenance label that must accompany every number shown to a user."""

    ASPEN = "aspen_plus_v15"        # extracted from an actual Aspen Plus V15 run
    PYTHON = "python_model"         # independent AmCraX Python calculation
    LITERATURE = "literature"       # published value (must carry a citation key)
    ASSUMPTION = "assumption"       # engineering assumption (must be documented)
    DEMO = "demo"                   # illustrative placeholder - never a real result


class CaseInputs(BaseModel):
    """Operating specification of one flowsheet case (Aspen and Python models share it)."""

    # The case id becomes a file name and appears in the Aspen input file (TITLE): restrict it to a
    # safe character set so that it can neither escape the run directory nor inject input language.
    case_id: str = Field("baseline", pattern=r"^[A-Za-z0-9_\-]{1,64}$",
                         description="Case identifier: letters, digits, underscore, hyphen (max 64)")
    feed_total_kmol_h: float = Field(100.0, gt=0, description="Total liquid ammonia feed, kmol/h")
    feed_h2o_mole_frac: float = Field(0.002, ge=0, lt=0.2, description="Water in the ammonia feed (mole fraction)")
    reactor_temperature_C: float = Field(600.0, ge=250, le=1000, description="Cracker (isothermal) temperature")
    reactor_pressure_bar: float = Field(20.0, ge=1.0, le=100, description="Cracker outlet pressure")
    heat_integration: bool = Field(True, description="True: feed/effluent exchanger FEHE present")
    fehe_hot_end_approach_K: float = Field(50.0, ge=5, le=300, description="FEHE: hot inlet minus cold outlet temperature")
    psa_feed_temperature_C: float = Field(40.0, ge=5, le=80, description="Cooler outlet / PSA feed temperature")
    psa_h2_recovery: float = Field(0.85, gt=0, le=1, description="Fraction of H2 in PSA feed recovered to product (reduced-order PSA)")
    psa_n2_slip: float = Field(0.001, ge=0, le=0.05, description="Fraction of N2 in PSA feed slipping to product (reduced-order PSA)")
    burner_excess_air: float = Field(0.15, ge=0, le=2.0, description="Tail-gas burner excess air (fraction over stoichiometric)")
    stack_temperature_C: float = Field(150.0, ge=60, le=400, description="Flue-gas temperature leaving heat recovery")
    property_method: str = Field("PENG-ROB", description="Aspen property method (one of PROPERTY_METHODS)")

    @field_validator("property_method")
    @classmethod
    def _known_property_method(cls, v: str) -> str:
        # written verbatim into the Aspen input file ("PROPERTIES <method>"): allow-list only
        method = str(v).strip().upper()
        if method not in PROPERTY_METHODS:
            raise ValueError(f"property_method must be one of {', '.join(PROPERTY_METHODS)}")
        return method


class StreamResult(BaseModel):
    id: str
    name: str = ""
    source_block: Optional[str] = None
    dest_block: Optional[str] = None
    phase: Optional[str] = Field(None, description="'liquid' | 'vapor' | 'mixed'")
    temperature_C: Optional[float] = None
    pressure_bar: Optional[float] = None
    vapor_fraction: Optional[float] = None
    mole_flow_kmol_h: Optional[float] = None
    mass_flow_kg_h: Optional[float] = None
    enthalpy_flow_kW: Optional[float] = Field(None, description="Total enthalpy flow (simulator reference state)")
    mole_frac: dict[str, float] = Field(default_factory=dict)
    mass_frac: dict[str, float] = Field(default_factory=dict)
    component_mole_flow_kmol_h: dict[str, float] = Field(default_factory=dict)


class BlockResult(BaseModel):
    id: str
    name: str = ""
    block_type: str = Field("", description="Aspen model type, e.g. RGibbs, HeatX, Heater, Pump, Sep, RStoic")
    duty_kW: Optional[float] = Field(None, description="Net heat duty; positive = heat added to process")
    power_kW: Optional[float] = Field(None, description="Shaft/electrical power (pumps, compressors)")
    outlet_temperature_C: Optional[float] = None
    outlet_pressure_bar: Optional[float] = None
    details: dict[str, Optional[float | str]] = Field(default_factory=dict)


class RunStatus(BaseModel):
    converged: bool = False
    has_errors: bool = False
    has_warnings: bool = False
    messages: list[str] = Field(default_factory=list)
    engine_time_s: Optional[float] = None


class KPIs(BaseModel):
    """Key performance indicators. ``None`` means 'not available' - never substitute a guess."""

    nh3_conversion: Optional[float] = Field(None, description="1 - NH3 out / NH3 in across the cracker")
    h2_in_cracked_gas_kmol_h: Optional[float] = None
    h2_product_kmol_h: Optional[float] = None
    h2_product_kg_h: Optional[float] = None
    h2_purity_mole_frac: Optional[float] = None
    h2_yield_overall: Optional[float] = Field(None, description="H2 in product / (1.5 x NH3 fed)")
    reactor_duty_kW: Optional[float] = None
    preheat_duty_kW: Optional[float] = Field(None, description="Trim/fired heater HEATER duty")
    vaporiser_duty_kW: Optional[float] = None
    recovered_heat_kW: Optional[float] = Field(None, description="FEHE duty (0 when heat integration is off)")
    total_external_heating_kW: Optional[float] = Field(None, description="VAPORIZR + HEATER + CRACKER duties, plus the FLUEHX duty when it is positive (flame temperature below stack temperature: the flue gas must be heated), as defined in amcrax.kpis")
    cooling_duty_kW: Optional[float] = Field(None, description="COOLER duty magnitude")
    pump_power_kW: Optional[float] = None
    tailgas_combustion_heat_kW: Optional[float] = Field(None, description="Heat released cooling burner flue gas to stack T: max(-Q_FLUEHX, 0)")
    tailgas_lhv_kW: Optional[float] = None
    specific_heat_demand_kWh_per_kgH2: Optional[float] = None
    net_fuel_heat_deficit_kW: Optional[float] = Field(None, description="External heating minus tail-gas combustion heat (>0 = import needed). First-law, upper-bound metric: flue heat is credited 1:1 even where it lies below the reactor temperature; temperature-level feasibility is in amcrax.heat_integration")
    lhv_efficiency: Optional[float] = Field(None, description="LHV(H2 product) / (LHV(NH3 feed) + max(deficit, 0) + power). First-law, upper-bound metric: imported heat counted 1:1 against LHV (a 100 %-efficient fired heater), flue heat credited regardless of its temperature level, no credit for a surplus")


class Balances(BaseModel):
    mass_in_kg_h: Optional[float] = None
    mass_out_kg_h: Optional[float] = None
    mass_closure_rel: Optional[float] = None
    n_atoms_in_kmol_h: Optional[float] = None
    n_atoms_out_kmol_h: Optional[float] = None
    h_atoms_in_kmol_h: Optional[float] = None
    h_atoms_out_kmol_h: Optional[float] = None
    energy_in_kW: Optional[float] = None
    energy_out_kW: Optional[float] = None
    energy_closure_rel: Optional[float] = None


class SimulationResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    case_id: str
    source: DataSource
    created_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    model_file: Optional[str] = None
    inputs: CaseInputs
    status: RunStatus
    streams: dict[str, StreamResult] = Field(default_factory=dict)
    blocks: dict[str, BlockResult] = Field(default_factory=dict)
    kpis: KPIs = Field(default_factory=KPIs)
    balances: Balances = Field(default_factory=Balances)
    notes: list[str] = Field(default_factory=list)


__all__ = [
    "SCHEMA_VERSION",
    "COMPONENTS",
    "MOLAR_MASS",
    "LHV_KJ_PER_MOL",
    "DataSource",
    "CaseInputs",
    "StreamResult",
    "BlockResult",
    "RunStatus",
    "KPIs",
    "Balances",
    "SimulationResult",
]
