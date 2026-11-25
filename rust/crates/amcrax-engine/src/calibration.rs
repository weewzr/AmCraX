//! Bayesian calibration of the Takahashi rate-determining-step parameters (port of the model
//! functions of `scripts/research/uq_takahashi_calibration.py`): the PFR forward model with the
//! perturbed rate constants, the bicubic logit(X) surrogate on the (ln s, dE) grid, the posterior,
//! the four adaptive-Metropolis chains with their diagnostics, the posterior summary and the
//! posterior predictive check.

use crate::error::EngineError;
use crate::kinetics::{KineticsRegistry, Overrides};
use crate::mcmc::{adaptive_metropolis, ess_bulk, rhat};
use crate::reactor::{PfrInput, SolverOptions, simulate_pfr};
use amcrax_numerics::random::{Pcg64, SeedSequence};
use amcrax_numerics::spline::RectBivariateSpline;
use amcrax_numerics::stats;
use std::collections::BTreeMap;

pub const ATM: f64 = 1.01325;
pub const RHO_BED: f64 = 1000.0;
pub const F_TOT_KMOL_H: f64 = 1.0;
pub const SIGMA_R: f64 = 0.01;
pub const BURN: usize = 5000;
pub const ADAPT: usize = 1000;

/// A NumPy `Generator` with its seed sequence (so that `spawn` continues the count).
#[derive(Debug, Clone)]
pub struct Generator {
    pub ss: SeedSequence,
    pub bg: Pcg64,
}

impl Generator {
    /// `numpy.random.default_rng(seed)`.
    pub fn new(seed: u128) -> Generator {
        let ss = SeedSequence::new(seed);
        let bg = Pcg64::from_seed_sequence(&ss);
        Generator { ss, bg }
    }
    /// `Generator.spawn(n)`.
    pub fn spawn(&mut self, n: usize) -> Vec<Generator> {
        self.ss
            .spawn(n)
            .into_iter()
            .map(|s| {
                let bg = Pcg64::from_seed_sequence(&s);
                Generator { ss: s, bg }
            })
            .collect()
    }
}

/// One digitised data point (the fields the model uses).
#[derive(Debug, Clone, PartialEq)]
pub struct Point {
    pub t_c: f64,
    pub sv_h_inv: f64,
    pub y_nh3: f64,
    pub y_h2: f64,
    pub y_ar: f64,
}

/// `overrides(key, lns, dE, jc)`: k2, k3, k4 scaled by s; constant j shifted by dE.
pub fn overrides(
    base: &BTreeMap<String, f64>,
    j: &str,
    t_ref_k: f64,
    r: f64,
    lns: f64,
    de: f64,
) -> Overrides {
    let s = lns.exp();
    let g = |k: &str| base.get(k).copied().unwrap_or(f64::NAN);
    let mut ov = Overrides::new();
    ov.insert("A2".into(), s * g("A2"));
    ov.insert("A3".into(), s * g("A3"));
    ov.insert("A4".into(), s * g("A4"));
    let a = format!("A{j}");
    let cur = ov.get(&a).copied().unwrap_or_else(|| g(&a));
    ov.insert(a, cur * (de * 1e3 / (r * t_ref_k)).exp());
    ov.insert(format!("Ea{j}"), g(&format!("Ea{j}")) + de);
    ov
}

