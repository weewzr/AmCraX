//! `EconomicAssumptions` (Python `economics/models.py`, defaults from `economics.yaml`) and the
//! legacy LCOH correlation (Python `economics/lcoh.py`: `crf`, `estimate_capex`, `compute_lcoh`,
//! `breakeven_ammonia_price`, `lcoh_sensitivity`). The legacy correlation is superseded for
//! research outputs but is the version 1 basis of the core stored results
//! (`results/simulations/economics_*.json`), so it is ported unchanged.

use super::reference::{ECONOMICS_YAML, EconomicsData};
use super::{jf, jo, json_bool, json_f64, json_opt_f64, json_string, pydiv, pypow};
use crate::error::EngineError;
use crate::odata::OValue;
use crate::pyops::py_sum;
use crate::units::{LHV_NH3_KJ_MOL, MM_H2, MM_H2O, MM_NH3};
use serde_json::{Map, Value, json};

/// Field names of `EconomicAssumptions` in the Python declaration order.
pub const ECON_FIELDS: [&str; 28] = [
    "nh3_price_USD_per_t",
    "electricity_price_USD_per_kWh",
    "heat_import_mode",
    "ammonia_fuel_heat_efficiency",
    "fired_heat_price_USD_per_kJ",
    "credit_heat_surplus",
    "cooling_water_price_USD_per_kJ",
    "catalyst",
    "catalyst_price_USD_per_kg",
    "catalyst_lifetime_yr",
    "catalyst_space_velocity_mL_NH3_per_gcat_h",
    "normal_molar_volume_L_per_mol",
    "catalyst_mass_kg",
    "capex_method",
    "capex_fixed_USD",
    "capacity_exponent",
    "chopra_exclude_compressor",
    "chopra_remove_location_factor",
    "capex_multiplier",
    "maintenance_frac_capex_per_yr",
    "insurance_frac_capex_per_yr",
    "labour_USD_per_yr",
    "plant_overhead_frac_labour_maint",
    "g_and_a_frac_fixed_opex",
    "plant_life_yr",
    "discount_rate",
    "operating_hours_h_per_yr",
    "compression_power_kW",
];

/// Python `EconomicAssumptions` (pydantic model; validation as its `Field` constraints).
#[derive(Debug, Clone, PartialEq)]
pub struct EconAssumptions {
    pub nh3_price_usd_per_t: f64,
    pub electricity_price_usd_per_kwh: f64,
    pub heat_import_mode: String,
    pub ammonia_fuel_heat_efficiency: f64,
    pub fired_heat_price_usd_per_kj: f64,
    pub credit_heat_surplus: bool,
    pub cooling_water_price_usd_per_kj: f64,
    pub catalyst: String,
    pub catalyst_price_usd_per_kg: Option<f64>,
    pub catalyst_lifetime_yr: f64,
    pub catalyst_space_velocity_ml_nh3_per_gcat_h: f64,
    pub normal_molar_volume_l_per_mol: f64,
    pub catalyst_mass_kg: Option<f64>,
    pub capex_method: String,
    pub capex_fixed_usd: Option<f64>,
    pub capacity_exponent: f64,
    pub chopra_exclude_compressor: bool,
    pub chopra_remove_location_factor: bool,
    pub capex_multiplier: f64,
    pub maintenance_frac_capex_per_yr: f64,
    pub insurance_frac_capex_per_yr: f64,
    pub labour_usd_per_yr: f64,
    pub plant_overhead_frac_labour_maint: f64,
    pub g_and_a_frac_fixed_opex: f64,
    pub plant_life_yr: f64,
    pub discount_rate: f64,
    pub operating_hours_h_per_yr: f64,
    pub compression_power_kw: f64,
    /// `defaults.catalyst_price_USD_per_kg.<catalyst>.value` (not a model field).
    catalyst_price_table: Vec<(String, f64)>,
}

fn dflt<'a>(e: &'a OValue, name: &str) -> &'a OValue {
    e.at(&["defaults", name, "value"])
}

fn dnum(e: &OValue, name: &str) -> Result<f64, EngineError> {
    dflt(e, name)
        .as_f64()
        .ok_or_else(|| EngineError::data(ECONOMICS_YAML, format!("defaults.{name}.value")))
}

fn dstr(e: &OValue, name: &str) -> Result<String, EngineError> {
    dflt(e, name)
        .as_str()
        .map(str::to_string)
        .ok_or_else(|| EngineError::data(ECONOMICS_YAML, format!("defaults.{name}.value")))
}

