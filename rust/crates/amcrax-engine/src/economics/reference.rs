//! Unified reference scenario and the CAPEX method `cho2026_itemised_v1` (Python
//! `economics/reference.py`, data `backend/amcrax/data/reference_scenario.yaml`).
//!
//! Installed cost of item i in the Cho et al. (2026) Ni-24.34 bar plant (2024 USD):
//! `I_i,ref = u_i * m_H2,ref * OH_ref / CRF(d_ref, n_ref)`; the ISBL items (boiler, heat
//! exchangers, PSA and adsorber from the T/PSA split, reactor, other ISBL) are scaled
//! `I_i = I_i,ref * (S_i / S_i,ref) ** n * location_factor * multiplier`, the product compressor is
//! excluded, and `TCI = sum(I_i) * (1 + OSBL) * (1 + engineering + contingency)`.

use super::{jf, pydiv, pypow};
use crate::error::EngineError;
use crate::odata::OValue;
use crate::pyops::{fmt_g, py_sum};
use serde_json::{Map, Value, json};

/// Repository path of the reference scenario.
pub const REL_PATH: &str = "backend/amcrax/data/reference_scenario.yaml";
/// Repository path of the legacy economics data.
pub const ECONOMICS_YAML: &str = "backend/amcrax/data/economics.yaml";
/// Repository path of the Singapore data.
pub const SINGAPORE_YAML: &str = "backend/amcrax/data/singapore.yaml";

/// ISBL items of the reference CAPEX method, in the Python order (`ISBL_ITEMS`).
pub const ISBL_ITEMS: [&str; 6] = [
    "boiler",
    "heat_exchangers",
    "psa",
    "adsorber",
    "reactor",
    "other_isbl",
];

/// Phase 1 key of an item (`LEGACY_KEY`: the reactor is the `cracker`).
pub fn legacy_key(item: &str) -> &str {
    if item == "reactor" { "cracker" } else { item }
}

/// `_crf(i, n)` of `reference.py` (1/n for a zero rate).
pub fn crf_ref(i: f64, n: f64) -> f64 {
    if i == 0.0 {
        return 1.0 / n;
    }
    let f = pypow(1.0 + i, n);
    i * f / (f - 1.0)
}

/// The typed reference scenario (Python `ReferenceScenario`).
#[derive(Debug, Clone, PartialEq)]
pub struct ReferenceScenario {
    pub raw: OValue,
    pub sha256: String,
    pub version: String,
    pub id: String,
    pub nh3_feed_kmol_h: f64,
    pub h2_product_kg_h: f64,
    pub operating_hours_h_per_yr: f64,
    pub discount_rate: f64,
    pub plant_life_yr: f64,
    pub maintenance_frac_capex_per_yr: f64,
    pub insurance_frac_capex_per_yr: f64,
    pub labour_usd_per_yr: f64,
    pub plant_overhead_frac_labour_maint: f64,
    pub g_and_a_frac_fixed_opex: f64,
    pub fx_sgd_per_usd: f64,
    pub fx_date: String,
    pub usd_per_eur: f64,
    pub electricity_usd_per_kwh: f64,
    /// Ammonia price scenarios in document order.
    pub nh3_prices_usd_per_t: Vec<(String, f64)>,
    pub default_nh3_scenario: String,
    pub h2_selling_price_usd_per_kg: f64,
    pub carbon_tax_sgd_per_t: f64,
    pub carbon_threshold_tco2e_per_yr: f64,
    pub capex_method: String,
    pub capex_scaling_exponent: f64,
}