/// `x_direct(key, lns, dE, p, ov)`: outlet conversion of the 1 atm isothermal PFR.
pub fn x_direct(
    reg: &KineticsRegistry,
    sopt: &SolverOptions,
    cid: &str,
    ov: &Overrides,
    p: &Point,
) -> Result<f64, EngineError> {
    let r = reg.r_kin_j_mol_k;
    let c0 = 101325.0 / (r * 273.15);
    let w_over_f = RHO_BED / (p.sv_h_inv / 3600.0 * c0);
    let w = w_over_f * F_TOT_KMOL_H * 1000.0 / 3600.0;
    let mut feed = BTreeMap::new();
    for (k, v) in [("NH3", p.y_nh3), ("H2", p.y_h2), ("Ar", p.y_ar)] {
        let x = F_TOT_KMOL_H * v;
        if x > 1e-12 {
            feed.insert(k.to_string(), x);
        }
    }
    let mut inp = PfrInput::new(cid, w);
    inp.t_in_c = p.t_c;
    inp.p_in_bar = ATM;
    inp.feed_kmol_h = Some(feed);
    inp.mode = "isothermal".into();
    inp.pressure_drop = false;
    inp.n_points = 2;
    inp.param_overrides = Some(ov.clone());
    Ok(simulate_pfr(reg, &inp, sopt)?.outlet.conversion)
}

fn logit(x: f64) -> f64 {
    let lo = 1e-7;
    let hi = 1.0 - 1e-7;
    let c = crate::pyops::py_min(crate::pyops::py_max(x, lo), hi);
    (c / (1.0 - c)).ln()
}

/// `Surrogate(grid)`: one bicubic spline of logit(X) per data point.
pub struct Surrogate {
    sp: Vec<RectBivariateSpline>,
}

impl Surrogate {
    /// `grid[i][j][k]` = X at (`lns[i]`, `de[j]`) for point k (NaN already replaced by 1e-7).
    pub fn new(lns: &[f64], de: &[f64], grid: &[Vec<Vec<f64>>]) -> Result<Surrogate, EngineError> {
        let npts = grid[0][0].len();
        let mut sp = Vec::with_capacity(npts);
        for k in 0..npts {
            let z: Vec<f64> = (0..lns.len())
                .flat_map(|i| (0..de.len()).map(move |j| (i, j)))
                .map(|(i, j)| logit(grid[i][j][k]))
                .collect();
            sp.push(
                RectBivariateSpline::new(lns, de, &z)
                    .map_err(|e| EngineError::Numerical(format!("spline: {e:?}")))?,
            );
        }
        Ok(Surrogate { sp })
    }

    /// `sur(lns, dE, idx)`.
    pub fn eval(&self, lns: f64, de: f64, idx: &[usize]) -> Vec<f64> {
        idx.iter()
            .map(|&k| 1.0 / (1.0 + (-self.sp[k].ev(lns, de)).exp()))
            .collect()
    }

    /// The logit value of point k (`sp[k].ev`).
    pub fn ev_logit(&self, k: usize, lns: f64, de: f64) -> f64 {
        self.sp[k].ev(lns, de)
    }
}

/// The posterior of `make_logp(sur, idx, y, dE_sd)`.
pub struct Posterior<'a> {
    pub sur: &'a Surrogate,
    pub idx: Vec<usize>,
    pub y: Vec<f64>,
    pub de_sd: f64,
    pub lns_grid: (f64, f64),
    pub de_grid: (f64, f64),
}

impl Posterior<'_> {
    /// `logp(theta)`.
    pub fn logp(&self, th: &[f64]) -> f64 {
        let (lns, de, lsd) = (th[0], th[1], th[2]);
        let inside = self.lns_grid.0 <= lns
            && lns <= self.lns_grid.1
            && self.de_grid.0 <= de
            && de <= self.de_grid.1;
        if !inside || lsd < -12.0 || lsd > 1.0 {
            return f64::NEG_INFINITY;
        }
        let sd = lsd.exp();
        let var = SIGMA_R.powi(2) + sd.powi(2);
        let mu = self.sur.eval(lns, de, &self.idx);
        let sq: Vec<f64> = self
            .y
            .iter()
            .zip(mu.iter())
            .map(|(a, b)| (a - b) * (a - b))
            .collect();
        let n = self.y.len() as f64;
        let ll = -0.5 * stats::sum(&sq) / var - 0.5 * n * (2.0 * std::f64::consts::PI * var).ln();
        let lp = -0.5 * lns.powi(2) / 4.0 - 0.5 * de.powi(2) / self.de_sd.powi(2)
            + (-0.5 * sd.powi(2) / 0.05_f64.powi(2) + lsd);
        ll + lp
    }
}

