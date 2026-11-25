//! Scenario-based life-cycle greenhouse-gas factors (Python `environmental/lca.py`): the gate
//! emission factors of the ammonia routes (`route_spec`, `blue_nh3_ef`, `green_nh3_ef`),
//! shipping, delivered factor, direct N2O/NO of NH3 combustion, the CCGT comparator and the SMR
//! hydrogen intensities. Stage 3 (what carbon pricing needs, and the rest of the module, which is
//! small). Gate: 1e-12 relative (`amcrax verify carbon`).
//!
//! The factors are constants of the Python module (not a data file); they are written here with
//! the same literal expressions (`0.05 / 1.49`, `32.52e3 / 47.1 / 1000.0`, ...) so that they are
//! the same doubles.

use crate::error::EngineError;
use serde_json::{Value, json};

/// Lee et al. (2022) conventional NG-based NH3, well-to-plant-gate, kg CO2e/kg NH3.
pub const NG_BASED_NH3_WTG: f64 = 2.60;
/// Process CO2 of NH3 production, kg CO2/kg NH3.
pub const NH3_PROCESS_CO2: f64 = 1.49;
/// Boiler flue-gas CO2 of NH3 production, kg CO2/kg NH3.
pub const NH3_COMBUSTION_CO2: f64 = 0.45;
/// Capture penalty of the process stream (derived from Lee's totals).
pub const CAPTURE_PENALTY_PROCESS: f64 = 0.05 / 1.49;
/// Capture penalty of the combustion stream (derived from Lee's totals).
pub const CAPTURE_PENALTY_COMBUSTION: f64 = (0.11 - 0.05) / 0.45;
/// kg natural gas per kg NH3.
pub const NG_PER_NH3: f64 = 32.52e3 / 47.1 / 1000.0;
/// Lee version 2 blue NH3, kg CO2e/kg NH3.
pub const BLUE_NH3_LEE_V2: f64 = 0.77;
/// Green NH3, Lee boundary.
pub const GREEN_NH3_LEE: f64 = 0.0;
/// IEA embedded emissions of renewable assets, kg CO2e/kg H2 (low, high).
pub const EMBEDDED_RENEWABLE_H2: (f64, f64) = (0.4, 2.7);
/// Grey NH3 range, kg CO2e/kg NH3.
pub const GREY_NH3_RANGE: (f64, f64) = (2.0, 4.6);
/// Coal-based NH3 range, kg CO2e/kg NH3.
pub const COAL_NH3: (f64, f64) = (2.18, 3.88);
/// GWP-100 of fossil CH4 (AR6).
pub const GWP100_CH4_FOSSIL: f64 = 29.8;
/// GWP-100 of N2O (AR6; the Singapore tax uses 265).
pub const GWP100_N2O: f64 = 273.0;
/// Ship emission factor, kg CO2e/(t km).
pub const SHIP_EF: f64 = 0.011;
/// Boil-off fraction (none sourced; default 0).
pub const BOIL_OFF_FRACTION: f64 = 0.0;
/// Natural-gas combustion CO2, kg CO2/TJ.
pub const NG_CO2_EF: f64 = 56100.0;
/// Natural-gas LHV, MJ/kg.
pub const NG_LHV: f64 = 47.1;
/// CCGT efficiency (assumption).
pub const CCGT_EFFICIENCY: f64 = 0.55;
/// SMR hydrogen, unabated, kg CO2e/kg H2.
pub const SMR_H2_UNABATED: (f64, f64) = (10.0, 12.0);
/// SMR hydrogen with CCS, kg CO2e/kg H2.
pub const SMR_H2_CCS: (f64, f64) = (3.4, 3.6);
/// Ahmad (2025) exhaust flow per MWh net, t/MWh.
pub const AHMAD_GAS_FLOW_PER_MWH: f64 = 150.52 / 43.1;
/// Ahmad (2025) N2O, ppmv (simulated).
pub const AHMAD_N2O_PPMV: f64 = 0.15;
/// Ahmad (2025) NO, ppmv (simulated).
pub const AHMAD_NO_PPMV: f64 = 107.0;
/// Flue-gas molar mass, g/mol.
pub const FLUE_GAS_MOLAR_MASS: f64 = 28.8;
/// Stoichiometric hydrogen content of NH3 (`3 * 1.008 / 17.031`).
pub const KG_H2_PER_KG_NH3: f64 = 3.0 * 1.008 / 17.031;

