//! End-use pathways for imported ammonia in Singapore (port of Python `enduse/pathways.py` and
//! `enduse/params.py`): the stoichiometry of partially cracked fuel, the stored Aspen cracker
//! activities, the hydrogen pathways (functional unit 1 kg usable H2) and power pathways
//! (functional unit 1 MWh net electricity), their carbon intensity, the LCOE of the reference
//! power plant (`power_cost`), the hydrogen cost on the reference scenario (`hydrogen_cost`) and
//! the break-even gate emission factor.
//!
//! Every Python expression is kept in its order of operations so that the results are the same
//! doubles up to the rounding of `pow` in the C library.

use crate::economics::lcoh::crf;
use crate::economics::reference::{EconomicsData, RefCapexArgs};
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate};
use crate::error::EngineError;
use crate::lca;
use crate::process::result::{LHV_KJ_PER_MOL, SimulationResult, molar_mass};
use crate::pyops::{fmt_f, py_max, py_min, py_repr};
use crate::species::Species;
use amcrax_numerics::roots::{BrentOptions, brentq};
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::path::Path;

/// `lca.FACTORS["grid_ef_singapore_2024"]["value"]`, kg CO2/kWh (EMA 2024 average grid factor).
pub const GRID_EF_SINGAPORE_2024: f64 = 0.402;

fn lhv(s: Species) -> f64 {
    LHV_KJ_PER_MOL
        .iter()
        .find(|e| e.0 == s)
        .map(|e| e.1)
        .unwrap_or(f64::NAN)
}

/// `LHV_NH3_MJ_KG` (18.60 on the AmCraX basis).
pub fn lhv_nh3_mj_kg() -> f64 {
    lhv(Species::NH3) / molar_mass(Species::NH3)
}

/// `LHV_H2_MJ_KG` (119.96).
pub fn lhv_h2_mj_kg() -> f64 {
    lhv(Species::H2) / molar_mass(Species::H2)
}

fn verr(msg: &str) -> EngineError {
    EngineError::Domain(format!("ValueError: {msg}"))
}

// ===================================================================================== params
/// Python `enduse.params` (literature-calibrated and assumed scenario inputs).
#[derive(Debug, Clone, PartialEq)]
pub struct Params {
    pub lhv_nh3_mj_kg: f64,
    pub lhv_h2_mj_kg: f64,
    pub ahmad_lhv_nh3: f64,
    pub eta_direct_ahmad: f64,
    pub eta_full_crack_ahmad: f64,
    pub elec_mj_per_kg_direct: f64,
    pub elec_mj_per_kg_full: f64,
    pub eta_gt_gas: f64,
    /// `AHMAD_ALPHA_BYPASS` in dict order.
    pub ahmad_alpha_bypass: Vec<(f64, f64)>,
    pub ahmad_crack_conversion: f64,
    pub ahmad_tci_2a_musd: f64,
    pub ahmad_w_net_2a_mw: f64,
    pub ahmad_oc_fixed_2a_usd_per_kwh: f64,
    pub ahmad_tci_2a_usd_per_kwh: f64,
    pub ahmad_lcoe_2a: f64,
    pub ahmad_nh3_price_usd_t: f64,
    pub ahmad_mass_flow_kg_s: f64,
    pub ahmad_hours_implied: f64,
    pub ahmad_tci_full_crack_musd: f64,
    pub plant_scale_exponent: f64,
    pub cracker_fixed_om_frac_tci: f64,
    pub halim_h2_blend_range_vol: (f64, f64),
    pub ng_combustor_h2_limit_vol: f64,
    pub hours_per_year: f64,
    pub power_plant_hours_per_year: f64,
    pub discount_rate: f64,
    pub plant_life_yr: f64,
    pub fx_sgd_per_usd: f64,
    /// `NH3_PRICE_SET_USD_T` (grey, blue, green_2050, green_2030, green_current).
    pub nh3_price_set_usd_t: Vec<(String, f64)>,
    pub nh3_price_ref_usd_t: f64,
    pub electricity_usd_kwh: f64,
    pub legacy_electricity_usd_kwh: f64,
    pub gwp_n2o_sg_carbon_pricing_act: f64,
}

/// `ReferenceScenario.power_value(key)` (`from_finance` reads the finance field).
pub fn power_value(d: &EconomicsData, key: &str) -> Result<f64, EngineError> {
    let v = d.reference.raw.at(&["power_plant", key, "value"]);
    if v.as_str() == Some("from_finance") {
        return match key {
            "discount_rate" => Ok(d.reference.discount_rate),
            "plant_life_yr" => Ok(d.reference.plant_life_yr),
            "operating_hours_h_per_yr" => Ok(d.reference.operating_hours_h_per_yr),
            _ => Err(EngineError::data(
                "reference_scenario.yaml",
                format!("power_plant.{key}: from_finance"),
            )),
        };
    }
    v.as_f64().ok_or_else(|| {
        EngineError::data(
            "reference_scenario.yaml",
            format!("power_plant.{key}.value"),
        )
    })
}

