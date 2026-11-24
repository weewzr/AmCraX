//! Shell-and-tube exchanger sizing and cost (port of Python `heat_integration/exchanger.py`):
//! LMTD with the 1-2 shell F correction (Bowman, Mueller and Nagle 1940 as in Towler and Sinnott
//! 2013 Sec. 19.6), N shells in series up to F >= 0.75, Turton et al. (2018) module costing and
//! the Towler and Sinnott (2013) U-tube correlation escalated by CEPCI, the reference-scenario
//! indirect factor and annual charge, and the break-even solves. Results are the JSON of the
//! Python dicts.

use crate::economics::reference::EconomicsData;
use crate::error::EngineError;
use crate::process::result::jf;
use crate::pyops::py_max;
use serde_json::{Value, json};

/// Towler and Sinnott 2013 Sec. 19.6: F below 0.75 is uneconomic.
pub const F_MIN: f64 = 0.75;
pub const MAX_SHELLS: u32 = 12;

/// `U_CASES`: (key, U, source_type, source, url).
pub fn u_case(key: &str) -> Option<(f64, &'static str, &'static str, Option<&'static str>)> {
    const VDI: &str = "https://doi.org/10.1007/978-3-540-77877-6";
    Some(match key {
        "low" => (
            35.0,
            "literature (typical range)",
            "vdi2010heatatlas, ch. C3 table, shell-and-tube, gas (~1 bar) / gas (~1 bar): 5-35 W/(m2 K) (upper bound)",
            Some(VDI),
        ),
        "central" => (
            (35.0_f64 * 150.0).sqrt(),
            "derived (interpolation between typical ranges)",
            "geometric mean of the low and high cases (35 and 150 W/(m2 K)); no sourced value at 20 bar",
            Some(VDI),
        ),
        "high" => (
            150.0,
            "literature (typical range)",
            "vdi2010heatatlas, ch. C3 table, shell-and-tube, high-pressure gas (200-300 bar) both sides: 150-500 W/(m2 K) (lower bound)",
            Some(VDI),
        ),
        "phase1_assumption" => (
            50.0,
            "assumption",
            "Phase 1 amcrax.heat_integration.analysis.U_ASSUMED_W_M2K (unsourced), kept for comparison",
            None,
        ),
        _ => return None,
    })
}

pub const CEPCI_TURTON_BASE: f64 = 397.0;
pub const CEPCI_TOWLER_BASE: f64 = 532.9;
pub const CEPCI_TARGET_CENTRAL: f64 = 797.9;

fn turton_k(kind: &str) -> Option<(f64, f64, f64)> {
    Some(match kind {
        "fixed_tube_sheet" => (4.3247, -0.3030, 0.1634),
        "floating_head" => (4.8306, -0.8509, 0.3187),
        "u_tube" => (4.1884, -0.2503, 0.1974),
        _ => return None,
    })
}
const TURTON_RANGE: (f64, f64) = (10.0, 1000.0);
const TURTON_PRESSURE: (f64, f64, f64) = (0.03881, -0.11272, 0.08183);
const TURTON_B1: f64 = 1.63;
const TURTON_B2: f64 = 1.66;

fn turton_fm(material: &str) -> Option<f64> {
    Some(match material {
        "CS/CS" => 1.0,
        "CS/SS" => 1.81,
        "SS/SS" => 2.73,
        "CS/Ni" => 2.68,
        "Ni/Ni" => 3.73,
        _ => return None,
    })
}

fn towler_abn(kind: &str) -> Option<(f64, f64, f64)> {
    Some(match kind {
        "u_tube" => (28000.0, 54.0, 1.2),
        "floating_head" => (32000.0, 70.0, 1.2),
        _ => return None,
    })
}
const TOWLER_RANGE: (f64, f64) = (10.0, 1000.0);
const TOWLER_INSTALL: f64 = 3.5;

