"""Pydantic models of the AmCraX techno-economic (LCOH) module.

Defaults are read from ``backend/amcrax/data/economics.yaml`` (single source of truth); no cost
number is hard-coded here.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

from amcrax.schemas import DataSource

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "economics.yaml"


@lru_cache(maxsize=1)
def load_economics_data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _d(name: str):
    return load_economics_data()["defaults"][name]["value"]


class EconomicAssumptions(BaseModel):
    """All economic inputs. Defaults come from data/economics.yaml (see provenance there)."""

    nh3_price_USD_per_t: float = Field(default_factory=lambda: float(_d("nh3_price_USD_per_t")), ge=0)
    electricity_price_USD_per_kWh: float = Field(default_factory=lambda: float(_d("electricity_price_USD_per_kWh")), ge=0)
    heat_import_mode: Literal["ammonia_fuel", "fired_heat"] = Field(default_factory=lambda: _d("heat_import_mode"))
    ammonia_fuel_heat_efficiency: float = Field(default_factory=lambda: float(_d("ammonia_fuel_heat_efficiency")), gt=0, le=1)
    fired_heat_price_USD_per_kJ: float = Field(default_factory=lambda: float(_d("fired_heat_price_USD_per_kJ")), ge=0)
    credit_heat_surplus: bool = Field(default_factory=lambda: bool(_d("credit_heat_surplus")))
    cooling_water_price_USD_per_kJ: float = Field(default_factory=lambda: float(_d("cooling_water_price_USD_per_kJ")), ge=0)
    catalyst: Literal["Ni", "Ru"] = Field(default_factory=lambda: _d("catalyst"))
    catalyst_price_USD_per_kg: Optional[float] = Field(None, ge=0, description="None -> literature price of `catalyst`")
    catalyst_lifetime_yr: float = Field(default_factory=lambda: float(_d("catalyst_lifetime_yr")), gt=0)
    catalyst_space_velocity_mL_NH3_per_gcat_h: float = Field(
        default_factory=lambda: float(_d("catalyst_space_velocity_mL_NH3_per_gcat_h")), gt=0)
    normal_molar_volume_L_per_mol: float = Field(default_factory=lambda: float(_d("normal_molar_volume_L_per_mol")), gt=0)
    catalyst_mass_kg: Optional[float] = Field(None, ge=0, description="Override of the space-velocity sizing")
    capex_method: Literal["ahmad2025_correlation", "chopra2026_point", "farokhi2025_point", "fixed"] = Field(
        default_factory=lambda: _d("capex_method"))
    capex_fixed_USD: Optional[float] = Field(None, ge=0, description="Required when capex_method == 'fixed'")
    capacity_exponent: float = Field(default_factory=lambda: float(_d("capacity_exponent")), gt=0, le=1.2)
    chopra_exclude_compressor: bool = True
    chopra_remove_location_factor: bool = True
    capex_multiplier: float = Field(default_factory=lambda: float(_d("capex_multiplier")), ge=0)
    maintenance_frac_capex_per_yr: float = Field(default_factory=lambda: float(_d("maintenance_frac_capex_per_yr")), ge=0)
    insurance_frac_capex_per_yr: float = Field(default_factory=lambda: float(_d("insurance_frac_capex_per_yr")), ge=0)
    labour_USD_per_yr: float = Field(default_factory=lambda: float(_d("labour_USD_per_yr")), ge=0)
    plant_overhead_frac_labour_maint: float = Field(default_factory=lambda: float(_d("plant_overhead_frac_labour_maint")), ge=0)
    g_and_a_frac_fixed_opex: float = Field(default_factory=lambda: float(_d("g_and_a_frac_fixed_opex")), ge=0)
    plant_life_yr: float = Field(default_factory=lambda: float(_d("plant_life_yr")), gt=0)
    discount_rate: float = Field(default_factory=lambda: float(_d("discount_rate")), ge=0)
    operating_hours_h_per_yr: float = Field(default_factory=lambda: float(_d("operating_hours_h_per_yr")), gt=0, le=8760)
    compression_power_kW: float = Field(default_factory=lambda: float(_d("compression_power_kW")), ge=0)

    def resolved_catalyst_price_USD_per_kg(self) -> float:
        if self.catalyst_price_USD_per_kg is not None:
            return self.catalyst_price_USD_per_kg
        return float(load_economics_data()["defaults"]["catalyst_price_USD_per_kg"][self.catalyst]["value"])


class InputProvenance(BaseModel):
    value: Optional[float | str | bool] = None
    unit: str = ""
    source: DataSource
    citekey: Optional[str] = None
    page: Optional[str] = None
    locator: Optional[str] = None
    note: Optional[str] = None


class CapexReferenceEstimate(BaseModel):
    method: str
    reference_capacity_kg_H2_h: Optional[float] = None
    reference_capex_USD: Optional[float] = None
    scaled_capex_USD: float
    exponent: Optional[float] = None
    cost_year: str
    citekey: Optional[str] = None
    page: Optional[str] = None
    locator: Optional[str] = None
    adjustments: list[str] = Field(default_factory=list)
    source: DataSource = DataSource.LITERATURE


class CapexDetail(BaseModel):
    method: str
    capacity_kg_H2_h: float
    total_capex_USD: float
    capex_multiplier: float
    estimate_class: str = ("Preliminary order-of-magnitude estimate (AACE class 4-5 type, capacity-factored from "
                           "literature plant-level data); NOT a detailed engineering estimate")
    cost_basis: str
    selected: CapexReferenceEstimate
    alternatives: list[CapexReferenceEstimate] = Field(default_factory=list)
    equipment_breakdown_USD: dict[str, float] = Field(default_factory=dict)
    equipment_breakdown_note: str = ""


class LCOHResult(BaseModel):
    case_id: str
    source: DataSource = DataSource.PYTHON
    input_source: DataSource
    input_file: Optional[str] = None
    lcoh_USD_per_kg: float
    breakdown_USD_per_kg: dict[str, float]
    annual_costs_USD_per_yr: dict[str, float]
    annual_h2_kg: float
    h2_product_kg_h: float
    crf: float
    capex: CapexDetail
    kg_nh3_feed_per_kg_h2: float
    kg_nh3_fuel_per_kg_h2: float
    stoichiometric_floor_kg_nh3_per_kg_h2: float
    reconversion_cost_USD_per_kg: float = Field(..., description="LCOH minus NH3 feed cost (cho2026nickel REC definition)")
    cost_basis: str
    assumptions: EconomicAssumptions
    provenance: dict[str, InputProvenance]
    notes: list[str] = Field(default_factory=list)


class TornadoBar(BaseModel):
    parameter: str
    unit: str = ""
    base_value: float
    low_value: float
    high_value: float
    lcoh_base: float
    lcoh_at_low: float
    lcoh_at_high: float
    source_of_range: str = ""

    @property
    def swing(self) -> float:
        return abs(self.lcoh_at_high - self.lcoh_at_low)
