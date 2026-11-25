//! Peng-Robinson (1976) cubic equation of state for gas mixtures (Python
//! `thermodynamics/peng_robinson.py`): fugacity coefficients (vapour or liquid root, with the
//! infinite-dilution limit for zero mole fractions), compressibility, enthalpy departure,
//! Wilson start, successive-substitution incipient liquid, pure-component saturation
//! temperature and the mixture dew point by scan + brentq. Data
//! `backend/amcrax/data/critical_properties.json` (CoolProp).
//!
//! A mixture is a slice of `(Species, mole fraction)`; it is processed in the fixed
//! [`Species`] (Python `COMPONENTS`) order, as Python does.
//!
//! The cubic: Python takes `numpy.roots` (companion-matrix eigenvalues), keeps the roots with
//! `|imag| < 1e-10` as real and then those `> B`; vapour = largest, liquid = smallest. Here the
//! roots come from the analytic solution with Newton polishing ([`classify_cubic`]); when it
//! finds one real root, the imaginary part of the complex pair is computed from the deflated
//! quadratic and the same `1e-10` rule decides whether NumPy would have reported the pair as real.
//! The two methods can disagree only when two roots are closer than the eigenvalue solver's
//! error (about `sqrt(eps)` times the root scale); the golden table
//! `rust/golden/stage1/peng_robinson.json` measures this band.

use crate::error::EngineError;
use crate::props::Phase;
use crate::provenance::sha256_hex;
use crate::pyops::{linspace, py_max_iter, py_sum};
use crate::species::{N_SPECIES, Species};
use crate::thermo::nasa7::R_J_MOL_K;
use amcrax_numerics::poly::cubic_real_roots;
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use amcrax_numerics::stats;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::f64::consts::SQRT_2;
use std::sync::OnceLock;

/// Repository path of the data file.
pub const DATA_FILE: &str = "backend/amcrax/data/critical_properties.json";
/// The data file, embedded at compile time.
pub const EMBEDDED_JSON: &str =
    include_str!("../../../../../backend/amcrax/data/critical_properties.json");
/// Threshold of numpy's root classification in the Python code.
pub const IMAG_TOL: f64 = 1e-10;

/// Critical constants of one species.
#[derive(Debug, Clone, Copy, PartialEq, Deserialize)]
pub struct Critical {
    #[serde(rename = "Tc_K")]
    pub tc_k: f64,
    #[serde(rename = "Pc_bar")]
    pub pc_bar: f64,
    pub omega: f64,
}

/// Critical constants of the five species.
#[derive(Debug, Clone, PartialEq)]
pub struct CriticalProperties {
    crit: Vec<Critical>,
    /// SHA-256 of the parsed JSON text.
    pub sha256: String,
}

#[derive(Deserialize)]
struct RawCrit {
    species: BTreeMap<String, Critical>,
}

impl CriticalProperties {
    /// Parse `critical_properties.json`.
    pub fn from_json(text: &str) -> Result<Self, EngineError> {
        let raw: RawCrit =
            serde_json::from_str(text).map_err(|e| EngineError::data(DATA_FILE, e.to_string()))?;
        let mut crit = Vec::with_capacity(N_SPECIES);
        for s in Species::ALL {
            crit.push(*raw.species.get(s.name()).ok_or_else(|| {
                EngineError::data(DATA_FILE, format!("species {} missing", s.name()))
            })?);
        }
        Ok(CriticalProperties {
            crit,
            sha256: sha256_hex(text.as_bytes()),
        })
    }

    /// The embedded data (parsed once).
    pub fn embedded() -> &'static CriticalProperties {
        static CELL: OnceLock<CriticalProperties> = OnceLock::new();
        CELL.get_or_init(|| {
            CriticalProperties::from_json(EMBEDDED_JSON)
                .expect("embedded critical_properties.json is valid (checked in CI)")
        })
    }

    /// Constants of `s`.
    pub fn get(&self, s: Species) -> Critical {
        self.crit[s.index()]
    }
}

fn crit(s: Species) -> Critical {
    CriticalProperties::embedded().get(s)
}