fn towler_fm(material: &str) -> Option<f64> {
    Some(match material {
        "CS" => 1.0,
        "SS304" => 1.3,
        "SS316" => 1.3,
        _ => return None,
    })
}

fn key_err(k: &str) -> EngineError {
    EngineError::Domain(format!("KeyError: {k:?}"))
}

/// `lmtd(dT1, dT2)`.
pub fn lmtd(dt1: f64, dt2: f64) -> Result<f64, EngineError> {
    if dt1 <= 0.0 || dt2 <= 0.0 {
        return Err(EngineError::Domain(format!(
            "terminal temperature differences must be > 0 (got {dt1}, {dt2})"
        )));
    }
    Ok(if (dt1 - dt2).abs() < 1e-9 {
        dt1
    } else {
        (dt1 - dt2) / (dt1 / dt2).ln()
    })
}

/// `_f_12(P, R)`: F of one 1-2 shell (None if infeasible).
pub fn f_12(p: f64, r: f64) -> Option<f64> {
    if p <= 0.0 {
        return Some(1.0);
    }
    let sq2 = 2.0_f64.sqrt();
    if (r - 1.0).abs() < 1e-9 {
        if p >= 1.0 {
            return None;
        }
        let den_arg = (2.0 - p * (2.0 - sq2)) / (2.0 - p * (2.0 + sq2));
        if den_arg <= 0.0 || 2.0 - p * (2.0 + sq2) <= 0.0 {
            return None;
        }
        return Some((p * sq2 / (1.0 - p)) / den_arg.ln());
    }
    let s = (r * r + 1.0).sqrt();
    let a = (1.0 - p) / (1.0 - p * r);
    let d1 = 2.0 - p * (r + 1.0 - s);
    let d2 = 2.0 - p * (r + 1.0 + s);
    if a <= 0.0 || d1 <= 0.0 || d2 <= 0.0 {
        return None;
    }
    let num = s * a.ln();
    let den = (r - 1.0) * (d1 / d2).ln();
    if den == 0.0 {
        return None;
    }
    let f = num / den;
    if 0.0 < f && f <= 1.0 + 1e-9 {
        Some(f)
    } else {
        None
    }
}

/// `f_correction(T_hot_in, T_hot_out, T_cold_in, T_cold_out, n_shells)`.
pub fn f_correction(
    thi: f64,
    tho: f64,
    tci: f64,
    tco: f64,
    n_shells: u32,
) -> Result<Option<f64>, EngineError> {
    let d_p = thi - tci;
    let d_r = tco - tci;
    if d_p == 0.0 || d_r == 0.0 {
        return Err(EngineError::Domain(
            "ZeroDivisionError: float division by zero".into(),
        ));
    }
    let p = (tco - tci) / d_p;
    let r = (thi - tho) / d_r;
    if n_shells == 1 {
        return Ok(f_12(p, r));
    }
    let n = n_shells as f64;
    let p1 = if (r - 1.0).abs() < 1e-9 {
        p / (n - (n - 1.0) * p)
    } else {
        let base = (1.0 - p * r) / (1.0 - p);
        if base <= 0.0 {
            return Ok(None);
        }
        let s = base.powf(1.0 / n);
        (s - 1.0) / (s - r)
    };
    Ok(f_12(p1, r))
}

/// `shells_needed(...)`: smallest N with F >= F_MIN.
pub fn shells_needed(thi: f64, tho: f64, tci: f64, tco: f64) -> Result<(u32, f64), EngineError> {
    for n in 1..=MAX_SHELLS {
        if let Some(f) = f_correction(thi, tho, tci, tco, n)?
            && f >= F_MIN
        {
            return Ok((n, f));
        }
    }
    Err(EngineError::Domain(format!(
        "no 1-2 shell arrangement up to {MAX_SHELLS} shells reaches F >= {F_MIN}"
    )))
}

