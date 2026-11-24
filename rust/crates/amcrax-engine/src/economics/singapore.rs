//! Singapore techno-economic framework (Python `economics/singapore.py`): `evaluate` with the
//! capital modes `reference` (cho2026_itemised_v1, default), `equipment` (Phase 1, superseded)
//! and `legacy` (the lcoh.py correlation, superseded), the overrides of `EconomicAssumptions` and
//! `SGParams`, the PSA-recovery rescaling, the carbon-tax threshold test, NPV, IRR (bisection),
//! payback, the purification memo, and the break-even ammonia price.
//!
//! The result is the Python dict as JSON (same keys, same nesting), so the comparison with the
//! golden tables is key by key and the CLI output can replace the Python output.

use super::lcoh::{EconAssumptions, crf, estimate_capex};
use super::reference::{EconomicsData, RefCapexArgs, SINGAPORE_YAML};
use super::{jf, jo, json_bool, json_f64, json_opt_f64, json_string, py_round, pydiv, pypow};
use crate::error::EngineError;
use crate::pyops::{fmt_g, py_sum};
use crate::units::{LHV_H2_KJ_MOL, LHV_NH3_KJ_MOL, MM_H2, MM_NH3};
use serde_json::{Map, Value, json};

/// Ammonia price scenarios (`SCENARIOS`).
pub const SCENARIOS: [&str; 5] = ["grey", "blue", "green_current", "green_2030", "green_2050"];

/// The process numbers `evaluate` needs (Python `extract_summary` output).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Summary {
    pub case_id: Option<String>,
    pub source: Option<String>,
    pub heat_integration: Value,
    pub h2_kg_h: f64,
    pub nh3_feed_kmol_h: f64,
    pub heat_deficit_kw: f64,
    pub cooling_kw: f64,
    pub pump_kw: f64,
    pub h2_cracked_kmol_h: Option<f64>,
    pub psa_recovery: Option<f64>,
    pub tailgas_lhv_kw: Option<f64>,
    pub tailgas_heat_kw: Option<f64>,
}

fn req_num(d: &Value, k: &str) -> Result<f64, EngineError> {
    d[k].as_f64()
        .ok_or_else(|| EngineError::Domain(format!("KeyError: summary field {k}")))
}

fn truthy(x: Option<f64>) -> bool {
    matches!(x, Some(v) if v != 0.0)
}

impl Summary {
    /// A summary dict (`{"h2_kg_h": ..., ...}`).
    pub fn from_summary_json(d: &Value) -> Result<Self, EngineError> {
        Ok(Summary {
            case_id: d["case_id"].as_str().map(str::to_string),
            source: d["source"].as_str().map(str::to_string),
            heat_integration: d["heat_integration"].clone(),
            h2_kg_h: req_num(d, "h2_kg_h")?,
            nh3_feed_kmol_h: req_num(d, "nh3_feed_kmol_h")?,
            heat_deficit_kw: req_num(d, "heat_deficit_kW")?,
            cooling_kw: req_num(d, "cooling_kW")?,
            pump_kw: req_num(d, "pump_kW")?,
            h2_cracked_kmol_h: d["h2_cracked_kmol_h"].as_f64(),
            psa_recovery: d["psa_recovery"].as_f64(),
            tailgas_lhv_kw: d["tailgas_lhv_kW"].as_f64(),
            tailgas_heat_kw: d["tailgas_heat_kW"].as_f64(),
        })
    }