impl ReferenceScenario {
    /// Build from the parsed YAML document and the SHA-256 of its bytes.
    pub fn from_value(d: OValue, sha256: String) -> Result<Self, EngineError> {
        let f = REL_PATH;
        let v = |p: &[&str]| d.num_v(f, p);
        let s = |p: &[&str]| -> Result<String, EngineError> {
            let x = d.val(p);
            x.as_str()
                .map(str::to_string)
                .ok_or_else(|| EngineError::data(f, format!("{}: string expected", p.join("."))))
        };
        let mut prices = Vec::new();
        for (k, e) in d.at(&["prices", "nh3_price_scenarios_USD_per_t"]).entries() {
            let x = e
                .get("value")
                .as_f64()
                .ok_or_else(|| EngineError::data(f, format!("nh3 scenario {k}: value")))?;
            prices.push((k.clone(), x));
        }
        let version = match d.get("version") {
            OValue::Str(x) => x.clone(),
            OValue::Int(i) => i.to_string(),
            OValue::Float(x) => format!("{x:?}"),
            _ => return Err(EngineError::data(f, "version")),
        };
        Ok(ReferenceScenario {
            version,
            id: d.string(f, &["id"])?,
            nh3_feed_kmol_h: v(&["plant", "nh3_feed_kmol_h"])?,
            h2_product_kg_h: v(&["plant", "h2_product_kg_h"])?,
            operating_hours_h_per_yr: v(&["operation", "operating_hours_h_per_yr"])?,
            discount_rate: v(&["finance", "discount_rate"])?,
            plant_life_yr: v(&["finance", "plant_life_yr"])?,
            maintenance_frac_capex_per_yr: v(&["finance", "maintenance_frac_capex_per_yr"])?,
            insurance_frac_capex_per_yr: v(&["finance", "insurance_frac_capex_per_yr"])?,
            labour_usd_per_yr: v(&["finance", "labour_USD_per_yr"])?,
            plant_overhead_frac_labour_maint: v(&["finance", "plant_overhead_frac_labour_maint"])?,
            g_and_a_frac_fixed_opex: v(&["finance", "g_and_a_frac_fixed_opex"])?,
            fx_sgd_per_usd: v(&["currency", "fx_SGD_per_USD"])?,
            fx_date: match d.at(&["currency", "fx_SGD_per_USD", "date"]) {
                OValue::Str(x) => x.clone(),
                other => format!("{:?}", other.to_json()),
            },
            usd_per_eur: v(&["currency", "usd_per_eur"])?,
            electricity_usd_per_kwh: v(&["prices", "electricity_USD_per_kWh"])?,
            nh3_prices_usd_per_t: prices,
            default_nh3_scenario: s(&["prices", "default_nh3_scenario"])?,
            h2_selling_price_usd_per_kg: v(&["prices", "h2_selling_price_USD_per_kg"])?,
            carbon_tax_sgd_per_t: v(&["carbon_pricing", "rate_SGD_per_tCO2e"])?,
            carbon_threshold_tco2e_per_yr: v(&["carbon_pricing", "threshold_tCO2e_per_yr"])?,
            capex_method: s(&["capex", "method"])?,
            capex_scaling_exponent: v(&["capex", "scaling_exponent"])?,
            raw: d,
            sha256,
        })
    }

    /// Price of a named ammonia scenario (`KeyError` -> domain error).
    pub fn nh3_price(&self, scenario: &str) -> Result<f64, EngineError> {
        self.nh3_prices_usd_per_t
            .iter()
            .find(|e| e.0 == scenario)
            .map(|e| e.1)
            .ok_or_else(|| EngineError::Domain(format!("KeyError: unknown scenario {scenario:?}")))
    }

    /// Python `economic_overrides()`: the EconomicAssumptions fields the scenario owns, in order.
    pub fn economic_overrides(&self) -> Vec<(&'static str, f64)> {
        vec![
            ("discount_rate", self.discount_rate),
            ("plant_life_yr", self.plant_life_yr),
            ("operating_hours_h_per_yr", self.operating_hours_h_per_yr),
            (
                "maintenance_frac_capex_per_yr",
                self.maintenance_frac_capex_per_yr,
            ),
            (
                "insurance_frac_capex_per_yr",
                self.insurance_frac_capex_per_yr,
            ),
            ("labour_USD_per_yr", self.labour_usd_per_yr),
            (
                "plant_overhead_frac_labour_maint",
                self.plant_overhead_frac_labour_maint,
            ),
            ("g_and_a_frac_fixed_opex", self.g_and_a_frac_fixed_opex),
            (
                "electricity_price_USD_per_kWh",
                self.electricity_usd_per_kwh,
            ),
        ]
    }

    /// Capital recovery factor of the scenario.
    pub fn crf(&self) -> f64 {
        crf_ref(self.discount_rate, self.plant_life_yr)
    }

    /// `sens(key)`: the sensitivity range `(low, high)`.
    pub fn sens(&self, key: &str) -> Result<(f64, f64), EngineError> {
        let v = self
            .raw
            .num_seq(REL_PATH, &["sensitivity_ranges", key, "value"])?;
        match v.as_slice() {
            [a, b] => Ok((*a, *b)),
            _ => Err(EngineError::data(
                REL_PATH,
                format!("sensitivity range {key}"),
            )),
        }
    }