/// Routes of `route_spec` (`ROUTES` plus `green_lee`).
pub const ROUTES: [&str; 7] = [
    "green",
    "green_lee",
    "blue",
    "blue_v2",
    "blue_param",
    "grey",
    "coal",
];

/// Python `blue_nh3_ef(capture_process, capture_combustion, leak_frac, gwp_ch4)`.
pub fn blue_nh3_ef(
    capture_process: f64,
    capture_combustion: f64,
    leak_frac: f64,
    gwp_ch4: Option<f64>,
) -> Result<f64, EngineError> {
    if !((0.0..=1.0).contains(&capture_process)
        && (0.0..=1.0).contains(&capture_combustion)
        && leak_frac >= 0.0)
    {
        return Err(EngineError::Domain(
            "ValueError: capture fractions must be in [0, 1] and leak_frac >= 0".into(),
        ));
    }
    let g = gwp_ch4.unwrap_or(GWP100_CH4_FOSSIL);
    let cp = capture_process * NH3_PROCESS_CO2;
    let cc = capture_combustion * NH3_COMBUSTION_CO2;
    Ok(NG_BASED_NH3_WTG - cp - cc
        + cp * CAPTURE_PENALTY_PROCESS
        + cc * CAPTURE_PENALTY_COMBUSTION
        + leak_frac * NG_PER_NH3 * g)
}

/// Python `green_nh3_ef(embedded)` (`"lee"`, `"low"`, `"high"`, `"mid"`).
pub fn green_nh3_ef(embedded: &str) -> Result<f64, EngineError> {
    if embedded == "lee" {
        return Ok(GREEN_NH3_LEE);
    }
    let (lo, hi) = EMBEDDED_RENEWABLE_H2;
    let v = match embedded {
        "low" => lo,
        "high" => hi,
        "mid" => 0.5 * (lo + hi),
        _ => return Err(EngineError::Domain(format!("KeyError: {embedded:?}"))),
    };
    Ok(v * KG_H2_PER_KG_NH3)
}

/// Python `RouteSpec`.
#[derive(Debug, Clone, PartialEq)]
pub struct RouteSpec {
    pub name: String,
    pub ef: f64,
    pub low: f64,
    pub high: f64,
    pub source_type: String,
    pub label: String,
}

impl RouteSpec {
    /// As the dataclass fields.
    pub fn to_json(&self) -> Value {
        json!({"name": self.name, "ef": self.ef, "low": self.low, "high": self.high,
               "source_type": self.source_type, "label": self.label})
    }
}

fn spec(name: &str, ef: f64, low: f64, high: f64, st: &str, label: &str) -> RouteSpec {
    RouteSpec {
        name: name.into(),
        ef,
        low,
        high,
        source_type: st.into(),
        label: label.into(),
    }
}

/// Python `route_spec(route)`: central gate factor and its sourced range.
pub fn route_spec(route: &str) -> Result<RouteSpec, EngineError> {
    let lit = "literature";
    Ok(match route {
        "green" => spec(
            "green",
            green_nh3_ef("mid")?,
            green_nh3_ef("low")?,
            green_nh3_ef("high")?,
            lit,
            "green NH3 (renewable, incl. embedded asset emissions)",
        ),
        "green_lee" => spec(
            "green_lee",
            0.0,
            0.0,
            green_nh3_ef("high")?,
            lit,
            "green NH3 (Lee boundary, zero)",
        ),
        "blue" => spec(
            "blue",
            blue_nh3_ef(1.0, 0.0, 0.0, None)?,
            BLUE_NH3_LEE_V2,
            blue_nh3_ef(0.9, 0.0, 0.03, None)?,
            lit,
            "blue NH3 (Lee v1: process CO2 captured)",
        ),
        "blue_v2" => spec(
            "blue_v2",
            blue_nh3_ef(1.0, 1.0, 0.0, None)?,
            blue_nh3_ef(1.0, 1.0, 0.0, None)?,
            blue_nh3_ef(0.9, 0.9, 0.03, None)?,
            lit,
            "blue NH3 (Lee v2: process + flue-gas CO2 captured)",
        ),
        "blue_param" => spec(
            "blue_param",
            blue_nh3_ef(0.95, 0.0, 0.015, None)?,
            blue_nh3_ef(1.0, 0.0, 0.002, None)?,
            blue_nh3_ef(0.9, 0.0, 0.03, None)?,
            "assumption",
            "blue NH3 (95 % process capture, 1.5 % extra CH4 leakage)",
        ),
        "grey" => spec(
            "grey",
            NG_BASED_NH3_WTG,
            GREY_NH3_RANGE.0,
            GREY_NH3_RANGE.1,
            lit,
            "grey NH3 (NG SMR, no capture)",
        ),
        "coal" => {
            let mid = 0.5 * (COAL_NH3.0 + COAL_NH3.1);
            spec(
                "coal",
                mid,
                COAL_NH3.0,
                COAL_NH3.1,
                "literature (low confidence)",
                "coal-based NH3",
            )
        }
        _ => {
            return Err(EngineError::Domain(format!(
                "ValueError: unknown route {route:?}"
            )));
        }
    })
}

