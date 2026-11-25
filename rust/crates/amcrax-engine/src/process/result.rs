//! Result and input data model of the flowsheet (Python `amcrax.schemas`: `CaseInputs`,
//! `StreamResult`, `BlockResult`, `RunStatus`, `KPIs`, `Balances`, `SimulationResult`), read from
//! and written to the JSON of the Python models. Mappings keep their insertion order (the Python
//! reference iterates and sums dicts in insertion order).

use crate::error::EngineError;
use crate::odata::OValue;
use crate::species::Species;
use serde_json::{Map, Value, json};

/// `amcrax.schemas.PROPERTY_METHODS`.
pub const PROPERTY_METHODS: [&str; 6] = ["PENG-ROB", "RK-SOAVE", "RKS-BM", "PR-BM", "SRK", "IDEAL"];
/// `amcrax.schemas.SCHEMA_VERSION`.
pub const SCHEMA_VERSION: &str = "1.0";

/// Molar masses (kg/kmol), `amcrax.schemas.MOLAR_MASS`.
pub fn molar_mass(s: Species) -> f64 {
    match s {
        Species::NH3 => 17.0305,
        Species::H2 => 2.01588,
        Species::N2 => 28.0134,
        Species::H2O => 18.01528,
        Species::O2 => 31.9988,
    }
}

/// `amcrax.schemas.LHV_KJ_PER_MOL` in its dict order.
pub const LHV_KJ_PER_MOL: [(Species, f64); 2] = [(Species::H2, 241.826), (Species::NH3, 316.80)];

/// Case inputs (Python `CaseInputs`, field names as in the JSON).
#[derive(Debug, Clone, PartialEq)]
pub struct CaseInputs {
    pub case_id: String,
    pub feed_total_kmol_h: f64,
    pub feed_h2o_mole_frac: f64,
    pub reactor_temperature_c: f64,
    pub reactor_pressure_bar: f64,
    pub heat_integration: bool,
    pub fehe_hot_end_approach_k: f64,
    pub psa_feed_temperature_c: f64,
    pub psa_h2_recovery: f64,
    pub psa_n2_slip: f64,
    pub burner_excess_air: f64,
    pub stack_temperature_c: f64,
    pub property_method: String,
}

impl Default for CaseInputs {
    fn default() -> Self {
        CaseInputs {
            case_id: "baseline".into(),
            feed_total_kmol_h: 100.0,
            feed_h2o_mole_frac: 0.002,
            reactor_temperature_c: 600.0,
            reactor_pressure_bar: 20.0,
            heat_integration: true,
            fehe_hot_end_approach_k: 50.0,
            psa_feed_temperature_c: 40.0,
            psa_h2_recovery: 0.85,
            psa_n2_slip: 0.001,
            burner_excess_air: 0.15,
            stack_temperature_c: 150.0,
            property_method: "PENG-ROB".into(),
        }
    }
}

const INPUT_KEYS: [&str; 13] = [
    "case_id",
    "feed_total_kmol_h",
    "feed_h2o_mole_frac",
    "reactor_temperature_C",
    "reactor_pressure_bar",
    "heat_integration",
    "fehe_hot_end_approach_K",
    "psa_feed_temperature_C",
    "psa_h2_recovery",
    "psa_n2_slip",
    "burner_excess_air",
    "stack_temperature_C",
    "property_method",
];

fn bad(msg: impl Into<String>) -> EngineError {
    EngineError::Domain(msg.into())
}

