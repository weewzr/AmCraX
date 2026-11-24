//! Separation and compression (stage 4): port of Python `separation/` - `params.py`,
//! `compression.py` (intercooled multi-stage compression, isentropic outlet from the NASA-7
//! entropy integral by Simpson's rule), `psa.py` (literature operating point applied as a
//! split), `membrane.py` (Pd-Ag membrane: Sieverts flux integrated along the area, pinch limit,
//! area search), `purification.py` (ISO 14687 evaluation, PSA recovery-purity relation, membrane
//! with finite N2 selectivity, area and selectivity searches, helpers), `slip.py` and
//! `compare.py`. Results are the JSON of the Python dicts and pydantic models.
//!
//! The membrane ODEs are integrated with Dormand-Prince 5(4) at `rtol = 1e-12` (Python: LSODA
//! at `rtol = 1e-10`), so the Rust values are closer to the exact solution than the Python ones
//! and the deviations measure the Python integration error.

use crate::error::EngineError;
use crate::odata::OValue;
use crate::process::result::{LHV_KJ_PER_MOL, SimulationResult, get_or, molar_mass};
use crate::pyops::{fmt_f, fmt_g, py_max, py_min, py_repr, py_sum};
use crate::species::Species;
use crate::thermo::nasa7::{R_J_MOL_K, species_cp_j_mol_k, species_enthalpy_kj_mol};
use amcrax_numerics::ode::{OdeOptions, dopri5};
use amcrax_numerics::roots::{BrentOptions, brentq_try};
use serde_json::{Map, Value, json};

/// `MODEL_LABEL`.
pub const MODEL_LABEL: &str = "reduced-order model";
/// Data file.
pub const DATA_FILE: &str = "backend/amcrax/data/separation.yaml";
/// The embedded data file (YAML).
pub const EMBEDDED_YAML: &str = include_str!("../../../../backend/amcrax/data/separation.yaml");
/// Tolerances of the Rust membrane integration.
pub const ODE_RTOL: f64 = 1e-12;
pub const ODE_ATOL: f64 = 1e-16;

/// Component flows in Python dict order.
pub type Flows = Vec<(String, f64)>;

/// A float as JSON, non-finite values as the strings `nan`, `inf`, `-inf` (as the golden tables).
pub fn jnf(x: f64) -> Value {
    if x.is_nan() {
        Value::String("nan".into())
    } else if x.is_infinite() {
        Value::String(if x > 0.0 { "inf" } else { "-inf" }.into())
    } else {
        serde_json::Number::from_f64(x)
            .map(Value::Number)
            .unwrap_or(Value::Null)
    }
}

fn jmap(m: &[(String, f64)]) -> Value {
    Value::Object(
        m.iter()
            .map(|(k, v)| (k.clone(), jnf(*v)))
            .collect::<Map<_, _>>(),
    )
}

/// `str(x)` of a YAML value as Python formats it.
pub fn py_str(v: &OValue) -> String {
    match v {
        OValue::Null => "None".into(),
        OValue::Bool(b) => if *b { "True" } else { "False" }.into(),
        OValue::Int(i) => i.to_string(),
        OValue::Float(f) => py_repr(*f),
        OValue::Str(s) => s.clone(),
        other => format!("{:?}", other.to_json()),
    }
}

fn dom(msg: impl Into<String>) -> EngineError {
    EngineError::Domain(msg.into())
}

/// `separation.yaml` (Python `params()`).
#[derive(Debug, Clone)]
pub struct SepParams {
    pub raw: OValue,
}

impl SepParams {
    /// Parse the embedded YAML.
    #[cfg(feature = "yaml")]
    pub fn embedded() -> &'static SepParams {
        static P: std::sync::OnceLock<SepParams> = std::sync::OnceLock::new();
        P.get_or_init(|| {
            SepParams::from_ovalue(OValue::from_yaml(DATA_FILE, EMBEDDED_YAML).unwrap_or_default())
        })
    }

    /// From the parsed YAML. The plain mapping key `n` of `membrane.flux_law` is read by
    /// serde-saphyr as the boolean `false` (key "False"), by PyYAML as the string "n"; the key is
    /// restored to "n" (the Python reading) so that the model finds the flux exponent.
    pub fn from_ovalue(mut raw: OValue) -> SepParams {
        if let OValue::Map(top) = &mut raw
            && let Some((_, OValue::Map(mem))) = top.iter_mut().find(|e| e.0 == "membrane")
            && let Some((_, OValue::Map(fl))) = mem.iter_mut().find(|e| e.0 == "flux_law")
            && !fl.iter().any(|e| e.0 == "n")
            && let Some(e) = fl.iter_mut().find(|e| e.0 == "False")
        {
            e.0 = "n".to_string();
        }
        SepParams { raw }
    }

    fn num(&self, path: &[&str]) -> Result<f64, EngineError> {
        self.raw.num(DATA_FILE, path)
    }

    /// `psa_point(id)`.
    pub fn psa_point(&self, id: &str) -> Result<&OValue, EngineError> {
        self.raw
            .at(&["psa", "operating_points"])
            .items()
            .iter()
            .find(|p| p.get("id").as_str() == Some(id))
            .ok_or_else(|| dom(format!("KeyError: unknown PSA operating point '{id}'")))
    }

    /// `permeability_set(id)` (default set when `None`; unusable sets are a `ValueError`).
    pub fn permeability_set(&self, id: Option<&str>) -> Result<&OValue, EngineError> {
        let m = self.raw.get("membrane");
        let id = match id {
            Some(i) => i.to_string(),
            None => m
                .get("default_permeability_set")
                .as_str()
                .unwrap_or("")
                .to_string(),
        };
        let s = m
            .get("permeability_sets")
            .items()
            .iter()
            .find(|s| s.get("id").as_str() == Some(id.as_str()))
            .ok_or_else(|| dom(format!("KeyError: unknown permeability set '{id}'")))?;
        if s.get("usable").as_bool() == Some(false) {
            return Err(dom(format!(
                "permeability set '{id}' is flagged not usable: {}",
                py_str(s.get("reason"))
            )));
        }
        Ok(s)
    }
}

/// `cite(d)`: "citekey p. X, locator" (or "assumption: rationale").
pub fn cite(d: &OValue) -> String {
    if d.get("source").as_str() == Some("assumption") {
        let r = match d.get("rationale") {
            OValue::Null => String::new(),
            v => py_str(v),
        };
        return format!("assumption: {}", r.trim());
    }
    format!(
        "{} p. {}, {}",
        py_str(d.get("citekey")),
        py_str(d.get("page")),
        py_str(d.get("locator"))
    )
}

fn sp(name: &str) -> Result<Species, EngineError> {
    Species::from_name(name).ok_or_else(|| dom(format!("KeyError: unknown species {name}")))
}

// ============================================================================ compression.py
fn mix_cp(y: &[(Species, f64)], t: f64) -> Result<f64, EngineError> {
    let mut v = Vec::with_capacity(y.len());
    for &(s, x) in y {
        if x > 0.0 {
            v.push(x * species_cp_j_mol_k(s, t)?);
        }
    }
    Ok(py_sum(v))
}

fn mix_h_j(y: &[(Species, f64)], t: f64) -> Result<f64, EngineError> {
    let mut v = Vec::with_capacity(y.len());
    for &(s, x) in y {
        if x > 0.0 {
            v.push(x * species_enthalpy_kj_mol(s, t)?);
        }
    }
    Ok(1000.0 * py_sum(v))
}

