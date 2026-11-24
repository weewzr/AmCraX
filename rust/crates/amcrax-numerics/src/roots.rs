//! Bracketing root finder: an exact port of SciPy's `brentq`.
//!
//! The algorithm is `scipy/optimize/Zeros/brentq.c` (Chuck Harris's version of Brent's method,
//! BSD-3 licence) together with the checks done by `scipy.optimize.brentq` in Python: the
//! tolerance checks (`xtol > 0`, `rtol >= 4 eps`) and the NaN check after every function call.
//! The same IEEE operations are done in the same order, so for the same function values the
//! iterates, the root, the iteration count and the number of function calls are identical to
//! SciPy's (verified bit for bit against SciPy 1.18 in `tests/golden.rs`).

use std::convert::Infallible;
use std::fmt;

/// SciPy's default `xtol`.
pub const XTOL_DEFAULT: f64 = 2e-12;
/// SciPy's default (and minimum) `rtol`: `4 * f64::EPSILON` = 8.881784197001252e-16.
pub const RTOL_DEFAULT: f64 = 4.0 * f64::EPSILON;
/// SciPy's default `maxiter`.
pub const MAXITER_DEFAULT: u32 = 100;

/// Tolerances of [`brentq`]; `Default` gives SciPy's defaults.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BrentOptions {
    /// Absolute tolerance (must be > 0).
    pub xtol: f64,
    /// Relative tolerance (must be >= `4 * f64::EPSILON`).
    pub rtol: f64,
    /// Maximum number of iterations.
    pub maxiter: u32,
}

impl Default for BrentOptions {
    fn default() -> Self {
        BrentOptions {
            xtol: XTOL_DEFAULT,
            rtol: RTOL_DEFAULT,
            maxiter: MAXITER_DEFAULT,
        }
    }
}

impl BrentOptions {
    /// SciPy defaults with a different `xtol`.
    pub fn with_xtol(xtol: f64) -> Self {
        BrentOptions {
            xtol,
            ..Self::default()
        }
    }
}

/// Result of a root search (SciPy `RootResults`).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Root {
    /// The root estimate.
    pub x: f64,
    /// Iterations done. SciPy leaves this field uninitialised when `f(a) == 0` or `f(b) == 0`;
    /// here it is 0 in that case.
    pub iterations: u32,
    /// Function evaluations done.
    pub function_calls: u32,
    /// Whether the tolerance was reached.
    pub converged: bool,
}

/// Failure of [`brentq`] / [`brentq_try`].
#[derive(Debug, Clone, PartialEq)]
pub enum BrentError<E> {
    /// `xtol <= 0` or `rtol < 4 eps` (SciPy raises `ValueError`).
    InvalidTolerance { xtol: f64, rtol: f64 },
    /// `f(a)` and `f(b)` have the same sign (SciPy raises `ValueError`).
    SignError { fa: f64, fb: f64 },
    /// The function returned NaN at `x` (SciPy raises `ValueError`).
    NanValue { x: f64, function_calls: u32 },
    /// `maxiter` iterations without convergence (SciPy raises `RuntimeError` when `disp=True`);
    /// the last iterate is kept.
    NotConverged(Root),
    /// The function itself failed.
    Function(E),
}

impl<E: fmt::Display> fmt::Display for BrentError<E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BrentError::InvalidTolerance { xtol, rtol } => {
                write!(f, "invalid tolerance (xtol = {xtol:e}, rtol = {rtol:e})")
            }
            BrentError::SignError { fa, fb } => write!(
                f,
                "f(a) and f(b) must have different signs (f(a) = {fa:e}, f(b) = {fb:e})"
            ),
            BrentError::NanValue { x, .. } => {
                write!(
                    f,
                    "the function value at x={x} is NaN; solver cannot continue"
                )
            }
            BrentError::NotConverged(r) => write!(
                f,
                "failed to converge after {} iterations, value is {}",
                r.iterations, r.x
            ),
            BrentError::Function(e) => write!(f, "function evaluation failed: {e}"),
        }
    }
}

impl<E: fmt::Debug + fmt::Display> std::error::Error for BrentError<E> {}

/// Find a root of `f` in `[a, b]` (SciPy `brentq`); `f` cannot fail.
pub fn brentq<F>(
    mut f: F,
    a: f64,
    b: f64,
    opts: BrentOptions,
) -> Result<Root, BrentError<Infallible>>
where
    F: FnMut(f64) -> f64,
{
    brentq_try(|x| Ok::<f64, Infallible>(f(x)), a, b, opts)
}

