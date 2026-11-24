//! Carbon intensity of cracked hydrogen and carbon pricing in Singapore (Python
//! `economics/carbon_pricing.py`; factors from `environmental.yaml` and `environmental/lca.py`).
//! Stage 3. Gate: 1e-12 relative (`amcrax verify carbon`).
//!
//! * Mode A `actual_sg`: the Carbon Pricing Act 2018 boundary (direct facility emissions, the
//!   25,000 tCO2e/yr threshold, N2O with the Act's GWP 265), computed by `evaluate`.
//! * Mode B `hypothetical_lca`: a price on the full carbon intensity that replaces the Mode A tax
//!   term (`LCOH_B = LCOH_A - tax_A + P CI / 1000 / fx`), always labelled hypothetical.
//! * `crossover_price`: the hypothetical price at which a dearer, cleaner route breaks even.

use crate::economics::reference::EconomicsData;
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate};
use crate::economics::{jf, jo, py_round, pydiv, pypow};
use crate::error::EngineError;
use crate::lca::route_spec;
use crate::odata::OValue;
use crate::pyops::{py_max, py_min, py_sum};
use crate::units::{LHV_NH3_KJ_MOL, MM_NH3};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// Heat supply of the cracker (Python `heating` option).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Heating {
    /// Natural-gas fired heater.
    NaturalGas,
    /// Burning a fraction of the product (PSA tail gas and NH3).
    SelfFiring,
    /// Electric heating.
    Electric,
}

impl Heating {
    /// Parse the Python option (`ValueError` otherwise).
    pub fn from_python(s: &str) -> Result<Heating, EngineError> {
        match s {
            "natural_gas" => Ok(Heating::NaturalGas),
            "self_firing" => Ok(Heating::SelfFiring),
            "electric" => Ok(Heating::Electric),
            _ => Err(EngineError::Domain(
                "ValueError: heating must be natural_gas | self_firing | electric".into(),
            )),
        }
    }

    /// The Python option.
    pub fn name(self) -> &'static str {
        match self {
            Heating::NaturalGas => "natural_gas",
            Heating::SelfFiring => "self_firing",
            Heating::Electric => "electric",
        }
    }
}

/// Carbon modes (`MODES`).
pub const MODES: [&str; 2] = ["actual_sg", "hypothetical_lca"];
/// Label of every Mode B output.
pub const HYPOTHETICAL_LABEL: &str = "HYPOTHETICAL life-cycle carbon price, not Singapore law; replaces the actual tax term \
                                      (no double counting)";
/// Label of Mode A.
pub const ACTUAL_LABEL: &str = "Singapore carbon tax, actual boundary (Carbon Pricing Act 2018): direct reckonable facility \
                                emissions only, only at or above 25,000 tCO2e/yr";
/// CPA second emissions threshold, tCO2e/yr.
pub const THRESHOLD_TCO2E_PER_YR: f64 = 25000.0;
/// CPA First Schedule GWP of N2O.
pub const GWP_N2O_CPA: f64 = 265.0;
/// EU ETS context level, EUR/tCO2 (secondary press report, context only).
pub const EU_ETS_EUR_PER_TCO2: f64 = 90.0;
/// Repository path of the emission factors.
pub const ENVIRONMENTAL_YAML: &str = "backend/amcrax/data/environmental.yaml";

/// The embedded emission-factor file.
#[cfg(feature = "yaml")]
pub const EMBEDDED_ENVIRONMENTAL: &str =
    include_str!("../../../../backend/amcrax/data/environmental.yaml");

/// The parsed `environmental.yaml` (Python `load_factors()`).
#[cfg(feature = "yaml")]
pub fn embedded_factors() -> &'static OValue {
    static CELL: std::sync::OnceLock<OValue> = std::sync::OnceLock::new();
    CELL.get_or_init(|| {
        OValue::from_yaml(ENVIRONMENTAL_YAML, EMBEDDED_ENVIRONMENTAL)
            .expect("embedded environmental.yaml is valid (checked in CI)")
    })
}

/// Python `legislated_rate_SGD(year)`.
pub fn legislated_rate_sgd(year: i64) -> f64 {
    if year <= 2023 {
        5.0
    } else if year <= 2025 {
        25.0
    } else {
        45.0
    }
}