fn verr(msg: String) -> EngineError {
    EngineError::Domain(format!("ValueError (pydantic validation): {msg}"))
}

impl EconAssumptions {
    /// The defaults (`EconomicAssumptions()`).
    pub fn defaults(d: &EconomicsData) -> Result<Self, EngineError> {
        let e = &d.economics;
        let mut table = Vec::new();
        for (k, v) in e.at(&["defaults", "catalyst_price_USD_per_kg"]).entries() {
            if let Some(x) = v.get("value").as_f64() {
                table.push((k.clone(), x));
            }
        }
        Ok(EconAssumptions {
            nh3_price_usd_per_t: dnum(e, "nh3_price_USD_per_t")?,
            electricity_price_usd_per_kwh: dnum(e, "electricity_price_USD_per_kWh")?,
            heat_import_mode: dstr(e, "heat_import_mode")?,
            ammonia_fuel_heat_efficiency: dnum(e, "ammonia_fuel_heat_efficiency")?,
            fired_heat_price_usd_per_kj: dnum(e, "fired_heat_price_USD_per_kJ")?,
            credit_heat_surplus: dflt(e, "credit_heat_surplus").as_bool().ok_or_else(|| {
                EngineError::data(ECONOMICS_YAML, "defaults.credit_heat_surplus.value")
            })?,
            cooling_water_price_usd_per_kj: dnum(e, "cooling_water_price_USD_per_kJ")?,
            catalyst: dstr(e, "catalyst")?,
            catalyst_price_usd_per_kg: None,
            catalyst_lifetime_yr: dnum(e, "catalyst_lifetime_yr")?,
            catalyst_space_velocity_ml_nh3_per_gcat_h: dnum(
                e,
                "catalyst_space_velocity_mL_NH3_per_gcat_h",
            )?,
            normal_molar_volume_l_per_mol: dnum(e, "normal_molar_volume_L_per_mol")?,
            catalyst_mass_kg: None,
            capex_method: dstr(e, "capex_method")?,
            capex_fixed_usd: None,
            capacity_exponent: dnum(e, "capacity_exponent")?,
            chopra_exclude_compressor: true,
            chopra_remove_location_factor: true,
            capex_multiplier: dnum(e, "capex_multiplier")?,
            maintenance_frac_capex_per_yr: dnum(e, "maintenance_frac_capex_per_yr")?,
            insurance_frac_capex_per_yr: dnum(e, "insurance_frac_capex_per_yr")?,
            labour_usd_per_yr: dnum(e, "labour_USD_per_yr")?,
            plant_overhead_frac_labour_maint: dnum(e, "plant_overhead_frac_labour_maint")?,
            g_and_a_frac_fixed_opex: dnum(e, "g_and_a_frac_fixed_opex")?,
            plant_life_yr: dnum(e, "plant_life_yr")?,
            discount_rate: dnum(e, "discount_rate")?,
            operating_hours_h_per_yr: dnum(e, "operating_hours_h_per_yr")?,
            compression_power_kw: dnum(e, "compression_power_kW")?,
            catalyst_price_table: table,
        })
    }

    /// True when `name` is a model field.
    pub fn is_field(name: &str) -> bool {
        ECON_FIELDS.contains(&name)
    }