    /// Python `extract_summary(res)` for a summary dict or a stored `SimulationResult` dict.
    pub fn extract(d: &Value) -> Result<Self, EngineError> {
        if d.get("h2_kg_h").is_some() {
            return Self::from_summary_json(d);
        }
        let k = &d["kpis"];
        let feed = &d["streams"]["FEED"];
        let nh3 = feed["component_mole_flow_kmol_h"]["NH3"].as_f64();
        let nh3 = match nh3 {
            Some(x) if x != 0.0 => x,
            _ => {
                let i = &d["inputs"];
                req_num(i, "feed_total_kmol_h")? * (1.0 - req_num(i, "feed_h2o_mole_frac")?)
            }
        };
        let pump = match k["pump_power_kW"].as_f64() {
            Some(p) => p,
            None => match d["blocks"]["PUMP"]["power_kW"].as_f64() {
                Some(p) if p != 0.0 => p,
                _ => 0.0,
            },
        };
        Ok(Summary {
            case_id: d["case_id"].as_str().map(str::to_string),
            source: d["source"].as_str().map(str::to_string),
            heat_integration: d["inputs"]["heat_integration"].clone(),
            h2_kg_h: req_num(k, "h2_product_kg_h")?,
            nh3_feed_kmol_h: nh3,
            heat_deficit_kw: req_num(k, "net_fuel_heat_deficit_kW")?,
            cooling_kw: req_num(k, "cooling_duty_kW")?.abs(),
            pump_kw: pump,
            h2_cracked_kmol_h: k["h2_in_cracked_gas_kmol_h"].as_f64(),
            psa_recovery: d["inputs"]["psa_h2_recovery"].as_f64(),
            tailgas_lhv_kw: k["tailgas_lhv_kW"].as_f64(),
            tailgas_heat_kw: k["tailgas_combustion_heat_kW"].as_f64(),
        })
    }

    /// As the Python summary dict.
    pub fn to_json(&self) -> Value {
        json!({"case_id": self.case_id, "source": self.source, "heat_integration": self.heat_integration,
               "h2_kg_h": jf(self.h2_kg_h), "nh3_feed_kmol_h": jf(self.nh3_feed_kmol_h),
               "heat_deficit_kW": jf(self.heat_deficit_kw), "cooling_kW": jf(self.cooling_kw),
               "pump_kW": jf(self.pump_kw), "h2_cracked_kmol_h": jo(self.h2_cracked_kmol_h),
               "psa_recovery": jo(self.psa_recovery), "tailgas_lhv_kW": jo(self.tailgas_lhv_kw),
               "tailgas_heat_kW": jo(self.tailgas_heat_kw)})
    }
}

/// Field names of `SGParams` in the Python declaration order.
pub const SG_FIELDS: [&str; 18] = [
    "nh3_price_USD_per_t",
    "electricity_price_USD_per_kWh",
    "heat_fuel",
    "gas_heat_price_USD_per_kJ",
    "fuel_efficiency",
    "carbon_tax_SGD_per_t",
    "apply_threshold",
    "other_facility_emissions_tCO2e",
    "n2o_tCO2e_per_yr",
    "capex_mode",
    "capacity_scale",
    "psa_recovery",
    "h2_price_USD_per_kg",
    "transport_USD_per_kg_H2",
    "labour_scales_with_capacity",
    "capex_scaling_exponent",
    "reactor_size_driver",
    "item_size_ratio",
];

/// Python `SGParams` (dataclass: no validation).
#[derive(Debug, Clone, PartialEq)]
pub struct SgParams {
    pub nh3_price_usd_per_t: f64,
    pub electricity_price_usd_per_kwh: f64,
    pub heat_fuel: String,
    pub gas_heat_price_usd_per_kj: Option<f64>,
    pub fuel_efficiency: Option<f64>,
    pub carbon_tax_sgd_per_t: f64,
    pub apply_threshold: bool,
    pub other_facility_emissions_tco2e: f64,
    pub n2o_tco2e_per_yr: f64,
    pub capex_mode: String,
    pub capacity_scale: f64,
    pub psa_recovery: Option<f64>,
    pub h2_price_usd_per_kg: f64,
    pub transport_usd_per_kg_h2: Option<f64>,
    pub labour_scales_with_capacity: bool,
    pub capex_scaling_exponent: Option<f64>,
    pub reactor_size_driver: Option<String>,
    pub item_size_ratio: Option<Vec<(String, f64)>>,
}

impl SgParams {
    /// The dataclass defaults (reference-scenario electricity, carbon tax and H2 price).
    pub fn defaults(d: &EconomicsData) -> Self {
        let r = &d.reference;
        SgParams {
            nh3_price_usd_per_t: 450.0,
            electricity_price_usd_per_kwh: r.electricity_usd_per_kwh,
            heat_fuel: "ammonia".into(),
            gas_heat_price_usd_per_kj: None,
            fuel_efficiency: None,
            carbon_tax_sgd_per_t: r.carbon_tax_sgd_per_t,
            apply_threshold: true,
            other_facility_emissions_tco2e: 0.0,
            n2o_tco2e_per_yr: 0.0,
            capex_mode: "reference".into(),
            capacity_scale: 1.0,
            psa_recovery: None,
            h2_price_usd_per_kg: r.h2_selling_price_usd_per_kg,
            transport_usd_per_kg_h2: None,
            labour_scales_with_capacity: false,
            capex_scaling_exponent: None,
            reactor_size_driver: None,
            item_size_ratio: None,
        }
    }

