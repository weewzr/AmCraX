//! Python and NumPy floating-point semantics that the port reproduces exactly.
//!
//! * [`py_sum`]: the builtin `sum()` of floats. Since Python 3.12 it is a Neumaier-compensated
//!   sum (CPython `builtin_sum_impl`), not a left-to-right sum; the reference runs on 3.12.
//! * [`py_min`], [`py_max`]: the builtins `min(a, b)` and `max(a, b)` (first argument kept on
//!   ties and on NaN comparisons).
//! * [`linspace`]: `numpy.linspace(start, stop, num)` (`i * step + start`, last point `stop`).

/// Python `sum(xs)` of floats (start value `0`), bit for bit as CPython 3.12.
pub fn py_sum<I: IntoIterator<Item = f64>>(xs: I) -> f64 {
    let mut it = xs.into_iter();
    let Some(first) = it.next() else {
        return 0.0;
    };
    // int 0 + float x
    let mut f = 0.0 + first;
    let mut c = 0.0_f64;
    for x in it {
        let t = f + x;
        if f.abs() >= x.abs() {
            c += (f - t) + x;
        } else {
            c += (x - t) + f;
        }
        f = t;
    }
    if c != 0.0 && c.is_finite() {
        f += c;
    }
    f
}

/// Python `min(a, b)`.
#[inline]
pub fn py_min(a: f64, b: f64) -> f64 {
    if b < a { b } else { a }
}

/// Python `max(a, b)`.
#[inline]
pub fn py_max(a: f64, b: f64) -> f64 {
    if b > a { b } else { a }
}

/// Python `max(iterable)` of floats (`None` for an empty iterable).
pub fn py_max_iter<I: IntoIterator<Item = f64>>(xs: I) -> Option<f64> {
    let mut it = xs.into_iter();
    let mut m = it.next()?;
    for x in it {
        if x > m {
            m = x;
        }
    }
    Some(m)
}

/// `numpy.linspace(start, stop, num)` with `endpoint=True`.
pub fn linspace(start: f64, stop: f64, num: usize) -> Vec<f64> {
    match num {
        0 => Vec::new(),
        1 => vec![start],
        _ => {
            let div = (num - 1) as f64;
            let step = (stop - start) / div;
            let mut v: Vec<f64> = (0..num).map(|i| i as f64 * step + start).collect();
            v[num - 1] = stop;
            v
        }
    }
}

/// Python `format(x, f".{prec}g")` (`{x:g}` is `prec = 6`).
pub fn fmt_g(x: f64, prec: usize) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf" } else { "-inf" }.into();
    }
    if x == 0.0 {
        return if x.is_sign_negative() { "-0" } else { "0" }.into();
    }
    let p = prec.max(1);
    let s = format!("{:.*e}", p - 1, x);
    let (mant, exp) = s.split_once('e').unwrap_or((s.as_str(), "0"));
    let e: i32 = exp.parse().unwrap_or(0);
    if e < -4 || e >= p as i32 {
        format!(
            "{}e{}{:02}",
            strip_zeros(mant),
            if e < 0 { '-' } else { '+' },
            e.abs()
        )
    } else {
        let decimals = (p as i32 - 1 - e).max(0) as usize;
        strip_zeros(&format!("{x:.decimals$}"))
    }
}

/// Python `repr(x)` / `str(x)` of a float (shortest round-trip digits; scientific notation when
/// the decimal exponent is below -4 or at least 16).
pub fn py_repr(x: f64) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf" } else { "-inf" }.into();
    }
    if x == 0.0 {
        return if x.is_sign_negative() { "-0.0" } else { "0.0" }.into();
    }
    let s = format!("{:e}", x.abs());
    let (m, e) = s.split_once('e').unwrap_or((s.as_str(), "0"));
    let e: i32 = e.parse().unwrap_or(0);
    let digits: String = m.chars().filter(|c| *c != '.').collect();
    let sign = if x < 0.0 { "-" } else { "" };
    let n = digits.len() as i32;
    if (-4..16).contains(&e) {
        let body = if e >= 0 {
            if n <= e + 1 {
                format!("{digits}{}.0", "0".repeat((e + 1 - n) as usize))
            } else {
                let k = (e + 1) as usize;
                format!("{}.{}", &digits[..k], &digits[k..])
            }
        } else {
            format!("0.{}{digits}", "0".repeat((-e - 1) as usize))
        };
        format!("{sign}{body}")
    } else {
        let mant = if n > 1 {
            format!("{}.{}", &digits[..1], &digits[1..])
        } else {
            digits.clone()
        };
        format!(
            "{sign}{mant}e{}{:02}",
            if e < 0 { '-' } else { '+' },
            e.abs()
        )
    }
}

/// Python `format(x, ".{prec}f")`.
pub fn fmt_f(x: f64, prec: usize) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf" } else { "-inf" }.into();
    }
    format!("{x:.prec$}")
}

fn strip_zeros(s: &str) -> String {
    if s.contains('.') {
        s.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        s.to_string()
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn format_g() {
        use super::fmt_g;
        assert_eq!(fmt_g(1e-6, 6), "1e-06");
        assert_eq!(fmt_g(20.0, 6), "20");
        assert_eq!(fmt_g(0.0370249404, 6), "0.0370249");
        assert_eq!(fmt_g(1e6, 6), "1e+06");
        assert_eq!(fmt_g(123456.7, 6), "123457");
        assert_eq!(fmt_g(2.5, 6), "2.5");
    }

    #[test]
    fn python_repr() {
        use super::py_repr;
        assert_eq!(py_repr(0.75), "0.75");
        assert_eq!(py_repr(5.0), "5.0");
        assert_eq!(py_repr(100.0), "100.0");
        assert_eq!(py_repr(1e-5), "1e-05");
        assert_eq!(py_repr(1.5e-7), "1.5e-07");
        assert_eq!(py_repr(0.0001), "0.0001");
        assert_eq!(py_repr(1e16), "1e+16");
        assert_eq!(py_repr(-2.25), "-2.25");
        assert_eq!(py_repr(0.1 + 0.2), "0.30000000000000004");
    }

    use super::*;

    #[test]
    fn compensated_sum() {
        assert_eq!(py_sum([0.1, 0.2, 0.3]), 0.6);
        assert_eq!(0.1 + 0.2 + 0.3, 0.6000000000000001);
        assert_eq!(py_sum([1e100, 1.0, -1e100]), 1.0);
        assert_eq!(py_sum(std::iter::empty()), 0.0);
        assert!(py_sum([f64::INFINITY, 1.0]).is_infinite());
    }

    #[test]
    fn linspace_matches_numpy() {
        assert_eq!(linspace(250.0, 600.0, 351)[1], 251.0);
        let v = linspace(0.0, 1.0, 3);
        assert_eq!(v, vec![0.0, 0.5, 1.0]);
        assert_eq!(py_max_iter([1.0, f64::NAN, 3.0]), Some(3.0));
        assert_eq!(py_min(1.0, 1.0), 1.0);
    }
}