    /// Set a field from a JSON value (pydantic lax coercion of numbers; no validation yet).
    pub fn set(&mut self, name: &str, v: &Value) -> Result<(), EngineError> {
        let f = |v: &Value| json_f64(name, v);
        match name {
            "nh3_price_USD_per_t" => self.nh3_price_usd_per_t = f(v)?,
            "electricity_price_USD_per_kWh" => self.electricity_price_usd_per_kwh = f(v)?,
            "heat_import_mode" => self.heat_import_mode = json_string(name, v)?,
            "ammonia_fuel_heat_efficiency" => self.ammonia_fuel_heat_efficiency = f(v)?,
            "fired_heat_price_USD_per_kJ" => self.fired_heat_price_usd_per_kj = f(v)?,
            "credit_heat_surplus" => self.credit_heat_surplus = json_bool(name, v)?,
            "cooling_water_price_USD_per_kJ" => self.cooling_water_price_usd_per_kj = f(v)?,
            "catalyst" => self.catalyst = json_string(name, v)?,
            "catalyst_price_USD_per_kg" => self.catalyst_price_usd_per_kg = json_opt_f64(name, v)?,
            "catalyst_lifetime_yr" => self.catalyst_lifetime_yr = f(v)?,
            "catalyst_space_velocity_mL_NH3_per_gcat_h" => {
                self.catalyst_space_velocity_ml_nh3_per_gcat_h = f(v)?
            }
            "normal_molar_volume_L_per_mol" => self.normal_molar_volume_l_per_mol = f(v)?,
            "catalyst_mass_kg" => self.catalyst_mass_kg = json_opt_f64(name, v)?,
            "capex_method" => self.capex_method = json_string(name, v)?,
            "capex_fixed_USD" => self.capex_fixed_usd = json_opt_f64(name, v)?,
            "capacity_exponent" => self.capacity_exponent = f(v)?,
            "chopra_exclude_compressor" => self.chopra_exclude_compressor = json_bool(name, v)?,
            "chopra_remove_location_factor" => {
                self.chopra_remove_location_factor = json_bool(name, v)?
            }
            "capex_multiplier" => self.capex_multiplier = f(v)?,
            "maintenance_frac_capex_per_yr" => self.maintenance_frac_capex_per_yr = f(v)?,
            "insurance_frac_capex_per_yr" => self.insurance_frac_capex_per_yr = f(v)?,
            "labour_USD_per_yr" => self.labour_usd_per_yr = f(v)?,
            "plant_overhead_frac_labour_maint" => self.plant_overhead_frac_labour_maint = f(v)?,
            "g_and_a_frac_fixed_opex" => self.g_and_a_frac_fixed_opex = f(v)?,
            "plant_life_yr" => self.plant_life_yr = f(v)?,
            "discount_rate" => self.discount_rate = f(v)?,
            "operating_hours_h_per_yr" => self.operating_hours_h_per_yr = f(v)?,
            "compression_power_kW" => self.compression_power_kw = f(v)?,
            _ => {
                return Err(EngineError::Domain(format!(
                    "KeyError: unknown EconomicAssumptions field '{name}'"
                )));
            }
        }
        Ok(())
    }

    /// The pydantic constraints of the model (`ge`, `gt`, `le`, the `Literal` options).
    pub fn validate(&self) -> Result<(), EngineError> {
        let ge0 = |n: &str, x: f64| {
            if x >= 0.0 {
                Ok(())
            } else {
                Err(verr(format!("{n} must be >= 0, got {x}")))
            }
        };
        let gt0 = |n: &str, x: f64| {
            if x > 0.0 {
                Ok(())
            } else {
                Err(verr(format!("{n} must be > 0, got {x}")))
            }
        };
        let le = |n: &str, x: f64, hi: f64| {
            if x <= hi {
                Ok(())
            } else {
                Err(verr(format!("{n} must be <= {hi}, got {x}")))
            }
        };
        ge0("nh3_price_USD_per_t", self.nh3_price_usd_per_t)?;
        ge0(
            "electricity_price_USD_per_kWh",
            self.electricity_price_usd_per_kwh,
        )?;
        if !matches!(
            self.heat_import_mode.as_str(),
            "ammonia_fuel" | "fired_heat"
        ) {
            return Err(verr(format!(
                "heat_import_mode {:?}",
                self.heat_import_mode
            )));
        }
        gt0(
            "ammonia_fuel_heat_efficiency",
            self.ammonia_fuel_heat_efficiency,
        )?;
        le(
            "ammonia_fuel_heat_efficiency",
            self.ammonia_fuel_heat_efficiency,
            1.0,
        )?;
        ge0(
            "fired_heat_price_USD_per_kJ",
            self.fired_heat_price_usd_per_kj,
        )?;
        ge0(
            "cooling_water_price_USD_per_kJ",
            self.cooling_water_price_usd_per_kj,
        )?;
        if !matches!(self.catalyst.as_str(), "Ni" | "Ru") {
            return Err(verr(format!("catalyst {:?}", self.catalyst)));
        }
        if let Some(x) = self.catalyst_price_usd_per_kg {
            ge0("catalyst_price_USD_per_kg", x)?;
        }
        gt0("catalyst_lifetime_yr", self.catalyst_lifetime_yr)?;
        gt0(
            "catalyst_space_velocity_mL_NH3_per_gcat_h",
            self.catalyst_space_velocity_ml_nh3_per_gcat_h,
        )?;
        gt0(
            "normal_molar_volume_L_per_mol",
            self.normal_molar_volume_l_per_mol,
        )?;
        if let Some(x) = self.catalyst_mass_kg {
            ge0("catalyst_mass_kg", x)?;
        }
        if !matches!(
            self.capex_method.as_str(),
            "ahmad2025_correlation" | "chopra2026_point" | "farokhi2025_point" | "fixed"
        ) {
            return Err(verr(format!("capex_method {:?}", self.capex_method)));
        }
        if let Some(x) = self.capex_fixed_usd {
            ge0("capex_fixed_USD", x)?;
        }
        gt0("capacity_exponent", self.capacity_exponent)?;
        le("capacity_exponent", self.capacity_exponent, 1.2)?;
        ge0("capex_multiplier", self.capex_multiplier)?;
        ge0(
            "maintenance_frac_capex_per_yr",
            self.maintenance_frac_capex_per_yr,
        )?;
        ge0(
            "insurance_frac_capex_per_yr",
            self.insurance_frac_capex_per_yr,
        )?;
        ge0("labour_USD_per_yr", self.labour_usd_per_yr)?;
        ge0(
            "plant_overhead_frac_labour_maint",
            self.plant_overhead_frac_labour_maint,
        )?;
        ge0("g_and_a_frac_fixed_opex", self.g_and_a_frac_fixed_opex)?;
        gt0("plant_life_yr", self.plant_life_yr)?;
        ge0("discount_rate", self.discount_rate)?;
        gt0("operating_hours_h_per_yr", self.operating_hours_h_per_yr)?;
        le(
            "operating_hours_h_per_yr",
            self.operating_hours_h_per_yr,
            8760.0,
        )?;
        ge0("compression_power_kW", self.compression_power_kw)?;
        Ok(())
    }