/// Python `eu_ets_SGD_per_t()`.
pub fn eu_ets_sgd_per_t(d: &EconomicsData) -> f64 {
    EU_ETS_EUR_PER_TCO2 * d.reference.usd_per_eur * d.reference.fx_sgd_per_usd
}

/// Python `CIFactors`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CiFactors {
    pub ship_ef_kg_per_tkm: f64,
    pub distance_km: f64,
    pub grid_kg_per_kwh: f64,
    pub natural_gas_kg_per_tj: f64,
    pub fired_heater_efficiency_lhv: f64,
    pub electric_heater_efficiency: f64,
}

impl CiFactors {
    /// Python `ci_factors(grid)` from the parsed `environmental.yaml`.
    pub fn from_factors(f: &OValue, grid: &str) -> Result<Self, EngineError> {
        let v = |p: &[&str]| f.num_v(ENVIRONMENTAL_YAML, p);
        Ok(CiFactors {
            ship_ef_kg_per_tkm: v(&["transport", "ship_ef"])?,
            distance_km: v(&["transport", "distance_km"])?,
            grid_kg_per_kwh: f.val(&["electricity", grid]).as_f64().ok_or_else(|| {
                EngineError::Domain(format!("KeyError: electricity grid {grid:?}"))
            })?,
            natural_gas_kg_per_tj: v(&["heating", "natural_gas_combustion"])?,
            fired_heater_efficiency_lhv: v(&["heating", "fired_heater_efficiency_lhv"])?,
            electric_heater_efficiency: v(&["heating", "electric_heater_efficiency"])?,
        })
    }

    /// From the JSON form of the test vectors.
    pub fn from_json(v: &Value) -> Result<Self, EngineError> {
        let g = |k: &str| {
            v[k].as_f64()
                .ok_or_else(|| EngineError::Domain(format!("factors.{k}")))
        };
        Ok(CiFactors {
            ship_ef_kg_per_tkm: g("ship_ef_kg_per_tkm")?,
            distance_km: g("distance_km")?,
            grid_kg_per_kwh: g("grid_kg_per_kWh")?,
            natural_gas_kg_per_tj: g("natural_gas_kg_per_TJ")?,
            fired_heater_efficiency_lhv: g("fired_heater_efficiency_lhv")?,
            electric_heater_efficiency: g("electric_heater_efficiency")?,
        })
    }

    /// As the dataclass fields.
    pub fn to_json(&self) -> Value {
        json!({"ship_ef_kg_per_tkm": self.ship_ef_kg_per_tkm, "distance_km": self.distance_km,
               "grid_kg_per_kWh": self.grid_kg_per_kwh, "natural_gas_kg_per_TJ": self.natural_gas_kg_per_tj,
               "fired_heater_efficiency_lhv": self.fired_heater_efficiency_lhv,
               "electric_heater_efficiency": self.electric_heater_efficiency})
    }
}

/// Python `route_gate_ef(route)`: gate factor of a price scenario (green_* share the green CI).
pub fn route_gate_ef(route: &str) -> Result<Value, EngineError> {
    let key = match route {
        "green_current" | "green_2030" | "green_2050" => "green",
        r => r,
    };
    let s = route_spec(key)?;
    Ok(
        json!({"route_ef_key": key, "central": s.ef, "low": s.low, "high": s.high, "label": s.label}),
    )
}

/// The activity inputs of the carbon intensity (`{h2_kg_h, nh3_feed_kg_h, heat_deficit_kW, pump_kW}`).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CiInputs {
    pub h2_kg_h: f64,
    pub nh3_feed_kg_h: f64,
    pub heat_deficit_kw: f64,
    pub pump_kw: f64,
}

impl CiInputs {
    /// Python `ci_inputs_from_result` (from the economics summary).
    pub fn from_summary(s: &Summary) -> Self {
        CiInputs {
            h2_kg_h: s.h2_kg_h,
            nh3_feed_kg_h: s.nh3_feed_kmol_h * MM_NH3,
            heat_deficit_kw: s.heat_deficit_kw,
            pump_kw: s.pump_kw,
        }
    }

