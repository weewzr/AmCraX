//! Descriptive statistics with NumPy's floating-point behaviour.
//!
//! * [`sum`] is NumPy's pairwise summation (`pairwise_sum_DOUBLE`: blocks of at most 128
//!   elements summed with eight accumulators, larger arrays split in two halves whose sizes are
//!   multiples of 8), so `sum`, [`mean`], [`var`] and [`std()`] are bit-identical to
//!   `numpy.sum/mean/var/std` of a contiguous float64 vector.
//! * [`quantile`] is `numpy.quantile(x, q)` with the default `method="linear"` (Hyndman and Fan
//!   type 7), including NumPy's two-sided `_lerp`; [`median`] is `numpy.median`.
//!
//! NaN handling follows NumPy: any NaN in the data gives NaN.

const PW_BLOCKSIZE: usize = 128;

fn pairwise(a: &[f64]) -> f64 {
    let n = a.len();
    if n < 8 {
        let mut res = 0.0;
        for &v in a {
            res += v;
        }
        res
    } else if n <= PW_BLOCKSIZE {
        let mut r = [0.0; 8];
        r.copy_from_slice(&a[..8]);
        let mut i = 8;
        while i < n - (n % 8) {
            for j in 0..8 {
                r[j] += a[i + j];
            }
            i += 8;
        }
        let mut res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]));
        while i < n {
            res += a[i];
            i += 1;
        }
        res
    } else {
        let mut n2 = n / 2;
        n2 -= n2 % 8;
        pairwise(&a[..n2]) + pairwise(&a[n2..])
    }
}

/// `numpy.sum` of a float64 vector (0 for an empty slice).
pub fn sum(x: &[f64]) -> f64 {
    pairwise(x)
}

/// `numpy.mean` (NaN for an empty slice).
pub fn mean(x: &[f64]) -> f64 {
    if x.is_empty() {
        return f64::NAN;
    }
    pairwise(x) / x.len() as f64
}

/// `numpy.var(x, ddof)`: two-pass variance `sum((x - mean)^2) / (n - ddof)`; NaN when
/// `n <= ddof`.
pub fn var(x: &[f64], ddof: usize) -> f64 {
    let n = x.len();
    if n <= ddof {
        return f64::NAN;
    }
    let m = pairwise(x) / n as f64;
    let sq: Vec<f64> = x
        .iter()
        .map(|v| {
            let d = v - m;
            d * d
        })
        .collect();
    pairwise(&sq) / (n - ddof) as f64
}

/// `numpy.std(x, ddof)` = `sqrt(var(x, ddof))`.
pub fn std(x: &[f64], ddof: usize) -> f64 {
    var(x, ddof).sqrt()
}

/// `numpy.quantile(sorted, q, method="linear")` for data already sorted ascending; `q` in [0, 1].
/// Returns NaN for empty data, for `q` outside [0, 1] or NaN, and when the data contain NaN.
pub fn quantile_sorted(sorted: &[f64], q: f64) -> f64 {
    let n = sorted.len();
    if n == 0 || q.is_nan() || !(0.0..=1.0).contains(&q) {
        return f64::NAN;
    }
    if sorted[n - 1].is_nan() || sorted[0].is_nan() {
        return f64::NAN;
    }
    // _quantile: virtual index (n - 1) * q, _get_indexes, _get_gamma, _lerp
    let vi = (n - 1) as f64 * q;
    let (prev, next, prev_f) = if vi >= (n - 1) as f64 {
        (n - 1, n - 1, -1.0)
    } else {
        let p = vi.floor();
        (p as usize, p as usize + 1, p)
    };
    let gamma = vi - prev_f;
    let a = sorted[prev];
    let b = sorted[next];
    let diff_b_a = b - a;
    if gamma >= 0.5 {
        b - diff_b_a * (1.0 - gamma)
    } else {
        a + diff_b_a * gamma
    }
}

fn sorted_copy(x: &[f64]) -> Option<Vec<f64>> {
    if x.iter().any(|v| v.is_nan()) {
        return None;
    }
    let mut s = x.to_vec();
    s.sort_by(f64::total_cmp);
    Some(s)
}

/// `numpy.quantile(x, q)` (default `method="linear"`).
pub fn quantile(x: &[f64], q: f64) -> f64 {
    match sorted_copy(x) {
        Some(s) => quantile_sorted(&s, q),
        None => f64::NAN,
    }
}

/// `numpy.quantile(x, qs)` for several probabilities (one sort).
pub fn quantiles(x: &[f64], qs: &[f64]) -> Vec<f64> {
    match sorted_copy(x) {
        Some(s) => qs.iter().map(|&q| quantile_sorted(&s, q)).collect(),
        None => vec![f64::NAN; qs.len()],
    }
}

/// `numpy.median(x)`: the middle element, or the mean of the two middle elements.
pub fn median(x: &[f64]) -> f64 {
    let Some(s) = sorted_copy(x) else {
        return f64::NAN;
    };
    let n = s.len();
    if n == 0 {
        return f64::NAN;
    }
    if n % 2 == 1 {
        s[n / 2]
    } else {
        pairwise(&s[n / 2 - 1..n / 2 + 1]) / 2.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn small_cases() {
        assert_eq!(sum(&[]), 0.0);
        assert!(mean(&[]).is_nan());
        assert_eq!(mean(&[1.0, 2.0, 3.0, 4.0]), 2.5);
        assert_eq!(var(&[1.0, 2.0, 3.0, 4.0], 0), 1.25);
        assert_eq!(var(&[1.0, 2.0, 3.0, 4.0], 1), 5.0 / 3.0);
        assert!(var(&[1.0], 1).is_nan());
        assert_eq!(median(&[3.0, 1.0, 2.0]), 2.0);
        assert_eq!(median(&[4.0, 1.0, 2.0, 3.0]), 2.5);
    }

    #[test]
    fn quantile_endpoints_and_interpolation() {
        let x = [5.0, 1.0, 4.0, 2.0, 3.0];
        assert_eq!(quantile(&x, 0.0), 1.0);
        assert_eq!(quantile(&x, 1.0), 5.0);
        assert_eq!(quantile(&x, 0.5), 3.0);
        assert_eq!(quantile(&x, 0.125), 1.5);
        assert!(quantile(&x, 1.5).is_nan());
        assert!(quantile(&[1.0, f64::NAN], 0.5).is_nan());
    }

    #[test]
    fn pairwise_matches_naive_for_exact_values() {
        let x: Vec<f64> = (0..1000).map(|i| i as f64).collect();
        assert_eq!(sum(&x), 499_500.0);
    }
}
