//! Rate laws (Python `kinetics/rate_laws.py`; data `backend/amcrax/data/kinetics.yaml`, sections
//! `catalysts` and `research_catalysts`): Takahashi micro-kinetic (Ni and Ru), Kum Temkin-Pyzhev
//! (both equilibrium-constant bases), the two Lucentini LHHW forms, the AmCraX approach factor
//! `1 - Q/Kp` and the optional `param_overrides` of Phase 2. Stage 2. Gate: 1e-12 relative.
//!
//! Partial pressures are `(name, bar)` pairs as the Python dict: `NH3`, `H2`, `N2` enter the laws,
//! every other name (H2O, Ar, ...) is an inert that only adds to the total pressure.
//!
//! One deliberate difference: Python silently ignores a misspelt name in `param_overrides`; here
//! an override must name a parameter of the catalyst ([`EngineError::Domain`] otherwise).

use crate::error::EngineError;
use crate::pyops::{py_max, py_sum};
use crate::thermo::equilibrium::equilibrium_constant;
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

/// Repository path of the registry.
pub const DATA_FILE: &str = "backend/amcrax/data/kinetics.yaml";
/// The registry, embedded at compile time (parsed with the `yaml` feature).
#[cfg(feature = "yaml")]
pub const EMBEDDED_YAML: &str = include_str!("../../../../backend/amcrax/data/kinetics.yaml");

/// Basis of the equilibrium constant of the Temkin-Pyzhev law (Python `keq_basis`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum KeqBasis {
    /// Kum Eq. 4 read as J per 2 mol NH3 (Python default of `rate_mol_per_kgcat_s`).
    #[default]
    Published,
    /// Kp of the AmCraX NASA-7 thermodynamics.
    AmcraxThermo,
}

impl KeqBasis {
    /// Parse the Python string.
    pub fn from_python(s: &str) -> Result<KeqBasis, EngineError> {
        match s {
            "published" => Ok(KeqBasis::Published),
            "amcrax_thermo" => Ok(KeqBasis::AmcraxThermo),
            _ => Err(EngineError::Domain(
                "keq_basis must be 'published' or 'amcrax_thermo'".into(),
            )),
        }
    }
}

/// Parameter overrides by name (uncertainty analysis).
pub type Overrides = BTreeMap<String, f64>;

/// Options of a rate evaluation (Python keyword arguments of `rate_mol_per_kgcat_s`).
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct RateOpts<'a> {
    /// Approach factor `1 - Q/K` (Takahashi and Lucentini forms); `None`: registry default.
    pub approach_factor: Option<bool>,
    /// Equilibrium-constant basis (Temkin-Pyzhev form only).
    pub keq_basis: KeqBasis,
    /// Parameter overrides (`None` leaves every result bit-identical).
    pub param_overrides: Option<&'a Overrides>,
}

/// Rate-law form (Python `form`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Form {
    TakahashiMicrokinetic,
    TemkinPyzhev,
    LhhwLucentini,
}

impl Form {
    fn from_python(s: &str) -> Option<Form> {
        match s {
            "takahashi_microkinetic" => Some(Form::TakahashiMicrokinetic),
            "temkin_pyzhev" => Some(Form::TemkinPyzhev),
            "lhhw_lucentini" => Some(Form::LhhwLucentini),
            _ => None,
        }
    }
}

/// One catalyst of the registry.
#[derive(Debug, Clone, PartialEq)]
pub struct Catalyst {
    pub id: String,
    pub label: String,
    pub form: Form,
    pub usable: bool,
    /// `parameters.<name>.value`
    pub params: BTreeMap<String, f64>,
    /// Validity block (`T_min_K`, `T_max_K`, `P_min_bar`, `P_max_bar`).
    pub validity: BTreeMap<String, f64>,
    /// From the `research_catalysts` section.
    pub research: bool,
}