    /// From a JSON object with the four keys.
    pub fn from_json(v: &Value) -> Result<Self, EngineError> {
        let g = |k: &str| {
            v[k].as_f64()
                .ok_or_else(|| EngineError::Domain(format!("KeyError: inputs.{k}")))
        };
        Ok(CiInputs {
            h2_kg_h: g("h2_kg_h")?,
            nh3_feed_kg_h: g("nh3_feed_kg_h")?,
            heat_deficit_kw: g("heat_deficit_kW")?,
            pump_kw: g("pump_kW")?,
        })
    }

    /// As the Python dict.
    pub fn to_json(&self) -> Value {
        json!({"h2_kg_h": self.h2_kg_h, "nh3_feed_kg_h": self.nh3_feed_kg_h,
               "heat_deficit_kW": self.heat_deficit_kw, "pump_kW": self.pump_kw})
    }
}

/// Python `carbon_intensity_h2(inputs, nh3_ef, heating, distance_km, factors)`: kg CO2e/kg H2.
pub fn carbon_intensity_h2(
    inputs: &CiInputs,
    nh3_ef_kg_per_kg: f64,
    heating: &str,
    distance_km: Option<f64>,
    fc: &CiFactors,
) -> Result<Value, EngineError> {
    let dist = distance_km.unwrap_or(fc.distance_km);
    let deficit = py_max(0.0, inputs.heat_deficit_kw);
    let fuel_kw = pydiv(
        deficit,
        fc.fired_heater_efficiency_lhv,
        "fired heater efficiency",
    )?;
    let lhv_kg = LHV_NH3_KJ_MOL / MM_NH3 * 1000.0;
    let ship = fc.ship_ef_kg_per_tkm * dist / 1000.0;
    let (mut elec, mut heat, mut fuel_kg) = (inputs.pump_kw, 0.0, 0.0);
    match Heating::from_python(heating)? {
        Heating::NaturalGas => {
            heat = fuel_kw * 3600.0 / 1e6 / 1000.0 * fc.natural_gas_kg_per_tj;
        }
        Heating::SelfFiring => {
            fuel_kg = fuel_kw * 3600.0 / lhv_kg;
            heat = fuel_kg * (nh3_ef_kg_per_kg + ship);
        }
        Heating::Electric => {
            elec += pydiv(
                deficit,
                fc.electric_heater_efficiency,
                "electric heater efficiency",
            )?;
        }
    }
    let h2 = inputs.h2_kg_h;
    let br = [
        pydiv(inputs.nh3_feed_kg_h * nh3_ef_kg_per_kg, h2, "H2")?,
        pydiv(inputs.nh3_feed_kg_h * ship, h2, "H2")?,
        pydiv(elec * fc.grid_kg_per_kwh, h2, "H2")?,
        pydiv(heat, h2, "H2")?,
    ];
    Ok(json!({
        "total_kgCO2e_per_kgH2": jf(py_sum(br)),
        "breakdown_kgCO2e_per_kgH2": {"upstream_ammonia": jf(br[0]), "transport": jf(br[1]),
                                      "electricity": jf(br[2]), "external_heat": jf(br[3])},
        "nh3_fuel_kg_h": jf(fuel_kg), "heating": heating,
        "statement": "simplified carbon-intensity accounting, not a life-cycle assessment",
    }))
}

fn num_at(v: &Value, path: &[&str]) -> Result<f64, EngineError> {
    path.iter()
        .fold(v, |v, k| &v[*k])
        .as_f64()
        .ok_or_else(|| EngineError::Numerical(format!("internal: {} missing", path.join("."))))
}

