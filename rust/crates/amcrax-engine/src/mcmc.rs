//! Adaptive Metropolis and convergence diagnostics (port of Python `uq/mcmc.py`: Haario,
//! Saksman and Tamminen 2001; rank-normalised split R-hat and bulk ESS of Vehtari et al. 2021).
//!
//! The proposal draws use NumPy's ziggurat normal stream (`Pcg64::standard_normal`), the
//! acceptance test `ln(random()) < lq - lp`, Welford running moments and a Cholesky factor that is
//! updated between `adapt_start` and `burn_in` and frozen afterwards, exactly as the Python code.
//! The autocovariance of the bulk ESS uses a radix-2 FFT with zero padding (NumPy pads to `2n`;
//! the linear autocovariance at lags below `n` is the same, the rounding differs).

use amcrax_numerics::random::Pcg64;
use amcrax_numerics::special::ndtri;
use amcrax_numerics::stats;

/// Lower Cholesky factor of a symmetric matrix (`None` if not positive definite, NumPy's
/// `LinAlgError`).
pub fn cholesky(c: &[Vec<f64>]) -> Option<Vec<Vec<f64>>> {
    let d = c.len();
    let mut l = vec![vec![0.0; d]; d];
    for j in 0..d {
        let mut s = c[j][j];
        for k in 0..j {
            s -= l[j][k] * l[j][k];
        }
        if s.is_nan() || s <= 0.0 {
            return None;
        }
        l[j][j] = s.sqrt();
        for i in j + 1..d {
            let mut v = c[i][j];
            for k in 0..j {
                v -= l[i][k] * l[j][k];
            }
            l[i][j] = v / l[j][j];
        }
    }
    Some(l)
}

/// Result of [`adaptive_metropolis`].
#[derive(Debug, Clone, PartialEq)]
pub struct AmResult {
    /// States, one row per iteration.
    pub chain: Vec<Vec<f64>>,
    pub logp: Vec<f64>,
    pub accept_rate: f64,
}

/// `adaptive_metropolis(logp, x0, n_iter, rng, adapt_start, burn_in, cov0, eps)`.
#[allow(clippy::too_many_arguments)]
pub fn adaptive_metropolis<F: FnMut(&[f64]) -> f64>(
    mut logp: F,
    x0: &[f64],
    n_iter: usize,
    rng: &mut Pcg64,
    adapt_start: usize,
    burn_in: usize,
    cov0: Option<&[Vec<f64>]>,
    eps: f64,
) -> AmResult {
    let d = x0.len();
    let mut x = x0.to_vec();
    let sd = 2.38_f64.powi(2) / d as f64;
    let c0: Vec<Vec<f64>> = match cov0 {
        Some(c) => c.to_vec(),
        None => (0..d)
            .map(|i| (0..d).map(|j| if i == j { 0.01 } else { 0.0 }).collect())
            .collect(),
    };
    let mut l = cholesky(&c0).unwrap_or_else(|| c0.clone());
    let mut lp = logp(&x);
    let mut chain = Vec::with_capacity(n_iter);
    let mut lps = Vec::with_capacity(n_iter);
    let mut acc = vec![false; n_iter];
    let mut mean = x.clone();
    let mut m2 = vec![vec![0.0; d]; d];
    let mut z = vec![0.0; d];
    for t in 0..n_iter {
        for zi in z.iter_mut() {
            *zi = rng.standard_normal();
        }
        let y: Vec<f64> = (0..d)
            .map(|i| {
                let mut s = 0.0;
                for j in 0..d {
                    s += l[i][j] * z[j];
                }
                x[i] + s
            })
            .collect();
        let lq = logp(&y);
        if rng.random().ln() < lq - lp {
            x = y;
            lp = lq;
            acc[t] = true;
        }
        chain.push(x.clone());
        lps.push(lp);
        let k = (t + 1) as f64;
        let delta: Vec<f64> = (0..d).map(|i| x[i] - mean[i]).collect();
        for i in 0..d {
            mean[i] += delta[i] / k;
        }
        for i in 0..d {
            for j in 0..d {
                m2[i][j] += delta[i] * (x[j] - mean[j]);
            }
        }
        if adapt_start <= t && t < burn_in && t + 1 > 1 {
            let c: Vec<Vec<f64>> = (0..d)
                .map(|i| {
                    (0..d)
                        .map(|j| sd * (m2[i][j] / (k - 1.0)) + if i == j { eps } else { 0.0 })
                        .collect()
                })
                .collect();
            if let Some(nl) = cholesky(&c) {
                l = nl;
            }
        }
    }
    let tail: Vec<f64> = if n_iter > burn_in {
        acc[burn_in..]
            .iter()
            .map(|a| if *a { 1.0 } else { 0.0 })
            .collect()
    } else {
        acc.iter().map(|a| if *a { 1.0 } else { 0.0 }).collect()
    };
    AmResult {
        chain,
        logp: lps,
        accept_rate: stats::mean(&tail),
    }
}

/// `_split(chains)`: the first and last halves of every chain as separate chains.
fn split(c: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let n = c[0].len();
    let h = n / 2;
    let mut out: Vec<Vec<f64>> = c.iter().map(|r| r[..h].to_vec()).collect();
    out.extend(c.iter().map(|r| r[n - h..].to_vec()));
    out
}

fn row_stats(c: &[Vec<f64>]) -> (f64, f64) {
    // W = mean of the within-chain variances; Bv = variance of the chain means (both ddof 1)
    let w: Vec<f64> = c.iter().map(|r| stats::var(r, 1)).collect();
    let means: Vec<f64> = c.iter().map(|r| stats::mean(r)).collect();
    (stats::mean(&w), stats::var(&means, 1))
}

