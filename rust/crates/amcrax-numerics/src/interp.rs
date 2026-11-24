//! Interpolation: PCHIP (port of `scipy.interpolate.PchipInterpolator`), piecewise-linear
//! (port of `numpy.interp`) and bilinear tables (the formula of the browser model).

use std::fmt;

/// Invalid interpolation data.
#[derive(Debug, Clone, PartialEq)]
pub enum InterpError {
    /// Fewer points than the method needs.
    TooFewPoints { needed: usize, got: usize },
    /// `x` and `y` (or the grid and the table) have different lengths.
    LengthMismatch,
    /// The abscissae are not strictly increasing (or contain NaN).
    NotIncreasing,
    /// A value is not finite.
    NonFinite,
}

impl fmt::Display for InterpError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            InterpError::TooFewPoints { needed, got } => {
                write!(f, "at least {needed} points are needed, got {got}")
            }
            InterpError::LengthMismatch => write!(f, "array lengths do not match"),
            InterpError::NotIncreasing => write!(f, "x must be a strictly increasing sequence"),
            InterpError::NonFinite => write!(f, "values must be finite"),
        }
    }
}

impl std::error::Error for InterpError {}

/// `numpy.sign` for floats (`NaN` for NaN).
#[inline]
fn np_sign(v: f64) -> f64 {
    if v.is_nan() {
        f64::NAN
    } else if v == 0.0 {
        0.0
    } else {
        v.signum()
    }
}

/// `np.sign(a) != np.sign(b)` (true when either is NaN, as in NumPy).
#[inline]
fn sign_differs(a: f64, b: f64) -> bool {
    let (sa, sb) = (np_sign(a), np_sign(b));
    sa != sb
}

/// Piecewise cubic Hermite interpolating polynomial with SciPy's derivative rule
/// (Fritsch-Butland weighted harmonic mean, one-sided three-point end conditions with
/// shape preservation, `PchipInterpolator._edge_case`). Evaluation outside the data
/// extrapolates with the end polynomials (SciPy `extrapolate=True`).
#[derive(Debug, Clone, PartialEq)]
pub struct Pchip {
    x: Vec<f64>,
    d: Vec<f64>,
    /// Power-basis coefficients per interval, highest power first (SciPy `PPoly.c[:, i]`).
    c: Vec<[f64; 4]>,
}

impl Pchip {
    /// Build the interpolant of `y(x)`; `x` strictly increasing, at least two points.
    pub fn new(x: &[f64], y: &[f64]) -> Result<Self, InterpError> {
        let n = x.len();
        if y.len() != n {
            return Err(InterpError::LengthMismatch);
        }
        if n < 2 {
            return Err(InterpError::TooFewPoints { needed: 2, got: n });
        }
        if x.iter().chain(y.iter()).any(|v| !v.is_finite()) {
            return Err(InterpError::NonFinite);
        }
        if x.windows(2).any(|w| w[1] - w[0] <= 0.0) {
            return Err(InterpError::NotIncreasing);
        }
        let d = Self::find_derivatives(x, y);
        // CubicHermiteSpline.__init__
        let mut c = Vec::with_capacity(n - 1);
        for i in 0..n - 1 {
            let dx = x[i + 1] - x[i];
            let slope = (y[i + 1] - y[i]) / dx;
            let t = (d[i] + d[i + 1] - 2.0 * slope) / dx;
            c.push([t / dx, (slope - d[i]) / dx - t, d[i], y[i]]);
        }
        Ok(Pchip {
            x: x.to_vec(),
            d,
            c,
        })
    }

    /// `PchipInterpolator._edge_case`.
    fn edge_case(h0: f64, h1: f64, m0: f64, m1: f64) -> f64 {
        let d = ((2.0 * h0 + h1) * m0 - h0 * m1) / (h0 + h1);
        let mask = sign_differs(d, m0);
        let mask2 = sign_differs(m0, m1) && (d.abs() > 3.0 * m0.abs());
        if mask {
            0.0
        } else if mask2 {
            3.0 * m0
        } else {
            d
        }
    }

    /// `PchipInterpolator._find_derivatives`.
    fn find_derivatives(x: &[f64], y: &[f64]) -> Vec<f64> {
        let n = x.len();
        let hk: Vec<f64> = (0..n - 1).map(|i| x[i + 1] - x[i]).collect();
        let mk: Vec<f64> = (0..n - 1).map(|i| (y[i + 1] - y[i]) / hk[i]).collect();
        if n == 2 {
            return vec![mk[0], mk[0]];
        }
        let mut dk = vec![0.0; n];
        for k in 1..n - 1 {
            let (m_prev, m_next) = (mk[k - 1], mk[k]);
            let condition = sign_differs(m_next, m_prev) || m_next == 0.0 || m_prev == 0.0;
            if !condition {
                let w1 = 2.0 * hk[k] + hk[k - 1];
                let w2 = hk[k] + 2.0 * hk[k - 1];
                let whmean = (w1 / m_prev + w2 / m_next) / (w1 + w2);
                dk[k] = 1.0 / whmean;
            }
        }
        dk[0] = Self::edge_case(hk[0], hk[1], mk[0], mk[1]);
        dk[n - 1] = Self::edge_case(hk[n - 2], hk[n - 3], mk[n - 2], mk[n - 3]);
        dk
    }