fn mix_s_int(y: &[(Species, f64)], t1: f64, t2: f64) -> Result<f64, EngineError> {
    let n = 40usize;
    let h = (t2 - t1) / n as f64;
    let mut tot = 0.0;
    for i in 0..=n {
        let t = t1 + i as f64 * h;
        let w = if i == 0 || i == n {
            1.0
        } else if i % 2 == 1 {
            4.0
        } else {
            2.0
        };
        tot += w * mix_cp(y, t)? / t;
    }
    Ok(tot * h / 3.0)
}

fn brent_default<F>(f: F, a: f64, b: f64) -> Result<f64, EngineError>
where
    F: FnMut(f64) -> Result<f64, EngineError>,
{
    brentq_try(f, a, b, BrentOptions::default())
        .map(|r| r.x)
        .map_err(crate::process::properties::brent_err)
}

/// `default_stages(P_in, P_out)`.
pub fn default_stages(p: &SepParams, p_in: f64, p_out: f64) -> Result<u32, EngineError> {
    let rmax = p.num(&["compression", "max_pressure_ratio_per_stage", "value"])?;
    if p_out <= p_in {
        return Ok(0);
    }
    let k = ((p_out / p_in).ln() / rmax.ln() - 1e-12).ceil();
    Ok((k as i64).max(1) as u32)
}

/// Result of [`compression_power_kw`].
#[derive(Debug, Clone, PartialEq)]
pub struct Compression {
    pub power_kw: f64,
    pub stages: u32,
    pub ratio: f64,
    pub t_out_k: f64,
    pub intercooler_kw: f64,
    pub eta: f64,
    pub note: &'static str,
}

impl Compression {
    /// The Python dict.
    pub fn to_json(&self) -> Value {
        json!({"power_kW": jnf(self.power_kw), "stages": self.stages, "pressure_ratio_per_stage": jnf(self.ratio),
               "T_out_stage_K": jnf(self.t_out_k), "intercooler_duty_kW": jnf(self.intercooler_kw), "eta": jnf(self.eta),
               "notes": [self.note]})
    }
}

/// `compression_power_kW(n, composition, T_in, P_in, P_out, stages, eta, cp_J_molK)`.
#[allow(clippy::too_many_arguments)]
pub fn compression_power_kw(
    p: &SepParams,
    n_kmol_h: f64,
    composition: &[(Species, f64)],
    t_in_k: f64,
    p_in: f64,
    p_out: f64,
    stages: Option<i64>,
    eta: Option<f64>,
    cp_j_mol_k: Option<f64>,
) -> Result<Compression, EngineError> {
    let eta = match eta {
        Some(e) => e,
        None => p.num(&["compression", "isentropic_efficiency", "default"])?,
    };
    if !(0.0 < eta && eta <= 1.0) {
        return Err(dom("eta must be in (0, 1]"));
    }
    if p_out <= p_in || n_kmol_h <= 0.0 {
        return Ok(Compression {
            power_kw: 0.0,
            stages: 0,
            ratio: 1.0,
            t_out_k: t_in_k,
            intercooler_kw: 0.0,
            eta,
            note: "no compression required",
        });
    }
    let stages = match stages {
        Some(s) => s,
        None => default_stages(p, p_in, p_out)? as i64,
    };
    if stages < 1 {
        return Err(dom("stages must be >= 1"));
    }
    let tot = py_sum(composition.iter().map(|x| x.1));
    let y: Vec<(Species, f64)> = composition
        .iter()
        .filter(|x| x.1 > 0.0)
        .map(|(s, v)| (*s, v / tot))
        .collect();
    let r = (p_out / p_in).powf(1.0 / stages as f64);
    let n_mol_s = n_kmol_h / 3.6;
    let (dh, t2) = if let Some(cp) = cp_j_mol_k {
        let t2s = t_in_k * r.powf(R_J_MOL_K / cp);
        let dh_s = cp * (t2s - t_in_k);
        let dh = dh_s / eta;
        (dh, t_in_k + dh / cp)
    } else {
        let target = R_J_MOL_K * r.ln();
        let t2s = brent_default(
            |t| Ok(mix_s_int(&y, t_in_k, t)? - target),
            t_in_k,
            t_in_k * r.powf(0.7) + 50.0,
        )?;
        let dh_s = mix_h_j(&y, t2s)? - mix_h_j(&y, t_in_k)?;
        let dh = dh_s / eta;
        let h_target = mix_h_j(&y, t_in_k)? + dh;
        let hi = t_in_k + 3.0 * dh / mix_cp(&y, t_in_k)? + 50.0;
        let t2 = brent_default(|t| Ok(mix_h_j(&y, t)? - h_target), t_in_k, hi)?;
        (dh, t2)
    };
    let w = stages as f64 * n_mol_s * dh / 1000.0;
    Ok(Compression {
        power_kw: w,
        stages: stages as u32,
        ratio: r,
        t_out_k: t2,
        intercooler_kw: -w,
        eta,
        note: "reduced-order model: ideal gas, equal stage ratios, ideal intercooling to T_in",
    })
}

// ============================================================================ psa.py
/// Optional arguments of [`psa_performance`].
#[derive(Debug, Clone, PartialEq)]
pub struct PsaArgs {
    pub tailgas_pressure_bar: Option<f64>,
    pub target_purity: Option<f64>,
    pub basis: String,
    pub h2_recovery: Option<f64>,
    pub required_feed_pressure_bar: Option<f64>,
    pub feed_temperature_k: f64,
    pub compressor_eta: Option<f64>,
    pub compressor_stages: Option<i64>,
}

impl Default for PsaArgs {
    fn default() -> Self {
        PsaArgs {
            tailgas_pressure_bar: None,
            target_purity: None,
            basis: "cho2026_5A".into(),
            h2_recovery: None,
            required_feed_pressure_bar: None,
            feed_temperature_k: 313.15,
            compressor_eta: None,
            compressor_stages: None,
        }
    }
}

/// `{k: float(v) for k, v in d.items() if v}` with species keys.
fn nonzero(feed: &[(String, f64)]) -> Vec<(String, f64)> {
    feed.iter().filter(|x| x.1 != 0.0).cloned().collect()
}

fn to_species(m: &[(String, f64)]) -> Result<Vec<(Species, f64)>, EngineError> {
    m.iter().map(|(k, v)| Ok((sp(k)?, *v))).collect()
}

