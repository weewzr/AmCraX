//! Problem-table algorithm (Linnhoff) for piecewise-linear H-T streams (port of Python
//! `heat_integration/pinch.py`).

use crate::error::EngineError;
use crate::pyops::{py_max, py_min, py_sum};
use amcrax_numerics::interp::interp_linear;

/// Width (K) used to represent an isothermal duty as a steep linear segment.
pub const ISOTHERMAL_WIDTH_K: f64 = 0.01;

/// Piecewise-linear stream; `t_k` strictly increasing, `h_kw` non-decreasing from 0.
#[derive(Debug, Clone, PartialEq)]
pub struct Curve {
    pub id: String,
    /// `hot` or `cold`.
    pub kind: String,
    pub t_k: Vec<f64>,
    pub h_kw: Vec<f64>,
    pub name: String,
    /// `meta["T_switch_K"]` (the only meta entry the analysis reads).
    pub t_switch_k: Option<f64>,
}

impl Curve {
    /// `duty_kW = H[-1] - H[0]`.
    pub fn duty_kw(&self) -> f64 {
        self.h_kw[self.h_kw.len() - 1] - self.h_kw[0]
    }
    /// `T_min_K`.
    pub fn t_min_k(&self) -> f64 {
        self.t_k[0]
    }
    /// `T_max_K`.
    pub fn t_max_k(&self) -> f64 {
        self.t_k[self.t_k.len() - 1]
    }
    /// `np.interp(T, T_K, H_kW)`.
    pub fn h_at(&self, t_k: f64) -> f64 {
        interp_linear(t_k, &self.t_k, &self.h_kw)
    }
    /// `np.interp(H, H_kW, T_K)`.
    pub fn t_at(&self, h_kw: f64) -> f64 {
        interp_linear(h_kw, &self.h_kw, &self.t_k)
    }
    /// `slice(T_lo, T_hi, id, kind)`.
    pub fn slice(&self, t_lo: f64, t_hi: f64, id: Option<&str>) -> Result<Curve, EngineError> {
        let lo = py_max(t_lo, self.t_min_k());
        let hi = py_min(t_hi, self.t_max_k());
        if hi <= lo {
            return Err(EngineError::Domain(format!(
                "empty slice of {}: [{t_lo}, {t_hi}]",
                self.id
            )));
        }
        let mut t = vec![lo];
        t.extend(self.t_k.iter().copied().filter(|x| *x > lo && *x < hi));
        t.push(hi);
        let h: Vec<f64> = t.iter().map(|x| self.h_at(*x)).collect();
        let h0 = h[0];
        Ok(Curve {
            id: id.unwrap_or(&self.id).to_string(),
            kind: self.kind.clone(),
            t_k: t,
            h_kw: h.iter().map(|x| x - h0).collect(),
            name: self.name.clone(),
            t_switch_k: self.t_switch_k,
        })
    }
}

/// `make_curve(id, kind, T, H, name)`: points in any order (sorted by T, then H); equal
/// temperatures are spread by [`ISOTHERMAL_WIDTH_K`].
pub fn make_curve(
    id: &str,
    kind: &str,
    t: &[f64],
    h: &[f64],
    name: &str,
) -> Result<Curve, EngineError> {
    let mut order: Vec<usize> = (0..t.len()).collect();
    // np.lexsort((H, T)): primary key T, secondary H, stable
    order.sort_by(|&a, &b| t[a].total_cmp(&t[b]).then(h[a].total_cmp(&h[b])));
    let mut tt: Vec<f64> = order.iter().map(|&i| t[i]).collect();
    let hh: Vec<f64> = order.iter().map(|&i| h[i]).collect();
    for i in 1..tt.len() {
        if tt[i] <= tt[i - 1] {
            tt[i] = tt[i - 1] + ISOTHERMAL_WIDTH_K;
        }
    }
    if hh.windows(2).any(|w| w[1] - w[0] < -1e-9) {
        return Err(EngineError::Domain(format!(
            "stream {id}: enthalpy must increase with temperature"
        )));
    }
    let h0 = hh[0];
    Ok(Curve {
        id: id.into(),
        kind: kind.into(),
        t_k: tt,
        h_kw: hh.iter().map(|x| x - h0).collect(),
        name: name.into(),
        t_switch_k: None,
    })
}

/// Result of [`problem_table`] (Python `PinchResult`).
#[derive(Debug, Clone, PartialEq)]
pub struct PinchResult {
    pub dt_min_k: f64,
    pub hot_utility_kw: f64,
    pub cold_utility_kw: f64,
    pub pinch_shifted_k: Option<f64>,
    pub threshold: bool,
    /// Descending.
    pub boundaries_shifted_k: Vec<f64>,
    pub interval_deficit_kw: Vec<f64>,
    pub cascade_kw: Vec<f64>,
    /// (H, T) ascending.
    pub hot_composite: (Vec<f64>, Vec<f64>),
    /// (H, T) ascending, shifted by the cold utility.
    pub cold_composite: (Vec<f64>, Vec<f64>),
    pub total_hot_kw: f64,
    pub total_cold_kw: f64,
}