impl Params {
    /// The module constants of `enduse/params.py` on the reference scenario.
    pub fn new(d: &EconomicsData) -> Result<Params, EngineError> {
        let r = &d.reference;
        let ahmad_lhv = 18.8;
        let eta_direct = 0.4912;
        let eta_full = 0.54;
        let elec_direct = eta_direct * ahmad_lhv;
        let elec_full = eta_full * ahmad_lhv;
        let lhv_nh3 = lhv_nh3_mj_kg();
        let set: Vec<(String, f64)> = ["grey", "blue", "green_2050", "green_2030", "green_current"]
            .iter()
            .map(|k| Ok((k.to_string(), r.nh3_price(k)?)))
            .collect::<Result<_, EngineError>>()?;
        let legacy = r
            .raw
            .at(&[
                "literature_reproduction",
                "legacy_v1",
                "value",
                "electricity_price_USD_per_kWh",
            ])
            .as_f64()
            .ok_or_else(|| EngineError::data("reference_scenario.yaml", "legacy_v1"))?;
        Ok(Params {
            lhv_nh3_mj_kg: lhv_nh3,
            lhv_h2_mj_kg: lhv_h2_mj_kg(),
            ahmad_lhv_nh3: ahmad_lhv,
            eta_direct_ahmad: eta_direct,
            eta_full_crack_ahmad: eta_full,
            elec_mj_per_kg_direct: elec_direct,
            elec_mj_per_kg_full: elec_full,
            eta_gt_gas: elec_direct / lhv_nh3,
            ahmad_alpha_bypass: vec![
                (0.75, 0.8125),
                (0.5, 0.5876),
                (0.4, 0.4845),
                (0.3, 0.3724),
                (0.2, 0.2502),
                (0.1, 0.1165),
                (0.0, 0.0),
            ],
            ahmad_crack_conversion: 0.97,
            ahmad_tci_2a_musd: 181.25,
            ahmad_w_net_2a_mw: 43.1,
            ahmad_oc_fixed_2a_usd_per_kwh: 0.02843,
            ahmad_tci_2a_usd_per_kwh: 0.06433,
            ahmad_lcoe_2a: 0.2798,
            ahmad_nh3_price_usd_t: power_value(d, "ahmad_reproduction_nh3_price_USD_per_t")?,
            ahmad_mass_flow_kg_s: 4.667,
            ahmad_hours_implied: power_value(d, "ahmad_reproduction_hours")?,
            ahmad_tci_full_crack_musd: 230.0,
            plant_scale_exponent: power_value(d, "scale_exponent")?,
            cracker_fixed_om_frac_tci: power_value(d, "cracker_fixed_om_frac_tci")?,
            halim_h2_blend_range_vol: (0.30, 0.60),
            ng_combustor_h2_limit_vol: 0.30,
            hours_per_year: r.operating_hours_h_per_yr,
            power_plant_hours_per_year: power_value(d, "operating_hours_h_per_yr")?,
            discount_rate: power_value(d, "discount_rate")?,
            plant_life_yr: power_value(d, "plant_life_yr")?,
            fx_sgd_per_usd: r.fx_sgd_per_usd,
            nh3_price_ref_usd_t: set[0].1,
            nh3_price_set_usd_t: set,
            electricity_usd_kwh: r.electricity_usd_per_kwh,
            legacy_electricity_usd_kwh: legacy,
            gwp_n2o_sg_carbon_pricing_act: 265.0,
        })
    }

    /// Price of a named entry of `NH3_PRICE_SET_USD_T`.
    pub fn price(&self, k: &str) -> f64 {
        self.nh3_price_set_usd_t
            .iter()
            .find(|e| e.0 == k)
            .map(|e| e.1)
            .unwrap_or(f64::NAN)
    }

    /// The numeric module constants by their Python names (for the golden comparison).
    pub fn named(&self) -> Vec<(&'static str, f64)> {
        vec![
            ("LHV_NH3_MJ_KG", self.lhv_nh3_mj_kg),
            ("LHV_H2_MJ_KG", self.lhv_h2_mj_kg),
            ("AHMAD_LHV_NH3", self.ahmad_lhv_nh3),
            ("ETA_DIRECT_AHMAD", self.eta_direct_ahmad),
            ("ETA_FULL_CRACK_AHMAD", self.eta_full_crack_ahmad),
            ("ELEC_MJ_PER_KG_DIRECT", self.elec_mj_per_kg_direct),
            ("ELEC_MJ_PER_KG_FULL", self.elec_mj_per_kg_full),
            ("ETA_GT_GAS", self.eta_gt_gas),
            ("AHMAD_CRACK_CONVERSION", self.ahmad_crack_conversion),
            ("AHMAD_TCI_2A_MUSD", self.ahmad_tci_2a_musd),
            ("AHMAD_W_NET_2A_MW", self.ahmad_w_net_2a_mw),
            (
                "AHMAD_OC_FIXED_2A_USD_PER_KWH",
                self.ahmad_oc_fixed_2a_usd_per_kwh,
            ),
            ("AHMAD_TCI_2A_USD_PER_KWH", self.ahmad_tci_2a_usd_per_kwh),
            ("AHMAD_LCOE_2A", self.ahmad_lcoe_2a),
            ("AHMAD_NH3_PRICE_USD_T", self.ahmad_nh3_price_usd_t),
            ("AHMAD_MASS_FLOW_KG_S", self.ahmad_mass_flow_kg_s),
            ("AHMAD_HOURS_IMPLIED", self.ahmad_hours_implied),
            ("AHMAD_TCI_FULL_CRACK_MUSD", self.ahmad_tci_full_crack_musd),
            ("PLANT_SCALE_EXPONENT", self.plant_scale_exponent),
            ("CRACKER_FIXED_OM_FRAC_TCI", self.cracker_fixed_om_frac_tci),
            ("NG_COMBUSTOR_H2_LIMIT_VOL", self.ng_combustor_h2_limit_vol),
            ("HOURS_PER_YEAR", self.hours_per_year),
            (
                "POWER_PLANT_HOURS_PER_YEAR",
                self.power_plant_hours_per_year,
            ),
            ("DISCOUNT_RATE", self.discount_rate),
            ("PLANT_LIFE_YR", self.plant_life_yr),
            ("FX_SGD_PER_USD", self.fx_sgd_per_usd),
            ("NH3_PRICE_REF_USD_T", self.nh3_price_ref_usd_t),
            ("ELECTRICITY_USD_KWH", self.electricity_usd_kwh),
            (
                "LEGACY_ELECTRICITY_USD_KWH",
                self.legacy_electricity_usd_kwh,
            ),
            (
                "GWP_N2O_SG_CARBON_PRICING_ACT",
                self.gwp_n2o_sg_carbon_pricing_act,
            ),
        ]
    }
}