    /// Knot abscissae.
    pub fn x(&self) -> &[f64] {
        &self.x
    }

    /// Derivatives at the knots.
    pub fn derivatives(&self) -> &[f64] {
        &self.d
    }

    /// Interval index as SciPy `find_interval` with extrapolation (`None` for NaN).
    fn interval(&self, xv: f64) -> Option<usize> {
        let n = self.x.len();
        let (a, b) = (self.x[0], self.x[n - 1]);
        if !(a..=b).contains(&xv) {
            if xv < a {
                Some(0)
            } else if xv > b {
                Some(n - 2)
            } else {
                None
            }
        } else if xv == b {
            Some(n - 2)
        } else {
            // largest i with x[i] <= xv (unique for strictly increasing x)
            Some(self.x.partition_point(|v| *v <= xv) - 1)
        }
    }

    /// Value at `xv` (NaN for NaN).
    pub fn eval(&self, xv: f64) -> f64 {
        let Some(i) = self.interval(xv) else {
            return f64::NAN;
        };
        let s = xv - self.x[i];
        let c = &self.c[i];
        // _ppoly.evaluate_poly1 with dx = 0: res += c[k-1-kp] * z * 1.0 (the factor 1.0 is exact); z *= s
        let mut res = 0.0;
        let mut z = 1.0;
        for kp in 0..4 {
            res += c[3 - kp] * z;
            if kp < 3 {
                z *= s;
            }
        }
        res
    }

    /// Values at several points.
    pub fn eval_many(&self, xs: &[f64]) -> Vec<f64> {
        xs.iter().map(|&v| self.eval(v)).collect()
    }
}

/// Piecewise-linear interpolation, a port of `numpy.interp(x, xp, fp)` with the default
/// `left = fp[0]`, `right = fp[-1]`. `xp` must be increasing (not checked, as NumPy).
/// Returns NaN for an empty table.
pub fn interp_linear(x: f64, xp: &[f64], fp: &[f64]) -> f64 {
    let n = xp.len().min(fp.len());
    if n == 0 {
        return f64::NAN;
    }
    if n == 1 {
        // NumPy's single-point path returns fp[0] for every x, including NaN
        return fp[0];
    }
    if x.is_nan() {
        return x;
    }
    // binary_search_with_guess: -1 below, n above, else the largest j with xp[j] <= x
    if x < xp[0] {
        return fp[0];
    }
    if x > xp[n - 1] {
        return fp[n - 1];
    }
    let j = xp[..n].partition_point(|v| *v <= x) - 1;
    if j == n - 1 || xp[j] == x {
        return fp[j];
    }
    let slope = (fp[j + 1] - fp[j]) / (xp[j + 1] - xp[j]);
    let mut r = slope * (x - xp[j]) + fp[j];
    if r.is_nan() {
        r = slope * (x - xp[j + 1]) + fp[j + 1];
        if r.is_nan() && fp[j] == fp[j + 1] {
            r = fp[j];
        }
    }
    r
}

/// Behaviour of [`Bilinear`] outside the grid.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutOfRange {
    /// Extrapolate linearly from the edge cell (browser `pfr.ts` viscosity table).
    Extrapolate,
    /// Clamp the coordinate to the grid (browser `process.ts` grid).
    Clamp,
}

/// Bilinear interpolation on a rectangular grid, with the cell search and the expression of the
/// browser model (`frontend/src/sim/pfr.ts`, `process.ts`):
/// `(1-t)((1-u) z00 + u z01) + t((1-u) z10 + u z11)`.
#[derive(Debug, Clone, PartialEq)]
pub struct Bilinear {
    xs: Vec<f64>,
    ys: Vec<f64>,
    /// Row-major table: `z[i * ny + j]` at `(xs[i], ys[j])`.
    z: Vec<f64>,
    mode: OutOfRange,
}

impl Bilinear {
    /// `z[i][j]` is the value at `(xs[i], ys[j])`; both axes strictly increasing, at least two
    /// points each.
    pub fn new(
        xs: &[f64],
        ys: &[f64],
        z: &[Vec<f64>],
        mode: OutOfRange,
    ) -> Result<Self, InterpError> {
        for axis in [xs, ys] {
            if axis.len() < 2 {
                return Err(InterpError::TooFewPoints {
                    needed: 2,
                    got: axis.len(),
                });
            }
            if axis.iter().any(|v| !v.is_finite()) {
                return Err(InterpError::NonFinite);
            }
            if axis.windows(2).any(|w| w[1] - w[0] <= 0.0) {
                return Err(InterpError::NotIncreasing);
            }
        }
        if z.len() != xs.len() || z.iter().any(|row| row.len() != ys.len()) {
            return Err(InterpError::LengthMismatch);
        }
        Ok(Bilinear {
            xs: xs.to_vec(),
            ys: ys.to_vec(),
            z: z.iter().flatten().copied().collect(),
            mode,
        })
    }