/// Alpha function (Python `alpha=`): `"standard"` Soave form, or Boston-Mathias above Tc.
/// Python treats every string other than `"boston-mathias"` as the standard form.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Alpha {
    #[default]
    Standard,
    BostonMathias,
}

impl Alpha {
    /// Python's reading of the `alpha` string.
    pub fn from_python(s: &str) -> Alpha {
        if s == "boston-mathias" {
            Alpha::BostonMathias
        } else {
            Alpha::Standard
        }
    }
}

/// Binary interaction parameters (Python `kij`: `None` or a mapping of species pairs).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Kij {
    m: [[f64; N_SPECIES]; N_SPECIES],
}

impl Default for Kij {
    fn default() -> Self {
        Kij::zero()
    }
}

impl Kij {
    /// All `k_ij = 0` (Python `kij=None`).
    pub fn zero() -> Kij {
        Kij {
            m: [[0.0; N_SPECIES]; N_SPECIES],
        }
    }

    /// From pairs, validated as Python `normalise_kij`: `k_ii` is an error, values must be finite,
    /// a pair given twice (either order) with different values is an error.
    pub fn from_pairs(pairs: &[(Species, Species, f64)]) -> Result<Kij, EngineError> {
        let mut k = Kij::zero();
        let mut set = [[false; N_SPECIES]; N_SPECIES];
        for &(a, b, v) in pairs {
            if a == b {
                return Err(EngineError::Domain(format!(
                    "kij key ({}, {}): k_ii is not a parameter (must be two different species)",
                    a.name(),
                    b.name()
                )));
            }
            if !v.is_finite() {
                return Err(EngineError::Domain(format!(
                    "kij[({}, {})] = {v} is not finite",
                    a.name(),
                    b.name()
                )));
            }
            let (i, j) = (a.index(), b.index());
            if set[i][j] && k.m[i][j] != v {
                return Err(EngineError::Domain(format!(
                    "kij pair {}-{} given twice with different values ({} and {v})",
                    a.name(),
                    b.name(),
                    k.m[i][j]
                )));
            }
            set[i][j] = true;
            set[j][i] = true;
            k.m[i][j] = v;
            k.m[j][i] = v;
        }
        Ok(k)
    }

    /// `k_ij`.
    pub fn get(&self, a: Species, b: Species) -> f64 {
        self.m[a.index()][b.index()]
    }
}

/// Roots of a cubic as numpy.roots + the `|imag| < 1e-10` rule would classify them.
#[derive(Debug, Clone, PartialEq)]
pub struct CubicClassification {
    /// Roots counted as real (ascending), real parts.
    pub real: Vec<f64>,
    /// Number of real roots of the analytic solution (1 or 3).
    pub n_real_analytic: usize,
    /// Imaginary part of the complex pair (0 when the analytic solution has three real roots).
    pub pair_imag: f64,
}

/// Classify the roots of `z^3 + a2 z^2 + a1 z + a0` (see the module documentation).
pub fn classify_cubic(a2: f64, a1: f64, a0: f64) -> CubicClassification {
    let r = cubic_real_roots(a2, a1, a0);
    if r.len() == 3 {
        return CubicClassification {
            real: r.as_slice().to_vec(),
            n_real_analytic: 3,
            pair_imag: 0.0,
        };
    }
    let x = r.min();
    // deflate: z^2 + p z + q = 0
    let p = a2 + x;
    let q = a1 + x * p;
    let disc = p * p - 4.0 * q;
    let (re, im) = if disc < 0.0 {
        (-p / 2.0, (-disc).sqrt() / 2.0)
    } else {
        (-p / 2.0, 0.0)
    };
    let mut real = vec![x];
    if im < IMAG_TOL {
        if disc >= 0.0 {
            let s = disc.sqrt();
            real.push((-p - s) / 2.0);
            real.push((-p + s) / 2.0);
        } else {
            real.push(re);
            real.push(re);
        }
        real.sort_by(f64::total_cmp);
    }
    CubicClassification {
        real,
        n_real_analytic: 1,
        pair_imag: im,
    }
}

fn phase_name(phase: Phase) -> &'static str {
    match phase {
        Phase::Vapour => "vapour",
        Phase::Liquid => "liquid",
    }
}