/// Python `carbon_cost(econ, ci_total, mode, price)`; `econ` is an `evaluate` output.
pub fn carbon_cost(
    econ: &Value,
    ci_total_kgco2e_per_kgh2: f64,
    mode: &str,
    price_sgd_per_t: f64,
) -> Result<Value, EngineError> {
    let fx = num_at(econ, &["fx_SGD_per_USD"])?;
    let tax = num_at(econ, &["breakdown_USD_per_kg", "carbon_tax"])?;
    let lcoh_a = num_at(econ, &["lcoh_USD_per_kg"])?;
    if mode == "actual_sg" {
        return Ok(
            json!({"mode": mode, "USD_per_kg_H2": jf(tax), "SGD_per_kg_H2": jf(tax * fx),
                         "lcoh_USD_per_kg": jf(lcoh_a), "lcoh_SGD_per_kg": jf(lcoh_a * fx),
                         "hypothetical": false, "label": ACTUAL_LABEL}),
        );
    }
    if mode != "hypothetical_lca" {
        return Err(EngineError::Domain(format!(
            "ValueError: mode must be one of {MODES:?}"
        )));
    }
    if price_sgd_per_t < 0.0 || !price_sgd_per_t.is_finite() {
        return Err(EngineError::Domain(
            "ValueError: price must be finite and >= 0".into(),
        ));
    }
    let sgd = price_sgd_per_t * ci_total_kgco2e_per_kgh2 / 1000.0;
    let usd = sgd / fx;
    let lcoh = lcoh_a - tax + usd;
    Ok(
        json!({"mode": mode, "USD_per_kg_H2": jf(usd), "SGD_per_kg_H2": jf(sgd), "lcoh_USD_per_kg": jf(lcoh),
              "lcoh_SGD_per_kg": jf(lcoh * fx), "hypothetical": true, "label": HYPOTHETICAL_LABEL}),
    )
}

/// Python `actual_boundary(result, scenario, year, n2o_kg_per_h, overrides)`: Mode A with the
/// explicit threshold test (N2O converted with the CPA GWP 265).
pub fn actual_boundary(
    d: &EconomicsData,
    s: &Summary,
    scenario: &Scenario,
    year: i64,
    n2o_kg_per_h: f64,
    overrides: &Overrides,
) -> Result<Value, EngineError> {
    let mut o = overrides.clone();
    let hours_default = d.reference.raw.num_v(
        crate::economics::reference::REL_PATH,
        &["operation", "operating_hours_h_per_yr"],
    )?;
    let hours = match o.get("operating_hours_h_per_yr") {
        Some(v) => crate::economics::json_f64("operating_hours_h_per_yr", v)?,
        None => hours_default,
    };
    let n2o_t = n2o_kg_per_h * hours / 1000.0 * GWP_N2O_CPA;
    if !o.contains_key("carbon_tax_SGD_per_t") {
        o.insert("carbon_tax_SGD_per_t".into(), jf(legislated_rate_sgd(year)));
    }
    let prior = match o.get("n2o_tCO2e_per_yr") {
        Some(v) => crate::economics::json_f64("n2o_tCO2e_per_yr", v)?,
        None => 0.0,
    };
    o.insert("n2o_tCO2e_per_yr".into(), jf(prior + n2o_t));
    let e = evaluate(d, s, scenario, &o)?;
    let thr = THRESHOLD_TCO2E_PER_YR;
    let dt = num_at(&e, &["direct_emissions_tCO2e_per_yr"])?;
    Ok(
        json!({"mode": "actual_sg", "label": ACTUAL_LABEL, "year": year, "rate_SGD_per_t": o["carbon_tax_SGD_per_t"],
              "direct_tCO2e_per_yr": jf(dt), "n2o_tCO2e_per_yr": jf(n2o_t), "threshold_tCO2e_per_yr": jf(thr),
              "threshold_fraction": jf(dt / thr), "liable": e["carbon_tax_liable"],
              "carbon_tax_USD_per_kg": e["breakdown_USD_per_kg"]["carbon_tax"], "lcoh_USD_per_kg": e["lcoh_USD_per_kg"],
              "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"], "upstream_emissions_taxed": false, "econ": e}),
    )
}