    fn set(&mut self, k: &str, v: &Value) -> Result<(), EngineError> {
        let f = |v: &Value| json_f64(k, v);
        let of = |v: &Value| json_opt_f64(k, v);
        match k {
            "nh3_price_USD_per_t" => self.nh3_price_usd_per_t = f(v)?,
            "electricity_price_USD_per_kWh" => self.electricity_price_usd_per_kwh = f(v)?,
            "heat_fuel" => self.heat_fuel = json_string(k, v)?,
            "gas_heat_price_USD_per_kJ" => self.gas_heat_price_usd_per_kj = of(v)?,
            "fuel_efficiency" => self.fuel_efficiency = of(v)?,
            "carbon_tax_SGD_per_t" => self.carbon_tax_sgd_per_t = f(v)?,
            "apply_threshold" => self.apply_threshold = json_bool(k, v)?,
            "other_facility_emissions_tCO2e" => self.other_facility_emissions_tco2e = f(v)?,
            "n2o_tCO2e_per_yr" => self.n2o_tco2e_per_yr = f(v)?,
            "capex_mode" => self.capex_mode = json_string(k, v)?,
            "capacity_scale" => self.capacity_scale = f(v)?,
            "psa_recovery" => self.psa_recovery = of(v)?,
            "h2_price_USD_per_kg" => self.h2_price_usd_per_kg = f(v)?,
            "transport_USD_per_kg_H2" => self.transport_usd_per_kg_h2 = of(v)?,
            "labour_scales_with_capacity" => self.labour_scales_with_capacity = json_bool(k, v)?,
            "capex_scaling_exponent" => self.capex_scaling_exponent = of(v)?,
            "reactor_size_driver" => {
                self.reactor_size_driver = if v.is_null() {
                    None
                } else {
                    Some(json_string(k, v)?)
                }
            }
            "item_size_ratio" => {
                self.item_size_ratio = match v {
                    Value::Null => None,
                    Value::Object(m) => Some(
                        m.iter()
                            .map(|(i, x)| json_f64(i, x).map(|f| (i.clone(), f)))
                            .collect::<Result<_, _>>()?,
                    ),
                    _ => {
                        return Err(EngineError::Domain(
                            "TypeError: item_size_ratio must be a mapping".into(),
                        ));
                    }
                }
            }
            _ => {
                return Err(EngineError::Domain(format!(
                    "KeyError: unknown SGParams field '{k}'"
                )));
            }
        }
        Ok(())
    }

    /// Python `p.__dict__`.
    pub fn to_json(&self) -> Value {
        json!({
            "nh3_price_USD_per_t": jf(self.nh3_price_usd_per_t),
            "electricity_price_USD_per_kWh": jf(self.electricity_price_usd_per_kwh),
            "heat_fuel": self.heat_fuel,
            "gas_heat_price_USD_per_kJ": jo(self.gas_heat_price_usd_per_kj),
            "fuel_efficiency": jo(self.fuel_efficiency),
            "carbon_tax_SGD_per_t": jf(self.carbon_tax_sgd_per_t),
            "apply_threshold": self.apply_threshold,
            "other_facility_emissions_tCO2e": jf(self.other_facility_emissions_tco2e),
            "n2o_tCO2e_per_yr": jf(self.n2o_tco2e_per_yr),
            "capex_mode": self.capex_mode,
            "capacity_scale": jf(self.capacity_scale),
            "psa_recovery": jo(self.psa_recovery),
            "h2_price_USD_per_kg": jf(self.h2_price_usd_per_kg),
            "transport_USD_per_kg_H2": jo(self.transport_usd_per_kg_h2),
            "labour_scales_with_capacity": self.labour_scales_with_capacity,
            "capex_scaling_exponent": jo(self.capex_scaling_exponent),
            "reactor_size_driver": self.reactor_size_driver,
            "item_size_ratio": self.item_size_ratio.as_ref().map(|m| {
                Value::Object(m.iter().map(|(k, v)| (k.clone(), jf(*v))).collect::<Map<_, _>>())
            }),
        })
    }
}