    /// Defaults, then the overrides in order, then validation (`EconomicAssumptions(**kw)`).
    pub fn with_overrides(d: &EconomicsData, kw: &[(String, Value)]) -> Result<Self, EngineError> {
        let mut a = Self::defaults(d)?;
        for (k, v) in kw {
            a.set(k, v)?;
        }
        a.validate()?;
        Ok(a)
    }

    /// Python `resolved_catalyst_price_USD_per_kg()`.
    pub fn resolved_catalyst_price_usd_per_kg(&self) -> Result<f64, EngineError> {
        if let Some(x) = self.catalyst_price_usd_per_kg {
            return Ok(x);
        }
        self.catalyst_price_table
            .iter()
            .find(|e| e.0 == self.catalyst)
            .map(|e| e.1)
            .ok_or_else(|| EngineError::Domain(format!("KeyError: catalyst {:?}", self.catalyst)))
    }

    /// Python `model_dump()`.
    pub fn to_json(&self) -> Value {
        json!({
            "nh3_price_USD_per_t": jf(self.nh3_price_usd_per_t),
            "electricity_price_USD_per_kWh": jf(self.electricity_price_usd_per_kwh),
            "heat_import_mode": self.heat_import_mode,
            "ammonia_fuel_heat_efficiency": jf(self.ammonia_fuel_heat_efficiency),
            "fired_heat_price_USD_per_kJ": jf(self.fired_heat_price_usd_per_kj),
            "credit_heat_surplus": self.credit_heat_surplus,
            "cooling_water_price_USD_per_kJ": jf(self.cooling_water_price_usd_per_kj),
            "catalyst": self.catalyst,
            "catalyst_price_USD_per_kg": jo(self.catalyst_price_usd_per_kg),
            "catalyst_lifetime_yr": jf(self.catalyst_lifetime_yr),
            "catalyst_space_velocity_mL_NH3_per_gcat_h": jf(self.catalyst_space_velocity_ml_nh3_per_gcat_h),
            "normal_molar_volume_L_per_mol": jf(self.normal_molar_volume_l_per_mol),
            "catalyst_mass_kg": jo(self.catalyst_mass_kg),
            "capex_method": self.capex_method,
            "capex_fixed_USD": jo(self.capex_fixed_usd),
            "capacity_exponent": jf(self.capacity_exponent),
            "chopra_exclude_compressor": self.chopra_exclude_compressor,
            "chopra_remove_location_factor": self.chopra_remove_location_factor,
            "capex_multiplier": jf(self.capex_multiplier),
            "maintenance_frac_capex_per_yr": jf(self.maintenance_frac_capex_per_yr),
            "insurance_frac_capex_per_yr": jf(self.insurance_frac_capex_per_yr),
            "labour_USD_per_yr": jf(self.labour_usd_per_yr),
            "plant_overhead_frac_labour_maint": jf(self.plant_overhead_frac_labour_maint),
            "g_and_a_frac_fixed_opex": jf(self.g_and_a_frac_fixed_opex),
            "plant_life_yr": jf(self.plant_life_yr),
            "discount_rate": jf(self.discount_rate),
            "operating_hours_h_per_yr": jf(self.operating_hours_h_per_yr),
            "compression_power_kW": jf(self.compression_power_kw),
        })
    }
}