/// `psa_performance(feed, feed_pressure, ...)`: the JSON of `PSAResult`.
pub fn psa_performance(
    p: &SepParams,
    feed_kmol_h: &[(String, f64)],
    feed_pressure_bar: f64,
    a: &PsaArgs,
) -> Result<Value, EngineError> {
    let pp = p.raw.get("psa");
    let mut notes = vec![format!(
        "{MODEL_LABEL}: literature operating point applied as a fixed split; not a designed PSA"
    )];
    let baseline = a.basis == "amcrax_baseline";
    let (pt_rec, pt_pur, pt_fp, pt_tp, src) = if baseline {
        let b = pp.get("amcrax_baseline");
        (
            b.get("recovery").clone(),
            OValue::Null,
            OValue::Null,
            OValue::Null,
            cite(b),
        )
    } else {
        let pt = p.psa_point(&a.basis)?;
        (
            pt.get("recovery").clone(),
            pt.get("purity").clone(),
            pt.get("feed_pressure_bar").clone(),
            pt.get("tail_pressure_bar").clone(),
            cite(pt),
        )
    };
    let rec = match a.h2_recovery {
        Some(r) => r,
        None => pt_rec.as_f64().ok_or_else(|| dom("recovery missing"))?,
    };
    if a.h2_recovery.is_some() {
        notes.push(format!(
            "H2 recovery {} given by caller (overrides basis value {})",
            py_repr(rec),
            py_str(&pt_rec)
        ));
    }
    let mut purity = a.target_purity.or(pt_pur.as_f64());
    if purity.is_none() {
        let spec = pp.get("product_purity_spec");
        let v = spec
            .get("value")
            .as_f64()
            .ok_or_else(|| dom("purity spec"))?;
        purity = Some(v);
        notes.push(format!(
            "basis reports no purity; product purity set to spec {} ({})",
            py_repr(v),
            cite(spec)
        ));
    }
    let purity = purity.unwrap_or(f64::NAN);
    if let (Some(tp), Some(pr)) = (a.target_purity, pt_pur.as_f64())
        && tp > pr
    {
        notes.push(format!(
            "WARNING: target purity {} exceeds the purity reported with this recovery ({}); recovery at higher purity is not known from the source",
            py_repr(tp),
            py_repr(pr)
        ));
    }
    if !((0.0..=1.0).contains(&rec) && 0.0 < purity && purity <= 1.0) {
        return Err(dom("recovery must be in [0,1], purity in (0,1]"));
    }
    let feed = nonzero(feed_kmol_h);
    let h2_in = get_or(&feed, "H2", 0.0);
    let h2_p = rec * h2_in;
    let floor = h2_p * (1.0 - purity) / purity;
    let n2_p = py_min(floor, get_or(&feed, "N2", 0.0));
    if n2_p < h2_p * (1.0 - purity) / purity - 1e-12 {
        notes.push(
            "feed N2 insufficient to reach purity floor; product purity is higher than target"
                .into(),
        );
    }
    let product = vec![("H2".to_string(), h2_p), ("N2".to_string(), n2_p)];
    let tail: Vec<(String, f64)> = feed
        .iter()
        .map(|(k, v)| (k.clone(), py_max(v - get_or(&product, k, 0.0), 0.0)))
        .collect();
    let ttot = py_sum(tail.iter().map(|x| x.1));
    let y_tail: Vec<(String, f64)> = if ttot > 0.0 {
        tail.iter().map(|(k, v)| (k.clone(), v / ttot)).collect()
    } else {
        vec![]
    };
    let truthy = |v: &OValue| v.as_f64().filter(|x| *x != 0.0);
    let (req, req_src) = match a.required_feed_pressure_bar {
        None => match truthy(&pt_fp) {
            Some(v) => (v, src.clone()),
            None => {
                let fr = pp.get("feed_pressure_requirement_bar");
                (
                    fr.get("default")
                        .as_f64()
                        .ok_or_else(|| dom("feed pressure requirement"))?,
                    cite(fr),
                )
            }
        },
        Some(v) => (v, "caller input".to_string()),
    };
    let tailgas = match a.tailgas_pressure_bar {
        Some(v) => v,
        None => {
            let v = truthy(&pt_tp).unwrap_or(1.2);
            if truthy(&pt_tp).is_none() {
                notes.push(
                    "tail-gas pressure 1.2 bar taken from cho2026nickel p. 6 Table 3 (labelled 'Assumed' there)".into(),
                );
            }
            v
        }
    };
    let p_ads = py_max(feed_pressure_bar, req);
    let mut comp = (0.0, 0u32, None::<f64>);
    if feed_pressure_bar < req {
        let ftot = py_sum(feed.iter().map(|x| x.1));
        let c = compression_power_kw(
            p,
            ftot,
            &to_species(&feed)?,
            a.feed_temperature_k,
            feed_pressure_bar,
            req,
            a.compressor_stages,
            a.compressor_eta,
            None,
        )?;
        notes.push(format!(
            "feed {} bar < required {} bar: cracked-gas compression {} kW ({} stages, eta {})",
            fmt_f(feed_pressure_bar, 2),
            fmt_f(req, 2),
            fmt_f(c.power_kw, 1),
            c.stages,
            py_repr(c.eta)
        ));
        comp = (c.power_kw, c.stages, Some(c.eta));
    }
    let kg_h2 = h2_p * molar_mass(Species::H2);
    let loss = h2_in - h2_p;
    let nh3_ppm = 1e6 * get_or(&product, "NH3", 0.0) / py_max(h2_p + n2_p, 1e-30);
    Ok(json!({
        "model": MODEL_LABEL, "basis": a.basis, "basis_source": src, "h2_recovery": jnf(rec),
        "h2_purity_mole_frac": jnf(if h2_p > 0.0 { h2_p / (h2_p + n2_p) } else { 0.0 }),
        "feed_kmol_h": jmap(&feed), "product_kmol_h": jmap(&product), "tailgas_kmol_h": jmap(&tail),
        "tailgas_mole_frac": jmap(&y_tail), "feed_pressure_bar": jnf(feed_pressure_bar),
        "required_feed_pressure_bar": jnf(req), "required_feed_pressure_source": req_src,
        "tailgas_pressure_bar": jnf(tailgas), "pressure_ratio_feed_to_tail": jnf(p_ads / tailgas),
        "compression_power_kW": jnf(comp.0), "compression_stages": comp.1,
        "compression_eta": comp.2.map(jnf).unwrap_or(Value::Null), "product_h2_kg_h": jnf(kg_h2),
        "specific_energy_kWh_per_kgH2": jnf(if kg_h2 > 0.0 { comp.0 / kg_h2 } else { f64::NAN }),
        "h2_loss_kmol_h": jnf(loss), "h2_loss_lhv_kW": jnf(loss * LHV_KJ_PER_MOL[0].1 / 3.6),
        "nh3_in_product_ppm": jnf(nh3_ppm), "notes": notes,
    }))
}

// ============================================================================ membrane.py
/// `permeance(T, set, thickness)`: Pe/delta, mol m-2 s-1 Pa-n.
pub fn permeance(
    p: &SepParams,
    t_k: f64,
    set_id: Option<&str>,
    thickness_m: Option<f64>,
) -> Result<f64, EngineError> {
    let s = p.permeability_set(set_id)?;
    let d = match thickness_m {
        Some(t) => t,
        None => {
            s.get("thickness_um")
                .as_f64()
                .ok_or_else(|| dom("thickness"))?
                * 1e-6
        }
    };
    let pe0 = s
        .get("Pe0_mol_m_s_Pa05")
        .as_f64()
        .ok_or_else(|| dom("Pe0"))?;
    let ea = s.get("Ea_kJ_mol").as_f64().ok_or_else(|| dom("Ea"))?;
    let pe = pe0 * (-ea * 1000.0 / (R_J_MOL_K * t_k)).exp();
    Ok(pe / d)
}

/// `sieverts_flux(p_ret, p_perm, permeance, n, multiplier)` (no back-permeation).
pub fn sieverts_flux(p_ret: f64, p_perm: f64, k: f64, n: f64, mult: f64) -> f64 {
    py_max(
        0.0,
        mult * k * (py_max(p_ret, 0.0).powf(n) - py_max(p_perm, 0.0).powf(n)),
    )
}

/// Options of [`membrane_separator`].
#[derive(Debug, Clone, PartialEq)]
pub struct MembraneArgs {
    pub permeate_pressure_bar: Option<f64>,
    pub t_k: Option<f64>,
    pub permeability: Option<String>,
    pub thickness_m: Option<f64>,
    pub n_exponent: Option<f64>,
    pub flux_multiplier: f64,
    pub n_profile: usize,
}