/// Python `ship_kg_per_kg_nh3(distance_km, ef_per_tkm)`.
pub fn ship_kg_per_kg_nh3(distance_km: f64, ef_per_tkm: Option<f64>) -> f64 {
    ef_per_tkm.unwrap_or(SHIP_EF) * distance_km / 1000.0
}

/// Python `delivered_nh3_ef(ef_gate, distance_km, boil_off, ef_per_tkm)`.
pub fn delivered_nh3_ef(
    ef_gate: f64,
    distance_km: f64,
    boil_off: Option<f64>,
    ef_per_tkm: Option<f64>,
) -> Result<f64, EngineError> {
    let bo = boil_off.unwrap_or(BOIL_OFF_FRACTION);
    if !(0.0..1.0).contains(&bo) {
        return Err(EngineError::Domain(
            "ValueError: boil_off must be in [0, 1)".into(),
        ));
    }
    Ok((ef_gate + ship_kg_per_kg_nh3(distance_km, ef_per_tkm)) / (1.0 - bo))
}

/// Python `n2o_noX_per_MWh()`: kg/MWh of N2O, its CO2e (GWP 273) and NO.
pub fn n2o_nox_per_mwh() -> (f64, f64, f64) {
    let flow_kg = AHMAD_GAS_FLOW_PER_MWH * 1000.0;
    let mm = FLUE_GAS_MOLAR_MASS;
    let n2o = AHMAD_N2O_PPMV * 1e-6 * 44.013 / mm * flow_kg;
    let no = AHMAD_NO_PPMV * 1e-6 * 30.006 / mm * flow_kg;
    (n2o, n2o * GWP100_N2O, no)
}

/// Python `ccgt_ci_kg_per_MWh(eff, leak_frac)`.
pub fn ccgt_ci_kg_per_mwh(eff: Option<f64>, leak_frac: f64) -> f64 {
    let e = eff.unwrap_or(CCGT_EFFICIENCY);
    let fuel_gj = 3.6 / e;
    let co2 = fuel_gj / 1000.0 * NG_CO2_EF;
    let ch4 = leak_frac * fuel_gj * 1000.0 / NG_LHV * GWP100_CH4_FOSSIL;
    co2 + ch4
}

/// Python `smr_h2_ci(ccs)`: midpoint of the sourced range.
pub fn smr_h2_ci(ccs: bool) -> f64 {
    let (lo, hi) = if ccs { SMR_H2_CCS } else { SMR_H2_UNABATED };
    0.5 * (lo + hi)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lee_versions_reproduced() {
        assert!((blue_nh3_ef(1.0, 0.0, 0.0, None).unwrap() - 1.16).abs() < 1e-12);
        assert!((blue_nh3_ef(1.0, 1.0, 0.0, None).unwrap() - 0.77).abs() < 1e-12);
        assert!(blue_nh3_ef(1.5, 0.0, 0.0, None).is_err());
        assert!(route_spec("purple").is_err());
        assert_eq!(route_spec("grey").unwrap().ef, 2.6);
    }
}