/// Find a root of a fallible `f` in `[a, b]` (SciPy `brentq`). An error returned by `f` stops the
/// search and is passed through as [`BrentError::Function`].
pub fn brentq_try<F, E>(
    mut f: F,
    xa: f64,
    xb: f64,
    opts: BrentOptions,
) -> Result<Root, BrentError<E>>
where
    F: FnMut(f64) -> Result<f64, E>,
{
    let BrentOptions {
        xtol,
        rtol,
        maxiter,
    } = opts;
    if xtol <= 0.0 || rtol < RTOL_DEFAULT {
        return Err(BrentError::InvalidTolerance { xtol, rtol });
    }
    let mut calls: u32 = 0;
    let mut eval = |x: f64, calls: &mut u32| -> Result<f64, BrentError<E>> {
        let v = f(x).map_err(BrentError::Function)?;
        *calls += 1;
        if v.is_nan() {
            return Err(BrentError::NanValue {
                x,
                function_calls: *calls,
            });
        }
        Ok(v)
    };

    let mut xpre = xa;
    let mut xcur = xb;
    let mut xblk = 0.0_f64;
    let mut fblk = 0.0_f64;
    let mut spre = 0.0_f64;
    let mut scur = 0.0_f64;

    let mut fpre = eval(xpre, &mut calls)?;
    let mut fcur = eval(xcur, &mut calls)?;
    if fpre == 0.0 {
        return Ok(Root {
            x: xpre,
            iterations: 0,
            function_calls: calls,
            converged: true,
        });
    }
    if fcur == 0.0 {
        return Ok(Root {
            x: xcur,
            iterations: 0,
            function_calls: calls,
            converged: true,
        });
    }
    if fpre.is_sign_negative() == fcur.is_sign_negative() {
        return Err(BrentError::SignError { fa: fpre, fb: fcur });
    }

    let mut iterations: u32 = 0;
    for _ in 0..maxiter {
        iterations += 1;
        if fpre != 0.0 && fcur != 0.0 && fpre.is_sign_negative() != fcur.is_sign_negative() {
            xblk = xpre;
            fblk = fpre;
            scur = xcur - xpre;
            spre = scur;
        }
        if fblk.abs() < fcur.abs() {
            xpre = xcur;
            xcur = xblk;
            xblk = xpre;

            fpre = fcur;
            fcur = fblk;
            fblk = fpre;
        }

        let delta = (xtol + rtol * xcur.abs()) / 2.0;
        let sbis = (xblk - xcur) / 2.0;
        if fcur == 0.0 || sbis.abs() < delta {
            return Ok(Root {
                x: xcur,
                iterations,
                function_calls: calls,
                converged: true,
            });
        }

        if spre.abs() > delta && fcur.abs() < fpre.abs() {
            let stry = if xpre == xblk {
                // interpolate
                -fcur * (xcur - xpre) / (fcur - fpre)
            } else {
                // extrapolate
                let dpre = (fpre - fcur) / (xpre - xcur);
                let dblk = (fblk - fcur) / (xblk - xcur);
                -fcur * (fblk * dblk - fpre * dpre) / (dblk * dpre * (fblk - fpre))
            };
            if 2.0 * stry.abs() < c_min(spre.abs(), 3.0 * sbis.abs() - delta) {
                // good short step
                spre = scur;
                scur = stry;
            } else {
                // bisect
                spre = sbis;
                scur = sbis;
            }
        } else {
            // bisect
            spre = sbis;
            scur = sbis;
        }

        xpre = xcur;
        fpre = fcur;
        if scur.abs() > delta {
            xcur += scur;
        } else {
            xcur += if sbis > 0.0 { delta } else { -delta };
        }

        fcur = eval(xcur, &mut calls)?;
    }
    Err(BrentError::NotConverged(Root {
        x: xcur,
        iterations,
        function_calls: calls,
        converged: false,
    }))
}

/// The C macro `MIN(a, b)` = `((a) < (b) ? (a) : (b))` (differs from `f64::min` for NaN).
#[inline]
fn c_min(a: f64, b: f64) -> f64 {
    if a < b { a } else { b }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_cubic_root() {
        let r = brentq(
            |x| x * x * x - 2.0 * x - 5.0,
            2.0,
            3.0,
            BrentOptions::default(),
        )
        .unwrap();
        assert!((r.x - 2.09455148154233).abs() < 1e-12);
        assert!(r.converged);
        assert_eq!(r.function_calls, r.iterations + 1);
    }

    #[test]
    fn endpoint_root_returns_endpoint() {
        let r = brentq(|x| x - 2.0, 2.0, 5.0, BrentOptions::default()).unwrap();
        assert_eq!(r.x, 2.0);
        assert_eq!(r.function_calls, 2);
        let r = brentq(|x| x - 5.0, 2.0, 5.0, BrentOptions::default()).unwrap();
        assert_eq!(r.x, 5.0);
    }

    #[test]
    fn sign_error() {
        let e = brentq(|x| x * x + 1.0, -1.0, 1.0, BrentOptions::default()).unwrap_err();
        assert!(matches!(e, BrentError::SignError { .. }));
    }

    #[test]
    fn invalid_tolerances() {
        let o = BrentOptions {
            xtol: 0.0,
            ..BrentOptions::default()
        };
        assert!(matches!(
            brentq(|x| x, -1.0, 1.0, o),
            Err(BrentError::InvalidTolerance { .. })
        ));
        let o = BrentOptions {
            rtol: 1e-16,
            ..BrentOptions::default()
        };
        assert!(matches!(
            brentq(|x| x, -1.0, 1.0, o),
            Err(BrentError::InvalidTolerance { .. })
        ));
    }

    #[test]
    fn nan_is_an_error() {
        let e = brentq(f64::sqrt, -1.0, 4.0, BrentOptions::default()).unwrap_err();
        assert!(matches!(
            e,
            BrentError::NanValue {
                function_calls: 1,
                ..
            }
        ));
    }

    #[test]
    fn not_converged_keeps_last_iterate() {
        let o = BrentOptions {
            maxiter: 3,
            ..BrentOptions::default()
        };
        match brentq(|x| x * x * x - 2.0 * x - 5.0, 2.0, 3.0, o) {
            Err(BrentError::NotConverged(r)) => {
                assert_eq!(r.iterations, 3);
                assert!(!r.converged);
                assert!(r.x > 2.0 && r.x < 3.0);
            }
            other => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn function_error_is_passed_through() {
        let e = brentq_try(
            |x| if x > 2.5 { Err("too hot") } else { Ok(x - 2.2) },
            2.0,
            3.0,
            BrentOptions::default(),
        )
        .unwrap_err();
        assert_eq!(e, BrentError::Function("too hot"));
    }

    #[test]
    fn respects_xtol() {
        let r = brentq(f64::ln, 0.5, 5.0, BrentOptions::with_xtol(0.02)).unwrap();
        assert!((r.x - 1.0).abs() < 0.02);
    }
}