impl CaseInputs {
    /// Parse and validate a JSON object (pydantic `CaseInputs.model_validate`: defaults for
    /// missing fields, the field constraints, unknown keys rejected).
    pub fn from_value(v: &Value) -> Result<CaseInputs, EngineError> {
        let obj = v
            .as_object()
            .ok_or_else(|| bad("CaseInputs: JSON object expected"))?;
        for k in obj.keys() {
            if !INPUT_KEYS.contains(&k.as_str()) {
                return Err(bad(format!("CaseInputs: unknown field {k}")));
            }
        }
        let mut c = CaseInputs::default();
        let num = |k: &str, d: f64| -> Result<f64, EngineError> {
            match obj.get(k) {
                None => Ok(d),
                Some(x) => x
                    .as_f64()
                    .ok_or_else(|| bad(format!("CaseInputs.{k}: number expected"))),
            }
        };
        if let Some(x) = obj.get("case_id") {
            c.case_id = x
                .as_str()
                .ok_or_else(|| bad("CaseInputs.case_id: string expected"))?
                .to_string();
        }
        c.feed_total_kmol_h = num("feed_total_kmol_h", c.feed_total_kmol_h)?;
        c.feed_h2o_mole_frac = num("feed_h2o_mole_frac", c.feed_h2o_mole_frac)?;
        c.reactor_temperature_c = num("reactor_temperature_C", c.reactor_temperature_c)?;
        c.reactor_pressure_bar = num("reactor_pressure_bar", c.reactor_pressure_bar)?;
        if let Some(x) = obj.get("heat_integration") {
            c.heat_integration = x
                .as_bool()
                .ok_or_else(|| bad("CaseInputs.heat_integration: boolean expected"))?;
        }
        c.fehe_hot_end_approach_k = num("fehe_hot_end_approach_K", c.fehe_hot_end_approach_k)?;
        c.psa_feed_temperature_c = num("psa_feed_temperature_C", c.psa_feed_temperature_c)?;
        c.psa_h2_recovery = num("psa_h2_recovery", c.psa_h2_recovery)?;
        c.psa_n2_slip = num("psa_n2_slip", c.psa_n2_slip)?;
        c.burner_excess_air = num("burner_excess_air", c.burner_excess_air)?;
        c.stack_temperature_c = num("stack_temperature_C", c.stack_temperature_c)?;
        if let Some(x) = obj.get("property_method") {
            c.property_method = x
                .as_str()
                .ok_or_else(|| bad("CaseInputs.property_method: string expected"))?
                .trim()
                .to_uppercase();
        }
        c.validate()?;
        Ok(c)
    }

    /// The pydantic field constraints of `CaseInputs`.
    pub fn validate(&self) -> Result<(), EngineError> {
        let id_ok = !self.case_id.is_empty()
            && self.case_id.len() <= 64
            && self
                .case_id
                .chars()
                .all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-');
        if !id_ok {
            return Err(bad("CaseInputs.case_id must match ^[A-Za-z0-9_\\-]{1,64}$"));
        }
        type Bound = Option<f64>;
        let checks: [(&str, f64, Bound, Bound, Bound, Bound); 10] = [
            // name, value, gt, ge, lt, le
            (
                "feed_total_kmol_h",
                self.feed_total_kmol_h,
                Some(0.0),
                None,
                None,
                None,
            ),
            (
                "feed_h2o_mole_frac",
                self.feed_h2o_mole_frac,
                None,
                Some(0.0),
                Some(0.2),
                None,
            ),
            (
                "reactor_temperature_C",
                self.reactor_temperature_c,
                None,
                Some(250.0),
                None,
                Some(1000.0),
            ),
            (
                "reactor_pressure_bar",
                self.reactor_pressure_bar,
                None,
                Some(1.0),
                None,
                Some(100.0),
            ),
            (
                "fehe_hot_end_approach_K",
                self.fehe_hot_end_approach_k,
                None,
                Some(5.0),
                None,
                Some(300.0),
            ),
            (
                "psa_feed_temperature_C",
                self.psa_feed_temperature_c,
                None,
                Some(5.0),
                None,
                Some(80.0),
            ),
            (
                "psa_h2_recovery",
                self.psa_h2_recovery,
                Some(0.0),
                None,
                None,
                Some(1.0),
            ),
            (
                "psa_n2_slip",
                self.psa_n2_slip,
                None,
                Some(0.0),
                None,
                Some(0.05),
            ),
            (
                "burner_excess_air",
                self.burner_excess_air,
                None,
                Some(0.0),
                None,
                Some(2.0),
            ),
            (
                "stack_temperature_C",
                self.stack_temperature_c,
                None,
                Some(60.0),
                None,
                Some(400.0),
            ),
        ];
        for (name, v, gt, ge, lt, le) in checks {
            let ok = v.is_finite()
                && gt.is_none_or(|b| v > b)
                && ge.is_none_or(|b| v >= b)
                && lt.is_none_or(|b| v < b)
                && le.is_none_or(|b| v <= b);
            if !ok {
                return Err(bad(format!(
                    "CaseInputs.{name} = {v} outside its allowed range"
                )));
            }
        }
        if !PROPERTY_METHODS.contains(&self.property_method.trim().to_uppercase().as_str()) {
            return Err(bad(format!(
                "property_method {:?} not in {PROPERTY_METHODS:?}",
                self.property_method
            )));
        }
        Ok(())
    }