/// The kinetics registry.
#[derive(Debug, Clone, PartialEq)]
pub struct KineticsRegistry {
    pub g_per_kg: f64,
    pub bar_per_atm: f64,
    /// Gas constant of the rate laws, J/(mol K) (8.314 as used by the sources).
    pub r_kin_j_mol_k: f64,
    /// Forms the approach factor applies to.
    pub approach_forms: Vec<Form>,
    /// Registry default of the approach factor.
    pub approach_default_on: bool,
    /// `catalysts.ru_kum_temkin_pyzhev.equilibrium_constant.dGr_coefficients_J`.
    pub kum_dgr_coefficients_j: Option<[f64; 4]>,
    catalysts: Vec<Catalyst>,
    /// SHA-256 of the YAML text (empty when built from a value).
    pub sha256: String,
}

fn f(v: &Value, what: &str) -> Result<f64, EngineError> {
    v.as_f64()
        .ok_or_else(|| EngineError::data(DATA_FILE, format!("{what}: number expected")))
}

impl KineticsRegistry {
    /// Build from the parsed YAML document.
    pub fn from_value(d: &Value) -> Result<Self, EngineError> {
        let uc = &d["unit_conversions"];
        let ef = &d["equilibrium_approach_factor"];
        let approach_forms = ef["applies_to_forms"]
            .as_array()
            .map(Vec::as_slice)
            .unwrap_or(&[])
            .iter()
            .filter_map(|v| v.as_str().and_then(Form::from_python))
            .collect();
        let mut catalysts = Vec::new();
        for (section, research) in [("catalysts", false), ("research_catalysts", true)] {
            let Some(obj) = d[section].as_object() else {
                continue;
            };
            for (id, c) in obj {
                let form = c["form"]
                    .as_str()
                    .and_then(Form::from_python)
                    .ok_or_else(|| {
                        EngineError::data(DATA_FILE, format!("{id}: unknown rate-law form"))
                    })?;
                let mut params = BTreeMap::new();
                for (k, v) in c["parameters"].as_object().into_iter().flatten() {
                    params.insert(k.clone(), f(&v["value"], k)?);
                }
                let mut validity = BTreeMap::new();
                for (k, v) in c["validity"].as_object().into_iter().flatten() {
                    if let Some(x) = v.as_f64() {
                        validity.insert(k.clone(), x);
                    }
                }
                catalysts.push(Catalyst {
                    id: id.clone(),
                    label: c["label"].as_str().unwrap_or("").to_string(),
                    form,
                    usable: c["usable"].as_bool().unwrap_or(false),
                    params,
                    validity,
                    research,
                });
            }
        }
        let kum =
            d["catalysts"]["ru_kum_temkin_pyzhev"]["equilibrium_constant"]["dGr_coefficients_J"]
                .as_array()
                .filter(|a| a.len() == 4)
                .map(|a| -> Result<[f64; 4], EngineError> {
                    Ok([
                        f(&a[0], "dGr")?,
                        f(&a[1], "dGr")?,
                        f(&a[2], "dGr")?,
                        f(&a[3], "dGr")?,
                    ])
                })
                .transpose()?;
        Ok(KineticsRegistry {
            g_per_kg: f(&uc["g_per_kg"], "g_per_kg")?,
            bar_per_atm: f(&uc["bar_per_atm"], "bar_per_atm")?,
            r_kin_j_mol_k: f(&uc["gas_constant_J_per_mol_K"], "gas_constant_J_per_mol_K")?,
            approach_forms,
            approach_default_on: ef["default_on"].as_bool().unwrap_or(true),
            kum_dgr_coefficients_j: kum,
            catalysts,
            sha256: String::new(),
        })
    }

    /// Parse the YAML text of `kinetics.yaml`.
    #[cfg(feature = "yaml")]
    pub fn from_yaml_str(text: &str) -> Result<Self, EngineError> {
        let v: Value = serde_saphyr::from_str(text)
            .map_err(|e| EngineError::data(DATA_FILE, e.to_string()))?;
        let mut r = Self::from_value(&v)?;
        r.sha256 = crate::provenance::sha256_hex(text.as_bytes());
        Ok(r)
    }

