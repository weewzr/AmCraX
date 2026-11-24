//! Uncertainty quantification (Python `uq/sobol.py`) and the probability distributions the
//! studies sample from (SciPy `triang`, `lognorm`, `norm` percent-point functions). Stage 3.
//!
//! Estimators (A, B: N x d base samples; AB_i = A with the columns of set i taken from B):
//!
//! * `V = var(concat(f(A), f(B)))`, `mu = mean(concat(f(A), f(B)))`;
//! * first order (Saltelli et al. 2010, Table 2 (b), centred outputs):
//!   `S_i = mean((f(B) - mu) * (f(AB_i) - f(A))) / V`;
//! * total effect (Jansen 1999): `ST_i = 0.5 * mean((f(A) - f(AB_i))^2) / V`;
//! * percentile bootstrap: `n_boot` resamples of the N rows (A, B and every AB_i together) drawn
//!   with `numpy.random.default_rng(seed).integers(0, N, N)`, quantiles `(1 - level) / 2` and
//!   `1 - (1 - level) / 2`.
//!
//! Every mean and variance is NumPy's pairwise sum ([`amcrax_numerics::stats`]) and the bootstrap
//! index stream is NumPy's (PCG64 + 32-bit Lemire), so the indices and the intervals reproduce
//! the Python values bit for bit for identical model outputs. Gate 1e-12 relative
//! (`amcrax verify uq`).

use crate::error::EngineError;
use amcrax_numerics::qmc::Sobol;
use amcrax_numerics::random::Pcg64;
use amcrax_numerics::special::ndtri;
use amcrax_numerics::stats;

/// Seed of every AmCraX uncertainty study (Python `amcrax.uq.SEED`).
pub const SEED: u64 = 20261123;

/// Python `indices_from_outputs(fA, fB, fAB)`: `(S, ST, V)` for the `k` rows of `fab`.
pub fn indices_from_outputs(fa: &[f64], fb: &[f64], fab: &[Vec<f64>]) -> (Vec<f64>, Vec<f64>, f64) {
    let mut cat = Vec::with_capacity(fa.len() + fb.len());
    cat.extend_from_slice(fa);
    cat.extend_from_slice(fb);
    let v = stats::var(&cat, 0);
    let k = fab.len();
    if v <= 0.0 {
        return (vec![0.0; k], vec![0.0; k], 0.0);
    }
    let mu = stats::mean(&cat);
    let n = fa.len();
    let mut s = Vec::with_capacity(k);
    let mut st = Vec::with_capacity(k);
    let mut t = vec![0.0; n];
    for row in fab {
        for i in 0..n {
            t[i] = (fb[i] - mu) * (row[i] - fa[i]);
        }
        s.push(stats::mean(&t) / v);
        for i in 0..n {
            let d = fa[i] - row[i];
            t[i] = d * d;
        }
        st.push(0.5 * stats::mean(&t) / v);
    }
    (s, st, v)
}

/// Bootstrap intervals `[lo, hi]` of S and ST (Python `bootstrap_ci`).
#[derive(Debug, Clone, PartialEq)]
pub struct BootstrapCi {
    pub s: Vec<[f64; 2]>,
    pub st: Vec<[f64; 2]>,
}

/// Python `bootstrap_ci(fA, fB, fAB, n_boot, seed, level)`.
pub fn bootstrap_ci(
    fa: &[f64],
    fb: &[f64],
    fab: &[Vec<f64>],
    n_boot: usize,
    seed: u64,
    level: f64,
) -> BootstrapCi {
    let mut rng = Pcg64::from_seed(u128::from(seed));
    let n = fa.len();
    let k = fab.len();
    let mut sb = vec![vec![0.0; n_boot]; k];
    let mut stb = vec![vec![0.0; n_boot]; k];
    let mut ra = vec![0.0; n];
    let mut rb = vec![0.0; n];
    let mut rab = vec![vec![0.0; n]; k];
    let mut idx = vec![0usize; n];
    for b in 0..n_boot {
        for x in idx.iter_mut() {
            *x = rng.integers_below(n as u64) as usize;
        }
        for (i, &j) in idx.iter().enumerate() {
            ra[i] = fa[j];
            rb[i] = fb[j];
        }
        for (r, src) in rab.iter_mut().zip(fab) {
            for (i, &j) in idx.iter().enumerate() {
                r[i] = src[j];
            }
        }
        let (s, st, _) = indices_from_outputs(&ra, &rb, &rab);
        for kk in 0..k {
            sb[kk][b] = s[kk];
            stb[kk][b] = st[kk];
        }
    }
    let a = (1.0 - level) / 2.0;
    let qs = [a, 1.0 - a];
    let ci = |m: &Vec<Vec<f64>>| -> Vec<[f64; 2]> {
        m.iter()
            .map(|col| {
                let q = stats::quantiles(col, &qs);
                [q[0], q[1]]
            })
            .collect()
    };
    BootstrapCi {
        s: ci(&sb),
        st: ci(&stb),
    }
}

/// The first `n_draws` bootstrap index vectors of [`bootstrap_ci`] (for the stream check).
pub fn bootstrap_indices(n: usize, n_draws: usize, seed: u64) -> Vec<Vec<u64>> {
    let mut rng = Pcg64::from_seed(u128::from(seed));
    (0..n_draws)
        .map(|_| (0..n).map(|_| rng.integers_below(n as u64)).collect())
        .collect()
}