/// Python `_z_root(A, B, phase)`.
pub fn z_root(a: f64, b: f64, phase: Phase) -> Result<f64, EngineError> {
    let a2 = -(1.0 - b);
    let a1 = a - 3.0 * b.powf(2.0) - 2.0 * b;
    let a0 = -(a * b - b.powf(2.0) - b.powf(3.0));
    let c = classify_cubic(a2, a1, a0);
    let phys: Vec<f64> = c.real.into_iter().filter(|z| *z > b).collect();
    if phys.is_empty() {
        return Err(EngineError::Numerical(format!(
            "Peng-Robinson: no physical {} root",
            phase_name(phase)
        )));
    }
    Ok(match phase {
        Phase::Vapour => phys.iter().copied().fold(f64::NEG_INFINITY, f64::max),
        Phase::Liquid => phys.iter().copied().fold(f64::INFINITY, f64::min),
    })
}

fn alpha_fn(t_k: f64, tc: f64, omega: f64, alpha: Alpha) -> f64 {
    let m = 0.37464 + 1.54226 * omega - 0.26992 * omega.powf(2.0);
    let tr = t_k / tc;
    if alpha == Alpha::BostonMathias && tr > 1.0 {
        let d = 1.0 + m / 2.0;
        let c = 1.0 - 1.0 / d;
        return (2.0 * c * (1.0 - tr.powf(d))).exp();
    }
    (1.0 + m * (1.0 - tr.sqrt())).powf(2.0)
}

/// Pure-component `a_i` (Pa m^6 mol^-2) and `b_i` (m^3 mol^-1) at `t_k`.
pub fn pure_params(species: &[Species], t_k: f64, alpha: Alpha) -> (Vec<f64>, Vec<f64>) {
    let mut a = Vec::with_capacity(species.len());
    let mut b = Vec::with_capacity(species.len());
    for &s in species {
        let c = crit(s);
        let tc = c.tc_k;
        let pc = c.pc_bar * 1e5;
        a.push(
            0.45724 * R_J_MOL_K.powf(2.0) * tc.powf(2.0) / pc * alpha_fn(t_k, tc, c.omega, alpha),
        );
        b.push(0.07780 * R_J_MOL_K * tc / pc);
    }
    (a, b)
}

/// van der Waals one-fluid mixing: `(a_m, b_m, a_ij)`.
fn mix(y: &[f64], a: &[f64], b: &[f64], k: &[Vec<f64>]) -> (f64, f64, Vec<Vec<f64>>) {
    let n = y.len();
    let mut aij = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..n {
            aij[i][j] = (a[i] * a[j]).sqrt() * (1.0 - k[i][j]);
        }
    }
    // (y @ aij) @ y
    let mut am = 0.0;
    for j in 0..n {
        let mut v = 0.0;
        for i in 0..n {
            v += y[i] * aij[i][j];
        }
        am += v * y[j];
    }
    let mut bm = 0.0;
    for i in 0..n {
        bm += y[i] * b[i];
    }
    (am, bm, aij)
}

/// Mixture prepared as Python `_prepare`.
struct Prepared {
    sp: Vec<Species>,
    /// indices (into `sp`) of the non-zero mole fractions
    nz: Vec<usize>,
    /// normalised non-zero mole fractions
    yv: Vec<f64>,
    a_all: Vec<f64>,
    b_all: Vec<f64>,
    kij: Kij,
}

fn ordered(y: &[(Species, f64)]) -> Result<(Vec<Species>, Vec<f64>), EngineError> {
    let mut v: Vec<(Species, f64)> = y.to_vec();
    v.sort_by_key(|(s, _)| s.index());
    for w in v.windows(2) {
        if w[0].0 == w[1].0 {
            return Err(EngineError::Domain(format!(
                "species {} given twice",
                w[0].0.name()
            )));
        }
    }
    Ok(v.into_iter().unzip())
}