    /// The embedded registry (parsed once).
    #[cfg(feature = "yaml")]
    pub fn embedded() -> &'static KineticsRegistry {
        static CELL: std::sync::OnceLock<KineticsRegistry> = std::sync::OnceLock::new();
        CELL.get_or_init(|| {
            KineticsRegistry::from_yaml_str(EMBEDDED_YAML)
                .expect("embedded kinetics.yaml is valid (checked in CI)")
        })
    }

    /// Catalyst by id (Python `get_catalyst`; `KeyError` -> [`EngineError::Domain`]).
    pub fn get(&self, id: &str) -> Result<&Catalyst, EngineError> {
        self.catalysts.iter().find(|c| c.id == id).ok_or_else(|| {
            EngineError::Domain(format!(
                "unknown catalyst_id {id:?}; known: {:?}",
                self.catalysts
                    .iter()
                    .map(|c| c.id.as_str())
                    .collect::<Vec<_>>()
            ))
        })
    }

    /// All catalysts (original section first).
    pub fn catalysts(&self) -> &[Catalyst] {
        &self.catalysts
    }

    fn params(
        &self,
        c: &Catalyst,
        ov: Option<&Overrides>,
    ) -> Result<BTreeMap<String, f64>, EngineError> {
        let mut p = c.params.clone();
        if let Some(ov) = ov {
            for (k, v) in ov {
                if !p.contains_key(k) {
                    return Err(EngineError::Domain(format!(
                        "param_overrides: {k:?} is not a parameter of {} (parameters: {:?})",
                        c.id,
                        c.params.keys().collect::<Vec<_>>()
                    )));
                }
                p.insert(k.clone(), *v);
            }
        }
        Ok(p)
    }
}

fn par(p: &BTreeMap<String, f64>, k: &str) -> Result<f64, EngineError> {
    p.get(k)
        .copied()
        .ok_or_else(|| EngineError::data(DATA_FILE, format!("parameter {k} missing")))
}

/// Value of `name` in the partial-pressure list (Python `p_bar.get(name, 0.0)`).
pub fn get_p(p: &[(&str, f64)], name: &str) -> f64 {
    p.iter().find(|x| x.0 == name).map(|x| x.1).unwrap_or(0.0)
}

/// `Q = p_N2^0.5 p_H2^1.5 / p_NH3` (bar, per mol NH3); infinity for `p_NH3 <= 0`.
pub fn reaction_quotient(p: &[(&str, f64)]) -> f64 {
    let pn = get_p(p, "NH3");
    if pn <= 0.0 {
        return f64::INFINITY;
    }
    py_max(get_p(p, "N2"), 0.0).powf(0.5) * py_max(get_p(p, "H2"), 0.0).powf(1.5) / pn
}

/// Keq of the Temkin-Pyzhev law per mol NH3 (Python `kum_keq`).
pub fn kum_keq(reg: &KineticsRegistry, t_k: f64, basis: KeqBasis) -> Result<f64, EngineError> {
    match basis {
        KeqBasis::Published => {
            let [a0, a1, a2, a3] = reg.kum_dgr_coefficients_j.ok_or_else(|| {
                EngineError::data(DATA_FILE, "ru_kum_temkin_pyzhev dGr_coefficients_J missing")
            })?;
            let dg = a0 + a1 * t_k + a2 * t_k.powf(2.0) + a3 * t_k.powf(3.0);
            Ok((-dg / (reg.r_kin_j_mol_k * t_k)).exp().sqrt())
        }
        KeqBasis::AmcraxThermo => equilibrium_constant(t_k),
    }
}