    /// JSON (`CaseInputs.model_dump()`).
    pub fn to_json(&self) -> Value {
        json!({
            "case_id": self.case_id,
            "feed_total_kmol_h": self.feed_total_kmol_h,
            "feed_h2o_mole_frac": self.feed_h2o_mole_frac,
            "reactor_temperature_C": self.reactor_temperature_c,
            "reactor_pressure_bar": self.reactor_pressure_bar,
            "heat_integration": self.heat_integration,
            "fehe_hot_end_approach_K": self.fehe_hot_end_approach_k,
            "psa_feed_temperature_C": self.psa_feed_temperature_c,
            "psa_h2_recovery": self.psa_h2_recovery,
            "psa_n2_slip": self.psa_n2_slip,
            "burner_excess_air": self.burner_excess_air,
            "stack_temperature_C": self.stack_temperature_c,
            "property_method": self.property_method,
        })
    }
}

/// A block detail value (`float | str | None`).
#[derive(Debug, Clone, PartialEq)]
pub enum Detail {
    Num(f64),
    Str(String),
    Null,
}

/// One stream (Python `StreamResult`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct StreamResult {
    pub id: String,
    pub name: String,
    pub source_block: Option<String>,
    pub dest_block: Option<String>,
    pub phase: Option<String>,
    pub temperature_c: Option<f64>,
    pub pressure_bar: Option<f64>,
    pub vapor_fraction: Option<f64>,
    pub mole_flow_kmol_h: Option<f64>,
    pub mass_flow_kg_h: Option<f64>,
    pub enthalpy_flow_kw: Option<f64>,
    pub mole_frac: Vec<(String, f64)>,
    pub mass_frac: Vec<(String, f64)>,
    pub component_mole_flow_kmol_h: Vec<(String, f64)>,
}

/// `dict.get(key, default)` of an ordered map.
pub fn get_or(m: &[(String, f64)], key: &str, default: f64) -> f64 {
    m.iter()
        .find(|x| x.0 == key)
        .map(|x| x.1)
        .unwrap_or(default)
}

/// `dict.get(key)` of an ordered map.
pub fn get_opt(m: &[(String, f64)], key: &str) -> Option<f64> {
    m.iter().find(|x| x.0 == key).map(|x| x.1)
}

/// One block (Python `BlockResult`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct BlockResult {
    pub id: String,
    pub name: String,
    pub block_type: String,
    pub duty_kw: Option<f64>,
    pub power_kw: Option<f64>,
    pub outlet_temperature_c: Option<f64>,
    pub outlet_pressure_bar: Option<f64>,
    pub details: Vec<(String, Detail)>,
}

/// Run status (Python `RunStatus`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct RunStatus {
    pub converged: bool,
    pub has_errors: bool,
    pub has_warnings: bool,
    pub messages: Vec<String>,
    pub engine_time_s: Option<f64>,
}

/// KPI names in the field order of Python `KPIs`.
pub const KPI_NAMES: [&str; 17] = [
    "nh3_conversion",
    "h2_in_cracked_gas_kmol_h",
    "h2_product_kmol_h",
    "h2_product_kg_h",
    "h2_purity_mole_frac",
    "h2_yield_overall",
    "reactor_duty_kW",
    "preheat_duty_kW",
    "vaporiser_duty_kW",
    "recovered_heat_kW",
    "total_external_heating_kW",
    "cooling_duty_kW",
    "pump_power_kW",
    "tailgas_combustion_heat_kW",
    "tailgas_lhv_kW",
    "specific_heat_demand_kWh_per_kgH2",
    "net_fuel_heat_deficit_kW",
];