/// Python `lcoh.crf(discount_rate, life_yr)` (`ValueError` for a life <= 0).
pub fn crf(discount_rate: f64, life_yr: f64) -> Result<f64, EngineError> {
    let (i, n) = (discount_rate, life_yr);
    if n <= 0.0 {
        return Err(EngineError::Domain(
            "ValueError: life_yr must be > 0".into(),
        ));
    }
    if i == 0.0 {
        return Ok(1.0 / n);
    }
    let f = pypow(1.0 + i, n);
    Ok(i * f / (f - 1.0))
}

/// One CAPEX estimate (Python `CapexReferenceEstimate`, numeric fields).
#[derive(Debug, Clone, PartialEq)]
pub struct CapexEstimate {
    pub method: String,
    pub reference_capacity_kg_h2_h: Option<f64>,
    pub reference_capex_usd: Option<f64>,
    pub scaled_capex_usd: f64,
    pub exponent: Option<f64>,
}

impl CapexEstimate {
    fn to_json(&self) -> Value {
        json!({"method": self.method, "reference_capacity_kg_H2_h": jo(self.reference_capacity_kg_h2_h),
               "reference_capex_USD": jo(self.reference_capex_usd), "scaled_capex_USD": jf(self.scaled_capex_usd),
               "exponent": jo(self.exponent)})
    }
}

/// Python `CapexDetail` (numeric fields).
#[derive(Debug, Clone, PartialEq)]
pub struct CapexDetail {
    pub method: String,
    pub capacity_kg_h2_h: f64,
    pub total_capex_usd: f64,
    pub capex_multiplier: f64,
    pub selected: CapexEstimate,
    pub alternatives: Vec<CapexEstimate>,
    /// Indicative split in the YAML order of `equipment_shares.shares_pct` (compressor removed).
    pub equipment_breakdown_usd: Vec<(String, f64)>,
}

impl CapexDetail {
    /// As the Python model dump (numeric and identifying fields).
    pub fn to_json(&self) -> Value {
        json!({"method": self.method, "capacity_kg_H2_h": jf(self.capacity_kg_h2_h),
               "total_capex_USD": jf(self.total_capex_usd), "capex_multiplier": jf(self.capex_multiplier),
               "selected": self.selected.to_json(),
               "alternatives": self.alternatives.iter().map(CapexEstimate::to_json).collect::<Vec<_>>(),
               "equipment_breakdown_USD": Value::Object(self.equipment_breakdown_usd.iter()
                    .map(|(k, v)| (k.clone(), jf(*v))).collect::<Map<String, Value>>())})
    }
}

fn enum_(d: &EconomicsData, path: &[&str]) -> Result<f64, EngineError> {
    let mut p = vec!["capex_references"];
    p.extend_from_slice(path);
    d.economics.num(ECONOMICS_YAML, &p)
}

/// Python `_capex_references(capacity_kg_h, a)` in the Python order (ahmad, chopra, farokhi).
pub fn capex_references(
    d: &EconomicsData,
    capacity_kg_h: f64,
    a: &EconAssumptions,
) -> Result<Vec<CapexEstimate>, EngineError> {
    let s_t_h = capacity_kg_h / 1000.0;
    let b = enum_(d, &["ahmad2025_correlation", "b"])?;
    let ahmad = CapexEstimate {
        method: "ahmad2025_correlation".into(),
        reference_capacity_kg_h2_h: None,
        reference_capex_usd: None,
        scaled_capex_usd: 1e6 * enum_(d, &["ahmad2025_correlation", "a_MUSD"])? * pypow(s_t_h, b),
        exponent: Some(b),
    };
    let n = a.capacity_exponent;
    let mut c1 = enum_(d, &["chopra2026_point", "capex_MUSD"])? * 1e6;
    if a.chopra_exclude_compressor {
        c1 *= 1.0 - enum_(d, &["chopra2026_point", "compressor_share_of_TCI", "value"])?;
    }
    if a.chopra_remove_location_factor {
        c1 /= enum_(d, &["chopra2026_point", "location_factor_india", "value"])?;
    }
    let s1 = enum_(d, &["chopra2026_point", "capacity_kg_H2_per_d"])? / 24.0;
    let chopra = CapexEstimate {
        method: "chopra2026_point".into(),
        reference_capacity_kg_h2_h: Some(s1),
        reference_capex_usd: Some(c1),
        scaled_capex_usd: c1 * pypow(capacity_kg_h / s1, n),
        exponent: Some(n),
    };
    let s1 = enum_(d, &["farokhi2025_point", "h2_kg_per_kg_nh3"])?
        * enum_(d, &["farokhi2025_point", "nh3_feed_kmol_h"])?
        * MM_NH3;
    let c1 = enum_(d, &["farokhi2025_point", "tci_kUSD"])? * 1e3;
    let farokhi = CapexEstimate {
        method: "farokhi2025_point".into(),
        reference_capacity_kg_h2_h: Some(s1),
        reference_capex_usd: Some(c1),
        scaled_capex_usd: c1 * pypow(capacity_kg_h / s1, n),
        exponent: Some(n),
    };
    Ok(vec![ahmad, chopra, farokhi])
}