/// Takahashi rate constants (Python `takahashi_constants`), mol s^-1 g^-1 and dimensionless.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct TakahashiConstants {
    pub k1: f64,
    pub k_minus1: f64,
    pub k2: f64,
    pub k3: f64,
    pub k4: f64,
    pub k_minus4: f64,
    #[serde(rename = "K1")]
    pub big_k1: f64,
    #[serde(rename = "K4")]
    pub big_k4: f64,
}

/// Python `takahashi_constants`.
pub fn takahashi_constants(
    reg: &KineticsRegistry,
    catalyst_id: &str,
    t_k: f64,
    overrides: Option<&Overrides>,
) -> Result<TakahashiConstants, EngineError> {
    let c = reg.get(catalyst_id)?;
    let p = reg.params(c, overrides)?;
    let rt = reg.r_kin_j_mol_k * t_k;
    let k1 = par(&p, "A1")?;
    let k2 = par(&p, "A2")? * (-par(&p, "Ea2")? * 1e3 / rt).exp();
    let k3 = par(&p, "A3")? * (-par(&p, "Ea3")? * 1e3 / rt).exp();
    let k4 = par(&p, "A4")? * (-par(&p, "Ea4")? * 1e3 / rt).exp();
    let big_k1 = par(&p, "A5")? * (-par(&p, "Ea5")? * 1e3 / rt).exp();
    let big_k4 = par(&p, "A6")? * (-par(&p, "Ea4")? * 1e3 / rt).exp();
    Ok(TakahashiConstants {
        k1,
        k_minus1: k1 / big_k1,
        k2,
        k3,
        k4,
        k_minus4: k4 / big_k4,
        big_k1,
        big_k4,
    })
}

/// Quasi-steady-state coverages and `r_NH3 = r2` (Python `takahashi_coverages`).
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct Coverages {
    pub theta_s: f64,
    #[serde(rename = "theta_NH3")]
    pub theta_nh3: f64,
    #[serde(rename = "theta_N")]
    pub theta_n: f64,
    #[serde(rename = "theta_H")]
    pub theta_h: f64,
    pub r_mol_per_g_s: f64,
    /// brentq iterations (0 when the guard `resid(0) <= 0` applies).
    #[serde(skip)]
    pub iterations: u32,
    #[serde(skip)]
    pub function_calls: u32,
}

/// Python `takahashi_coverages`: site balance solved for `ln theta_s` by brentq on [-300, 0]
/// (xtol 1e-14, rtol 1e-13, maxiter 500).
pub fn takahashi_coverages(
    reg: &KineticsRegistry,
    catalyst_id: &str,
    t_k: f64,
    y_nh3: f64,
    y_h2: f64,
    overrides: Option<&Overrides>,
) -> Result<Coverages, EngineError> {
    let c = takahashi_constants(reg, catalyst_id, t_k, overrides)?;
    let y_nh3 = py_max(y_nh3, 0.0);
    let y_h2 = py_max(y_h2, 0.0);
    let parts = |ths: f64| {
        let th_nh3 = c.k1 * y_nh3 * ths / (c.k_minus1 + c.k2 * ths.powf(3.0));
        let r2 = c.k2 * th_nh3 * ths.powf(3.0);
        let th_n = (r2 / (2.0 * c.k3)).sqrt();
        let th_h = ((1.5 * r2 + c.k_minus4 * y_h2 * ths.powf(2.0)) / c.k4).sqrt();
        (th_nh3, th_n, th_h, r2)
    };
    let resid = |u: f64| -> Result<f64, EngineError> {
        let ths = u.exp();
        let (a, b, h, _) = parts(ths);
        Ok(ths + a + b + h - 1.0)
    };
    let (u, it, calls) = if resid(0.0)? <= 0.0 {
        (0.0, 0, 0)
    } else {
        let opts = BrentOptions {
            xtol: 1e-14,
            rtol: 1e-13,
            maxiter: 500,
        };
        let r = brentq_try(resid, -300.0, 0.0, opts).map_err(|e| match e {
            BrentError::Function(e) => e,
            BrentError::SignError { fa, fb } => EngineError::Domain(format!(
                "f(a) and f(b) must have different signs (f(a) = {fa:e}, f(b) = {fb:e})"
            )),
            BrentError::NanValue { x, .. } => {
                EngineError::Domain(format!("the function value at x={x} is NaN"))
            }
            other => EngineError::Numerical(format!("Takahashi coverages: {other}")),
        })?;
        (r.x, r.iterations, r.function_calls)
    };
    let ths = u.exp();
    let (a, b, h, r2) = parts(ths);
    Ok(Coverages {
        theta_s: ths,
        theta_nh3: a,
        theta_n: b,
        theta_h: h,
        r_mol_per_g_s: r2,
        iterations: it,
        function_calls: calls,
    })
}