// ===================================================================================== stoichiometry
/// `cracked_share_for_h2_fraction(y_h2, conversion)`.
pub fn cracked_share_for_h2_fraction(y_h2: f64, conversion: f64) -> Result<f64, EngineError> {
    if !(0.0 <= y_h2 && y_h2 < 0.75 + 1e-12) {
        return Err(verr(
            "H2 fraction must be in [0, 0.75] for unpurified cracked NH3",
        ));
    }
    let m = y_h2 / (1.5 - y_h2);
    let f = m / conversion;
    if f > 1.0 + 1e-9 {
        return Err(verr("target H2 fraction not reachable at this conversion"));
    }
    Ok(py_min(f, 1.0))
}

/// `h2_fraction_of_blend(f, conversion)`.
pub fn h2_fraction_of_blend(f: f64, conversion: f64) -> f64 {
    let m = f * conversion;
    1.5 * m / (1.0 + m)
}

/// `alpha_of_cracked_share(f, conversion)`: Ahmad's alpha = NH3 / (NH3 + H2).
pub fn alpha_of_cracked_share(f: f64, conversion: f64) -> f64 {
    let m = f * conversion;
    (1.0 - m) / (1.0 - m + 1.5 * m)
}

/// `fuel_lhv_mj_per_kg_nh3_fed(f, conversion)`.
pub fn fuel_lhv_mj_per_kg_nh3_fed(f: f64, conversion: f64) -> f64 {
    let m = f * conversion;
    let per_mol = (1.0 - m) * lhv(Species::NH3) + 1.5 * m * lhv(Species::H2);
    per_mol / molar_mass(Species::NH3)
}

// ===================================================================================== crackers
/// Python `Cracker` (stored Aspen cracker activities).
#[derive(Debug, Clone, PartialEq)]
pub struct Cracker {
    pub case_id: String,
    pub source: String,
    pub conversion: f64,
    pub nh3_kg_h: f64,
    pub h2_cracked_kg_h: f64,
    pub h2_product_kg_h: f64,
    pub purity_mole_frac: f64,
    pub recovery: f64,
    pub cracker_heat_kw: f64,
    pub vaporiser_kw: f64,
    pub deficit_kw: f64,
    pub pump_kw: f64,
}

impl Cracker {
    pub fn crack_heat_mj_per_kg_nh3(&self) -> f64 {
        self.cracker_heat_kw * 3.6 / self.nh3_kg_h
    }
    pub fn deficit_mj_per_kg_nh3(&self) -> f64 {
        self.deficit_kw * 3.6 / self.nh3_kg_h
    }
    pub fn h2_product_per_kg_nh3(&self) -> f64 {
        self.h2_product_kg_h / self.nh3_kg_h
    }
    pub fn pump_kwh_per_kg_nh3(&self) -> f64 {
        self.pump_kw / self.nh3_kg_h
    }

    /// `load_cracker(case)` on a parsed stored result.
    pub fn from_result(case: &str, r: &SimulationResult) -> Result<Cracker, EngineError> {
        let k = &r.kpis;
        let need = |v: Option<f64>, n: &str| {
            v.ok_or_else(|| EngineError::Domain(format!("TypeError: kpis.{n} is None")))
        };
        let nh3_kmol = r
            .stream("FEED")
            .and_then(|s| {
                s.component_mole_flow_kmol_h
                    .iter()
                    .find(|x| x.0 == "NH3")
                    .map(|x| x.1)
            })
            .ok_or_else(|| EngineError::Domain("KeyError: FEED NH3".into()))?;
        Ok(Cracker {
            case_id: case.into(),
            source: r.source.clone(),
            conversion: need(k.nh3_conversion, "nh3_conversion")?,
            nh3_kg_h: nh3_kmol * molar_mass(Species::NH3),
            h2_cracked_kg_h: need(k.h2_in_cracked_gas_kmol_h, "h2_in_cracked_gas_kmol_h")?
                * molar_mass(Species::H2),
            h2_product_kg_h: need(k.h2_product_kg_h, "h2_product_kg_h")?,
            purity_mole_frac: need(k.h2_purity_mole_frac, "h2_purity_mole_frac")?,
            recovery: r.inputs.psa_h2_recovery,
            cracker_heat_kw: need(k.reactor_duty_kw, "reactor_duty_kW")?
                + need(k.preheat_duty_kw, "preheat_duty_kW")?,
            vaporiser_kw: need(k.vaporiser_duty_kw, "vaporiser_duty_kW")?,
            deficit_kw: need(k.net_fuel_heat_deficit_kw, "net_fuel_heat_deficit_kW")?,
            pump_kw: match k.pump_power_kw {
                Some(v) if v != 0.0 => v,
                _ => 0.0,
            },
        })
    }