    /// Cell index and local coordinate (`locate` / `bil` of the browser code).
    fn locate(v: &[f64], q: f64, mode: OutOfRange) -> (usize, f64) {
        let n = v.len();
        let mut i = 0;
        while i < n - 2 && q > v[i + 1] {
            i += 1;
        }
        let qc = match mode {
            OutOfRange::Extrapolate => q,
            // Math.min(Math.max(q, lo), hi), which propagates NaN
            OutOfRange::Clamp => {
                if q < v[0] {
                    v[0]
                } else if q > v[n - 1] {
                    v[n - 1]
                } else {
                    q
                }
            }
        };
        (i, (qc - v[i]) / (v[i + 1] - v[i]))
    }

    /// Value at `(x, y)`.
    pub fn eval(&self, x: f64, y: f64) -> f64 {
        let ny = self.ys.len();
        let (i, ti) = Self::locate(&self.xs, x, self.mode);
        let (j, tj) = Self::locate(&self.ys, y, self.mode);
        let g = |a: usize, b: usize| self.z[a * ny + b];
        (1.0 - ti) * ((1.0 - tj) * g(i, j) + tj * g(i, j + 1))
            + ti * ((1.0 - tj) * g(i + 1, j) + tj * g(i + 1, j + 1))
    }

    /// Whether `(x, y)` lies outside the grid.
    pub fn outside(&self, x: f64, y: f64) -> bool {
        fn out(v: &[f64], q: f64) -> bool {
            if q < v[0] {
                return true;
            }
            q > v[v.len() - 1]
        }
        out(&self.xs, x) || out(&self.ys, y)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pchip_reproduces_data_and_is_monotone() {
        let x = [0.0, 1.0, 2.0, 3.0, 4.0];
        let y = [0.0, 0.1, 0.9, 1.0, 1.0];
        let p = Pchip::new(&x, &y).unwrap();
        for (xi, yi) in x.iter().zip(&y) {
            assert_eq!(p.eval(*xi), *yi);
        }
        let mut prev = p.eval(0.0);
        for k in 1..=400 {
            let v = p.eval(k as f64 * 0.01);
            assert!(v >= prev - 1e-15, "not monotone at {k}");
            prev = v;
        }
        assert!(p.eval(f64::NAN).is_nan());
    }

    #[test]
    fn pchip_two_points_is_linear() {
        let p = Pchip::new(&[0.0, 2.0], &[1.0, 5.0]).unwrap();
        assert_eq!(p.eval(1.0), 3.0);
        assert_eq!(p.eval(3.0), 7.0);
    }

    #[test]
    fn pchip_rejects_bad_input() {
        assert_eq!(
            Pchip::new(&[0.0, 0.0], &[1.0, 2.0]),
            Err(InterpError::NotIncreasing)
        );
        assert_eq!(
            Pchip::new(&[0.0], &[1.0]),
            Err(InterpError::TooFewPoints { needed: 2, got: 1 })
        );
        assert_eq!(
            Pchip::new(&[0.0, 1.0], &[1.0]),
            Err(InterpError::LengthMismatch)
        );
    }

    #[test]
    fn linear_matches_numpy_rules() {
        let xp = [1.0, 2.0, 4.0];
        let fp = [10.0, 20.0, 0.0];
        assert_eq!(interp_linear(0.0, &xp, &fp), 10.0);
        assert_eq!(interp_linear(5.0, &xp, &fp), 0.0);
        assert_eq!(interp_linear(1.5, &xp, &fp), 15.0);
        assert_eq!(interp_linear(3.0, &xp, &fp), 10.0);
        assert_eq!(interp_linear(4.0, &xp, &fp), 0.0);
        assert!(interp_linear(f64::NAN, &xp, &fp).is_nan());
    }

    #[test]
    fn bilinear_corners_and_center() {
        let b = Bilinear::new(
            &[0.0, 1.0],
            &[0.0, 2.0],
            &[vec![1.0, 3.0], vec![5.0, 7.0]],
            OutOfRange::Clamp,
        )
        .unwrap();
        assert_eq!(b.eval(0.0, 0.0), 1.0);
        assert_eq!(b.eval(1.0, 2.0), 7.0);
        assert_eq!(b.eval(0.5, 1.0), 4.0);
        assert_eq!(b.eval(-1.0, 0.0), 1.0);
        assert!(b.outside(-1.0, 0.0));
        let e = Bilinear::new(
            &[0.0, 1.0],
            &[0.0, 2.0],
            &[vec![1.0, 3.0], vec![5.0, 7.0]],
            OutOfRange::Extrapolate,
        )
        .unwrap();
        assert_eq!(e.eval(2.0, 0.0), 9.0);
    }
}