/// Python `sobol_base(n, d, seed)`: `(A, B)` from one scrambled Sobol' sequence of dimension
/// `2 d` (`qmc.Sobol(d=2d, scramble=True, seed=seed).random_base2(m)`; the legacy `seed`
/// keyword seeds `numpy.random.default_rng(seed)` directly, without SciPy's spawn).
pub fn sobol_base(n: usize, d: usize, seed: u64) -> Result<(Matrix, Matrix), EngineError> {
    let m = (n as f64).log2().round() as u32;
    if 1usize << m != n {
        return Err(EngineError::Domain(
            "ValueError: n must be a power of 2".into(),
        ));
    }
    let mut rng = Pcg64::from_seed(u128::from(seed));
    let mut eng = Sobol::new_scrambled(2 * d, &mut rng)
        .map_err(|e| EngineError::Domain(format!("ValueError: {e}")))?;
    let u = eng
        .random_base2(m)
        .map_err(|e| EngineError::Domain(format!("ValueError: {e}")))?;
    let a = u.iter().map(|r| r[..d].to_vec()).collect();
    let b = u.iter().map(|r| r[d..].to_vec()).collect();
    Ok((a, b))
}

/// Row-major sample matrix (rows are samples).
pub type Matrix = Vec<Vec<f64>>;

/// Python `ab_matrix(A, B, cols)`.
pub fn ab_matrix(a: &[Vec<f64>], b: &[Vec<f64>], cols: &[usize]) -> Vec<Vec<f64>> {
    a.iter()
        .zip(b)
        .map(|(ra, rb)| {
            let mut r = ra.clone();
            for &c in cols {
                r[c] = rb[c];
            }
            r
        })
        .collect()
}

/// `scipy.stats.triang.ppf(q, c, loc, scale)` for `0 < q < 1`:
/// `where(q < c, sqrt(c q), 1 - sqrt((1 - c)(1 - q))) * scale + loc`.
pub fn triang_ppf(q: f64, c: f64, loc: f64, scale: f64) -> f64 {
    if !(0.0..=1.0).contains(&c)
        || scale.is_nan()
        || scale <= 0.0
        || !(0.0..=1.0).contains(&q)
        || q.is_nan()
    {
        return f64::NAN;
    }
    if q == 0.0 {
        return loc;
    }
    if q == 1.0 {
        return scale + loc;
    }
    let x = if q < c {
        (c * q).sqrt()
    } else {
        1.0 - ((1.0 - c) * (1.0 - q)).sqrt()
    };
    x * scale + loc
}

/// `tri_ppf(u, lo, mode, hi)` of the studies: `triang.ppf(u, (mode - lo) / (hi - lo), lo, hi - lo)`.
pub fn tri_ppf(u: f64, lo: f64, mode: f64, hi: f64) -> f64 {
    triang_ppf(u, (mode - lo) / (hi - lo), lo, hi - lo)
}

/// `scipy.stats.norm.ppf(q)` (= `ndtri`).
pub fn norm_ppf(q: f64) -> f64 {
    ndtri(q)
}

/// `scipy.stats.lognorm.ppf(q, s, scale=scale)` = `exp(s * ndtri(q)) * scale` for `0 < q < 1`.
pub fn lognorm_ppf(q: f64, s: f64, scale: f64) -> f64 {
    if s.is_nan()
        || s <= 0.0
        || scale.is_nan()
        || scale <= 0.0
        || !(0.0..=1.0).contains(&q)
        || q.is_nan()
    {
        return f64::NAN;
    }
    if q == 0.0 {
        return 0.0;
    }
    if q == 1.0 {
        return f64::INFINITY;
    }
    (s * ndtri(q)).exp() * scale
}

/// `numpy.clip(u, lo, hi)` for one value.
#[inline]
pub fn clip(u: f64, lo: f64, hi: f64) -> f64 {
    if u.is_nan() {
        u
    } else if u < lo {
        lo
    } else if u > hi {
        hi
    } else {
        u
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn linear_model_indices() {
        // f = x1 + 2 x2 on a tiny design: AB_1 = A with column 1 from B
        let a = vec![
            vec![0.1, 0.9],
            vec![0.4, 0.2],
            vec![0.7, 0.6],
            vec![0.3, 0.5],
        ];
        let b = vec![
            vec![0.8, 0.3],
            vec![0.2, 0.7],
            vec![0.5, 0.1],
            vec![0.9, 0.4],
        ];
        let f = |m: &[Vec<f64>]| -> Vec<f64> { m.iter().map(|r| r[0] + 2.0 * r[1]).collect() };
        let fab = vec![f(&ab_matrix(&a, &b, &[0])), f(&ab_matrix(&a, &b, &[1]))];
        let (s, st, v) = indices_from_outputs(&f(&a), &f(&b), &fab);
        assert!(v > 0.0 && s.len() == 2 && st.iter().all(|x| *x >= 0.0));
        let ci = bootstrap_ci(&f(&a), &f(&b), &fab, 50, 1, 0.95);
        assert!(ci.st.iter().all(|c| c[0] <= c[1]));
        let flat = vec![1.0; 4];
        assert_eq!(
            indices_from_outputs(&flat, &flat, std::slice::from_ref(&flat)).2,
            0.0
        );
        assert!(sobol_base(1000, 2, 1).is_err());
    }

    #[test]
    fn ppf_edges() {
        assert_eq!(tri_ppf(0.5, 0.0, 1.0, 2.0), 1.0);
        assert_eq!(lognorm_ppf(0.5, 0.3, 1.0), 1.0);
        assert_eq!(clip(2.0, 0.0, 1.0), 1.0);
    }
}