fn split(area: f64, rng: (f64, f64)) -> (u32, f64, bool) {
    let n = ((area / rng.1).ceil() as i64).max(1) as u32;
    let a = area / n as f64;
    (n, a, a < rng.0)
}

/// `turton_cost(area, P_barg, material, kind, cepci_target, min_units)`.
pub fn turton_cost(
    area_m2: f64,
    p_barg: f64,
    material: &str,
    kind: &str,
    cepci_target: f64,
    min_units: u32,
) -> Result<Value, EngineError> {
    let rng = TURTON_RANGE;
    let (mut n, mut a, mut below) = split(area_m2, rng);
    if min_units > n {
        n = min_units;
        a = area_m2 / min_units as f64;
        below = a < rng.0;
    }
    let a_eval = py_max(a, rng.0);
    let (k1, k2, k3) = turton_k(kind).ok_or_else(|| key_err(kind))?;
    let la = a_eval.log10();
    let cp0 = 10f64.powf(k1 + k2 * la + k3 * la * la);
    let (c1, c2, c3) = TURTON_PRESSURE;
    let fp = if p_barg < 5.0 {
        1.0
    } else {
        let lp = p_barg.log10();
        10f64.powf(c1 + c2 * lp + c3 * lp * lp)
    };
    let fm = turton_fm(material).ok_or_else(|| key_err(material))?;
    let fbm = TURTON_B1 + TURTON_B2 * fm * fp;
    let esc = cepci_target / CEPCI_TURTON_BASE;
    let nf = n as f64;
    let purchased = nf * cp0 * fm * fp * esc;
    let bare = nf * cp0 * fbm * esc;
    Ok(json!({
        "correlation": format!("turton2018_{kind}"), "n_units": n, "area_per_unit_m2": jf(a), "below_range": below,
        "Cp0_per_unit_USD_2001": jf(cp0), "FP": jf(fp), "FM": jf(fm), "F_BM": jf(fbm), "escalation": jf(esc),
        "purchase_USD": jf(purchased), "installed_USD": jf(bare), "installed_definition": "bare-module cost (Turton)",
    }))
}

/// `towler_cost(area, material, kind, cepci_target, min_units)`.
pub fn towler_cost(
    area_m2: f64,
    material: &str,
    kind: &str,
    cepci_target: f64,
    min_units: u32,
) -> Result<Value, EngineError> {
    let rng = TOWLER_RANGE;
    let (mut n, mut a, mut below) = split(area_m2, rng);
    if min_units > n {
        n = min_units;
        a = area_m2 / min_units as f64;
        below = a < rng.0;
    }
    let a_eval = py_max(a, rng.0);
    let (ca, cb, cn) = towler_abn(kind).ok_or_else(|| key_err(kind))?;
    let ce = ca + cb * a_eval.powf(cn);
    let esc = cepci_target / CEPCI_TOWLER_BASE;
    let fm = towler_fm(material).ok_or_else(|| key_err(material))?;
    let nf = n as f64;
    let purchased = nf * ce * fm * esc;
    let installed = nf * ce * esc * (TOWLER_INSTALL + (fm - 1.0));
    Ok(json!({
        "correlation": format!("towler2013_{kind}"), "n_units": n, "area_per_unit_m2": jf(a), "below_range": below,
        "Ce_per_unit_USD_2010": jf(ce), "FM": jf(fm), "escalation": jf(esc), "purchase_USD": jf(purchased),
        "installed_USD": jf(installed), "installed_definition": "Hand installation factor 3.5 on CS cost + alloy premium",
    }))
}

/// `indirect_factor()`: (1 + OSBL)(1 + engineering + contingency) of the reference scenario.
pub fn indirect_factor(d: &EconomicsData) -> Result<f64, EngineError> {
    let c = d.reference.raw.get("capex");
    let f = "reference_scenario.yaml";
    let osbl = c.num_v(f, &["osbl_frac_isbl"])?;
    let eng = c.num_v(f, &["engineering_frac_isbl_osbl"])?;
    let cont = c.num_v(f, &["contingency_frac_isbl_osbl"])?;
    Ok((1.0 + osbl) * (1.0 + eng + cont))
}