/// Python `estimate_capex(capacity_kg_H2_h, a)`.
pub fn estimate_capex(
    d: &EconomicsData,
    capacity_kg_h2_h: f64,
    a: &EconAssumptions,
) -> Result<CapexDetail, EngineError> {
    let refs = capex_references(d, capacity_kg_h2_h, a)?;
    let sel = if a.capex_method == "fixed" {
        let x = a.capex_fixed_usd.ok_or_else(|| {
            EngineError::Domain("ValueError: capex_method 'fixed' requires capex_fixed_USD".into())
        })?;
        CapexEstimate {
            method: "fixed".into(),
            reference_capacity_kg_h2_h: None,
            reference_capex_usd: None,
            scaled_capex_usd: x,
            exponent: None,
        }
    } else {
        refs.iter()
            .find(|r| r.method == a.capex_method)
            .cloned()
            .ok_or_else(|| EngineError::Domain(format!("KeyError: {}", a.capex_method)))?
    };
    let total = sel.scaled_capex_usd * a.capex_multiplier;
    // _equipment_breakdown(total)
    let shares: Vec<(String, f64)> = d
        .economics
        .num_map(ECONOMICS_YAML, &["equipment_shares", "shares_pct"])?
        .into_iter()
        .filter(|e| e.0 != "compressor")
        .collect();
    let s = py_sum(shares.iter().map(|e| e.1));
    let br = shares
        .iter()
        .map(|(k, v)| (k.clone(), total * v / s))
        .collect();
    Ok(CapexDetail {
        alternatives: refs
            .into_iter()
            .filter(|r| r.method != sel.method)
            .collect(),
        method: sel.method.clone(),
        capacity_kg_h2_h,
        total_capex_usd: total,
        capex_multiplier: a.capex_multiplier,
        selected: sel,
        equipment_breakdown_usd: br,
    })
}

/// The fields of a `SimulationResult` that `compute_lcoh` reads.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct LcohInput {
    pub case_id: String,
    pub source_is_aspen: bool,
    pub h2_product_kg_h: Option<f64>,
    pub net_fuel_heat_deficit_kw: Option<f64>,
    pub cooling_duty_kw: Option<f64>,
    pub pump_power_kw_kpi: Option<f64>,
    pub pump_block_power_kw: Option<f64>,
    pub feed_stream_present: bool,
    pub feed_mass_flow_kg_h: Option<f64>,
    pub feed_nh3_kmol_h: Option<f64>,
    pub feed_total_kmol_h: f64,
    pub feed_h2o_mole_frac: f64,
}

fn opt_num(v: &Value) -> Option<f64> {
    v.as_f64()
}