/// Python `lucentini_rate_mol_per_g_s` (published, irreversible), mol NH3 g^-1 s^-1.
pub fn lucentini_rate_mol_per_g_s(
    reg: &KineticsRegistry,
    catalyst_id: &str,
    t_k: f64,
    p: &[(&str, f64)],
    overrides: Option<&Overrides>,
) -> Result<f64, EngineError> {
    let c = reg.get(catalyst_id)?;
    let pr = reg.params(c, overrides)?;
    let rt = reg.r_kin_j_mol_k * t_k;
    let c_nh3 = py_max(get_p(p, "NH3"), 0.0) * 1e5 / rt;
    let c_h2 = py_max(get_p(p, "H2"), 0.0) * 1e5 / rt;
    let k = par(&pr, "k0")? * (-par(&pr, "Ek")? * 1e3 / rt).exp();
    let k1 = par(&pr, "K1")?;
    let den = 1.0 + k1 * c_nh3 + (c_h2 / par(&pr, "K4")?).sqrt();
    Ok(k * k1 * c_nh3 / den.powf(2.0))
}

/// A rate with the scale of the cancelling terms (for verification) and the brentq counters.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RateDetail {
    /// Net NH3 consumption rate, mol NH3 / (kg_cat s).
    pub rate: f64,
    /// Sum of the magnitudes of the terms whose difference is the rate (`|r|(1 + Q/K)` with the
    /// approach factor, `k (fwd + rev)` for Temkin-Pyzhev, `|r|` otherwise), same unit.
    pub scale: f64,
    pub iterations: u32,
    pub function_calls: u32,
}

/// Net NH3 consumption rate, mol NH3 / (kg_cat s) (Python `rate_mol_per_kgcat_s`).
pub fn rate_mol_per_kgcat_s(
    reg: &KineticsRegistry,
    catalyst_id: &str,
    t_k: f64,
    p: &[(&str, f64)],
    opts: RateOpts<'_>,
) -> Result<f64, EngineError> {
    Ok(rate_detail(reg, catalyst_id, t_k, p, opts)?.rate)
}