    pub fn to_json(&self) -> Value {
        json!({"case_id": self.case_id, "source": self.source, "conversion": self.conversion,
               "nh3_kg_h": self.nh3_kg_h, "h2_cracked_kg_h": self.h2_cracked_kg_h,
               "h2_product_kg_h": self.h2_product_kg_h, "purity_mole_frac": self.purity_mole_frac,
               "recovery": self.recovery, "cracker_heat_kW": self.cracker_heat_kw,
               "vaporiser_kW": self.vaporiser_kw, "deficit_kW": self.deficit_kw,
               "pump_kW": self.pump_kw,
               "crack_heat_MJ_per_kg_nh3": self.crack_heat_mj_per_kg_nh3(),
               "deficit_MJ_per_kg_nh3": self.deficit_mj_per_kg_nh3(),
               "h2_product_per_kg_nh3": self.h2_product_per_kg_nh3(),
               "pump_kWh_per_kg_nh3": self.pump_kwh_per_kg_nh3()})
    }
}

/// A stored simulation result: the typed result and the raw JSON (for `singapore.evaluate`).
#[derive(Debug, Clone)]
pub struct Stored {
    pub result: SimulationResult,
    pub raw: Value,
}

/// The stored results and data the end-use calculations read (Python `load_result` and the
/// files opened by the pathway functions), loaded once from the repository.
pub struct Ctx<'a> {
    pub d: &'a EconomicsData,
    pub p: Params,
    pub cases: BTreeMap<String, Result<Stored, String>>,
    pub purification: Value,
}

/// The stored cases the end-use studies read.
pub const CASES: [&str; 5] = [
    "baseline",
    "baseline_no_hi",
    "scn_fuel_cell_grade",
    "scn_low_temperature",
    "scn_high_temperature",
];

fn read_json(root: &Path, rel: &str) -> Result<Value, EngineError> {
    let t = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    serde_json::from_str(&t).map_err(|e| EngineError::data(rel, e.to_string()))
}

impl<'a> Ctx<'a> {
    /// Load the stored cases and the purification study from the repository.
    pub fn new(d: &'a EconomicsData, root: &Path) -> Result<Ctx<'a>, EngineError> {
        let mut cases = BTreeMap::new();
        for c in CASES {
            let rel = format!("results/simulations/{c}.json");
            let r = std::fs::read_to_string(root.join(&rel))
                .map_err(|e| format!("[Errno 2] No such file or directory: {rel} ({e})"))
                .and_then(|t| {
                    let raw: Value = serde_json::from_str(&t).map_err(|e| e.to_string())?;
                    let result = SimulationResult::from_json_text(&t).map_err(|e| e.to_string())?;
                    Ok(Stored { result, raw })
                });
            cases.insert(c.to_string(), r);
        }
        Ok(Ctx {
            d,
            p: Params::new(d)?,
            cases,
            purification: read_json(
                root,
                "results/research/purification/purification_study.json",
            )?,
        })
    }

    /// `load_result(case)`.
    pub fn stored(&self, case: &str) -> Result<&Stored, EngineError> {
        match self.cases.get(case) {
            Some(Ok(s)) => Ok(s),
            Some(Err(e)) => Err(EngineError::Domain(format!("FileNotFoundError: {e}"))),
            None => Err(EngineError::Domain(format!(
                "FileNotFoundError: results/simulations/{case}.json not loaded"
            ))),
        }
    }

    /// `load_cracker(case)`.
    pub fn cracker(&self, case: &str) -> Result<Cracker, EngineError> {
        Cracker::from_result(case, &self.stored(case)?.result)
    }
}

// ===================================================================================== activities
/// Python `Activity` (per functional unit; `nh3_kg` includes NH3 burnt for heat).
#[derive(Debug, Clone, PartialEq)]
pub struct Activity {
    pub id: String,
    pub label: String,
    pub product: String,
    pub functional_unit: String,
    pub nh3_kg: f64,
    pub aux_kwh: f64,
    pub efficiency: f64,
    pub n2o_kgco2e: f64,
    pub no_kg: Option<f64>,
    pub cracker_h2_kg_h: f64,
    pub capex_kind: String,
    pub h2_fraction_vol: Option<f64>,
    pub cracked_share: Option<f64>,
    pub purity_note: String,
    pub heat_mode: String,
    pub cracker_nh3_kg_h: f64,
}

impl Activity {
    /// `Activity(id, label, product, functional_unit, nh3_kg, aux_kWh, efficiency)` with the
    /// dataclass defaults for the other fields.
    pub fn new(
        id: &str,
        label: &str,
        product: &str,
        fu: &str,
        nh3_kg: f64,
        aux_kwh: f64,
        efficiency: f64,
    ) -> Activity {
        Activity {
            id: id.into(),
            label: label.into(),
            product: product.into(),
            functional_unit: fu.into(),
            nh3_kg,
            aux_kwh,
            efficiency,
            n2o_kgco2e: 0.0,
            no_kg: None,
            cracker_h2_kg_h: 0.0,
            capex_kind: "none".into(),
            h2_fraction_vol: None,
            cracked_share: None,
            purity_note: String::new(),
            heat_mode: String::new(),
            cracker_nh3_kg_h: 0.0,
        }
    }