    /// Python `provenance_stamp()`.
    pub fn provenance_stamp(&self) -> Value {
        json!({"file": REL_PATH, "sha256": self.sha256, "version": self.version, "id": self.id,
               "fx_SGD_per_USD": self.fx_sgd_per_usd, "fx_date": self.fx_date,
               "capex_method": self.capex_method})
    }

    /// `price_year_label` of the scenario.
    pub fn price_year_label(&self) -> String {
        self.raw
            .get("price_year_label")
            .as_str()
            .unwrap_or_default()
            .to_string()
    }
}

/// The three economic data files.
#[derive(Debug, Clone, PartialEq)]
pub struct EconomicsData {
    /// `economics.yaml` (legacy correlation and the EconomicAssumptions defaults).
    pub economics: OValue,
    /// `singapore.yaml`.
    pub singapore: OValue,
    /// `reference_scenario.yaml`.
    pub reference: ReferenceScenario,
}

/// The YAML files, embedded at compile time.
#[cfg(feature = "yaml")]
pub mod embedded {
    pub const ECONOMICS: &str = include_str!("../../../../../backend/amcrax/data/economics.yaml");
    pub const SINGAPORE: &str = include_str!("../../../../../backend/amcrax/data/singapore.yaml");
    pub const REFERENCE: &str =
        include_str!("../../../../../backend/amcrax/data/reference_scenario.yaml");
}

impl EconomicsData {
    /// Build from parsed documents.
    pub fn from_values(
        economics: OValue,
        singapore: OValue,
        reference: OValue,
        reference_sha256: String,
    ) -> Result<Self, EngineError> {
        Ok(EconomicsData {
            economics,
            singapore,
            reference: ReferenceScenario::from_value(reference, reference_sha256)?,
        })
    }

    /// Parse the YAML texts.
    #[cfg(feature = "yaml")]
    pub fn from_yaml(
        economics: &str,
        singapore: &str,
        reference: &str,
    ) -> Result<Self, EngineError> {
        Self::from_values(
            OValue::from_yaml(ECONOMICS_YAML, economics)?,
            OValue::from_yaml(SINGAPORE_YAML, singapore)?,
            OValue::from_yaml(REL_PATH, reference)?,
            crate::provenance::sha256_hex(reference.as_bytes()),
        )
    }