impl Default for MembraneArgs {
    fn default() -> Self {
        MembraneArgs {
            permeate_pressure_bar: None,
            t_k: None,
            permeability: None,
            thickness_m: None,
            n_exponent: None,
            flux_multiplier: 1.0,
            n_profile: 41,
        }
    }
}

/// `membrane_separator(feed, area, feed_pressure, ...)`: the JSON of `MembraneResult`.
pub fn membrane_separator(
    p: &SepParams,
    feed_kmol_h: &[(String, f64)],
    area_m2: f64,
    feed_pressure_bar: f64,
    a: &MembraneArgs,
) -> Result<Value, EngineError> {
    let m = p.raw.get("membrane");
    let t_k = match a.t_k {
        Some(t) => t,
        None => {
            m.at(&["default_temperature_C", "value"])
                .as_f64()
                .ok_or_else(|| dom("T"))?
                + 273.15
        }
    };
    let p_perm_bar = match a.permeate_pressure_bar {
        Some(v) => v,
        None => m
            .at(&["default_permeate_pressure_bar", "value"])
            .as_f64()
            .ok_or_else(|| dom("P_perm"))?,
    };
    let n = match a.n_exponent {
        Some(v) => v,
        None => m.at(&["flux_law", "n"]).as_f64().ok_or_else(|| dom("n"))?,
    };
    if area_m2 < 0.0 {
        return Err(dom("area must be >= 0"));
    }
    let pset = p.permeability_set(a.permeability.as_deref())?;
    let k = permeance(p, t_k, a.permeability.as_deref(), a.thickness_m)?;
    let feed = nonzero(feed_kmol_h);
    let others = py_sum(feed.iter().filter(|x| x.0 != "H2").map(|x| x.1));
    let h2_in = get_or(&feed, "H2", 0.0) / 3.6;
    let p_ret = feed_pressure_bar * 1e5;
    let p_perm = p_perm_bar * 1e5;
    let oth = others / 3.6;
    let mult = a.flux_multiplier;
    let flux = |nh2: f64| -> f64 {
        let y = if nh2 + oth > 0.0 {
            nh2 / (nh2 + oth)
        } else {
            0.0
        };
        sieverts_flux(y * p_ret, p_perm, k, n, mult)
    };
    let grid = crate::pyops::linspace(0.0, area_m2, a.n_profile.max(2));
    let nh2: Vec<f64> = if area_m2 > 0.0 && h2_in > 0.0 {
        let mut rhs = |_t: f64, x: &[f64; 1], dx: &mut [f64; 1]| -> Result<(), String> {
            dx[0] = -flux(py_max(x[0], 0.0));
            Ok(())
        };
        let sol = dopri5(
            &mut rhs,
            (0.0, area_m2),
            [h2_in],
            Some(&grid),
            &mut [],
            &OdeOptions::new(ODE_RTOL, ODE_ATOL),
        )
        .map_err(|e| EngineError::Integration(format!("{e:?}")))?;
        sol.y.iter().map(|y| py_max(y[0], 0.0)).collect()
    } else {
        vec![h2_in; grid.len()]
    };
    let mut prof = Vec::with_capacity(grid.len());
    for (aa, x) in grid.iter().zip(nh2.iter()) {
        let y = if x + oth > 0.0 { x / (x + oth) } else { 0.0 };
        prof.push(json!({"area_m2": jnf(*aa), "h2_retentate_kmol_h": jnf(x * 3.6), "y_h2_retentate": jnf(y),
                         "flux_mol_m2_s": jnf(flux(*x)), "recovery": jnf(if h2_in != 0.0 { 1.0 - x / h2_in } else { 0.0 })}));
    }
    let h2_out = nh2[nh2.len() - 1] * 3.6;
    let h2_feed = get_or(&feed, "H2", 0.0);
    let h2_perm = h2_feed - h2_out;
    let mut ret = feed.clone();
    match ret.iter_mut().find(|x| x.0 == "H2") {
        Some(x) => x.1 = h2_out,
        None => ret.push(("H2".into(), h2_out)),
    }
    let rtot = py_sum(ret.iter().map(|x| x.1));
    let y_p = p_perm / p_ret;
    let rmax = if y_p >= 1.0 {
        0.0
    } else {
        let nh2_p = y_p / (1.0 - y_p) * oth;
        if h2_in != 0.0 {
            py_max(0.0, 1.0 - nh2_p / h2_in)
        } else {
            0.0
        }
    };
    let t_c = t_k - 273.15;
    let win = m.get("operating_window_C");
    let thick = match a.thickness_m.filter(|v| *v != 0.0) {
        Some(t) => t,
        None => pset.get("thickness_um").as_f64().unwrap_or(f64::NAN) * 1e-6,
    };
    let mut notes = vec![
        format!(
            "{MODEL_LABEL}: isothermal, isobaric plug flow, ideal Sieverts flux, pure-H2 permeate"
        ),
        format!(
            "permeability {}: Pe0 {} mol/(m s Pa^0.5), Ea {} kJ/mol, {} um ({})",
            py_str(pset.get("id")),
            fmt_g(pset.get("Pe0_mol_m_s_Pa05").as_f64().unwrap_or(f64::NAN), 6),
            py_str(pset.get("Ea_kJ_mol")),
            fmt_g(thick * 1e6, 6),
            cite(pset)
        ),
    ];
    let (wmin, wmax) = (
        win.get("min").as_f64().unwrap_or(f64::NAN),
        win.get("max").as_f64().unwrap_or(f64::NAN),
    );
    let in_win = wmin <= t_c && t_c <= wmax;
    if !in_win {
        notes.push(format!(
            "WARNING: {} degC outside Pd window {}-{} degC ({})",
            fmt_f(t_c, 0),
            py_str(win.get("min")),
            py_str(win.get("max")),
            cite(win)
        ));
    }
    if mult != 1.0 {
        notes.push(format!(
            "flux multiplier {} applied (concentration-polarisation sensitivity)",
            py_repr(mult)
        ));
    }
    let ret_frac: Vec<(String, f64)> = if rtot > 0.0 {
        ret.iter().map(|(k, v)| (k.clone(), v / rtot)).collect()
    } else {
        vec![]
    };
    Ok(json!({
        "model": MODEL_LABEL, "permeability_set": py_str(pset.get("id")), "permeability_source": cite(pset),
        "T_K": jnf(t_k), "feed_pressure_bar": jnf(feed_pressure_bar), "permeate_pressure_bar": jnf(p_perm_bar),
        "area_m2": jnf(area_m2), "n_exponent": jnf(n), "flux_multiplier": jnf(mult), "permeance_mol_m2_s_Pa_n": jnf(k),
        "feed_kmol_h": jmap(&feed), "permeate_kmol_h": {"H2": jnf(h2_perm)}, "retentate_kmol_h": jmap(&ret),
        "retentate_mole_frac": jmap(&ret_frac),
        "h2_recovery": jnf(if h2_feed != 0.0 { h2_perm / h2_feed } else { 0.0 }),
        "max_recovery_at_pinch": jnf(rmax), "h2_purity_mole_frac": 1.0,
        "purity_basis": "infinite selectivity assumed (richard2024technoeconomic p. 7); measured Pd-Ag in NH3 service >99.999 % H2, NH3 < 0.01 ppm (cechetto2023membrane pp. 15, 17, Tables 8, 10)",
        "product_h2_kg_h": jnf(h2_perm * molar_mass(Species::H2)), "h2_loss_kmol_h": jnf(h2_out),
        "h2_loss_lhv_kW": jnf(h2_out * LHV_KJ_PER_MOL[0].1 / 3.6), "in_pd_window": in_win, "profile": prof, "notes": notes,
    }))
}