/// KPIs (Python `KPIs`; `lhv_efficiency` is the 18th field).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Kpis {
    pub nh3_conversion: Option<f64>,
    pub h2_in_cracked_gas_kmol_h: Option<f64>,
    pub h2_product_kmol_h: Option<f64>,
    pub h2_product_kg_h: Option<f64>,
    pub h2_purity_mole_frac: Option<f64>,
    pub h2_yield_overall: Option<f64>,
    pub reactor_duty_kw: Option<f64>,
    pub preheat_duty_kw: Option<f64>,
    pub vaporiser_duty_kw: Option<f64>,
    pub recovered_heat_kw: Option<f64>,
    pub total_external_heating_kw: Option<f64>,
    pub cooling_duty_kw: Option<f64>,
    pub pump_power_kw: Option<f64>,
    pub tailgas_combustion_heat_kw: Option<f64>,
    pub tailgas_lhv_kw: Option<f64>,
    pub specific_heat_demand_kwh_per_kgh2: Option<f64>,
    pub net_fuel_heat_deficit_kw: Option<f64>,
    pub lhv_efficiency: Option<f64>,
}

impl Kpis {
    fn fields(&self) -> [(&'static str, Option<f64>); 18] {
        [
            ("nh3_conversion", self.nh3_conversion),
            ("h2_in_cracked_gas_kmol_h", self.h2_in_cracked_gas_kmol_h),
            ("h2_product_kmol_h", self.h2_product_kmol_h),
            ("h2_product_kg_h", self.h2_product_kg_h),
            ("h2_purity_mole_frac", self.h2_purity_mole_frac),
            ("h2_yield_overall", self.h2_yield_overall),
            ("reactor_duty_kW", self.reactor_duty_kw),
            ("preheat_duty_kW", self.preheat_duty_kw),
            ("vaporiser_duty_kW", self.vaporiser_duty_kw),
            ("recovered_heat_kW", self.recovered_heat_kw),
            ("total_external_heating_kW", self.total_external_heating_kw),
            ("cooling_duty_kW", self.cooling_duty_kw),
            ("pump_power_kW", self.pump_power_kw),
            (
                "tailgas_combustion_heat_kW",
                self.tailgas_combustion_heat_kw,
            ),
            ("tailgas_lhv_kW", self.tailgas_lhv_kw),
            (
                "specific_heat_demand_kWh_per_kgH2",
                self.specific_heat_demand_kwh_per_kgh2,
            ),
            ("net_fuel_heat_deficit_kW", self.net_fuel_heat_deficit_kw),
            ("lhv_efficiency", self.lhv_efficiency),
        ]
    }

    fn from_ov(v: &OValue) -> Kpis {
        let g = |k: &str| v.get(k).as_f64();
        Kpis {
            nh3_conversion: g("nh3_conversion"),
            h2_in_cracked_gas_kmol_h: g("h2_in_cracked_gas_kmol_h"),
            h2_product_kmol_h: g("h2_product_kmol_h"),
            h2_product_kg_h: g("h2_product_kg_h"),
            h2_purity_mole_frac: g("h2_purity_mole_frac"),
            h2_yield_overall: g("h2_yield_overall"),
            reactor_duty_kw: g("reactor_duty_kW"),
            preheat_duty_kw: g("preheat_duty_kW"),
            vaporiser_duty_kw: g("vaporiser_duty_kW"),
            recovered_heat_kw: g("recovered_heat_kW"),
            total_external_heating_kw: g("total_external_heating_kW"),
            cooling_duty_kw: g("cooling_duty_kW"),
            pump_power_kw: g("pump_power_kW"),
            tailgas_combustion_heat_kw: g("tailgas_combustion_heat_kW"),
            tailgas_lhv_kw: g("tailgas_lhv_kW"),
            specific_heat_demand_kwh_per_kgh2: g("specific_heat_demand_kWh_per_kgH2"),
            net_fuel_heat_deficit_kw: g("net_fuel_heat_deficit_kW"),
            lhv_efficiency: g("lhv_efficiency"),
        }
    }

    /// JSON (`KPIs.model_dump()`).
    pub fn to_json(&self) -> Value {
        Value::Object(
            self.fields()
                .iter()
                .map(|(k, v)| (k.to_string(), jo(*v)))
                .collect(),
        )
    }
}

/// Overall balances (Python `Balances`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Balances {
    pub mass_in_kg_h: Option<f64>,
    pub mass_out_kg_h: Option<f64>,
    pub mass_closure_rel: Option<f64>,
    pub n_atoms_in_kmol_h: Option<f64>,
    pub n_atoms_out_kmol_h: Option<f64>,
    pub h_atoms_in_kmol_h: Option<f64>,
    pub h_atoms_out_kmol_h: Option<f64>,
    pub energy_in_kw: Option<f64>,
    pub energy_out_kw: Option<f64>,
    pub energy_closure_rel: Option<f64>,
}