impl LcohInput {
    /// Read a stored `SimulationResult` JSON (`results/simulations/*.json`).
    pub fn from_result_json(d: &Value) -> Result<Self, EngineError> {
        let k = &d["kpis"];
        let feed = &d["streams"]["FEED"];
        let i = &d["inputs"];
        Ok(LcohInput {
            case_id: d["case_id"].as_str().unwrap_or_default().to_string(),
            source_is_aspen: d["source"].as_str() == Some("aspen"),
            h2_product_kg_h: opt_num(&k["h2_product_kg_h"]),
            net_fuel_heat_deficit_kw: opt_num(&k["net_fuel_heat_deficit_kW"]),
            cooling_duty_kw: opt_num(&k["cooling_duty_kW"]),
            pump_power_kw_kpi: opt_num(&k["pump_power_kW"]),
            pump_block_power_kw: opt_num(&d["blocks"]["PUMP"]["power_kW"]),
            feed_stream_present: feed.is_object(),
            feed_mass_flow_kg_h: opt_num(&feed["mass_flow_kg_h"]),
            feed_nh3_kmol_h: opt_num(&feed["component_mole_flow_kmol_h"]["NH3"]),
            feed_total_kmol_h: i["feed_total_kmol_h"].as_f64().ok_or_else(|| {
                EngineError::Domain("SimulationResult.inputs.feed_total_kmol_h missing".into())
            })?,
            feed_h2o_mole_frac: i["feed_h2o_mole_frac"].as_f64().ok_or_else(|| {
                EngineError::Domain("SimulationResult.inputs.feed_h2o_mole_frac missing".into())
            })?,
        })
    }

    fn feed_mass_kg_h(&self) -> f64 {
        if let Some(m) = self
            .feed_mass_flow_kg_h
            .filter(|m| self.feed_stream_present && *m != 0.0)
        {
            return m;
        }
        let x = self.feed_h2o_mole_frac;
        self.feed_total_kmol_h * ((1.0 - x) * MM_NH3 + x * MM_H2O)
    }

    fn feed_nh3(&self) -> f64 {
        if let Some(n) = self
            .feed_nh3_kmol_h
            .filter(|n| self.feed_stream_present && *n != 0.0)
        {
            return n;
        }
        self.feed_total_kmol_h * (1.0 - self.feed_h2o_mole_frac)
    }

    fn pump_kw(&self) -> Result<f64, EngineError> {
        if let Some(p) = self.pump_power_kw_kpi {
            return Ok(p);
        }
        self.pump_block_power_kw.ok_or_else(|| {
            EngineError::Domain("ValueError: pump power not available in SimulationResult".into())
        })
    }
}

fn req(v: Option<f64>, name: &str) -> Result<f64, EngineError> {
    v.ok_or_else(|| {
        EngineError::Domain(format!(
            "ValueError: SimulationResult.kpis.{name} is None - LCOH cannot be computed without it"
        ))
    })
}

/// Python `catalyst_mass_kg(res, a)`.
pub fn catalyst_mass_kg(inp: &LcohInput, a: &EconAssumptions) -> f64 {
    if let Some(m) = a.catalyst_mass_kg {
        return m;
    }
    let ml_h = inp.feed_nh3() * 1000.0 * a.normal_molar_volume_l_per_mol * 1000.0;
    ml_h / a.catalyst_space_velocity_ml_nh3_per_gcat_h / 1000.0
}

/// Category order of the legacy breakdown (`CATEGORIES`).
pub const CATEGORIES: [&str; 7] = [
    "capex",
    "fixed_opex",
    "ammonia_feed",
    "imported_heat",
    "electricity",
    "cooling_water",
    "catalyst",
];