fn recovery_of(v: &Value) -> f64 {
    v["h2_recovery"].as_f64().unwrap_or(f64::NAN)
}

/// `area_for_recovery(feed, target, P_feed, P_perm, T)`: area (m2) or `None` above the pinch.
pub fn area_for_recovery(
    p: &SepParams,
    feed: &[(String, f64)],
    target: f64,
    feed_pressure_bar: f64,
    a: &MembraneArgs,
) -> Result<Option<f64>, EngineError> {
    let r0 = membrane_separator(p, feed, 0.0, feed_pressure_bar, a)?;
    if target >= r0["max_recovery_at_pinch"].as_f64().unwrap_or(f64::NAN) {
        return Ok(None);
    }
    let a2 = MembraneArgs {
        n_profile: 2,
        ..a.clone()
    };
    let mut hi = 10.0;
    while recovery_of(&membrane_separator(p, feed, hi, feed_pressure_bar, &a2)?) < target {
        hi *= 2.0;
        if hi > 1e7 {
            return Ok(None);
        }
    }
    let r = brentq_try(
        |x| Ok(recovery_of(&membrane_separator(p, feed, x, feed_pressure_bar, &a2)?) - target),
        0.0,
        hi,
        BrentOptions::with_xtol(1e-6),
    )
    .map_err(crate::process::properties::brent_err)?;
    Ok(Some(r.x))
}

// ============================================================================ purification.py
/// `ISO_SOURCE`.
pub const ISO_SOURCE: &str = "ISO 14687:2019 Hydrogen fuel quality - Product specification, first edition 2019-11; Table 2 (grade D), Table 3 (grade E), Table 4 (grades A-C); text read from https://consultations.standards.govt.nz/draft-standards/hydrogen-standards-pc/user_uploads/dz-14687.pdf, accessed 2026-11-23";
const MODELLED_SPECIES: [&str; 3] = ["NH3", "N2", "H2O"];

struct Grade {
    name: &'static str,
    index_min_pct: f64,
    total_max_ppm: f64,
    limits: &'static [(&'static str, f64)],
    other: &'static [&'static str],
}

fn grade(g: &str) -> Option<Grade> {
    Some(match g {
        "D" => Grade {
            name: "ISO 14687:2019 Type I/II grade D (PEM fuel cell road vehicles)",
            index_min_pct: 99.97,
            total_max_ppm: 300.0,
            limits: &[
                ("H2O", 5.0),
                ("THC_ex_CH4", 2.0),
                ("CH4", 100.0),
                ("O2", 5.0),
                ("He", 300.0),
                ("N2", 300.0),
                ("Ar", 300.0),
                ("CO2", 2.0),
                ("CO", 0.2),
                ("S_total", 0.004),
                ("HCHO", 0.2),
                ("HCOOH", 0.2),
                ("NH3", 0.1),
                ("halogenated", 0.05),
            ],
            other: &["particulate_mg_per_kg", "CO_HCHO_HCOOH_sum_ppm"],
        },
        "E3" => Grade {
            name: "ISO 14687:2019 Type I grade E category 3 (PEM stationary, gaseous hydrogen)",
            index_min_pct: 99.9,
            total_max_ppm: 1000.0,
            limits: &[
                ("THC_ex_CH4", 2.0),
                ("CH4", 100.0),
                ("O2", 50.0),
                ("N2+Ar+He", 1000.0),
                ("CO2", 2.0),
                ("CO", 0.2),
                ("S_total", 0.004),
                ("HCHO", 0.2),
                ("HCOOH", 0.2),
                ("NH3", 0.1),
                ("halogenated", 0.05),
            ],
            other: &["water", "particulate_mg_per_kg"],
        },
        "B" => Grade {
            name: "ISO 14687:2019 Type I grade B (Table 4, applications other than PEM fuel cells), used here as the industrial 99.9 % hydrogen specification",
            index_min_pct: 99.9,
            total_max_ppm: 1000.0,
            limits: &[],
            other: &["note"],
        },
        "A" => Grade {
            name: "ISO 14687:2019 Type I grade A (Table 4, gaseous hydrogen for combustion engines and other non-PEM uses)",
            index_min_pct: 98.0,
            total_max_ppm: 20000.0,
            limits: &[],
            other: &["note"],
        },
        _ => return None,
    })
}

/// `evaluate_product(y_ppm, grade, h2_frac, nh3_basis)`.
pub fn evaluate_product(
    y_ppm: &[(String, f64)],
    g: &str,
    h2_frac: Option<f64>,
    nh3_basis: &str,
) -> Result<Value, EngineError> {
    let gd = grade(g).ok_or_else(|| dom(format!("KeyError: '{g}'")))?;
    let nonh2 = py_sum(MODELLED_SPECIES.iter().map(|s| get_or(y_ppm, s, 0.0)));
    let index = match h2_frac {
        None => 100.0 - nonh2 / 1e4,
        Some(f) => 100.0 * f,
    };
    let mut checks = vec![
        json!({"item": "hydrogen fuel index", "value": jnf(index), "limit": jnf(gd.index_min_pct), "unit": "% min",
               "pass": index >= gd.index_min_pct - 1e-12, "kind": "overall"}),
        json!({"item": "total non-hydrogen gases (modelled species)", "value": jnf(nonh2), "limit": jnf(gd.total_max_ppm),
               "unit": "umol/mol max", "pass": nonh2 <= gd.total_max_ppm + 1e-12, "kind": "overall"}),
    ];
    let lim = |k: &str| gd.limits.iter().find(|x| x.0 == k).map(|x| x.1);
    let mut evaluated: Vec<&str> = Vec::new();
    for spn in MODELLED_SPECIES {
        let mut key = if lim(spn).is_some() { Some(spn) } else { None };
        if spn == "N2" && lim("N2").is_none() && lim("N2+Ar+He").is_some() {
            key = Some("N2+Ar+He");
        }
        let Some(key) = key else { continue };
        evaluated.push(key);
        let v = get_or(y_ppm, spn, 0.0);
        let l = lim(key).unwrap_or(f64::NAN);
        let item = if key == spn {
            spn.to_string()
        } else {
            format!("{spn} (counted in {key}; Ar, He not modelled)")
        };
        let mut c = json!({"item": item, "value": jnf(v), "limit": jnf(l), "unit": "umol/mol max",
                           "pass": v <= l + 1e-12, "kind": "contaminant"});
        if spn == "NH3" {
            c["value_basis"] = Value::String(nh3_basis.into());
        }
        checks.push(c);
    }
    let mut not_eval: Vec<String> = gd
        .limits
        .iter()
        .filter(|(k, _)| !evaluated.contains(k))
        .map(|(k, _)| k.to_string())
        .collect();
    not_eval.extend(
        gd.other
            .iter()
            .filter(|k| **k != "note")
            .map(|k| k.to_string()),
    );
    if gd.other.contains(&"note") {
        not_eval.push("per-species rows not applied (see grade note)".into());
    }
    let missing: Vec<&str> = MODELLED_SPECIES
        .iter()
        .copied()
        .filter(|s| lim(s).is_none() && *s != "N2")
        .collect();
    let all_pass = checks.iter().all(|c| c["pass"].as_bool() == Some(true));
    Ok(
        json!({"grade": g, "grade_name": gd.name, "source": ISO_SOURCE, "checks": checks, "all_modelled_pass": all_pass,
              "not_evaluated": not_eval, "modelled_species_without_limit_in_grade": missing,
              "meets_within_model_scope": all_pass}),
    )
}