impl Balances {
    /// JSON (`Balances.model_dump()`).
    pub fn to_json(&self) -> Value {
        json!({
            "mass_in_kg_h": jo(self.mass_in_kg_h),
            "mass_out_kg_h": jo(self.mass_out_kg_h),
            "mass_closure_rel": jo(self.mass_closure_rel),
            "n_atoms_in_kmol_h": jo(self.n_atoms_in_kmol_h),
            "n_atoms_out_kmol_h": jo(self.n_atoms_out_kmol_h),
            "h_atoms_in_kmol_h": jo(self.h_atoms_in_kmol_h),
            "h_atoms_out_kmol_h": jo(self.h_atoms_out_kmol_h),
            "energy_in_kW": jo(self.energy_in_kw),
            "energy_out_kW": jo(self.energy_out_kw),
            "energy_closure_rel": jo(self.energy_closure_rel),
        })
    }
}

/// A complete result (Python `SimulationResult`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct SimulationResult {
    pub schema_version: String,
    pub case_id: String,
    pub source: String,
    pub model_file: Option<String>,
    pub inputs: CaseInputs,
    pub status: RunStatus,
    pub streams: Vec<(String, StreamResult)>,
    pub blocks: Vec<(String, BlockResult)>,
    pub kpis: Kpis,
    pub balances: Balances,
    pub notes: Vec<String>,
}

impl SimulationResult {
    /// Stream `id`.
    pub fn stream(&self, id: &str) -> Option<&StreamResult> {
        self.streams.iter().find(|x| x.0 == id).map(|x| &x.1)
    }
    /// Block `id`.
    pub fn block(&self, id: &str) -> Option<&BlockResult> {
        self.blocks.iter().find(|x| x.0 == id).map(|x| &x.1)
    }