/// Python `compute_lcoh(result, assumptions)`: the numeric fields of `LCOHResult` as JSON.
pub fn compute_lcoh(
    d: &EconomicsData,
    inp: &LcohInput,
    a: &EconAssumptions,
) -> Result<Value, EngineError> {
    let h2_kg_h = req(inp.h2_product_kg_h, "h2_product_kg_h")?;
    if h2_kg_h <= 0.0 {
        return Err(EngineError::Domain(
            "ValueError: H2 product flow must be > 0".into(),
        ));
    }
    let deficit_kw = req(inp.net_fuel_heat_deficit_kw, "net_fuel_heat_deficit_kW")?;
    let cooling_kw = req(inp.cooling_duty_kw, "cooling_duty_kW")?.abs();
    let hours = a.operating_hours_h_per_yr;
    let annual_h2 = h2_kg_h * hours;
    let feed_kg_h = inp.feed_nh3() * MM_NH3;
    let _feed_stream_kg_h = inp.feed_mass_kg_h();
    let nh3_usd_per_kg = a.nh3_price_usd_per_t / 1000.0;
    let heat_kw = if deficit_kw > 0.0 || a.credit_heat_surplus {
        deficit_kw
    } else {
        0.0
    };
    let mut fuel_kg_h = 0.0;
    let heat_usd_h = if a.heat_import_mode == "ammonia_fuel" {
        fuel_kg_h =
            heat_kw / (LHV_NH3_KJ_MOL * a.ammonia_fuel_heat_efficiency) * 3600.0 * MM_NH3 / 1000.0;
        fuel_kg_h * nh3_usd_per_kg
    } else {
        heat_kw * 3600.0 * a.fired_heat_price_usd_per_kj
    };
    let elec_kw = inp.pump_kw()? + a.compression_power_kw;
    let m_cat = catalyst_mass_kg(inp, a);
    let cat_usd_yr = m_cat * a.resolved_catalyst_price_usd_per_kg()? / a.catalyst_lifetime_yr;
    let cap = estimate_capex(d, h2_kg_h, a)?;
    let f = crf(a.discount_rate, a.plant_life_yr)?;
    let capex_yr = cap.total_capex_usd * f;
    let maint = a.maintenance_frac_capex_per_yr * cap.total_capex_usd;
    let ins = a.insurance_frac_capex_per_yr * cap.total_capex_usd;
    let overhead = a.plant_overhead_frac_labour_maint * (a.labour_usd_per_yr + maint);
    let fixed_base = maint + ins + a.labour_usd_per_yr + overhead;
    let fixed_yr = fixed_base * (1.0 + a.g_and_a_frac_fixed_opex);
    let annual = [
        capex_yr,
        fixed_yr,
        feed_kg_h * nh3_usd_per_kg * hours,
        heat_usd_h * hours,
        elec_kw * a.electricity_price_usd_per_kwh * hours,
        cooling_kw * 3600.0 * a.cooling_water_price_usd_per_kj * hours,
        cat_usd_yr,
    ];
    let breakdown: Vec<f64> = annual.iter().map(|v| v / annual_h2).collect();
    let total = py_sum(breakdown.iter().copied());
    let mut ann = Map::new();
    let mut br = Map::new();
    for (i, c) in CATEGORIES.iter().enumerate() {
        ann.insert(c.to_string(), jf(annual[i]));
        br.insert(c.to_string(), jf(breakdown[i]));
    }
    ann.insert("fixed_opex.maintenance".into(), jf(maint));
    ann.insert("fixed_opex.insurance".into(), jf(ins));
    ann.insert("fixed_opex.labour".into(), jf(a.labour_usd_per_yr));
    ann.insert("fixed_opex.plant_overhead".into(), jf(overhead));
    ann.insert(
        "fixed_opex.g_and_a".into(),
        jf(fixed_base * a.g_and_a_frac_fixed_opex),
    );
    ann.insert("total".into(), jf(py_sum(annual.iter().copied())));
    Ok(json!({
        "case_id": inp.case_id,
        "lcoh_USD_per_kg": jf(total),
        "breakdown_USD_per_kg": br,
        "annual_costs_USD_per_yr": ann,
        "annual_h2_kg": jf(annual_h2),
        "h2_product_kg_h": jf(h2_kg_h),
        "crf": jf(f),
        "capex": cap.to_json(),
        "kg_nh3_feed_per_kg_h2": jf(feed_kg_h / h2_kg_h),
        "kg_nh3_fuel_per_kg_h2": jf(fuel_kg_h / h2_kg_h),
        "stoichiometric_floor_kg_nh3_per_kg_h2": jf(STOICHIOMETRIC_KG_NH3_PER_KG_H2),
        "reconversion_cost_USD_per_kg": jf(total - breakdown[2]),
    }))
}

/// `2 NH3 -> N2 + 3 H2`: kg NH3 per kg H2 at complete conversion and recovery.
pub const STOICHIOMETRIC_KG_NH3_PER_KG_H2: f64 = 2.0 * MM_NH3 / (3.0 * MM_H2);

/// Python `breakeven_ammonia_price(result, a, target)` (`None` below the zero-price LCOH).
pub fn breakeven_ammonia_price(
    d: &EconomicsData,
    inp: &LcohInput,
    a: &EconAssumptions,
    target_lcoh_usd_per_kg: f64,
) -> Result<Option<f64>, EngineError> {
    let lcoh_at = |p: f64| -> Result<f64, EngineError> {
        let mut b = a.clone();
        b.nh3_price_usd_per_t = p;
        Ok(compute_lcoh(d, inp, &b)?["lcoh_USD_per_kg"]
            .as_f64()
            .unwrap_or(f64::NAN))
    };
    let l0 = lcoh_at(0.0)?;
    let l1 = lcoh_at(1000.0)?;
    let slope = (l1 - l0) / 1000.0;
    let p = pydiv(target_lcoh_usd_per_kg - l0, slope, "breakeven slope")?;
    Ok(if p >= 0.0 { Some(p) } else { None })
}