fn prepare(
    y: &[(Species, f64)],
    t_k: f64,
    alpha: Alpha,
    kij: &Kij,
) -> Result<(Vec<Species>, Option<Prepared>), EngineError> {
    let (sp, yall) = ordered(y)?;
    if yall.iter().any(|v| *v < 0.0 || !v.is_finite()) {
        return Err(EngineError::Domain(format!(
            "mole fractions must be finite and >= 0: {:?}",
            y.iter().map(|(s, v)| (s.name(), *v)).collect::<Vec<_>>()
        )));
    }
    let nz: Vec<usize> = (0..sp.len()).filter(|&i| yall[i] > 0.0).collect();
    if nz.is_empty() {
        return Ok((sp, None));
    }
    let (a_all, b_all) = pure_params(&sp, t_k, alpha);
    let yv0: Vec<f64> = nz.iter().map(|&i| yall[i]).collect();
    let s = stats::sum(&yv0);
    let yv: Vec<f64> = yv0.iter().map(|v| v / s).collect();
    Ok((
        sp.clone(),
        Some(Prepared {
            sp,
            nz,
            yv,
            a_all,
            b_all,
            kij: *kij,
        }),
    ))
}

impl Prepared {
    fn k_sub(&self) -> Vec<Vec<f64>> {
        self.nz
            .iter()
            .map(|&i| {
                self.nz
                    .iter()
                    .map(|&j| self.kij.get(self.sp[i], self.sp[j]))
                    .collect()
            })
            .collect()
    }
}

/// Fugacity coefficients of the mixture `y` (Python `fugacity_coefficients`), in species order.
pub fn fugacity_coefficients(
    y: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    kij: &Kij,
    alpha: Alpha,
    phase: Phase,
) -> Result<Vec<(Species, f64)>, EngineError> {
    let (sp, prep) = prepare(y, t_k, alpha, kij)?;
    let Some(pp) = prep else {
        return Ok(sp.into_iter().map(|s| (s, 1.0)).collect());
    };
    let a: Vec<f64> = pp.nz.iter().map(|&i| pp.a_all[i]).collect();
    let b: Vec<f64> = pp.nz.iter().map(|&i| pp.b_all[i]).collect();
    let k = pp.k_sub();
    let (am, bm, aij) = mix(&pp.yv, &a, &b, &k);
    let p = p_bar * 1e5;
    let rt = R_J_MOL_K * t_k;
    let aa = am * p / rt.powf(2.0);
    let bb = bm * p / rt;
    let z = z_root(aa, bb, phase)?;
    let lg = ((z + (1.0 + SQRT_2) * bb) / (z + (1.0 - SQRT_2) * bb)).ln();
    let n = pp.nz.len();
    let sum_a: Vec<f64> = (0..n)
        .map(|r| {
            let mut s = 0.0;
            for c in 0..n {
                s += aij[r][c] * pp.yv[c];
            }
            s
        })
        .collect();
    let mut out = Vec::with_capacity(sp.len());
    for (i, &s) in sp.iter().enumerate() {
        let (bi, sa) = if let Some(kpos) = pp.nz.iter().position(|&j| j == i) {
            (b[kpos], sum_a[kpos])
        } else {
            // zero mole fraction: infinite-dilution limit in the same mixture, (1 - k_ij) applied
            let mut sa = 0.0;
            for (kk, &j) in pp.nz.iter().enumerate() {
                sa += (pp.a_all[i] * a[kk]).sqrt() * (1.0 - pp.kij.get(s, pp.sp[j])) * pp.yv[kk];
            }
            (pp.b_all[i], sa)
        };
        let ln_phi = (bi / bm) * (z - 1.0)
            - (z - bb).ln()
            - aa / (2.0 * SQRT_2 * bb) * (2.0 * sa / am - bi / bm) * lg;
        out.push((s, ln_phi.exp()));
    }
    Ok(out)
}

/// Compressibility factor of the mixture (Python `compressibility`).
pub fn compressibility(
    y: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    kij: &Kij,
    alpha: Alpha,
    phase: Phase,
) -> Result<f64, EngineError> {
    let (_, prep) = prepare(y, t_k, alpha, kij)?;
    let pp = prep.ok_or_else(|| EngineError::Domain("all mole fractions are zero".into()))?;
    let a: Vec<f64> = pp.nz.iter().map(|&i| pp.a_all[i]).collect();
    let b: Vec<f64> = pp.nz.iter().map(|&i| pp.b_all[i]).collect();
    let (am, bm, _) = mix(&pp.yv, &a, &b, &pp.k_sub());
    let rt = R_J_MOL_K * t_k;
    z_root(
        am * p_bar * 1e5 / rt.powf(2.0),
        bm * p_bar * 1e5 / rt,
        phase,
    )
}