impl PinchResult {
    /// `pinch_hot_K`.
    pub fn pinch_hot_k(&self) -> Option<f64> {
        self.pinch_shifted_k.map(|p| p + self.dt_min_k / 2.0)
    }
    /// `pinch_cold_K`.
    pub fn pinch_cold_k(&self) -> Option<f64> {
        self.pinch_shifted_k.map(|p| p - self.dt_min_k / 2.0)
    }
}

fn heat_in_interval(c: &Curve, lo: f64, hi: f64) -> f64 {
    let a = py_max(lo, c.t_min_k());
    let b = py_min(hi, c.t_max_k());
    if b <= a { 0.0 } else { c.h_at(b) - c.h_at(a) }
}

fn shift(c: &Curve, dt: f64) -> Curve {
    let s = if c.kind == "hot" { -dt / 2.0 } else { dt / 2.0 };
    Curve {
        t_k: c.t_k.iter().map(|t| t + s).collect(),
        ..c.clone()
    }
}

/// `np.unique` of floats (sorted ascending, exact duplicates removed).
fn unique(mut v: Vec<f64>) -> Vec<f64> {
    v.sort_by(f64::total_cmp);
    v.dedup_by(|a, b| a == b);
    v
}

/// `composite(curves)`: (cumulative H, T), both ascending.
pub fn composite(curves: &[&Curve]) -> (Vec<f64>, Vec<f64>) {
    if curves.is_empty() {
        return (vec![0.0], vec![f64::NAN]);
    }
    let t = unique(curves.iter().flat_map(|c| c.t_k.iter().copied()).collect());
    let mut h = vec![0.0; t.len()];
    for i in 1..t.len() {
        h[i] = h[i - 1] + py_sum(curves.iter().map(|c| heat_in_interval(c, t[i - 1], t[i])));
    }
    (h, t)
}

/// `problem_table(curves, dT_min, tol_kW=1e-6)`.
pub fn problem_table(curves: &[&Curve], dt_min_k: f64) -> Result<PinchResult, EngineError> {
    let tol_kw = 1e-6;
    if dt_min_k < 0.0 {
        return Err(EngineError::Domain("dT_min_K must be >= 0".into()));
    }
    let hot: Vec<&Curve> = curves.iter().copied().filter(|c| c.kind == "hot").collect();
    let cold: Vec<&Curve> = curves
        .iter()
        .copied()
        .filter(|c| c.kind == "cold")
        .collect();
    let shifted: Vec<Curve> = curves.iter().map(|c| shift(c, dt_min_k)).collect();
    let mut bounds = unique(shifted.iter().flat_map(|c| c.t_k.iter().copied()).collect());
    bounds.reverse();
    let mut deficit = Vec::with_capacity(bounds.len().saturating_sub(1));
    for w in bounds.windows(2) {
        let (hi, lo) = (w[0], w[1]);
        let c_sum = py_sum(
            shifted
                .iter()
                .filter(|c| c.kind == "cold")
                .map(|c| heat_in_interval(c, lo, hi)),
        );
        let h_sum = py_sum(
            shifted
                .iter()
                .filter(|c| c.kind == "hot")
                .map(|c| heat_in_interval(c, lo, hi)),
        );
        deficit.push(c_sum - h_sum);
    }
    // raw = [0, -cumsum(deficit)]
    let mut raw = vec![0.0];
    let mut acc = 0.0;
    for d in &deficit {
        acc += d;
        raw.push(-acc);
    }
    let raw_min = raw
        .iter()
        .copied()
        .fold(f64::INFINITY, |m, x| if x < m { x } else { m });
    let qh = py_max(0.0, -raw_min);
    let casc: Vec<f64> = raw.iter().map(|x| x + qh).collect();
    let qc = casc[casc.len() - 1];
    let total_hot = py_sum(hot.iter().map(|c| c.duty_kw()));
    let total_cold = py_sum(cold.iter().map(|c| c.duty_kw()));
    let lim = tol_kw * py_max(1.0, total_hot + total_cold);
    let zero: Vec<usize> = (0..casc.len()).filter(|&i| casc[i] <= lim).collect();
    let inner: Vec<usize> = zero
        .iter()
        .copied()
        .filter(|&i| 0 < i && i < casc.len() - 1)
        .collect();
    let threshold = qh <= tol_kw || qc <= tol_kw;
    let pinch = if let Some(&i) = inner.first() {
        Some(bounds[i])
    } else if !zero.is_empty() && !threshold {
        Some(bounds[zero[0]])
    } else {
        None
    };
    let (hh, th) = composite(&hot);
    let (hc, tc) = composite(&cold);
    Ok(PinchResult {
        dt_min_k,
        hot_utility_kw: qh,
        cold_utility_kw: qc,
        pinch_shifted_k: pinch,
        threshold: threshold && inner.is_empty(),
        boundaries_shifted_k: bounds,
        interval_deficit_kw: deficit,
        cascade_kw: casc,
        hot_composite: (hh, th),
        cold_composite: (hc.iter().map(|x| x + qc).collect(), tc),
        total_hot_kw: total_hot,
        total_cold_kw: total_cold,
    })
}