/// Python `n2o_threshold_test(result, econ)`: the N2O emission that would make the plant liable,
/// against the fuel nitrogen burnt and the flue gas (`result`: stored SimulationResult dict).
pub fn n2o_threshold_test(result: &Value, econ: &Value) -> Result<Value, EngineError> {
    let thr = THRESHOLD_TCO2E_PER_YR;
    let hours = num_at(
        econ,
        &["assumptions", "economic", "operating_hours_h_per_yr"],
    )?;
    let n2o_t_yr = thr / GWP_N2O_CPA;
    let n2o_kg_h = n2o_t_yr * 1000.0 / hours;
    let n2o_kmol_h = n2o_kg_h / 44.013;
    let tg = &result["streams"]["TAILGAS"]["component_mole_flow_kmol_h"];
    let fuel_nh3_kmol_h =
        num_at(econ, &["kg_nh3_fuel_per_kg_h2"])? * num_at(econ, &["h2_product_kg_h"])? / MM_NH3;
    let fuel_n_kmol_h = tg["NH3"].as_f64().unwrap_or(0.0) + fuel_nh3_kmol_h;
    let flue = &result["streams"]["FLUE"];
    let o2 = num_at(flue, &["mole_frac", "O2"])?;
    let add_flue = fuel_nh3_kmol_h * (0.5 + 1.5 + 0.75 * 0.79 / 0.21) / (1.0 - o2 / 0.21);
    let flue_kmol_h = num_at(flue, &["mole_flow_kmol_h"])? + add_flue;
    Ok(json!({
        "n2o_needed_t_per_yr": jf(n2o_t_yr), "n2o_needed_kg_per_h": jf(n2o_kg_h),
        "fuel_nitrogen_kmol_N_per_h": jf(fuel_n_kmol_h),
        "fraction_of_fuel_N_to_N2O_needed": jf(pydiv(2.0 * n2o_kmol_h, fuel_n_kmol_h, "fuel N")?),
        "flue_gas_kmol_h_estimate": jf(flue_kmol_h),
        "n2o_ppmv_needed_in_flue": jf(n2o_kmol_h / flue_kmol_h * 1e6),
        "basis": "threshold 25,000 tCO2e/yr / GWP 265; fuel N = tail-gas NH3 (Aspen) + supplementary NH3 (economics); \
                  flue = stored FLUE + stoichiometric flue of the supplementary NH3 at the stored excess O2 (estimate)",
    }))
}

/// Python `n2o_at_ppmv(ppmv, threshold_test, hours)`.
pub fn n2o_at_ppmv(ppmv: f64, threshold_test: &Value, hours: f64) -> Result<Value, EngineError> {
    let kg_h = ppmv * 1e-6 * num_at(threshold_test, &["flue_gas_kmol_h_estimate"])? * 44.013;
    let t = kg_h * hours / 1000.0 * GWP_N2O_CPA;
    Ok(
        json!({"ppmv": jf(ppmv), "n2o_kg_per_h": jf(kg_h), "tCO2e_per_yr": jf(t),
              "threshold_fraction": jf(t / THRESHOLD_TCO2E_PER_YR)}),
    )
}

/// Options of Python `route_case` (keyword arguments).
#[derive(Debug, Clone, PartialEq)]
pub struct RouteCaseOpts {
    pub mode: String,
    pub price_sgd_per_t: f64,
    pub ci_level: String,
    pub nh3_ef_kg_per_kg: Option<f64>,
    pub benchmark_usd_per_kg: Option<f64>,
    pub benchmark_ci_kgco2e_per_kgh2: f64,
    pub overrides: Overrides,
}

impl Default for RouteCaseOpts {
    fn default() -> Self {
        RouteCaseOpts {
            mode: "actual_sg".into(),
            price_sgd_per_t: 0.0,
            ci_level: "central".into(),
            nh3_ef_kg_per_kg: None,
            benchmark_usd_per_kg: None,
            benchmark_ci_kgco2e_per_kgh2: 11.0,
            overrides: Overrides::new(),
        }
    }
}