/// [`rate_mol_per_kgcat_s`] with the term scale and counters.
pub fn rate_detail(
    reg: &KineticsRegistry,
    catalyst_id: &str,
    t_k: f64,
    p: &[(&str, f64)],
    opts: RateOpts<'_>,
) -> Result<RateDetail, EngineError> {
    let d = reg.get(catalyst_id)?;
    if !d.usable {
        return Err(EngineError::Domain(format!(
            "catalyst {catalyst_id} is flagged usable=false"
        )));
    }
    let ptot = py_sum(p.iter().map(|x| py_max(x.1, 0.0)));
    if ptot <= 0.0 {
        return Err(EngineError::Domain("total pressure must be > 0".into()));
    }
    let zero = RateDetail {
        rate: 0.0,
        scale: 0.0,
        iterations: 0,
        function_calls: 0,
    };
    let approach = |r_g: f64| -> Result<(f64, f64), EngineError> {
        let use_it = opts.approach_factor.unwrap_or(reg.approach_default_on);
        if use_it {
            let qk = reaction_quotient(p) / equilibrium_constant(t_k)?;
            Ok((r_g * (1.0 - qk), r_g.abs() * (1.0 + qk.abs())))
        } else {
            Ok((r_g, r_g.abs()))
        }
    };
    match d.form {
        Form::TakahashiMicrokinetic => {
            let y_nh3 = py_max(get_p(p, "NH3"), 0.0) / ptot;
            let y_h2 = py_max(get_p(p, "H2"), 0.0) / ptot;
            if y_nh3 <= 0.0 {
                return Ok(zero);
            }
            let cov =
                takahashi_coverages(reg, catalyst_id, t_k, y_nh3, y_h2, opts.param_overrides)?;
            let (r_g, s) = approach(cov.r_mol_per_g_s)?;
            Ok(RateDetail {
                rate: r_g * reg.g_per_kg,
                scale: s * reg.g_per_kg,
                iterations: cov.iterations,
                function_calls: cov.function_calls,
            })
        }
        Form::TemkinPyzhev => {
            let pr = reg.params(d, opts.param_overrides)?;
            let (pn, ph) = (get_p(p, "NH3"), get_p(p, "H2"));
            let pn2 = py_max(get_p(p, "N2"), 0.0);
            if pn <= 0.0 || ph <= 0.0 {
                return Err(EngineError::Domain(
                    "Temkin-Pyzhev form is singular for p_NH3 <= 0 or p_H2 <= 0 (seed H2 in the reactor)"
                        .into(),
                ));
            }
            let beta = par(&pr, "beta")?;
            let k = par(&pr, "ko")? * (-par(&pr, "Ea")? / (reg.r_kin_j_mol_k * t_k)).exp();
            let keq = kum_keq(reg, t_k, opts.keq_basis)?;
            let ln_ratio = 2.0 * pn.ln() - 3.0 * ph.ln();
            let fwd = (beta * ln_ratio).exp();
            let rev = (pn2 / keq.powf(2.0)) * (-(1.0 - beta) * ln_ratio).exp();
            Ok(RateDetail {
                rate: k * (fwd - rev) * reg.g_per_kg,
                scale: k * (fwd.abs() + rev.abs()) * reg.g_per_kg,
                iterations: 0,
                function_calls: 0,
            })
        }
        Form::LhhwLucentini => {
            if py_max(get_p(p, "NH3"), 0.0) <= 0.0 {
                return Ok(zero);
            }
            let r_g = lucentini_rate_mol_per_g_s(reg, catalyst_id, t_k, p, opts.param_overrides)?;
            let (r_g, s) = approach(r_g)?;
            Ok(RateDetail {
                rate: r_g * reg.g_per_kg,
                scale: s * reg.g_per_kg,
                iterations: 0,
                function_calls: 0,
            })
        }
    }
}

#[cfg(all(test, feature = "yaml"))]
mod tests {
    use super::*;

    #[test]
    fn registry_and_rates() {
        let reg = KineticsRegistry::embedded();
        assert_eq!(reg.r_kin_j_mol_k, 8.314);
        assert_eq!(reg.catalysts().len(), 5);
        let p = [("NH3", 0.9), ("H2", 0.075), ("N2", 0.025)];
        let r = rate_mol_per_kgcat_s(
            reg,
            "ni_takahashi_microkinetic",
            723.15,
            &p,
            RateOpts::default(),
        )
        .unwrap();
        // stored browser test vector rate_tni_T723.15_P1
        assert!((r / 0.04660084059895399 - 1.0).abs() < 1e-12);
        assert!(rate_mol_per_kgcat_s(reg, "nope", 723.15, &p, RateOpts::default()).is_err());
        let mut ov = Overrides::new();
        ov.insert("A22".into(), 1.0);
        let o = RateOpts {
            param_overrides: Some(&ov),
            ..RateOpts::default()
        };
        assert!(rate_mol_per_kgcat_s(reg, "ni_takahashi_microkinetic", 723.15, &p, o).is_err());
    }
}
