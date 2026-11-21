"""Pydantic result models of the heat-integration analysis (JSON-serialisable)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..schemas import DataSource


class HIStream(BaseModel):
    id: str
    name: str
    kind: str = Field(description="'hot' | 'cold'")
    supply_temperature_C: float
    target_temperature_C: float
    duty_kW: float = Field(description="Heat released (hot) or absorbed (cold), magnitude")
    included_in: list[str] = Field(description="'process' and/or 'with_flue'")
    curve_T_C: list[float]
    curve_H_kW: list[float] = Field(description="Cumulative heat content from the cold end")


class ProblemTableRow(BaseModel):
    T_shifted_hi_C: float
    T_shifted_lo_C: float
    deficit_kW: float = Field(description="Cold demand minus hot supply in the interval")
    cascade_out_kW: float = Field(description="Heat cascaded below the interval (feasible cascade)")


class PinchTargets(BaseModel):
    label: str
    dT_min_K: float
    hot_utility_kW: float
    cold_utility_kW: float
    total_hot_streams_kW: float
    total_cold_streams_kW: float
    heat_recovery_kW: float = Field(description="Cold demand met by hot streams = total cold - hot utility")
    pinch_shifted_C: Optional[float] = None
    pinch_hot_C: Optional[float] = None
    pinch_cold_C: Optional[float] = None
    threshold_problem: bool = Field(False, description="True when one utility is zero (no pinch)")
    energy_balance_residual_kW: float = Field(description="(Qh - Qc) - (sum cold - sum hot); ~0")
    hot_composite_H_kW: list[float]
    hot_composite_T_C: list[float]
    cold_composite_H_kW: list[float]
    cold_composite_T_C: list[float]
    gcc_H_kW: list[float]
    gcc_T_shifted_C: list[float]
    problem_table: list[ProblemTableRow]


class ConfigurationRow(BaseModel):
    id: str
    label: str
    external_heating_kW: float
    external_cooling_kW: float
    process_heat_recovered_kW: float = Field(description="Process-to-process exchange (FEHE or pinch target)")
    tailgas_heat_used_kW: float = Field(0.0, description="Flue-gas heat credited to process duties")
    reduction_vs_no_recovery: float = Field(description="Fractional reduction of external heating vs config (a)")
    specific_heat_demand_kWh_per_kgH2: Optional[float] = None
    basis: str = Field(description="How the numbers were obtained")


class FEHEAssessment(BaseModel):
    present_in_simulation: bool
    duty_kW: float
    duty_source: str
    hot_in_C: float
    hot_out_C: float
    cold_in_C: float
    cold_out_C: float
    hot_end_approach_K: float
    cold_end_approach_K: float
    min_internal_approach_K: float = Field(description="Minimum dT along the counter-current exchanger (non-linear H-T)")
    temperature_cross: bool
    approach_violation: bool = Field(description="min internal approach < dT_min")
    lmtd_K: Optional[float] = Field(None, description="Log-mean temperature difference from terminal temperatures")
    ua_lmtd_kW_K: Optional[float] = None
    ua_segmented_kW_K: Optional[float] = Field(None, description="Sum of dQ/LMTD over segments (accounts for non-linear H-T)")
    U_assumed_W_m2K: float
    U_range_W_m2K: list[float]
    area_m2: Optional[float] = None
    area_range_m2: list[float] = Field(default_factory=list)
    U_note: str
    hot_side_duty_model_kW: float = Field(description="Model hot-side enthalpy change between simulated terminal T")
    cold_side_duty_model_kW: float
    profile_duty_kW: list[float] = Field(default_factory=list)
    profile_hot_T_C: list[float] = Field(default_factory=list)
    profile_cold_T_C: list[float] = Field(default_factory=list)


class ConsistencyCheck(BaseModel):
    item: str
    model_kW: float
    simulated_kW: Optional[float] = None
    rel_deviation: Optional[float] = None


class HeatIntegrationResult(BaseModel):
    case_id: str
    source: DataSource = DataSource.PYTHON
    input_source: DataSource
    dT_min_K: float
    reactor_temperature_C: float
    h2_product_kg_h: Optional[float] = None
    reaction_duty_source: str
    feed_saturation_temperature_C: float
    feed_latent_heat_kW: float
    streams: list[HIStream]
    targets_process: PinchTargets
    targets_with_flue: Optional[PinchTargets] = None
    configurations: list[ConfigurationRow]
    fehe: Optional[FEHEAssessment] = None
    consistency: list[ConsistencyCheck] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