fn h2_of(feed: &[(String, f64)]) -> Result<f64, EngineError> {
    feed.iter()
        .find(|x| x.0 == "H2")
        .map(|x| x.1)
        .ok_or_else(|| dom("KeyError: 'H2'"))
}

/// `psa_tail_h2_fraction_from_point(feed, recovery, purity)`.
pub fn psa_tail_h2_fraction_from_point(
    feed: &[(String, f64)],
    recovery: f64,
    purity: f64,
) -> Result<f64, EngineError> {
    let h2 = h2_of(feed)?;
    let h2p = recovery * h2;
    let n2p = py_min(h2p * (1.0 - purity) / purity, get_or(feed, "N2", 0.0));
    let tail_other = py_sum(feed.iter().filter(|x| x.0 != "H2").map(|x| x.1)) - n2p;
    let h2t = h2 - h2p;
    Ok(h2t / (h2t + tail_other))
}

/// `psa_recovery_at_purity(feed, purity, y_tail_h2)`.
pub fn psa_recovery_at_purity(
    feed: &[(String, f64)],
    purity: f64,
    y_tail_h2: f64,
) -> Result<f64, EngineError> {
    let h2 = h2_of(feed)?;
    let other = py_sum(feed.iter().filter(|x| x.0 != "H2").map(|x| x.1));
    let q = (1.0 - purity) / purity;
    let k = y_tail_h2 / (1.0 - y_tail_h2);
    let mut x = (h2 - other * k) / (1.0 - q * k);
    let n2p = x * q;
    if n2p > get_or(feed, "N2", 0.0) {
        x = h2 - (other - get_or(feed, "N2", 0.0)) * k;
    }
    Ok(py_max(0.0, py_min(1.0, x / h2)))
}

/// `psa_split(feed, recovery, purity)`: (product, tail).
pub fn psa_split(
    feed: &[(String, f64)],
    recovery: f64,
    purity: f64,
) -> Result<(Flows, Flows), EngineError> {
    let h2p = recovery * h2_of(feed)?;
    let n2p = py_min(h2p * (1.0 - purity) / purity, get_or(feed, "N2", 0.0));
    let prod = vec![("H2".to_string(), h2p), ("N2".to_string(), n2p)];
    let tail = feed
        .iter()
        .map(|(k, v)| (k.clone(), v - get_or(&prod, k, 0.0)))
        .collect();
    Ok((prod, tail))
}

/// Options of [`membrane_with_leakage`].
#[derive(Debug, Clone, PartialEq)]
pub struct LeakArgs {
    pub alpha_h2_n2: f64,
    pub permeability: Option<String>,
    pub thickness_m: Option<f64>,
    pub flux_multiplier: f64,
    pub n: f64,
}

impl Default for LeakArgs {
    fn default() -> Self {
        LeakArgs {
            alpha_h2_n2: f64::INFINITY,
            permeability: None,
            thickness_m: None,
            flux_multiplier: 1.0,
            n: 0.5,
        }
    }
}

/// `membrane_with_leakage(feed, area, P_feed, P_perm, T, ...)`.
pub fn membrane_with_leakage(
    p: &SepParams,
    feed_kmol_h: &[(String, f64)],
    area_m2: f64,
    p_feed_bar: f64,
    p_perm_bar: f64,
    t_k: f64,
    a: &LeakArgs,
) -> Result<Value, EngineError> {
    let k = permeance(p, t_k, a.permeability.as_deref(), a.thickness_m)? * a.flux_multiplier;
    let dp_ref = 1e5_f64;
    let j_ref = k * dp_ref.powf(a.n);
    let l_n2 = if a.alpha_h2_n2.is_infinite() {
        0.0
    } else {
        j_ref / a.alpha_h2_n2 / dp_ref
    };
    let feed = nonzero(feed_kmol_h);
    let (h2_0, n2_0) = (
        get_or(&feed, "H2", 0.0) / 3.6,
        get_or(&feed, "N2", 0.0) / 3.6,
    );
    let inert = py_sum(
        feed.iter()
            .filter(|x| x.0 != "H2" && x.0 != "N2")
            .map(|x| x.1),
    ) / 3.6;
    let (pr, pp) = (p_feed_bar * 1e5, p_perm_bar * 1e5);
    let n = a.n;
    let (h2_r, n2_r) = if area_m2 > 0.0 {
        let mut rhs = |_t: f64, x: &[f64; 2], dx: &mut [f64; 2]| -> Result<(), String> {
            let (h2, n2) = (py_max(x[0], 0.0), py_max(x[1], 0.0));
            let tot = h2 + n2 + inert;
            let jh = sieverts_flux(h2 / tot * pr, pp, k, n, 1.0);
            let jn = l_n2 * (n2 / tot * pr);
            dx[0] = -jh;
            dx[1] = -jn;
            Ok(())
        };
        let sol = dopri5(
            &mut rhs,
            (0.0, area_m2),
            [h2_0, n2_0],
            None,
            &mut [],
            &OdeOptions::new(ODE_RTOL, ODE_ATOL),
        )
        .map_err(|e| EngineError::Integration(format!("{e:?}")))?;
        let last = sol.y[sol.y.len() - 1];
        (py_max(last[0], 0.0), py_max(last[1], 0.0))
    } else {
        (h2_0, n2_0)
    };
    let (h2_p, n2_p) = (h2_0 - h2_r, n2_0 - n2_r);
    let mut ret = feed.clone();
    for (key, val) in [("H2", h2_r * 3.6), ("N2", n2_r * 3.6)] {
        match ret.iter_mut().find(|x| x.0 == key) {
            Some(x) => x.1 = val,
            None => ret.push((key.into(), val)),
        }
    }
    Ok(json!({
        "permeate_kmol_h": {"H2": jnf(h2_p * 3.6), "N2": jnf(n2_p * 3.6)}, "retentate_kmol_h": jmap(&ret),
        "h2_recovery": jnf(if h2_0 != 0.0 { h2_p / h2_0 } else { 0.0 }),
        "n2_in_permeate_ppm": jnf(if h2_p + n2_p > 0.0 { 1e6 * n2_p / (h2_p + n2_p) } else { 0.0 }),
        "permeance_mol_m2_s_Pa05": jnf(k), "alpha_H2_N2": jnf(a.alpha_h2_n2), "area_m2": jnf(area_m2),
    }))
}

/// `pinch_recovery(feed, P_feed, P_perm, n)`.
pub fn pinch_recovery(
    feed: &[(String, f64)],
    p_feed_bar: f64,
    p_perm_bar: f64,
) -> Result<f64, EngineError> {
    let h2 = h2_of(feed)?;
    let other = py_sum(feed.iter().filter(|x| x.0 != "H2").map(|x| x.1));
    let y_p = p_perm_bar / p_feed_bar;
    if y_p >= 1.0 {
        return Ok(0.0);
    }
    Ok(py_max(0.0, 1.0 - (y_p / (1.0 - y_p) * other) / h2))
}