/// Output of [`run_chains`].
pub struct Chains {
    /// `C[chain][iteration][parameter]` after burn-in.
    pub c: Vec<Vec<Vec<f64>>>,
    /// (rhat, ess_bulk) per parameter.
    pub diag: Vec<(f64, f64)>,
    pub acc: Vec<f64>,
}

fn clip(x: f64, lo: f64, hi: f64) -> f64 {
    crate::pyops::py_min(crate::pyops::py_max(x, lo), hi)
}

/// `run_chains(logp, rng, n_iter, dE_sd)`: four chains spawned from `rng`.
pub fn run_chains(post: &Posterior, rng: &mut Generator, n_iter: usize, de_sd: f64) -> Chains {
    let burn = BURN.min(n_iter / 2);
    let cov0 = vec![
        vec![0.05, 0.0, 0.0],
        vec![0.0, 4.0, 0.0],
        vec![0.0, 0.0, 0.1],
    ];
    let mut chains = Vec::new();
    let mut acc = Vec::new();
    for mut child in rng.spawn(4) {
        let x0 = loop {
            let mut x0 = [
                child.bg.normal(0.0, 2.0) * 1.5,
                child.bg.normal(0.0, de_sd) * 1.5,
                (child.bg.normal(0.0, 0.05).abs() + 1e-3).ln(),
            ];
            x0[0] = clip(x0[0], post.lns_grid.0 + 0.1, post.lns_grid.1 - 0.1);
            x0[1] = clip(x0[1], post.de_grid.0 + 1.0, post.de_grid.1 - 1.0);
            if post.logp(&x0).is_finite() {
                break x0;
            }
        };
        let r = adaptive_metropolis(
            |t| post.logp(t),
            &x0,
            n_iter,
            &mut child.bg,
            ADAPT,
            burn,
            Some(&cov0),
            1e-8,
        );
        chains.push(r.chain[burn..].to_vec());
        acc.push(r.accept_rate);
    }
    let diag = (0..3)
        .map(|k| {
            let ck: Vec<Vec<f64>> = chains
                .iter()
                .map(|ch| ch.iter().map(|row| row[k]).collect())
                .collect();
            (rhat(&ck), ess_bulk(&ck))
        })
        .collect();
    Chains {
        c: chains,
        diag,
        acc,
    }
}

/// The flattened chains (`C.reshape(-1, 3)`).
pub fn flat(c: &[Vec<Vec<f64>>]) -> Vec<Vec<f64>> {
    c.iter().flatten().cloned().collect()
}

/// `summarise(C)`: per parameter (mean, sd, p5, p50, p95) and sigma_d (mean, p5, p50, p95).
pub fn summarise(c: &[Vec<Vec<f64>>]) -> (Vec<[f64; 5]>, [f64; 4]) {
    let f = flat(c);
    let col = |k: usize| -> Vec<f64> { f.iter().map(|r| r[k]).collect() };
    let mut out = Vec::new();
    for k in 0..3 {
        let x = col(k);
        out.push([
            stats::mean(&x),
            stats::std(&x, 1),
            stats::quantile(&x, 5.0 / 100.0),
            stats::quantile(&x, 50.0 / 100.0),
            stats::quantile(&x, 95.0 / 100.0),
        ]);
    }
    let sd: Vec<f64> = col(2).iter().map(|v| v.exp()).collect();
    let sig = [
        stats::mean(&sd),
        stats::quantile(&sd, 5.0 / 100.0),
        stats::quantile(&sd, 50.0 / 100.0),
        stats::quantile(&sd, 95.0 / 100.0),
    ];
    (out, sig)
}