/// The `scenario` argument: a scenario name or a price in USD/t.
#[derive(Debug, Clone, PartialEq)]
pub enum Scenario {
    Named(String),
    Price(f64),
}

impl Scenario {
    /// From a JSON value (string or number).
    pub fn from_json(v: &Value) -> Result<Self, EngineError> {
        match v {
            Value::String(s) => Ok(Scenario::Named(s.clone())),
            Value::Number(n) => n
                .as_f64()
                .map(Scenario::Price)
                .ok_or_else(|| EngineError::Domain("scenario".into())),
            _ => Err(EngineError::Domain(format!(
                "KeyError: scenario must be a name or a number, got {v}"
            ))),
        }
    }

    /// Python `scenario_price(scenario)`.
    pub fn price(&self, d: &EconomicsData) -> Result<f64, EngineError> {
        match self {
            Scenario::Price(p) => Ok(*p),
            Scenario::Named(s) => d.reference.nh3_price(s),
        }
    }
}

/// Overrides of `evaluate` (a flat mapping, as the Python dict).
pub type Overrides = Map<String, Value>;

/// Keyword arguments in order.
pub type KwList = Vec<(String, Value)>;

/// Python `_split_overrides`: (EconomicAssumptions keys, SGParams keys); `KeyError` otherwise.
pub fn split_overrides(o: &Overrides) -> Result<(KwList, KwList), EngineError> {
    let mut eo = Vec::new();
    let mut so = Vec::new();
    for (k, v) in o {
        if SG_FIELDS.contains(&k.as_str()) {
            so.push((k.clone(), v.clone()));
        } else if EconAssumptions::is_field(k) {
            eo.push((k.clone(), v.clone()));
        } else {
            return Err(EngineError::Domain(format!(
                "KeyError: unknown override '{k}'"
            )));
        }
    }
    Ok((eo, so))
}

/// Python `default_electricity_USD_per_kWh()` (2025 USEP average + network cost + fees).
pub fn default_electricity_usd_per_kwh(d: &EconomicsData) -> Result<f64, EngineError> {
    let sg = &d.singapore;
    let usep = sg.num_seq(
        SINGAPORE_YAML,
        &["electricity", "usep_2025_monthly_SGD_per_MWh", "value"],
    )?;
    let sgd = py_sum(usep.iter().copied()) / usep.len() as f64 / 1000.0
        + sg.num_v(SINGAPORE_YAML, &["electricity", "network_cost_SGD_per_kWh"])?
        + sg.num_v(SINGAPORE_YAML, &["electricity", "fees_SGD_per_kWh"])?;
    Ok(sgd / d.reference.fx_sgd_per_usd)
}

/// Python `equipment_capex(nh3_feed_kmol_h, a, location_factor, exponent)` (Phase 1 basis).
pub fn equipment_capex(
    d: &EconomicsData,
    nh3_feed_kmol_h: f64,
    a: &EconAssumptions,
    location_factor: Option<f64>,
    exponent: Option<f64>,
) -> Result<Value, EngineError> {
    let sg = &d.singapore;
    let f = SINGAPORE_YAML;
    let shares = sg.num_map(f, &["capex_equipment", "equipment_shares_pct", "value"])?;
    let s = py_sum(shares.iter().map(|e| e.1));
    let pec_ref = sg.num_v(f, &["capex_equipment", "pec_reference_kUSD"])? * 1e3;
    let ratio = nh3_feed_kmol_h / sg.num_v(f, &["capex_equipment", "reference_feed_kmol_h"])?;
    let n = match exponent {
        Some(x) => x,
        None => sg.num_v(f, &["capex_equipment", "scaling_exponent"])?,
    };
    let lf = match location_factor {
        Some(x) => x,
        None => sg.num_v(f, &["capex_equipment", "singapore_location_factor"])?,
    };
    let pec: Vec<(String, f64)> = shares
        .iter()
        .map(|(k, v)| (k.clone(), pec_ref * v / s * pypow(ratio, n) * lf))
        .collect();
    let pec_tot = py_sum(pec.iter().map(|e| e.1));
    let fac = sg.num_v(f, &["capex_equipment", "tci_over_pec"])?;
    let tci = pec_tot * fac * a.capex_multiplier;
    Ok(json!({
        "pec_USD": Value::Object(pec.iter().map(|(k, v)| (k.clone(), jf(*v))).collect()),
        "pec_total_USD": jf(pec_tot), "tci_over_pec": jf(fac), "scaling_exponent": jf(n),
        "location_factor": jf(lf), "capex_multiplier": jf(a.capex_multiplier), "total_capex_USD": jf(tci),
        "tci_by_equipment_USD": Value::Object(pec.iter()
            .map(|(k, v)| (k.clone(), jf(v * fac * a.capex_multiplier))).collect()),
        "basis": "Farokhi 2025 PEC point (500 kmol/h) split by Chopra 2026 shares, scaled by feed^0.8, x TCI/PEC 5.93",
    }))
}