/// `annual_charge_factor(crf)`: CRF + maintenance + insurance + overhead on maintenance, with G&A.
pub fn annual_charge_factor(d: &EconomicsData, crf: Option<f64>) -> f64 {
    let r = &d.reference;
    let f = crf.unwrap_or_else(|| r.crf());
    f + (r.maintenance_frac_capex_per_yr * (1.0 + r.plant_overhead_frac_labour_maint)
        + r.insurance_frac_capex_per_yr)
        * (1.0 + r.g_and_a_frac_fixed_opex)
}

/// `annualised_cost(capital, crf)`.
pub fn annualised_cost(d: &EconomicsData, capital_usd: f64, crf: Option<f64>) -> f64 {
    capital_usd * annual_charge_factor(d, crf)
}

/// `capital_for_annual(annual, crf)`.
pub fn capital_for_annual(d: &EconomicsData, annual_usd_per_yr: f64, crf: Option<f64>) -> f64 {
    annual_usd_per_yr / annual_charge_factor(d, crf)
}

/// `breakeven_crf(annual_saving, capital)`.
pub fn breakeven_crf(
    d: &EconomicsData,
    annual_saving: f64,
    capital_usd: f64,
) -> Result<f64, EngineError> {
    if capital_usd <= 0.0 {
        return Err(EngineError::Domain("capital must be positive".into()));
    }
    Ok(annual_saving / capital_usd - annual_charge_factor(d, Some(0.0)))
}

/// U specification of [`size_and_cost`].
#[derive(Debug, Clone, PartialEq)]
pub enum UCase {
    Key(String),
    Value(f64),
}

/// Options of [`size_and_cost`] (Python keyword arguments).
#[derive(Debug, Clone, PartialEq)]
pub struct SizeOptions {
    pub ua_kw_k: Option<f64>,
    pub p_barg: f64,
    pub material: String,
    pub correlation: String,
    pub counter_current: bool,
    pub cepci_target: Option<f64>,
}

impl Default for SizeOptions {
    fn default() -> Self {
        SizeOptions {
            ua_kw_k: None,
            p_barg: 19.5,
            material: "SS/SS".into(),
            correlation: "turton".into(),
            counter_current: false,
            cepci_target: None,
        }
    }
}