    /// Parse a stored or golden result (`SimulationResult.model_validate`). Mappings keep the
    /// order of `v`.
    pub fn from_ov(v: &OValue) -> Result<SimulationResult, EngineError> {
        let s = |x: &OValue| x.as_str().map(str::to_string);
        let fmap = |x: &OValue| -> Vec<(String, f64)> {
            x.entries()
                .iter()
                .filter_map(|(k, val)| val.as_f64().map(|f| (k.clone(), f)))
                .collect()
        };
        let mut streams = Vec::new();
        for (k, st) in v.get("streams").entries() {
            streams.push((
                k.clone(),
                StreamResult {
                    id: s(st.get("id")).unwrap_or_else(|| k.clone()),
                    name: s(st.get("name")).unwrap_or_default(),
                    source_block: s(st.get("source_block")),
                    dest_block: s(st.get("dest_block")),
                    phase: s(st.get("phase")),
                    temperature_c: st.get("temperature_C").as_f64(),
                    pressure_bar: st.get("pressure_bar").as_f64(),
                    vapor_fraction: st.get("vapor_fraction").as_f64(),
                    mole_flow_kmol_h: st.get("mole_flow_kmol_h").as_f64(),
                    mass_flow_kg_h: st.get("mass_flow_kg_h").as_f64(),
                    enthalpy_flow_kw: st.get("enthalpy_flow_kW").as_f64(),
                    mole_frac: fmap(st.get("mole_frac")),
                    mass_frac: fmap(st.get("mass_frac")),
                    component_mole_flow_kmol_h: fmap(st.get("component_mole_flow_kmol_h")),
                },
            ));
        }
        let mut blocks = Vec::new();
        for (k, b) in v.get("blocks").entries() {
            let details = b
                .get("details")
                .entries()
                .iter()
                .map(|(dk, dv)| {
                    let d = match dv {
                        OValue::Str(t) => Detail::Str(t.clone()),
                        OValue::Null => Detail::Null,
                        other => other.as_f64().map(Detail::Num).unwrap_or(Detail::Null),
                    };
                    (dk.clone(), d)
                })
                .collect();
            blocks.push((
                k.clone(),
                BlockResult {
                    id: s(b.get("id")).unwrap_or_else(|| k.clone()),
                    name: s(b.get("name")).unwrap_or_default(),
                    block_type: s(b.get("block_type")).unwrap_or_default(),
                    duty_kw: b.get("duty_kW").as_f64(),
                    power_kw: b.get("power_kW").as_f64(),
                    outlet_temperature_c: b.get("outlet_temperature_C").as_f64(),
                    outlet_pressure_bar: b.get("outlet_pressure_bar").as_f64(),
                    details,
                },
            ));
        }
        let st = v.get("status");
        let inputs = CaseInputs::from_value(&v.get("inputs").to_json())?;
        Ok(SimulationResult {
            schema_version: s(v.get("schema_version")).unwrap_or_else(|| SCHEMA_VERSION.into()),
            case_id: s(v.get("case_id"))
                .ok_or_else(|| EngineError::data("SimulationResult", "case_id missing"))?,
            source: s(v.get("source")).unwrap_or_else(|| "python_model".into()),
            model_file: s(v.get("model_file")),
            inputs,
            status: RunStatus {
                converged: st.get("converged").as_bool().unwrap_or(false),
                has_errors: st.get("has_errors").as_bool().unwrap_or(false),
                has_warnings: st.get("has_warnings").as_bool().unwrap_or(false),
                messages: st
                    .get("messages")
                    .items()
                    .iter()
                    .filter_map(|m| m.as_str().map(str::to_string))
                    .collect(),
                engine_time_s: st.get("engine_time_s").as_f64(),
            },
            streams,
            blocks,
            kpis: Kpis::from_ov(v.get("kpis")),
            balances: {
                let b = v.get("balances");
                let g = |k: &str| b.get(k).as_f64();
                Balances {
                    mass_in_kg_h: g("mass_in_kg_h"),
                    mass_out_kg_h: g("mass_out_kg_h"),
                    mass_closure_rel: g("mass_closure_rel"),
                    n_atoms_in_kmol_h: g("n_atoms_in_kmol_h"),
                    n_atoms_out_kmol_h: g("n_atoms_out_kmol_h"),
                    h_atoms_in_kmol_h: g("h_atoms_in_kmol_h"),
                    h_atoms_out_kmol_h: g("h_atoms_out_kmol_h"),
                    energy_in_kw: g("energy_in_kW"),
                    energy_out_kw: g("energy_out_kW"),
                    energy_closure_rel: g("energy_closure_rel"),
                }
            },
            notes: v
                .get("notes")
                .items()
                .iter()
                .filter_map(|m| m.as_str().map(str::to_string))
                .collect(),
        })
    }

    /// Parse JSON text (mappings in document order).
    pub fn from_json_text(text: &str) -> Result<SimulationResult, EngineError> {
        let ov: OValue = serde_json::from_str(text)
            .map_err(|e| EngineError::data("SimulationResult", e.to_string()))?;
        SimulationResult::from_ov(&ov)
    }

    /// Parse a `serde_json::Value` whose mappings were sorted by key (golden tables): species
    /// mappings are put back into `COMPONENTS` order, which is the insertion order of the
    /// Python flowsheet's streams.
    pub fn from_sorted_value(v: &Value) -> Result<SimulationResult, EngineError> {
        SimulationResult::from_ov(&ov_components_order(v))
    }