/// Python `_irr(capex, net, n)`: 200 bisection steps on [0, 10] (`None` when no positive IRR).
pub fn irr(capex: f64, net: f64, n: i64) -> Option<f64> {
    if net <= 0.0 || net * n as f64 <= capex {
        return None;
    }
    let (mut lo, mut hi) = (0.0_f64, 10.0_f64);
    let npv = |r: f64| -> f64 {
        if r > 0.0 {
            -capex + net * (1.0 - pypow(1.0 + r, -(n as f64))) / r
        } else {
            -capex + net * n as f64
        }
    };
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        if npv(mid) > 0.0 {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    Some(0.5 * (lo + hi))
}

fn get_f(v: &Value, k: &str) -> Result<f64, EngineError> {
    v[k].as_f64()
        .ok_or_else(|| EngineError::Numerical(format!("internal: {k} missing")))
}

/// Python `evaluate(result_or_summary, scenario, overrides)`.
pub fn evaluate(
    d: &EconomicsData,
    s: &Summary,
    scenario: &Scenario,
    overrides: &Overrides,
) -> Result<Value, EngineError> {
    let (eo, so) = split_overrides(overrides)?;
    let r = &d.reference;
    let mode_raw = so
        .iter()
        .find(|e| e.0 == "capex_mode")
        .map(|e| e.1.clone())
        .unwrap_or_else(|| Value::String("reference".into()));
    let eo: Vec<(String, Value)> = if mode_raw != Value::String("legacy".into()) {
        let mut v: Vec<(String, Value)> = r
            .economic_overrides()
            .into_iter()
            .filter(|e| e.0 != "electricity_price_USD_per_kWh")
            .map(|(k, x)| (k.to_string(), jf(x)))
            .collect();
        v.extend(eo);
        v
    } else {
        eo
    };
    let a = EconAssumptions::with_overrides(d, &eo)?;
    let mut p = SgParams::defaults(d);
    let mut price: Option<Value> = None;
    for (k, v) in &so {
        if k == "nh3_price_USD_per_t" {
            price = Some(v.clone());
        } else {
            p.set(k, v)?;
        }
    }
    p.nh3_price_usd_per_t = match &price {
        None => scenario.price(d)?,
        Some(v) => json_f64("nh3_price_USD_per_t", v)?,
    };
    let mut notes: Vec<String> = Vec::new();
    let sc = p.capacity_scale;
    let hours = a.operating_hours_h_per_yr;

    let (mut h2_kg_h, mut nh3_kmol_h) = (s.h2_kg_h, s.nh3_feed_kmol_h);
    let (mut deficit, mut cooling, mut pump) = (s.heat_deficit_kw, s.cooling_kw, s.pump_kw);
    let rec = s.psa_recovery;
    if let Some(new_rec) = p.psa_recovery
        && truthy(rec)
        && truthy(s.h2_cracked_kmol_h)
    {
        let rec_v = rec.unwrap_or_default();
        let h2c = s.h2_cracked_kmol_h.unwrap_or_default();
        let eff = if truthy(s.tailgas_lhv_kw) {
            let th = s
                .tailgas_heat_kw
                .ok_or_else(|| EngineError::Domain("TypeError: tailgas_heat_kW is None".into()))?;
            th / s.tailgas_lhv_kw.unwrap_or_default()
        } else {
            1.0
        };
        let d_lost = h2c * (rec_v - new_rec) * 1000.0 / 3600.0 * LHV_H2_KJ_MOL;
        h2_kg_h = h2c * new_rec * MM_H2;
        deficit -= eff * d_lost;
        notes.push(format!(
            "PSA recovery {} -> {}: H2 and tail-gas heat rescaled linearly from the stored \
             result (not re-simulated; cooler/exchanger duties and PSA power held).",
            fmt_g(rec_v, 6),
            fmt_g(new_rec, 6)
        ));
    }
    h2_kg_h *= sc;
    nh3_kmol_h *= sc;
    deficit *= sc;
    cooling *= sc;
    pump *= sc;
    if deficit < 0.0 {
        notes.push(format!("Heat surplus {:.1} kW not credited.", -deficit));
        deficit = 0.0;
    }
    let annual_h2 = h2_kg_h * hours;
    let nh3_usd_kg = p.nh3_price_usd_per_t / 1000.0;
    let eff_f = p.fuel_efficiency.unwrap_or(a.ammonia_fuel_heat_efficiency);
    let feed_kg_h = nh3_kmol_h * MM_NH3;
    let fx = r.fx_sgd_per_usd;
    let mut co2_t_yr = 0.0;
    let (fuel_nh3_kg_h, heat_usd_yr) = match p.heat_fuel.as_str() {
        "ammonia" => {
            let fuel = pydiv(deficit, LHV_NH3_KJ_MOL * eff_f, "fuel efficiency")? * 3600.0 * MM_NH3
                / 1000.0;
            (fuel, fuel * nh3_usd_kg * hours)
        }
        "natural_gas" => {
            let price = p
                .gas_heat_price_usd_per_kj
                .unwrap_or(a.fired_heat_price_usd_per_kj);
            let gj_yr = pydiv(deficit, eff_f, "fuel efficiency")? * 3600.0 / 1e6 * hours;
            co2_t_yr = gj_yr
                * d.singapore.num_v(
                    SINGAPORE_YAML,
                    &["gas_and_fuel", "natural_gas_co2_factor_kg_per_GJ"],
                )?
                / 1000.0;
            (0.0, gj_yr * 1e6 * price)
        }
        _ => {
            return Err(EngineError::Domain(
                "ValueError: heat_fuel must be 'ammonia' or 'natural_gas'".into(),
            ));
        }
    };
    let direct_t = co2_t_yr + p.n2o_tco2e_per_yr;
    let thr = r.carbon_threshold_tco2e_per_yr;
    let liable = (!p.apply_threshold) || (direct_t + p.other_facility_emissions_tco2e >= thr);
    let tax_usd_yr = if liable {
        direct_t * p.carbon_tax_sgd_per_t / fx
    } else {
        0.0
    };
    if direct_t == 0.0 {
        notes.push(
            "Direct CO2e = 0 (ammonia-fuelled heat, no carbon in the feed); N2O not quantified; carbon tax 0."
                .into(),
        );
    } else if !liable {
        notes.push(format!(
            "Direct emissions {direct_t:.0} tCO2e/yr below the {thr:?} t threshold: no tax liability."
        ));
    }
    let elec_kw = pump;
    let elec_usd_yr = elec_kw * p.electricity_price_usd_per_kwh * hours;
    let cool_usd_yr = cooling * 3600.0 * a.cooling_water_price_usd_per_kj * hours;
    let mut m_cat = nh3_kmol_h * 1000.0 * a.normal_molar_volume_l_per_mol * 1000.0
        / a.catalyst_space_velocity_ml_nh3_per_gcat_h
        / 1000.0;
    if let Some(m) = a.catalyst_mass_kg {
        m_cat = m * sc;
    }
    let cat_usd_yr = m_cat * a.resolved_catalyst_price_usd_per_kg()? / a.catalyst_lifetime_yr;

    // capital
    let (cap, capex_usd, tci_eq): (Value, f64, Option<Value>) = match p.capex_mode.as_str() {
        "legacy" => {
            let c = estimate_capex(d, h2_kg_h, &a)?.total_capex_usd;
            (
                json!({"total_capex_USD": jf(c), "basis": "legacy plant-level correlation (lcoh.py)"}),
                c,
                None,
            )
        }
        "reference" => {
            let mut args = RefCapexArgs::new(nh3_kmol_h);
            args.catalyst_mass_kg = Some(m_cat);
            args.reactor_size_driver = p.reactor_size_driver.clone();
            args.item_size_ratio = p.item_size_ratio.clone();
            args.exponent = p.capex_scaling_exponent;
            args.capex_multiplier = a.capex_multiplier;
            let c = d.reference_capex(&args)?;
            let t = get_f(&c, "total_capex_USD")?;
            let e = c["tci_by_equipment_USD"].clone();
            (c, t, Some(e))
        }
        "equipment" => {
            let c = equipment_capex(d, nh3_kmol_h, &a, None, p.capex_scaling_exponent)?;
            let t = get_f(&c, "total_capex_USD")?;
            let e = c["tci_by_equipment_USD"].clone();
            (c, t, Some(e))
        }
        _ => {
            return Err(EngineError::Domain(
                "ValueError: capex_mode must be 'reference', 'equipment' or 'legacy'".into(),
            ));
        }
    };
    let f = crf(a.discount_rate, a.plant_life_yr)?;
    let maint = a.maintenance_frac_capex_per_yr * capex_usd;
    let ins = a.insurance_frac_capex_per_yr * capex_usd;
    let lab = a.labour_usd_per_yr
        * (if p.labour_scales_with_capacity {
            sc
        } else {
            1.0
        });
    let overhead = a.plant_overhead_frac_labour_maint * (lab + maint);
    let fixed_base = maint + ins + lab + overhead;
    let fixed_usd_yr = fixed_base * (1.0 + a.g_and_a_frac_fixed_opex);

    const KEYS: [&str; 8] = [
        "capex",
        "fixed_opex",
        "ammonia_feed",
        "heat_fuel",
        "electricity",
        "cooling_water",
        "catalyst",
        "carbon_tax",
    ];
    let annual = [
        capex_usd * f,
        fixed_usd_yr,
        feed_kg_h * nh3_usd_kg * hours,
        heat_usd_yr,
        elec_usd_yr,
        cool_usd_yr,
        cat_usd_yr,
        tax_usd_yr,
    ];
    let mut breakdown = [0.0; 8];
    for i in 0..8 {
        breakdown[i] = pydiv(annual[i], annual_h2, "annual H2")?;
    }
    let lcoh = py_sum(breakdown.iter().copied());
    let rec_cost = lcoh - breakdown[2];

    let purification = match &tci_eq {
        Some(t) => {
            let pur_tci = get_f(t, "psa")? + get_f(t, "adsorber")?;
            let pur_yr = pur_tci
                * (f + (a.maintenance_frac_capex_per_yr + a.insurance_frac_capex_per_yr)
                    * (1.0 + a.g_and_a_frac_fixed_opex));
            Some(pydiv(pur_yr, annual_h2, "annual H2")?)
        }
        None => None,
    };
    let landed = p.transport_usd_per_kg_h2.map(|t| lcoh + t);
    let opex_yr = py_sum(annual[1..].iter().copied());
    let net = p.h2_price_usd_per_kg * annual_h2 - opex_yr;
    let n = py_round(a.plant_life_yr);
    let npv = if a.discount_rate > 0.0 {
        -capex_usd + net * (1.0 - pypow(1.0 + a.discount_rate, -(n as f64))) / a.discount_rate
    } else {
        -capex_usd + net * n as f64
    };
    let irr_v = irr(capex_usd, net, n);
    let payback = if net > 0.0 {
        Some(capex_usd / net)
    } else {
        None
    };
    if p.capex_mode == "reference" {
        notes.push(
            "Reference CAPEX (cho2026_itemised_v1, 2024 USD) excludes product compression/storage, NOx \
             after-treatment, land and taxes; no Singapore location factor (none sourced)."
                .into(),
        );
    } else if tci_eq.is_some() {
        notes.push(
            "Equipment-level CAPEX excludes NOx after-treatment, product compression/storage, land and taxes; \
             no Singapore location factor (none sourced)."
                .into(),
        );
    }
    notes.push(
        "Ammonia price is a scenario (delivered, international basis), not a Singapore transaction price."
            .into(),
    );
    let obj = |v: &[f64; 8], m: f64| -> Value {
        Value::Object(
            KEYS.iter()
                .zip(v)
                .map(|(k, x)| (k.to_string(), jf(x * m)))
                .collect(),
        )
    };
    let cost_basis = if p.capex_mode == "reference" {
        r.price_year_label()
    } else {
        d.singapore
            .get("base_year_label")
            .as_str()
            .unwrap_or_default()
            .to_string()
    };
    Ok(json!({
        "case_id": s.case_id, "input_source": s.source,
        "scenario": match scenario { Scenario::Named(n) => n.clone(), Scenario::Price(_) => "custom".into() },
        "source_type": "python", "currency": "USD",
        "cost_basis": cost_basis,
        "capex_mode": p.capex_mode, "fx_SGD_per_USD": jf(fx), "reference_scenario": r.provenance_stamp(),
        "lcoh_SGD_per_kg": jf(lcoh * fx), "rec_SGD_per_kg": jf(rec_cost * fx),
        "breakdown_SGD_per_kg": obj(&breakdown, fx),
        "npv_SGD": jf(npv * fx), "capex_total_SGD": jf(capex_usd * fx),
        "fixed_opex_detail_USD_per_yr": {"maintenance": jf(maint), "insurance": jf(ins), "labour": jf(lab),
                                         "plant_overhead": jf(overhead),
                                         "g_and_a": jf(fixed_base * a.g_and_a_frac_fixed_opex)},
        "nh3_price_USD_per_t": jf(p.nh3_price_usd_per_t), "h2_product_kg_h": jf(h2_kg_h), "annual_h2_kg": jf(annual_h2),
        "lcoh_USD_per_kg": jf(lcoh), "rec_USD_per_kg": jf(rec_cost), "breakdown_USD_per_kg": obj(&breakdown, 1.0),
        "purification_memo_USD_per_kg": jo(purification), "landed_cost_USD_per_kg": jo(landed),
        "npv_USD": jf(npv), "irr": jo(irr_v), "payback_yr": jo(payback), "h2_price_USD_per_kg": jf(p.h2_price_usd_per_kg),
        "kg_nh3_feed_per_kg_h2": jf(pydiv(feed_kg_h, h2_kg_h, "H2 product")?),
        "kg_nh3_fuel_per_kg_h2": jf(pydiv(fuel_nh3_kg_h, h2_kg_h, "H2 product")?),
        "catalyst_mass_kg": jf(m_cat), "direct_emissions_tCO2e_per_yr": jf(direct_t), "carbon_tax_liable": liable,
        "crf": jf(f), "capex": cap, "annual_USD_per_yr": obj(&annual, 1.0), "notes": notes,
        "assumptions": {"economic": a.to_json(), "singapore": p.to_json()},
    }))
}

/// Python `breakeven_nh3_price(result, target, overrides, metric)`: the NH3 price (USD/t) at
/// which `metric` equals the target (two evaluations; `None` when negative).
pub fn breakeven_nh3_price(
    d: &EconomicsData,
    s: &Summary,
    target_usd_per_kg: f64,
    overrides: &Overrides,
    metric: &str,
) -> Result<Option<f64>, EngineError> {
    let m = |e: &Value| -> Result<f64, EngineError> {
        e[metric].as_f64().ok_or_else(|| {
            EngineError::Domain(format!("KeyError/TypeError: metric {metric} not a number"))
        })
    };
    let l0 = m(&evaluate(d, s, &Scenario::Price(0.0), overrides)?)?;
    let l1 = m(&evaluate(d, s, &Scenario::Price(1000.0), overrides)?)?;
    let p = pydiv(
        target_usd_per_kg - l0,
        (l1 - l0) / 1000.0,
        "break-even slope",
    )?;
    Ok(if p >= 0.0 { Some(p) } else { None })
}

#[cfg(all(test, feature = "yaml"))]
mod tests {
    use super::*;

    fn baseline() -> Summary {
        let text = include_str!("../../../../../results/simulations/baseline.json");
        Summary::extract(&serde_json::from_str(text).unwrap()).unwrap()
    }

    #[test]
    fn published_baseline_numbers() {
        let d = EconomicsData::embedded();
        let s = baseline();
        let e = evaluate(d, &s, &Scenario::Named("grey".into()), &Overrides::new()).unwrap();
        let lcoh = e["lcoh_USD_per_kg"].as_f64().unwrap();
        assert!((lcoh / 4.015461254695034 - 1.0).abs() < 1e-12, "{lcoh}");
        let npv = e["npv_USD"].as_f64().unwrap();
        assert!((npv / -17455719.99837225 - 1.0).abs() < 1e-12, "{npv}");
        let be = breakeven_nh3_price(d, &s, 3.06, &Overrides::new(), "lcoh_USD_per_kg")
            .unwrap()
            .unwrap();
        assert!((be - 320.0081986623751).abs() < 1e-9, "{be}");
        let mut o = Overrides::new();
        o.insert("bogus".into(), json!(1));
        assert!(evaluate(d, &s, &Scenario::Named("grey".into()), &o).is_err());
    }
}