/// `H - H_ideal-gas` of the mixture, J/mol (Python `enthalpy_departure_J_mol`; central
/// difference for `da/dT` with `dT = 1e-3 T`).
pub fn enthalpy_departure_j_mol(
    y: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    kij: &Kij,
    alpha: Alpha,
    phase: Phase,
) -> Result<f64, EngineError> {
    let (a, b) = enthalpy_departure_terms_j_mol(y, t_k, p_bar, kij, alpha, phase)?;
    Ok(a + b)
}

/// The two terms of [`enthalpy_departure_j_mol`], `RT (Z - 1)` and
/// `(T da/dT - a) / (2 sqrt2 b) ln[...]` (they cancel almost completely in a near-ideal gas, so
/// their magnitudes are the scale of the rounding error of the sum).
pub fn enthalpy_departure_terms_j_mol(
    y: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    kij: &Kij,
    alpha: Alpha,
    phase: Phase,
) -> Result<(f64, f64), EngineError> {
    let (_, prep) = prepare(y, t_k, alpha, kij)?;
    let pp = prep.ok_or_else(|| EngineError::Domain("all mole fractions are zero".into()))?;
    let sub: Vec<Species> = pp.nz.iter().map(|&i| pp.sp[i]).collect();
    let k = pp.k_sub();
    let amix = |t: f64| {
        let (a, b) = pure_params(&sub, t, alpha);
        let (am, bm, _) = mix(&pp.yv, &a, &b, &k);
        (am, bm)
    };
    let (am, bm) = amix(t_k);
    let dt = 1e-3 * t_k;
    let dadt = (amix(t_k + dt).0 - amix(t_k - dt).0) / (2.0 * dt);
    let p = p_bar * 1e5;
    let rt = R_J_MOL_K * t_k;
    let aa = am * p / rt.powf(2.0);
    let bb = bm * p / rt;
    let z = z_root(aa, bb, phase)?;
    let lg = ((z + (1.0 + SQRT_2) * bb) / (z + (1.0 - SQRT_2) * bb)).ln();
    Ok((rt * (z - 1.0), (t_k * dadt - am) / (2.0 * SQRT_2 * bm) * lg))
}

/// Result of [`dew_liquid`]: incipient liquid `x`, `S`, iterations.
pub type DewLiquid = (Vec<(Species, f64)>, f64, usize);

/// Wilson K-value estimate of the incipient liquid `x_i ~ y_i / K_i`.
pub fn wilson_liquid(y: &[(Species, f64)], t_k: f64, p_bar: f64) -> Vec<(Species, f64)> {
    let w: Vec<(Species, f64)> = y
        .iter()
        .map(|&(s, v)| {
            let c = crit(s);
            (
                s,
                v / (c.pc_bar / p_bar * (5.373 * (1.0 + c.omega) * (1.0 - c.tc_k / t_k)).exp()),
            )
        })
        .collect();
    let tot = py_sum(w.iter().map(|x| x.1));
    w.into_iter().map(|(s, v)| (s, v / tot)).collect()
}

fn value_of(v: &[(Species, f64)], s: Species) -> f64 {
    v.iter().find(|x| x.0 == s).map(|x| x.1).unwrap_or(f64::NAN)
}