fn rhat_basic(c: &[Vec<f64>]) -> f64 {
    let n = c[0].len() as f64;
    let (w, bv) = row_stats(c);
    let b = n * bv;
    let var_plus = (n - 1.0) / n * w + b / n;
    (var_plus / w).sqrt()
}

/// `scipy.stats.rankdata` (method `average`) of a flat array.
pub fn rankdata(x: &[f64]) -> Vec<f64> {
    let n = x.len();
    let mut idx: Vec<usize> = (0..n).collect();
    idx.sort_by(|&a, &b| x[a].total_cmp(&x[b]));
    let mut r = vec![0.0; n];
    let mut i = 0;
    while i < n {
        let mut j = i;
        while j + 1 < n && x[idx[j + 1]] == x[idx[i]] {
            j += 1;
        }
        // ranks i+1 .. j+1, average (SciPy: 0.5 * (count[dense] + count[dense - 1] + 1))
        let avg = 0.5 * ((j + 1) as f64 + i as f64 + 1.0);
        for k in i..=j {
            r[idx[k]] = avg;
        }
        i = j + 1;
    }
    r
}

fn rank_normalise(c: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let flat: Vec<f64> = c.iter().flatten().copied().collect();
    let size = flat.len() as f64;
    let r = rankdata(&flat);
    let n = c[0].len();
    c.iter()
        .enumerate()
        .map(|(i, row)| {
            (0..row.len())
                .map(|j| ndtri((r[i * n + j] - 3.0 / 8.0) / (size + 0.25)))
                .collect()
        })
        .collect()
}

/// `rhat(chains)`: rank-normalised split R-hat (max of bulk and folded), chains `(m, n)`.
pub fn rhat(chains: &[Vec<f64>]) -> f64 {
    let s = split(chains);
    let bulk = rhat_basic(&rank_normalise(&s));
    let flat: Vec<f64> = s.iter().flatten().copied().collect();
    let med = stats::median(&flat);
    let folded: Vec<Vec<f64>> = s
        .iter()
        .map(|r| r.iter().map(|v| (v - med).abs()).collect())
        .collect();
    let tail = rhat_basic(&rank_normalise(&folded));
    if tail > bulk { tail } else { bulk }
}

/// In-place iterative radix-2 FFT of `(re, im)` (length a power of two); `inverse` without the
/// 1/n factor.
fn fft(re: &mut [f64], im: &mut [f64], inverse: bool) {
    let n = re.len();
    let mut j = 0;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j |= bit;
        if i < j {
            re.swap(i, j);
            im.swap(i, j);
        }
    }
    let mut len = 2;
    while len <= n {
        let ang = 2.0 * std::f64::consts::PI / len as f64 * if inverse { 1.0 } else { -1.0 };
        for start in (0..n).step_by(len) {
            for k in 0..len / 2 {
                let (wr, wi) = ((ang * k as f64).cos(), (ang * k as f64).sin());
                let (a, b) = (start + k, start + k + len / 2);
                let tr = re[b] * wr - im[b] * wi;
                let ti = re[b] * wi + im[b] * wr;
                re[b] = re[a] - tr;
                im[b] = im[a] - ti;
                re[a] += tr;
                im[a] += ti;
            }
        }
        len <<= 1;
    }
}

/// Autocovariance `acov[k] = sum_t x_t x_{t+k} / n` for `k < n` (x centred by the caller).
fn autocov(x: &[f64]) -> Vec<f64> {
    let n = x.len();
    let mut size = 1;
    while size < 2 * n {
        size <<= 1;
    }
    let mut re = vec![0.0; size];
    let mut im = vec![0.0; size];
    re[..n].copy_from_slice(x);
    fft(&mut re, &mut im, false);
    for k in 0..size {
        re[k] = re[k] * re[k] + im[k] * im[k];
        im[k] = 0.0;
    }
    fft(&mut re, &mut im, true);
    (0..n).map(|k| re[k] / size as f64 / n as f64).collect()
}

fn ess_basic(c: &[Vec<f64>]) -> f64 {
    let m = c.len();
    let n = c[0].len();
    let acov: Vec<Vec<f64>> = c
        .iter()
        .map(|r| {
            let mu = stats::mean(r);
            let x: Vec<f64> = r.iter().map(|v| v - mu).collect();
            autocov(&x)
        })
        .collect();
    let (w, bv) = row_stats(c);
    let nf = n as f64;
    let var_plus = if m > 1 {
        (nf - 1.0) / nf * w + nf * bv / nf
    } else {
        w
    };
    let mut rho: Vec<f64> = (0..n)
        .map(|t| {
            let mut s = 0.0;
            for a in &acov {
                s += a[t];
            }
            1.0 - (w - s / m as f64) / var_plus
        })
        .collect();
    rho[0] = 1.0;
    let (mut tau, mut prev) = (-1.0, f64::INFINITY);
    let mut t = 0;
    while t + 1 < n {
        let mut p = rho[t] + rho[t + 1];
        if p < 0.0 {
            break;
        }
        if prev < p {
            p = prev;
        }
        prev = p;
        tau += 2.0 * p;
        t += 2;
    }
    (m * n) as f64 / if tau > 1e-12 { tau } else { 1e-12 }
}

/// `ess_bulk(chains)`.
pub fn ess_bulk(chains: &[Vec<f64>]) -> f64 {
    ess_basic(&rank_normalise(&split(chains)))
}