/// Python `route_case(result, route, mode, price, ...)`: cost of hydrogen from one ammonia
/// route under one carbon mode (LCOH, carbon cost, break-even NH3 price, NPV).
pub fn route_case(
    d: &EconomicsData,
    factors: &OValue,
    s: &Summary,
    route: &str,
    k: &RouteCaseOpts,
) -> Result<Value, EngineError> {
    let r = &d.reference;
    let fx = r.fx_sgd_per_usd;
    let o = &k.overrides;
    let econ = evaluate(d, s, &Scenario::Named(route.into()), o)?;
    let ef = route_gate_ef(route)?;
    let ef_val = match k.nh3_ef_kg_per_kg {
        Some(x) => x,
        None => ef[k.ci_level.as_str()]
            .as_f64()
            .ok_or_else(|| EngineError::Domain(format!("KeyError: ci_level {:?}", k.ci_level)))?,
    };
    let fc = CiFactors::from_factors(factors, "singapore_2024")?;
    let ci = carbon_intensity_h2(&CiInputs::from_summary(s), ef_val, "self_firing", None, &fc)?;
    let ci_total = num_at(&ci, &["total_kgCO2e_per_kgH2"])?;
    let cc = carbon_cost(&econ, ci_total, &k.mode, k.price_sgd_per_t)?;
    let bench = k
        .benchmark_usd_per_kg
        .unwrap_or(r.h2_selling_price_usd_per_kg);
    let hyp = k.mode == "hypothetical_lca";
    let bench_adj = bench
        + if hyp {
            k.price_sgd_per_t * k.benchmark_ci_kgco2e_per_kgh2 / 1000.0 / fx
        } else {
            0.0
        };
    let e0 = evaluate(d, s, &Scenario::Price(0.0), o)?;
    let e1 = evaluate(d, s, &Scenario::Price(1000.0), o)?;
    let l0 = num_at(&e0, &["lcoh_USD_per_kg"])?;
    let slope = (num_at(&e1, &["lcoh_USD_per_kg"])? - l0) / 1000.0;
    let tax0 = num_at(&e0, &["breakdown_USD_per_kg", "carbon_tax"])?;
    let cc_usd = num_at(&cc, &["USD_per_kg_H2"])?;
    let base0 = l0 - tax0 + if hyp { cc_usd } else { tax0 };
    let be = pydiv(bench - base0, slope, "break-even slope")?;
    let be_adj = pydiv(bench_adj - base0, slope, "break-even slope")?;
    let rate = num_at(&econ, &["assumptions", "economic", "discount_rate"])?;
    let n = py_round(num_at(
        &econ,
        &["assumptions", "economic", "plant_life_yr"],
    )?);
    let annuity = pydiv(1.0 - pypow(1.0 + rate, -(n as f64)), rate, "discount rate")?;
    let d_carbon = cc_usd - num_at(&econ, &["breakdown_USD_per_kg", "carbon_tax"])?;
    let q = num_at(&econ, &["annual_h2_kg"])? * annuity;
    let npv = num_at(&econ, &["npv_USD"])? + (bench - num_at(&econ, &["h2_price_USD_per_kg"])?) * q
        - d_carbon * q;
    let npv_adj = npv + (bench_adj - bench) * q;
    let ef_del = ef_val + fc.ship_ef_kg_per_tkm * fc.distance_km / 1000.0;
    let nh3_price = num_at(&econ, &["nh3_price_USD_per_t"])?;
    let nh3_incl = nh3_price
        + if hyp {
            k.price_sgd_per_t * ef_del / fx
        } else {
            0.0
        };
    let mut out = json!({
        "route": route, "mode": k.mode, "hypothetical": hyp, "label": cc["label"],
        "carbon_price_SGD_per_tCO2e": if hyp { jf(k.price_sgd_per_t) }
            else { jf(num_at(&econ, &["assumptions", "singapore", "carbon_tax_SGD_per_t"])?) },
        "ci_level": if k.nh3_ef_kg_per_kg.is_none() { k.ci_level.clone() } else { "custom".into() },
        "nh3_gate_ef_kgCO2e_per_kgNH3": jf(ef_val),
        "carbon_intensity_kgCO2e_per_kgH2": jf(ci_total),
        "nh3_price_USD_per_t": jf(nh3_price),
        "nh3_cost_incl_carbon_USD_per_t": jf(nh3_incl), "nh3_cost_incl_carbon_SGD_per_t": jf(nh3_incl * fx),
        "carbon_cost_USD_per_kg": cc["USD_per_kg_H2"], "carbon_cost_SGD_per_kg": cc["SGD_per_kg_H2"],
        "lcoh_USD_per_kg": cc["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": cc["lcoh_SGD_per_kg"],
        "benchmark_USD_per_kg": jf(bench), "benchmark_carbon_adjusted_USD_per_kg": jf(bench_adj),
        "breakeven_nh3_USD_per_t": jf(be), "breakeven_nh3_vs_carbon_adjusted_benchmark_USD_per_t": jf(be_adj),
        "npv_USD": jf(npv), "npv_SGD": jf(npv * fx), "npv_at_carbon_adjusted_benchmark_USD": jf(npv_adj),
        "fx_SGD_per_USD": jf(fx),
    });
    if !hyp && let Some(m) = out.as_object_mut() {
        m.insert(
            "mode_a_note".into(),
            Value::String(
                "Upstream and shipping emissions of imported NH3 are outside the Act; the CI is reported \
                 for information and is not priced."
                    .into(),
            ),
        );
    }
    Ok(out)
}

/// Python `crossover_price(lcoh_a, ci_a, lcoh_b, ci_b, fx)`: 0 when route a is not dearer, `None`
/// when it never overtakes.
pub fn crossover_price(lcoh_a: f64, ci_a: f64, lcoh_b: f64, ci_b: f64, fx: f64) -> Option<f64> {
    if lcoh_a <= lcoh_b {
        return Some(0.0);
    }
    if ci_b <= ci_a {
        return None;
    }
    Some((lcoh_a - lcoh_b) * fx * 1000.0 / (ci_b - ci_a))
}

/// The pairwise threshold row of `scripts/research/carbon_pricing_run.py` (`thr` and the analytic
/// check): the hypothetical price at which route `a` overtakes route `b`, central and over the
/// corners of the gate-factor ranges.
pub fn pair_threshold(
    d: &EconomicsData,
    factors: &OValue,
    s: &Summary,
    a: &str,
    b: &str,
) -> Result<Value, EngineError> {
    let fx = d.reference.fx_sgd_per_usd;
    let fc = CiFactors::from_factors(factors, "singapore_2024")?;
    let inp = CiInputs::from_summary(s);
    let ci_of = |route: &str, level: &str| -> Result<f64, EngineError> {
        let ef = route_gate_ef(route)?[level].as_f64().unwrap_or(f64::NAN);
        num_at(
            &carbon_intensity_h2(&inp, ef, "self_firing", None, &fc)?,
            &["total_kgCO2e_per_kgH2"],
        )
    };
    let lc = |route: &str| -> Result<f64, EngineError> {
        num_at(
            &evaluate(d, s, &Scenario::Named(route.into()), &Overrides::new())?,
            &["lcoh_USD_per_kg"],
        )
    };
    let (la, lb) = (lc(a)?, lc(b)?);
    let ca = [ci_of(a, "central")?, ci_of(a, "low")?, ci_of(a, "high")?];
    let cb = [ci_of(b, "central")?, ci_of(b, "low")?, ci_of(b, "high")?];
    let cen = crossover_price(la, ca[0], lb, cb[0], fx);
    let mut corners = Vec::new();
    for x in [1, 2] {
        for y in [1, 2] {
            corners.push(crossover_price(la, ca[x], lb, cb[y], fx));
        }
    }
    let finite: Vec<f64> = corners.iter().flatten().copied().collect();
    let unbounded = corners.iter().any(Option::is_none);
    let lo = finite.iter().copied().reduce(py_min);
    let hi = if unbounded {
        None
    } else {
        finite.iter().copied().reduce(py_max)
    };
    let sd = |route: &str| -> Result<f64, EngineError> {
        d.singapore.num_v(
            crate::economics::reference::SINGAPORE_YAML,
            &["nh3_price_scenarios_USD_per_t", route],
        )
    };
    let dp = sd(a)? - sd(b)?;
    let de = route_gate_ef(b)?["central"].as_f64().unwrap_or(f64::NAN)
        - route_gate_ef(a)?["central"].as_f64().unwrap_or(f64::NAN);
    let analytic = if dp > 0.0 && de > 0.0 {
        Some(dp * fx / de)
    } else if dp <= 0.0 {
        Some(0.0)
    } else {
        None
    };
    Ok(
        json!({"route": a, "overtakes": b, "lcoh_gap_at_zero_USD_per_kg": jf(la - lb),
              "ci_gap_central_kgCO2e_per_kgH2": jf(cb[0] - ca[0]),
              "threshold_central_SGD_per_tCO2e": jo(cen),
              "threshold_range_from_ci_ranges_SGD_per_tCO2e": [jo(lo), jo(hi)],
              "upper_unbounded": unbounded, "analytic_dp_fx_over_def_SGD_per_tCO2e": jo(analytic)}),
    )
}