/// Incipient liquid in equilibrium with vapour `y` and `S = sum y_i phi_i^V / phi_i^L(x)`
/// (Python `dew_liquid`, `max_iter = 2000`). Returns `(x, S, iterations)`.
pub fn dew_liquid(
    y: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    kij: &Kij,
    alpha: Alpha,
    max_iter: usize,
) -> Result<DewLiquid, EngineError> {
    let (sp, yv) = ordered(y)?;
    let y: Vec<(Species, f64)> = sp.iter().copied().zip(yv.iter().copied()).collect();
    let phi_v = fugacity_coefficients(&y, t_k, p_bar, kij, alpha, Phase::Vapour)?;
    let mut x = wilson_liquid(&y, t_k, p_bar);
    for it in 0..max_iter {
        let phi_l = fugacity_coefficients(&x, t_k, p_bar, kij, alpha, Phase::Liquid)?;
        let w: Vec<(Species, f64)> = y
            .iter()
            .map(|&(s, v)| (s, v * value_of(&phi_v, s) / value_of(&phi_l, s)))
            .collect();
        let s_sum = py_sum(w.iter().map(|q| q.1));
        let xn: Vec<(Species, f64)> = w.iter().map(|&(s, v)| (s, v / s_sum)).collect();
        let dx = py_max_iter(xn.iter().zip(&x).map(|(a, b)| (a.1 - b.1).abs())).unwrap_or(0.0);
        if dx < 1e-14 {
            let dy = py_max_iter(xn.iter().zip(&y).map(|(a, b)| (a.1 - b.1).abs())).unwrap_or(0.0);
            if dy < 1e-8 {
                return Err(EngineError::Numerical(
                    "dew-point iteration converged to the trivial solution x = y".into(),
                ));
            }
            return Ok((xn, s_sum, it + 1));
        }
        x = xn;
    }
    Err(EngineError::Numerical(
        "dew-point successive substitution did not converge".into(),
    ))
}

fn brent_err(e: BrentError<EngineError>) -> EngineError {
    match e {
        BrentError::Function(e) => e,
        BrentError::NotConverged(r) => EngineError::Numerical(format!(
            "brentq failed to converge after {} iterations",
            r.iterations
        )),
        BrentError::SignError { fa, fb } => {
            EngineError::Bracket(format!("f(a) = {fa}, f(b) = {fb}"))
        }
        BrentError::NanValue { x, .. } => {
            EngineError::Domain(format!("the function value at x={x} is NaN"))
        }
        BrentError::InvalidTolerance { xtol, rtol } => {
            EngineError::Domain(format!("invalid tolerance {xtol} {rtol}"))
        }
    }
}

/// Root of a brentq search with its counters.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BrentRecord {
    pub a: f64,
    pub b: f64,
    pub root: f64,
    pub iterations: u32,
    pub function_calls: u32,
}

/// Pure-component PR saturation temperature (Python `saturation_temperature_K`: 600-point scan
/// from 0.4 Tc to Tc - 1e-6 K, then brentq with xtol 1e-11).
pub fn saturation_temperature_k(
    species: Species,
    p_bar: f64,
    alpha: Alpha,
) -> Result<(f64, BrentRecord), EngineError> {
    let tc = crit(species).tc_k;
    let y = [(species, 1.0)];
    let kij = Kij::zero();
    let g = |t: f64| -> Result<f64, EngineError> {
        let l = fugacity_coefficients(&y, t, p_bar, &kij, alpha, Phase::Liquid)?[0].1;
        let v = fugacity_coefficients(&y, t, p_bar, &kij, alpha, Phase::Vapour)?[0].1;
        Ok((l / v).ln())
    };
    let mut prev: Option<(f64, f64)> = None;
    for t in linspace(0.4 * tc, tc - 1e-6, 600) {
        let v = g(t)?;
        if let Some((tp, vp)) = prev
            && vp < 0.0
            && 0.0 < v
        {
            let r = brentq_try(g, tp, t, BrentOptions::with_xtol(1e-11)).map_err(brent_err)?;
            return Ok((
                r.x,
                BrentRecord {
                    a: tp,
                    b: t,
                    root: r.x,
                    iterations: r.iterations,
                    function_calls: r.function_calls,
                },
            ));
        }
        if v != 0.0 {
            prev = Some((t, v));
        }
    }
    Err(EngineError::Numerical(format!(
        "PR saturation temperature of {} at {p_bar} bar not bracketed",
        species.name()
    )))
}

/// One temperature of the dew-point scan: `Some(S - 1)` or `None` when `dew_liquid` failed.
pub type ScanPoint = (f64, Option<f64>);

/// Result of [`dew_point_k`].
#[derive(Debug, Clone, PartialEq)]
pub struct DewPoint {
    pub t_k: f64,
    pub x: Vec<(Species, f64)>,
    /// The scan up to the bracket (empty for a single component).
    pub scan: Vec<ScanPoint>,
    /// The brentq search (`None` for a single component, whose saturation search is in `saturation`).
    pub brentq: Option<BrentRecord>,
    pub saturation: Option<BrentRecord>,
}