/// `size_and_cost(duty, T_hot_in, T_hot_out, T_cold_in, T_cold_out, U_case, ...)` (degC).
#[allow(clippy::too_many_arguments)]
pub fn size_and_cost(
    d: &EconomicsData,
    duty_kw: f64,
    thi: f64,
    tho: f64,
    tci: f64,
    tco: f64,
    u: &UCase,
    o: &SizeOptions,
) -> Result<Value, EngineError> {
    if duty_kw <= 0.0 {
        return Err(EngineError::Domain("duty_kW must be > 0".into()));
    }
    let (uval, u_src, u_case_name) = match u {
        UCase::Key(k) => {
            let (v, st, src, url) = u_case(k).ok_or_else(|| key_err(k))?;
            (
                v,
                json!({"source_type": st, "source": src, "url": url}),
                k.clone(),
            )
        }
        UCase::Value(v) => (
            *v,
            json!({"source_type": "caller", "source": "value passed by caller", "url": null}),
            "custom".to_string(),
        ),
    };
    let (dt1, dt2) = (thi - tco, tho - tci);
    let lm = lmtd(dt1, dt2)?;
    let ua = o.ua_kw_k.unwrap_or(duty_kw / lm);
    let (n_sh, f) = if o.counter_current {
        (1, 1.0)
    } else {
        shells_needed(thi, tho, tci, tco)?
    };
    let area = ua * 1000.0 / (uval * f);
    let cep = o.cepci_target.unwrap_or(CEPCI_TARGET_CENTRAL);
    let c = match o.correlation.as_str() {
        "turton" => turton_cost(area, o.p_barg, &o.material, "fixed_tube_sheet", cep, n_sh)?,
        "towler" => {
            let mat = match o.material.as_str() {
                "SS/SS" => "SS304",
                "CS/CS" => "CS",
                _ => "SS304",
            };
            towler_cost(area, mat, "u_tube", cep, n_sh)?
        }
        _ => {
            return Err(EngineError::Domain(
                "correlation must be 'turton' or 'towler'".into(),
            ));
        }
    };
    let fac = indirect_factor(d)?;
    let fx = d.reference.fx_sgd_per_usd;
    let purchase = c["purchase_USD"].as_f64().unwrap_or(f64::NAN);
    let installed = c["installed_USD"].as_f64().unwrap_or(f64::NAN);
    let tci_usd = installed * fac;
    Ok(json!({
        "duty_kW": jf(duty_kw), "T_hot_in_C": jf(thi), "T_hot_out_C": jf(tho), "T_cold_in_C": jf(tci),
        "T_cold_out_C": jf(tco), "hot_end_dT_K": jf(dt1), "cold_end_dT_K": jf(dt2), "lmtd_K": jf(lm),
        "temperature_cross": tco > tho, "ua_kW_K": jf(ua),
        "ua_basis": if o.ua_kw_k.is_none() { "Q/LMTD" } else { "segmented H-T curves (caller)" },
        "F": jf(f), "n_shells": n_sh,
        "arrangement": if o.counter_current { "counter-current (F = 1)".to_string() } else { format!("{n_sh} x 1-2 shell in series") },
        "U_W_m2K": jf(uval), "U_case": u_case_name, "U_source": u_src,
        "area_m2": jf(area), "P_barg": jf(o.p_barg), "material": o.material, "cepci_target": jf(cep), "cost_year": 2024,
        "cost": c, "purchase_USD": jf(purchase), "installed_USD": jf(installed),
        "indirect_factor": jf(fac), "tci_equivalent_USD": jf(tci_usd), "annualised_USD_per_yr": jf(annualised_cost(d, tci_usd, None)),
        "fx_SGD_per_USD": jf(fx), "purchase_SGD": jf(purchase * fx), "installed_SGD": jf(installed * fx),
        "tci_equivalent_SGD": jf(tci_usd * fx),
    }))
}

/// `breakeven_U(...)`: U (W/(m2 K)) at which the TCI-equivalent equals the target (bisection on
/// log U between 0.01 and 5000).
#[allow(clippy::too_many_arguments)]
pub fn breakeven_u(
    d: &EconomicsData,
    duty_kw: f64,
    thi: f64,
    tho: f64,
    tci: f64,
    tco: f64,
    tci_breakeven_usd: f64,
    o: &SizeOptions,
) -> Result<Option<f64>, EngineError> {
    let tci_of = |u: f64| -> Result<f64, EngineError> {
        let v = size_and_cost(d, duty_kw, thi, tho, tci, tco, &UCase::Value(u), o)?;
        Ok(v["tci_equivalent_USD"].as_f64().unwrap_or(f64::NAN))
    };
    let (mut lo, mut hi) = (0.01_f64, 5000.0_f64);
    if tci_of(lo)? <= tci_breakeven_usd {
        return Ok(Some(lo));
    }
    if tci_of(hi)? > tci_breakeven_usd {
        return Ok(None);
    }
    for _ in 0..200 {
        let mid = (lo * hi).sqrt();
        if tci_of(mid)? > tci_breakeven_usd {
            lo = mid;
        } else {
            hi = mid;
        }
        if hi / lo < 1.0 + 1e-10 {
            break;
        }
    }
    Ok(Some(hi))
}