    /// The dataclass fields by their Python names.
    pub fn to_json(&self) -> Value {
        json!({"id": self.id, "label": self.label, "product": self.product,
               "functional_unit": self.functional_unit, "nh3_kg": self.nh3_kg,
               "aux_kWh": self.aux_kwh, "efficiency": self.efficiency,
               "n2o_kgCO2e": self.n2o_kgco2e, "no_kg": self.no_kg,
               "cracker_h2_kg_h": self.cracker_h2_kg_h, "capex_kind": self.capex_kind,
               "h2_fraction_vol": self.h2_fraction_vol, "cracked_share": self.cracked_share,
               "purity_note": self.purity_note, "heat_mode": self.heat_mode,
               "cracker_nh3_kg_h": self.cracker_nh3_kg_h})
    }
}

/// `carbon_intensity(a, route_ef, distance_km, grid, boil_off, ship_ef)`: kg CO2e per
/// functional unit as (upstream_ammonia, shipping, electricity, direct_n2o, total).
pub fn carbon_intensity(
    a: &Activity,
    route_ef: f64,
    distance_km: f64,
    grid: Option<f64>,
    boil_off: Option<f64>,
    ship_ef: Option<f64>,
) -> [f64; 5] {
    let g = grid.unwrap_or(GRID_EF_SINGAPORE_2024);
    let ship = lca::ship_kg_per_kg_nh3(distance_km, ship_ef);
    let bo = boil_off.unwrap_or(lca::BOIL_OFF_FRACTION);
    let up = a.nh3_kg * route_ef / (1.0 - bo);
    let tr = a.nh3_kg * ship / (1.0 - bo);
    let el = a.aux_kwh * g;
    let tot = up + tr + el + a.n2o_kgco2e;
    [up, tr, el, a.n2o_kgco2e, tot]
}

/// The dict of [`carbon_intensity`].
pub fn ci_json(b: &[f64; 5]) -> Value {
    json!({"upstream_ammonia": b[0], "shipping": b[1], "electricity": b[2], "direct_n2o": b[3],
           "total": b[4]})
}

/// `breakeven_ef(a, alt_ci, distance_km, grid)`: gate factor at which the pathway equals the
/// alternative's intensity.
pub fn breakeven_ef(a: &Activity, alt_ci: f64, distance_km: f64, grid: Option<f64>) -> f64 {
    let zero = carbon_intensity(a, 0.0, distance_km, grid, None, None)[4];
    (alt_ci - zero) / a.nh3_kg
}

/// `hydrogen_activity(case, id, label, purity_note)`.
pub fn hydrogen_activity(
    ctx: &Ctx,
    case: &str,
    id: &str,
    label: &str,
    purity_note: &str,
) -> Result<Activity, EngineError> {
    let p = &ctx.p;
    let c = ctx.cracker(case)?;
    let heat_nh3 = c.deficit_mj_per_kg_nh3() / p.lhv_nh3_mj_kg;
    let per_h2 = 1.0 / c.h2_product_per_kg_nh3();
    let nh3 = per_h2 * (1.0 + heat_nh3);
    let eff = p.lhv_h2_mj_kg / (nh3 * p.lhv_nh3_mj_kg);
    let mut a = Activity::new(
        id,
        label,
        "H2",
        "1 kg H2 at stated purity",
        nh3,
        c.pump_kwh_per_kg_nh3() * per_h2,
        eff,
    );
    a.cracker_h2_kg_h = c.h2_product_kg_h;
    a.capex_kind = "purified".into();
    a.purity_note = purity_note.into();
    a.heat_mode = "tail gas + extra NH3 (stored Aspen heat deficit)".into();
    a.cracker_nh3_kg_h = c.nh3_kg_h;
    Ok(a)
}

/// `hydrogen_activity_purification(config_id, grade_key, id, label)`: the activity and the
/// purification study's cost record.
pub fn hydrogen_activity_purification(
    ctx: &Ctx,
    config_id: &str,
    grade_key: &str,
    id: &str,
    label: &str,
) -> Result<(Activity, Value), EngineError> {
    let p = &ctx.p;
    let case = &ctx.purification["cases"]["20bar_baseline"];
    let cfg = case["configs"]
        .as_array()
        .and_then(|v| v.iter().find(|c| c["id"].as_str() == Some(config_id)))
        .ok_or_else(|| EngineError::Domain(format!("KeyError: '{config_id}'")))?;
    let n = |v: &Value, k: &str| -> Result<f64, EngineError> {
        v[k].as_f64()
            .ok_or_else(|| EngineError::Domain(format!("KeyError: '{k}'")))
    };
    let c0 = ctx.cracker("baseline")?;
    let h2_kg_h = n(cfg, "product_h2_kg_h")?;
    let heat_kw = n(cfg, "net_heat_deficit_kW")?;
    let nh3 = c0.nh3_kg_h / h2_kg_h + heat_kw * 3.6 / p.lhv_nh3_mj_kg / h2_kg_h;
    let cost = cfg["costs"][grade_key].clone();
    if cost.is_null() {
        return Err(EngineError::Domain(format!("KeyError: '{grade_key}'")));
    }
    let el =
        c0.pump_kwh_per_kg_nh3() * c0.nh3_kg_h / h2_kg_h + n(&cost, "compression_kWh_per_kg_h2")?;
    let mut a = Activity::new(
        id,
        label,
        "H2",
        "1 kg H2 at stated purity",
        nh3,
        el,
        p.lhv_h2_mj_kg / (nh3 * p.lhv_nh3_mj_kg),
    );
    a.cracker_h2_kg_h = h2_kg_h;
    a.capex_kind = "purified".into();
    a.purity_note = format!(
        "{} mol% H2, recovery {}",
        fmt_f(n(cfg, "product_purity_h2_mole_frac")? * 100.0, 3),
        fmt_f(n(cfg, "h2_recovery")?, 3)
    );
    a.heat_mode = "tail gas + extra NH3".into();
    a.cracker_nh3_kg_h = c0.nh3_kg_h;
    Ok((a, cost))
}

/// Result of [`hydrogen_cost`].
#[derive(Debug, Clone, PartialEq)]
pub struct HydrogenCost {
    pub usd_per_kg: f64,
    pub breakdown: Value,
    pub sgd_per_kg: f64,
    pub capex_total_usd: f64,
}

impl HydrogenCost {
    pub fn to_json(&self) -> Value {
        json!({"USD_per_kg": self.usd_per_kg, "breakdown": self.breakdown,
               "SGD_per_kg": self.sgd_per_kg, "capex_total_USD": self.capex_total_usd})
    }
}

/// `hydrogen_cost(case, nh3_price, hours, electricity, capex_mode)`: LCOH of a stored case on
/// the reference scenario (`singapore.evaluate`).
pub fn hydrogen_cost(
    ctx: &Ctx,
    case: &str,
    nh3_price: f64,
    hours: Option<f64>,
    electricity: Option<f64>,
    capex_mode: &str,
) -> Result<HydrogenCost, EngineError> {
    let mut ov = Overrides::new();
    ov.insert(
        "operating_hours_h_per_yr".into(),
        json!(hours.unwrap_or(ctx.p.hours_per_year)),
    );
    ov.insert("capex_mode".into(), json!(capex_mode));
    ov.insert(
        "electricity_price_USD_per_kWh".into(),
        json!(electricity.unwrap_or(ctx.p.electricity_usd_kwh)),
    );
    let st = ctx.stored(case)?;
    let s = Summary::extract(&st.raw)?;
    let e = evaluate(ctx.d, &s, &Scenario::Price(nh3_price), &ov)?;
    let f = |v: &Value, k: &str| -> Result<f64, EngineError> {
        v.as_f64()
            .ok_or_else(|| EngineError::Domain(format!("evaluate: {k} not a number")))
    };
    Ok(HydrogenCost {
        usd_per_kg: f(&e["lcoh_USD_per_kg"], "lcoh_USD_per_kg")?,
        breakdown: e["breakdown_USD_per_kg"].clone(),
        sgd_per_kg: f(&e["lcoh_SGD_per_kg"], "lcoh_SGD_per_kg")?,
        capex_total_usd: f(&e["capex"]["total_capex_USD"], "total_capex_USD")?,
    })
}

/// `eta_exhaust_integrated(f)`: electricity per kg NH3 (MJ), linear in the cracked share.
pub fn eta_exhaust_integrated(p: &Params, f: f64) -> f64 {
    p.elec_mj_per_kg_direct + f * (p.elec_mj_per_kg_full - p.elec_mj_per_kg_direct)
}

fn n2o_per_mwh(nh3_energy_share: f64) -> f64 {
    lca::n2o_nox_per_mwh().1 * nh3_energy_share
}

/// Options of [`power_activity`] (Python keyword arguments).
#[derive(Debug, Clone, PartialEq)]
pub struct PowerOpts {
    pub case: String,
    pub gain_scale: f64,
    pub eta_h2_fuel: Option<f64>,
    pub heat_fuel_efficiency: f64,
}

impl Default for PowerOpts {
    fn default() -> Self {
        PowerOpts {
            case: "baseline".into(),
            gain_scale: 1.0,
            eta_h2_fuel: None,
            heat_fuel_efficiency: 1.0,
        }
    }
}

/// `int(round(y * 100))` of the pathway id.
pub fn pct_tag(y: f64) -> i64 {
    (y * 100.0).round_ties_even() as i64
}

/// `power_activity(kind, y_h2, case, gain_scale, eta_h2_fuel, heat_fuel_efficiency)`.
pub fn power_activity(
    ctx: &Ctx,
    kind: &str,
    y_h2: Option<f64>,
    o: &PowerOpts,
) -> Result<Activity, EngineError> {
    let p = &ctx.p;
    let eta_gas = o.eta_h2_fuel.unwrap_or(p.eta_gt_gas);
    if !(0.0 < o.heat_fuel_efficiency && o.heat_fuel_efficiency <= 1.0) {
        return Err(verr("heat_fuel_efficiency must lie in (0, 1]"));
    }
    let c = ctx.cracker(&o.case)?;
    let x = c.conversion;
    let heat_nh3_per_kg_cracked =
        c.crack_heat_mj_per_kg_nh3() / p.lhv_nh3_mj_kg / o.heat_fuel_efficiency;
    let need_y = || {
        y_h2.ok_or_else(|| {
            EngineError::Domain(
                "TypeError: '<=' not supported between instances of 'int' and 'NoneType'".into(),
            )
        })
    };
    let f: Option<f64> = match kind {
        "direct" => Some(0.0),
        "full_exhaust" | "full_fired" | "full_purified" => Some(1.0),
        "partial_exhaust" | "partial_fired" => Some(cracked_share_for_h2_fraction(need_y()?, x)?),
        "blend_purified" => None,
        other => return Err(verr(other)),
    };
    let lhv_n = p.lhv_nh3_mj_kg;
    let lhv_h = p.lhv_h2_mj_kg;
    let (elec, total_nh3, h2f, nh3_energy_share, cracked, heat_mode, cap, pure);
    match kind {
        "direct" | "partial_exhaust" | "full_exhaust" => {
            let f = f.unwrap_or(0.0);
            elec = p.elec_mj_per_kg_direct
                + o.gain_scale * (eta_exhaust_integrated(p, f) - p.elec_mj_per_kg_direct);
            total_nh3 = 1.0;
            h2f = h2_fraction_of_blend(f, x);
            nh3_energy_share = py_max(
                0.0,
                (1.0 - f * x) * lhv_n / fuel_lhv_mj_per_kg_nh3_fed(f, x),
            );
            cracked = f;
            heat_mode = if f > 0.0 {
                "exhaust-heated cracker (literature efficiency)"
            } else {
                "none"
            }
            .to_string();
            cap = if f > 0.0 { "unpurified" } else { "none" };
            pure = String::new();
        }
        "partial_fired" | "full_fired" => {
            let f = f.unwrap_or(0.0);
            elec = eta_gas * fuel_lhv_mj_per_kg_nh3_fed(f, x);
            total_nh3 = 1.0 + f * heat_nh3_per_kg_cracked;
            h2f = h2_fraction_of_blend(f, x);
            nh3_energy_share = py_max(
                0.0,
                (1.0 - f * x) * lhv_n / fuel_lhv_mj_per_kg_nh3_fed(f, x),
            );
            cracked = f;
            heat_mode =
                "cracker heat from extra NH3 (stored Aspen reactor + pre-heater duty)".into();
            cap = "unpurified";
            pure = String::new();
        }
        "full_purified" => {
            let h2p = c.h2_product_per_kg_nh3();
            elec = eta_gas * h2p * lhv_h;
            total_nh3 = 1.0 + c.deficit_mj_per_kg_nh3() / lhv_n / o.heat_fuel_efficiency;
            h2f = 1.0;
            nh3_energy_share = 0.0;
            cracked = 1.0;
            heat_mode = "tail gas + extra NH3 (stored Aspen heat deficit)".into();
            cap = "purified";
            pure = format!(
                "PSA product {} mol% H2 (recovery {})",
                fmt_f(c.purity_mole_frac * 100.0, 3),
                py_repr(c.recovery)
            );
        }
        _ => {
            // blend_purified: share g of NH3 cracked and purified, the rest burnt directly
            let y = need_y()?;
            let h2p = c.h2_product_per_kg_nh3();
            let (mh2, mnh3) = (molar_mass(Species::H2), molar_mass(Species::NH3));
            let yfun = |g: f64| {
                let n_h2 = g * h2p / mh2;
                let n_nh3 = (1.0 - g) / mnh3;
                n_h2 / (n_h2 + n_nh3) - y
            };
            let g = brentq(yfun, 1e-9, 1.0, BrentOptions::default())
                .map_err(|e| verr(&format!("brentq: {e}")))?
                .x;
            elec = eta_gas * ((1.0 - g) * lhv_n + g * h2p * lhv_h);
            total_nh3 = 1.0 + g * c.deficit_mj_per_kg_nh3() / lhv_n / o.heat_fuel_efficiency;
            let n_h2 = g * h2p / mh2;
            let n_nh3 = (1.0 - g) / mnh3;
            h2f = n_h2 / (n_h2 + n_nh3);
            nh3_energy_share = (1.0 - g) * lhv_n / ((1.0 - g) * lhv_n + g * h2p * lhv_h);
            cracked = g;
            heat_mode = "tail gas + extra NH3 (stored Aspen heat deficit)".into();
            cap = "purified";
            pure = format!(
                "blend of NH3 + PSA H2 ({} mol%)",
                fmt_f(c.purity_mole_frac * 100.0, 3)
            );
        }
    }
    let elec_per_kg_total = elec / total_nh3;
    let nh3_per_mwh = 3600.0 / elec_per_kg_total;
    let eff = elec_per_kg_total / lhv_n;
    let m_total_h = p.ahmad_mass_flow_kg_s * 3600.0;
    let (nh3_cracked_h, cracker_h2) = match kind {
        "full_purified" => {
            let v = m_total_h / total_nh3;
            (v, v * c.h2_product_per_kg_nh3())
        }
        "blend_purified" => {
            let v = m_total_h / total_nh3 * cracked;
            (v, v * c.h2_product_per_kg_nh3())
        }
        _ => {
            let v = m_total_h / total_nh3 * cracked;
            (v, v * lca::KG_H2_PER_KG_NH3 * x)
        }
    };
    let n2o = if kind != "full_purified" {
        n2o_per_mwh(nh3_energy_share)
    } else {
        0.0
    };
    let through = if matches!(kind, "full_purified" | "blend_purified") {
        nh3_cracked_h
    } else {
        m_total_h / total_nh3 * cracked
    };
    let id = match y_h2 {
        Some(y) => format!("{kind}_{}", pct_tag(y)),
        None => kind.to_string(),
    };
    Ok(Activity {
        cracker_nh3_kg_h: through,
        id,
        label: kind.replace('_', " "),
        product: "electricity".into(),
        functional_unit: "1 MWh net electricity".into(),
        nh3_kg: nh3_per_mwh,
        aux_kwh: c.pump_kwh_per_kg_nh3() * nh3_per_mwh * cracked,
        efficiency: eff,
        n2o_kgco2e: n2o,
        no_kg: if kind == "direct" {
            Some(lca::n2o_nox_per_mwh().2)
        } else {
            None
        },
        cracker_h2_kg_h: cracker_h2,
        capex_kind: cap.into(),
        h2_fraction_vol: Some(h2f),
        cracked_share: Some(cracked),
        purity_note: pure,
        heat_mode,
    })
}

/// Options of [`power_cost`] (Python keyword arguments; defaults from [`Params`]).
#[derive(Debug, Clone, PartialEq)]
pub struct CostOpts {
    pub hours: f64,
    pub discount: f64,
    pub life: f64,
    pub mass_basis_kg_s: f64,
    pub electricity_price: f64,
    pub unpurified_full_correlation: bool,
    pub cracker_capex_factor: f64,
    pub plant_capex_factor: f64,
    pub extra_capex_usd_per_kw: f64,
}

impl CostOpts {
    pub fn new(p: &Params) -> CostOpts {
        CostOpts {
            hours: p.power_plant_hours_per_year,
            discount: p.discount_rate,
            life: p.plant_life_yr,
            mass_basis_kg_s: p.ahmad_mass_flow_kg_s,
            electricity_price: p.electricity_usd_kwh,
            unpurified_full_correlation: false,
            cracker_capex_factor: 1.0,
            plant_capex_factor: 1.0,
            extra_capex_usd_per_kw: 0.0,
        }
    }
}

/// Result of [`power_cost`].
#[derive(Debug, Clone, PartialEq)]
pub struct PowerCost {
    pub lcoe_usd_per_mwh: f64,
    pub w_net_mw: f64,
    pub tci_musd: f64,
    pub tci_cracker_musd: f64,
    /// capital, fixed_om, ammonia, aux_electricity (USD/MWh).
    pub components: [f64; 4],
}

impl PowerCost {
    pub fn to_json(&self) -> Value {
        let c = &self.components;
        json!({"LCOE_USD_per_MWh": self.lcoe_usd_per_mwh, "W_net_MW": self.w_net_mw,
               "TCI_MUSD": self.tci_musd, "TCI_cracker_MUSD": self.tci_cracker_musd,
               "components_USD_per_MWh": {"capital": c[0], "fixed_om": c[1], "ammonia": c[2],
                                          "aux_electricity": c[3]}})
    }
}

/// `power_cost(a, nh3_price, ...)`: LCOE of the reference plant (Ahmad basis 4.667 kg/s NH3).
pub fn power_cost(
    ctx: &Ctx,
    a: &Activity,
    nh3_price: f64,
    o: &CostOpts,
) -> Result<PowerCost, EngineError> {
    let p = &ctx.p;
    let eff_mj = 3600.0 / a.nh3_kg;
    let w_mw = o.mass_basis_kg_s * eff_mj;
    let scale = (w_mw / p.ahmad_w_net_2a_mw).powf(p.plant_scale_exponent);
    let tci_plant = p.ahmad_tci_2a_musd * 1e6 * scale * o.plant_capex_factor
        + o.extra_capex_usd_per_kw * w_mw * 1e3;
    let fixed_plant =
        p.ahmad_oc_fixed_2a_usd_per_kwh * p.ahmad_w_net_2a_mw * 1e3 * p.ahmad_hours_implied * scale;
    let mut tci_crk = 0.0;
    if a.capex_kind != "none" && a.cracker_nh3_kg_h > 0.0 {
        let mut args = RefCapexArgs::new(a.cracker_nh3_kg_h / molar_mass(Species::NH3));
        if a.capex_kind == "unpurified" && !o.unpurified_full_correlation {
            args.exclude = vec!["psa".into(), "adsorber".into()];
        }
        let cap = ctx.d.reference_capex(&args)?;
        tci_crk = cap["total_capex_USD"]
            .as_f64()
            .ok_or_else(|| EngineError::Domain("reference_capex: total_capex_USD".into()))?
            * o.cracker_capex_factor;
    }
    let k = crf(o.discount, o.life)?;
    let mwh_y = w_mw * o.hours;
    let capital = (tci_plant + tci_crk) * k;
    let fixed = fixed_plant + p.cracker_fixed_om_frac_tci * tci_crk;
    let fuel = o.mass_basis_kg_s * 3600.0 * o.hours * nh3_price / 1000.0;
    let elec = a.aux_kwh * mwh_y * o.electricity_price;
    let tot = capital + fixed + fuel + elec;
    Ok(PowerCost {
        lcoe_usd_per_mwh: tot / mwh_y,
        w_net_mw: w_mw,
        tci_musd: (tci_plant + tci_crk) / 1e6,
        tci_cracker_musd: tci_crk / 1e6,
        components: [capital / mwh_y, fixed / mwh_y, fuel / mwh_y, elec / mwh_y],
    })
}