/// `membrane_area_for_recovery(feed, R, P_feed, P_perm, T, ...)`.
#[allow(clippy::too_many_arguments)]
pub fn membrane_area_for_recovery(
    p: &SepParams,
    feed: &[(String, f64)],
    r: f64,
    p_feed_bar: f64,
    p_perm_bar: f64,
    t_k: f64,
    a: &LeakArgs,
) -> Result<Option<f64>, EngineError> {
    if r >= pinch_recovery(feed, p_feed_bar, p_perm_bar)? {
        return Ok(None);
    }
    let f = |x: f64| -> Result<f64, EngineError> {
        Ok(
            membrane_with_leakage(p, feed, x, p_feed_bar, p_perm_bar, t_k, a)?["h2_recovery"]
                .as_f64()
                .unwrap_or(f64::NAN)
                - r,
        )
    };
    let mut hi = 1.0;
    while f(hi)? < 0.0 {
        hi *= 2.0;
        if hi > 1e7 {
            return Ok(None);
        }
    }
    let root = brentq_try(f, 0.0, hi, BrentOptions::with_xtol(1e-9))
        .map_err(crate::process::properties::brent_err)?;
    Ok(Some(root.x))
}

/// `required_selectivity(feed, area, P_feed, P_perm, T, n2_limit_ppm, ...)` (bisection on log alpha).
#[allow(clippy::too_many_arguments)]
pub fn required_selectivity(
    p: &SepParams,
    feed: &[(String, f64)],
    area: f64,
    p_feed_bar: f64,
    p_perm_bar: f64,
    t_k: f64,
    n2_limit_ppm: f64,
    a: &LeakArgs,
) -> Result<Option<f64>, EngineError> {
    let ppm = |alpha: f64| -> Result<f64, EngineError> {
        let la = LeakArgs {
            alpha_h2_n2: alpha,
            ..a.clone()
        };
        Ok(membrane_with_leakage(p, feed, area, p_feed_bar, p_perm_bar, t_k, &la)?["n2_in_permeate_ppm"]
            .as_f64()
            .unwrap_or(f64::NAN))
    };
    if ppm(1e9)? > n2_limit_ppm {
        return Ok(None);
    }
    let (mut lo, mut hi) = (1.0_f64, 1e9_f64);
    for _ in 0..80 {
        let mid = (lo * hi).sqrt();
        if ppm(mid)? > n2_limit_ppm {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    Ok(Some(hi))
}

/// `lhv_kW(flows)`.
pub fn lhv_kw(flows: &[(String, f64)]) -> f64 {
    let lhv = |s: &str| {
        LHV_KJ_PER_MOL
            .iter()
            .find(|x| x.0.name() == s)
            .map(|x| x.1)
            .unwrap_or(0.0)
    };
    py_sum(flows.iter().map(|(s, v)| v * lhv(s))) / 3.6
}

/// `mass_kg_h(flows)`.
pub fn mass_kg_h(flows: &[(String, f64)]) -> Result<f64, EngineError> {
    let mut v = Vec::with_capacity(flows.len());
    for (s, x) in flows {
        v.push(x * molar_mass(sp(s)?));
    }
    Ok(py_sum(v))
}

/// `closure(feed, outs)`.
pub fn closure(feed: &[(String, f64)], outs: &[Vec<(String, f64)>]) -> Result<Value, EngineError> {
    let mut names: Vec<String> = feed.iter().map(|x| x.0.clone()).collect();
    for o in outs {
        names.extend(o.iter().map(|x| x.0.clone()));
    }
    names.sort();
    names.dedup();
    let mut rel = Vec::new();
    for s in &names {
        let out = py_sum(outs.iter().map(|o| get_or(o, s, 0.0)));
        let f = get_or(feed, s, 0.0);
        let r = if f != 0.0 {
            (out - f) / f
        } else if out.abs() < 1e-12 {
            0.0
        } else {
            f64::INFINITY
        };
        rel.push((s.clone(), r));
    }
    let mf = mass_kg_h(feed)?;
    let mut mo_terms = Vec::new();
    for o in outs {
        mo_terms.push(mass_kg_h(o)?);
    }
    let mo = py_sum(mo_terms);
    let max_abs = rel
        .iter()
        .map(|x| x.1.abs())
        .fold(f64::NEG_INFINITY, |m, x| if x > m { x } else { m });
    Ok(
        json!({"component_rel_error": jmap(&rel), "max_abs_rel_error": jnf(max_abs), "mass_rel_error": jnf((mo - mf) / mf)}),
    )
}

/// `h2_compression_kWh_per_kg(P_in, P_out, T, eta)`.
pub fn h2_compression_kwh_per_kg(
    p: &SepParams,
    p_in: f64,
    p_out: f64,
    t_k: f64,
    eta: Option<f64>,
) -> Result<f64, EngineError> {
    let r = compression_power_kw(
        p,
        1.0,
        &[(Species::H2, 1.0)],
        t_k,
        p_in,
        p_out,
        None,
        eta,
        None,
    )?;
    Ok(r.power_kw / molar_mass(Species::H2))
}

/// `gas_compression_kWh_per_kg_h2(flows, T, P_in, P_out, h2_kg_h, eta)`.
#[allow(clippy::too_many_arguments)]
pub fn gas_compression_kwh_per_kg_h2(
    p: &SepParams,
    flows: &[(String, f64)],
    t_k: f64,
    p_in: f64,
    p_out: f64,
    h2_kg_h: f64,
    eta: Option<f64>,
) -> Result<f64, EngineError> {
    let tot = py_sum(flows.iter().map(|x| x.1));
    let r = compression_power_kw(
        p,
        tot,
        &to_species(flows)?,
        t_k,
        p_in,
        p_out,
        None,
        eta,
        None,
    )?;
    Ok(if h2_kg_h > 0.0 {
        r.power_kw / h2_kg_h
    } else {
        f64::NAN
    })
}

// ============================================================================ slip.py
/// `ammonia_slip(cracked_gas, product)`: the JSON of `AmmoniaSlipResult`.
pub fn ammonia_slip(
    p: &SepParams,
    cracked: &[(String, f64)],
    product_kmol_h: Option<f64>,
) -> Result<Value, EngineError> {
    let s = p.raw.get("ammonia_slip");
    let lim = s.get("fuel_cell_limit_ppm");
    let limv = lim.get("value").as_f64().ok_or_else(|| dom("limit"))?;
    let nh3 = get_or(cracked, "NH3", 0.0);
    let tot = py_sum(cracked.iter().map(|x| x.1));
    let prod = product_kmol_h.unwrap_or_else(|| get_or(cracked, "H2", 0.0));
    let allowed = limv * 1e-6 * prod;
    let rf = if nh3 > 0.0 {
        py_max(0.0, 1.0 - allowed / nh3)
    } else {
        0.0
    };
    let ev: Vec<String> = s
        .get("removal_evidence")
        .items()
        .iter()
        .map(|e| {
            let val = match e.get("outlet_ppm") {
                OValue::Null => py_str(e.get("H2_recovery")),
                v => py_str(v),
            };
            format!(
                "{}: {} ({} p. {}, {})",
                py_str(e.get("method")),
                val,
                py_str(e.get("citekey")),
                py_str(e.get("page")),
                py_str(e.get("locator"))
            )
        })
        .collect();
    Ok(json!({
        "model": MODEL_LABEL, "nh3_cracked_gas_kmol_h": jnf(nh3),
        "nh3_cracked_gas_ppm": jnf(if tot != 0.0 { 1e6 * nh3 / tot } else { 0.0 }), "limit_ppm": jnf(limv),
        "limit_source": cite(lim), "product_kmol_h": jnf(prod), "nh3_allowed_in_product_kmol_h": jnf(allowed),
        "required_nh3_removal_factor": jnf(rf), "meets_limit_without_removal": rf == 0.0, "removal_evidence": ev,
        "notes": [format!("{MODEL_LABEL}: requirement only - NH3 removal unit (TSA/adsorber) not designed")],
    }))
}

// ============================================================================ compare.py
/// `PSA_BASES`.
pub const PSA_BASES: [&str; 4] = [
    "cho2026_5A",
    "hansen2024_cha_AC",
    "kum2026_lumped",
    "amcrax_baseline",
];

/// `cracked_gas(result)`: (stream id, flows, P, T degC) of the PSA feed.
pub fn cracked_gas(
    res: &SimulationResult,
) -> Result<(String, Flows, f64, Option<f64>), EngineError> {
    for (sid, s) in &res.streams {
        if s.dest_block.as_deref() == Some("PSA") {
            return Ok((
                sid.clone(),
                nonzero(&s.component_mole_flow_kmol_h),
                s.pressure_bar.unwrap_or(f64::NAN),
                s.temperature_c,
            ));
        }
    }
    Err(dom("no stream with dest_block 'PSA' in result"))
}

/// `compare_purification(result)` with the default arguments: the JSON of
/// `PurificationComparison`.
pub fn compare_purification(p: &SepParams, res: &SimulationResult) -> Result<Value, EngineError> {
    let (sid, feed, pf, t_c) = cracked_gas(res)?;
    let t_k = t_c.unwrap_or(40.0) + 273.15;
    let h2_in = get_or(&feed, "H2", 0.0);
    let prod_s = res.streams.iter().map(|x| &x.1).find(|s| {
        s.source_block.as_deref() == Some("PSA") && s.id.to_uppercase().starts_with("H2")
    });
    let product_p = prod_s
        .and_then(|s| s.pressure_bar)
        .filter(|v| *v != 0.0)
        .unwrap_or(pf);
    let mut notes = vec![
        format!(
            "{MODEL_LABEL}s; PSA rows apply literature operating points (no interpolation); membrane row uses ideal Sieverts flux with literature Pd-Ag permeability. Neither is a designed or validated unit."
        ),
        format!("input {} case '{}', feed stream {sid}", res.source, res.case_id),
        format!(
            "energy = cracked-gas compression to the PSA feed requirement (zero if already above); the 'incl. product recompression' column adds compression of the H2 product to {} bar (eta as for the cracked-gas compressor), which is what the membrane permeate at low pressure needs to match the PSA product pressure",
            fmt_g(product_p, 6)
        ),
        "membrane heating not counted: the membrane is assumed placed where the effluent is at the membrane temperature (upstream of COOLER); the cooled stream composition is used".to_string(),
    ];
    let mut rows = Vec::new();
    let mut psa = Map::new();
    for b in PSA_BASES {
        let tp = if b == "amcrax_baseline" {
            res.kpis.h2_purity_mole_frac.filter(|v| *v != 0.0)
        } else {
            None
        };
        let args = PsaArgs {
            target_purity: tp,
            basis: b.into(),
            feed_temperature_k: t_k,
            ..PsaArgs::default()
        };
        let mut r = psa_performance(p, &feed, pf, &args)?;
        if let Some(t) = tp
            && let Some(n) = r["notes"].as_array_mut()
        {
            n.push(Value::String(format!(
                "purity {} = simulated H2PROD purity of the input case ({})",
                fmt_f(t, 6),
                res.source
            )));
        }
        let g = |k: &str| r[k].as_f64().unwrap_or(f64::NAN);
        let e = g("specific_energy_kWh_per_kgH2");
        rows.push(json!({
            "option": format!("PSA ({b})"), "basis": r["basis_source"], "h2_recovery": jnf(g("h2_recovery")),
            "h2_purity_mole_frac": jnf(g("h2_purity_mole_frac")), "product_h2_kg_h": jnf(g("product_h2_kg_h")),
            "membrane_area_m2": null, "feed_pressure_bar": jnf(pf),
            "product_pressure_bar": jnf(py_max(pf, g("required_feed_pressure_bar"))),
            "compression_power_kW": jnf(g("compression_power_kW")), "energy_kWh_per_kgH2": jnf(e),
            "energy_kWh_per_kgH2_incl_product_recompression": jnf(e), "h2_loss_kmol_h": jnf(g("h2_loss_kmol_h")),
            "h2_loss_lhv_kW": jnf(g("h2_loss_lhv_kW")),
            "h2_loss_fraction": jnf(if h2_in != 0.0 { g("h2_loss_kmol_h") / h2_in } else { 0.0 }),
        }));
        // `specific_energy` is NaN when no H2 is produced; keep the row as Python builds it
        psa.insert(b.to_string(), std::mem::take(&mut r));
    }
    let mut mem = Map::new();
    for rr in [0.756, 0.90] {
        let ma = MembraneArgs::default();
        let Some(area) = area_for_recovery(p, &feed, rr, pf, &ma)? else {
            notes.push(format!(
                "membrane recovery {} above pinch limit at {} bar - row omitted",
                py_repr(rr),
                fmt_g(pf, 6)
            ));
            continue;
        };
        let m = membrane_separator(p, &feed, area, pf, &ma)?;
        let g = |k: &str| m[k].as_f64().unwrap_or(f64::NAN);
        let perm_h2 = m["permeate_kmol_h"]["H2"].as_f64().unwrap_or(f64::NAN);
        let rc = compression_power_kw(
            p,
            perm_h2,
            &[(Species::H2, 1.0)],
            t_k,
            g("permeate_pressure_bar"),
            product_p,
            None,
            None,
            None,
        )?;
        let kg = g("product_h2_kg_h");
        rows.push(json!({
            "option": format!("Pd-Ag membrane (R={})", fmt_g(rr, 6)), "basis": m["permeability_source"],
            "h2_recovery": jnf(g("h2_recovery")), "h2_purity_mole_frac": jnf(g("h2_purity_mole_frac")),
            "product_h2_kg_h": jnf(kg), "membrane_area_m2": jnf(area), "feed_pressure_bar": jnf(pf),
            "product_pressure_bar": jnf(g("permeate_pressure_bar")), "compression_power_kW": 0.0,
            "energy_kWh_per_kgH2": 0.0,
            "energy_kWh_per_kgH2_incl_product_recompression": jnf(if kg != 0.0 { rc.power_kw / kg } else { 0.0 }),
            "h2_loss_kmol_h": jnf(g("h2_loss_kmol_h")), "h2_loss_lhv_kW": jnf(g("h2_loss_lhv_kW")),
            "h2_loss_fraction": jnf(if h2_in != 0.0 { g("h2_loss_kmol_h") / h2_in } else { 0.0 }),
        }));
        mem.insert(format!("R{}", fmt_g(rr, 6)), m);
    }
    Ok(json!({
        "model": MODEL_LABEL, "case_id": res.case_id, "input_source": res.source, "feed_stream": sid,
        "feed_kmol_h": jmap(&feed), "feed_pressure_bar": jnf(pf),
        "feed_temperature_C": t_c.map(jnf).unwrap_or(Value::Null), "rows": rows, "psa": Value::Object(psa),
        "membrane": Value::Object(mem), "ammonia_slip": ammonia_slip(p, &feed, None)?, "notes": notes,
    }))
}