    /// The embedded data (parsed once).
    #[cfg(feature = "yaml")]
    pub fn embedded() -> &'static EconomicsData {
        static CELL: std::sync::OnceLock<EconomicsData> = std::sync::OnceLock::new();
        CELL.get_or_init(|| {
            EconomicsData::from_yaml(
                embedded::ECONOMICS,
                embedded::SINGAPORE,
                embedded::REFERENCE,
            )
            .expect("embedded economic data files are valid (checked in CI)")
        })
    }

    fn capex(&self) -> &OValue {
        self.reference.raw.get("capex")
    }

    fn cv(&self, key: &str) -> Result<f64, EngineError> {
        self.reference.raw.num_v(REL_PATH, &["capex", key])
    }

    /// Python `reference_item_costs()`.
    pub fn reference_item_costs(&self) -> Result<ItemCosts, EngineError> {
        let c = self.capex();
        let u = |k: &str| -> Result<f64, EngineError> {
            c.at(&["unit_capex_USD_per_kg_h2", "value", k])
                .as_f64()
                .ok_or_else(|| EngineError::data(REL_PATH, format!("unit_capex {k}")))
        };
        let m = self.cv("reference_plant_h2_kg_h")?;
        let oh = self.cv("reference_operating_hours_h_per_yr")?;
        let k = crf_ref(
            self.cv("reference_discount_rate")?,
            self.cv("reference_plant_life_yr")?,
        );
        let fac = (1.0 + self.cv("osbl_frac_isbl")?)
            * (1.0
                + self.cv("engineering_frac_isbl_osbl")?
                + self.cv("contingency_frac_isbl_osbl")?);
        let isbl_total_u = u("total")? / fac;
        let itemised =
            u("boiler")? + u("heat_exchangers")? + u("compressor")? + u("tpsa")? + u("reactor")?;
        let sp = |k: &str| -> Result<f64, EngineError> {
            c.at(&["tpsa_split_psa_adsorber", "value", k])
                .as_f64()
                .ok_or_else(|| EngineError::data(REL_PATH, format!("tpsa split {k}")))
        };
        let s = sp("psa")? + sp("adsorber")?;
        let unit = vec![
            ("boiler".to_string(), u("boiler")?),
            ("heat_exchangers".to_string(), u("heat_exchangers")?),
            ("compressor".to_string(), u("compressor")?),
            ("psa".to_string(), u("tpsa")? * sp("psa")? / s),
            ("adsorber".to_string(), u("tpsa")? * sp("adsorber")? / s),
            ("reactor".to_string(), u("reactor")?),
            ("other_isbl".to_string(), isbl_total_u - itemised),
        ];
        let to_usd = m * oh / k;
        Ok(ItemCosts {
            installed_usd: unit.iter().map(|(i, x)| (i.clone(), x * to_usd)).collect(),
            unit_usd_per_kg_h2: unit,
            indirect_factor: fac,
            reference_crf: k,
            reference_h2_kg_h: m,
            reference_nh3_feed_kmol_h: self.cv("reference_plant_nh3_feed_kmol_h")?,
        })
    }

    /// Python `reference_catalyst_mass_kg()` with the default space velocity (9000 mL/(g h))
    /// and molar volume (22.414 L/mol).
    pub fn reference_catalyst_mass_kg(&self) -> Result<f64, EngineError> {
        let n = self.cv("reference_plant_nh3_feed_kmol_h")?;
        Ok(n * 1000.0 * 22.414 * 1000.0 / 9000.0 / 1000.0)
    }

    /// Python `reference_capex(...)`.
    pub fn reference_capex(&self, a: &RefCapexArgs) -> Result<Value, EngineError> {
        let c = self.capex();
        let base = self.reference_item_costs()?;
        let n = a.exponent.unwrap_or(self.reference.capex_scaling_exponent);
        let lf = match a.location_factor {
            Some(x) => x,
            None => self.cv("location_factor_singapore")?,
        };
        let mut driver: Vec<(String, String)> = c
            .at(&["size_driver", "value"])
            .entries()
            .iter()
            .map(|(k, v)| (k.clone(), v.as_str().unwrap_or_default().to_string()))
            .collect();
        if let Some(rd) = a.reactor_size_driver.as_deref().filter(|s| !s.is_empty()) {
            let pos = driver.iter().position(|e| e.0 == "reactor");
            match pos {
                Some(k) => driver[k].1 = rd.to_string(),
                None => driver.push(("reactor".into(), rd.to_string())),
            }
        }
        let feed_ratio = a.nh3_feed_kmol_h / base.reference_nh3_feed_kmol_h;
        let mut ratios: Vec<(&str, f64)> = Vec::new();
        for i in ISBL_ITEMS {
            let given = a
                .item_size_ratio
                .as_ref()
                .and_then(|m| m.iter().find(|e| e.0 == i).map(|e| e.1));
            let r = if let Some(r) = given {
                r
            } else {
                let d = driver
                    .iter()
                    .find(|e| e.0 == i)
                    .map(|e| e.1.as_str())
                    .ok_or_else(|| EngineError::Domain(format!("KeyError: size driver of {i}")))?;
                if d == "catalyst_mass" {
                    let m = a.catalyst_mass_kg.ok_or_else(|| {
                        EngineError::Domain(
                            "ValueError: reactor_size_driver 'catalyst_mass' needs catalyst_mass_kg"
                                .into(),
                        )
                    })?;
                    pydiv(m, self.reference_catalyst_mass_kg()?, "catalyst mass ratio")?
                } else {
                    feed_ratio
                }
            };
            ratios.push((i, r));
        }
        let installed = |i: &str| base.installed_usd.iter().find(|e| e.0 == i).map(|e| e.1);
        let mut isbl: Vec<(&str, f64)> = Vec::new();
        for (i, r) in &ratios {
            if a.exclude.iter().any(|x| x == i) {
                continue;
            }
            let b = installed(i).ok_or_else(|| EngineError::data(REL_PATH, format!("item {i}")))?;
            isbl.push((i, b * pypow(*r, n) * lf * a.capex_multiplier));
        }
        let fac = base.indirect_factor;
        let tci: Vec<(&str, f64)> = isbl.iter().map(|(i, v)| (*i, v * fac)).collect();
        let total = py_sum(tci.iter().map(|e| e.1));
        let isbl_sum = py_sum(isbl.iter().map(|e| e.1));
        let obj = |v: &[(&str, f64)], legacy: bool| -> Value {
            let mut m = Map::new();
            for (k, x) in v {
                m.insert(if legacy { legacy_key(k) } else { k }.to_string(), jf(*x));
            }
            Value::Object(m)
        };
        let mut excluded = vec![Value::String("compressor".into())];
        excluded.extend(a.exclude.iter().map(|x| Value::String(x.clone())));
        let cost_year = c.val(&["cost_year"]).to_json();
        Ok(json!({
            "method": self.reference.capex_method,
            "total_capex_USD": jf(total),
            "isbl_USD": obj(&isbl, false),
            "isbl_total_USD": jf(isbl_sum),
            "indirect_factor": jf(fac),
            "indirects_USD": jf(total - isbl_sum),
            "tci_by_item_USD": obj(&tci, false),
            "size_ratio": obj(&ratios, false),
            "scaling_exponent": jf(n),
            "location_factor": jf(lf),
            "capex_multiplier": jf(a.capex_multiplier),
            "excluded": excluded,
            "cost_year": cost_year,
            "pec_USD": obj(&isbl, true),
            "pec_total_USD": jf(isbl_sum),
            "tci_over_pec": jf(fac),
            "tci_by_equipment_USD": obj(&tci, true),
            "basis": format!(
                "cho2026_itemised_v1: Cho 2026 Ni-24.34 bar itemised installed cost (2024 USD), product compressor \
                 removed, items scaled by size ratio^{}, x (1+OSBL 0.12)(1+eng 0.10+cont 0.18)",
                fmt_g(n, 6)
            ),
        }))
    }
}