    /// JSON (`SimulationResult.model_dump()`; NaN as null).
    pub fn to_json(&self) -> Value {
        let fm = |m: &[(String, f64)]| -> Value {
            Value::Object(m.iter().map(|(k, v)| (k.clone(), jf(*v))).collect())
        };
        let mut streams = Map::new();
        for (k, s) in &self.streams {
            streams.insert(
                k.clone(),
                json!({
                    "id": s.id, "name": s.name, "source_block": s.source_block, "dest_block": s.dest_block,
                    "phase": s.phase, "temperature_C": jo(s.temperature_c), "pressure_bar": jo(s.pressure_bar),
                    "vapor_fraction": jo(s.vapor_fraction), "mole_flow_kmol_h": jo(s.mole_flow_kmol_h),
                    "mass_flow_kg_h": jo(s.mass_flow_kg_h), "enthalpy_flow_kW": jo(s.enthalpy_flow_kw),
                    "mole_frac": fm(&s.mole_frac), "mass_frac": fm(&s.mass_frac),
                    "component_mole_flow_kmol_h": fm(&s.component_mole_flow_kmol_h),
                }),
            );
        }
        let mut blocks = Map::new();
        for (k, b) in &self.blocks {
            let det: Map<String, Value> = b
                .details
                .iter()
                .map(|(dk, d)| {
                    let v = match d {
                        Detail::Num(x) => jf(*x),
                        Detail::Str(t) => Value::String(t.clone()),
                        Detail::Null => Value::Null,
                    };
                    (dk.clone(), v)
                })
                .collect();
            blocks.insert(
                k.clone(),
                json!({
                    "id": b.id, "name": b.name, "block_type": b.block_type, "duty_kW": jo(b.duty_kw),
                    "power_kW": jo(b.power_kw), "outlet_temperature_C": jo(b.outlet_temperature_c),
                    "outlet_pressure_bar": jo(b.outlet_pressure_bar), "details": Value::Object(det),
                }),
            );
        }
        json!({
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "source": self.source,
            "model_file": self.model_file,
            "inputs": self.inputs.to_json(),
            "status": {
                "converged": self.status.converged, "has_errors": self.status.has_errors,
                "has_warnings": self.status.has_warnings, "messages": self.status.messages,
                "engine_time_s": jo(self.status.engine_time_s),
            },
            "streams": Value::Object(streams),
            "blocks": Value::Object(blocks),
            "kpis": self.kpis.to_json(),
            "balances": self.balances.to_json(),
            "notes": self.notes,
        })
    }
}

/// A float as JSON (non-finite as null).
pub fn jf(x: f64) -> Value {
    serde_json::Number::from_f64(x)
        .map(Value::Number)
        .unwrap_or(Value::Null)
}

/// An optional float as JSON.
pub fn jo(x: Option<f64>) -> Value {
    x.map(jf).unwrap_or(Value::Null)
}

/// Convert a key-sorted `Value` into an [`OValue`], putting mappings whose keys are all species
/// names into `COMPONENTS` order.
pub fn ov_components_order(v: &Value) -> OValue {
    match v {
        Value::Null => OValue::Null,
        Value::Bool(b) => OValue::Bool(*b),
        Value::Number(n) => {
            if n.is_i64() {
                OValue::Int(n.as_i64().unwrap_or(0))
            } else {
                OValue::Float(n.as_f64().unwrap_or(f64::NAN))
            }
        }
        Value::String(s) => match s.as_str() {
            "nan" => OValue::Float(f64::NAN),
            "inf" => OValue::Float(f64::INFINITY),
            "-inf" => OValue::Float(f64::NEG_INFINITY),
            _ => OValue::Str(s.clone()),
        },
        Value::Array(a) => OValue::Seq(a.iter().map(ov_components_order).collect()),
        Value::Object(m) => {
            let mut entries: Vec<(String, OValue)> = m
                .iter()
                .map(|(k, x)| (k.clone(), ov_components_order(x)))
                .collect();
            if !entries.is_empty() && entries.iter().all(|(k, _)| Species::from_name(k).is_some()) {
                entries
                    .sort_by_key(|(k, _)| Species::from_name(k).map(Species::index).unwrap_or(99));
            }
            OValue::Map(entries)
        }
    }
}