/// PR dew-point temperature of vapour `y` at `p_bar` (Python `dew_point_K`: scan of
/// `linspace(250, 600, 351)` for the sign change of `S - 1` from + to -, then brentq with
/// xtol 1e-9). A scan temperature where `dew_liquid` fails (Python `RuntimeError`) resets the
/// bracket start, as in Python.
pub fn dew_point_k(
    p_bar: f64,
    y: &[(Species, f64)],
    kij: &Kij,
    alpha: Alpha,
) -> Result<DewPoint, EngineError> {
    let mut scan = Vec::new();
    dew_point_k_traced(p_bar, y, kij, alpha, &mut scan)
}

/// [`dew_point_k`], writing the scan into `scan` also when no bracket is found.
pub fn dew_point_k_traced(
    p_bar: f64,
    y: &[(Species, f64)],
    kij: &Kij,
    alpha: Alpha,
    scan: &mut Vec<ScanPoint>,
) -> Result<DewPoint, EngineError> {
    let (sp, yv) = ordered(y)?;
    let pos: Vec<(Species, f64)> = sp
        .iter()
        .copied()
        .zip(yv.iter().copied())
        .filter(|x| x.1 > 0.0)
        .collect();
    let tot = py_sum(pos.iter().map(|x| x.1));
    let y: Vec<(Species, f64)> = pos.iter().map(|&(s, v)| (s, v / tot)).collect();
    if y.len() == 1 {
        let (t, rec) = saturation_temperature_k(y[0].0, p_bar, alpha)?;
        return Ok(DewPoint {
            t_k: t,
            x: vec![(y[0].0, 1.0)],
            scan: Vec::new(),
            brentq: None,
            saturation: Some(rec),
        });
    }
    let f = |t: f64| -> Result<f64, EngineError> {
        Ok(dew_liquid(&y, t, p_bar, kij, alpha, 2000)?.1 - 1.0)
    };
    scan.clear();
    let mut prev: Option<(f64, f64)> = None;
    for t in linspace(250.0, 600.0, 351) {
        let v = match f(t) {
            Ok(v) => v,
            Err(EngineError::Numerical(_)) => {
                scan.push((t, None));
                prev = None;
                continue;
            }
            Err(e) => return Err(e),
        };
        scan.push((t, Some(v)));
        if let Some((tp, vp)) = prev
            && vp > 0.0
            && 0.0 > v
        {
            let r = brentq_try(f, tp, t, BrentOptions::with_xtol(1e-9)).map_err(brent_err)?;
            let (x, _, _) = dew_liquid(&y, r.x, p_bar, kij, alpha, 2000)?;
            return Ok(DewPoint {
                t_k: r.x,
                x,
                scan: scan.clone(),
                brentq: Some(BrentRecord {
                    a: tp,
                    b: t,
                    root: r.x,
                    iterations: r.iterations,
                    function_calls: r.function_calls,
                }),
                saturation: None,
            });
        }
        prev = Some((t, v));
    }
    Err(EngineError::Numerical("PR dew point not bracketed".into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ideal_limit_and_kij_validation() {
        let y = [(Species::N2, 1.0)];
        let phi = fugacity_coefficients(
            &y,
            1000.0,
            0.01,
            &Kij::zero(),
            Alpha::Standard,
            Phase::Vapour,
        )
        .unwrap();
        assert!((phi[0].1 - 1.0).abs() < 1e-4);
        assert!(Kij::from_pairs(&[(Species::NH3, Species::NH3, 0.1)]).is_err());
        assert!(
            Kij::from_pairs(&[
                (Species::NH3, Species::H2, 0.1),
                (Species::H2, Species::NH3, 0.2)
            ])
            .is_err()
        );
        let k = Kij::from_pairs(&[
            (Species::NH3, Species::H2, 0.1),
            (Species::H2, Species::NH3, 0.1),
        ])
        .unwrap();
        assert_eq!(k.get(Species::H2, Species::NH3), 0.1);
        let c = classify_cubic(-6.0, 11.0, -6.0);
        assert_eq!(c.real.len(), 3);
    }
}