/// Result of [`EconomicsData::reference_item_costs`] (items in the Python order).
#[derive(Debug, Clone, PartialEq)]
pub struct ItemCosts {
    pub installed_usd: Vec<(String, f64)>,
    pub unit_usd_per_kg_h2: Vec<(String, f64)>,
    pub indirect_factor: f64,
    pub reference_crf: f64,
    pub reference_h2_kg_h: f64,
    pub reference_nh3_feed_kmol_h: f64,
}

impl ItemCosts {
    /// As the Python dict.
    pub fn to_json(&self) -> Value {
        let o = |v: &[(String, f64)]| -> Value {
            Value::Object(v.iter().map(|(k, x)| (k.clone(), jf(*x))).collect())
        };
        json!({"installed_USD": o(&self.installed_usd), "unit_USD_per_kg_h2": o(&self.unit_usd_per_kg_h2),
               "indirect_factor": jf(self.indirect_factor), "reference_crf": jf(self.reference_crf),
               "reference_h2_kg_h": jf(self.reference_h2_kg_h),
               "reference_nh3_feed_kmol_h": jf(self.reference_nh3_feed_kmol_h)})
    }
}

/// Keyword arguments of Python `reference_capex`.
#[derive(Debug, Clone, PartialEq)]
pub struct RefCapexArgs {
    pub nh3_feed_kmol_h: f64,
    pub catalyst_mass_kg: Option<f64>,
    pub reactor_size_driver: Option<String>,
    pub item_size_ratio: Option<Vec<(String, f64)>>,
    pub exclude: Vec<String>,
    pub exponent: Option<f64>,
    pub capex_multiplier: f64,
    pub location_factor: Option<f64>,
}

impl RefCapexArgs {
    /// Defaults of the Python signature for a feed.
    pub fn new(nh3_feed_kmol_h: f64) -> Self {
        RefCapexArgs {
            nh3_feed_kmol_h,
            catalyst_mass_kg: None,
            reactor_size_driver: None,
            item_size_ratio: None,
            exclude: Vec::new(),
            exponent: None,
            capex_multiplier: 1.0,
            location_factor: None,
        }
    }
}

#[cfg(all(test, feature = "yaml"))]
mod tests {
    use super::*;

    #[test]
    fn baseline_capex_and_crf() {
        let d = EconomicsData::embedded();
        let cap = d.reference_capex(&RefCapexArgs::new(99.8)).unwrap();
        let total = cap["total_capex_USD"].as_f64().unwrap();
        // stored results/research/reference_scenario/baseline.json capex_total_USD
        assert!((total / 7666560.407024863 - 1.0).abs() < 1e-12, "{total}");
        assert!((d.reference.crf() - 0.11016807219002081).abs() < 1e-15);
        assert_eq!(d.reference.nh3_price("grey").unwrap(), 450.0);
        assert!(d.reference.nh3_price("purple").is_err());
    }
}
