//! Interpolating tensor-product cubic spline on a rectangular grid, equivalent to
//! `scipy.interpolate.RectBivariateSpline(x, y, z, kx=3, ky=3, s=0)`.
//!
//! With `s = 0` FITPACK (`regrid`/`fpregr`) places the interior knots at the data points
//! `x[2], ..., x[m-3]` with four-fold end knots (the not-a-knot conditions), so the spline is the
//! unique tensor-product cubic interpolant with those knots. FITPACK computes the coefficients by
//! Givens rotations; here they are the solutions of the two collocation systems (LU with partial
//! pivoting), so the two agree to rounding. Evaluation is a port of FITPACK `fpbisp`/`fpbspl`
//! (interval search with clamping at the ends, the same summation order).

/// Error of [`RectBivariateSpline::new`].
#[derive(Debug, Clone, PartialEq)]
pub enum SplineError {
    /// At least four points are needed in each direction.
    TooFewPoints,
    /// Abscissae not strictly increasing.
    NotIncreasing,
    /// `z` is not `x.len() * y.len()`.
    Shape,
    /// The collocation matrix is singular.
    Singular,
}

const K: usize = 3;

/// Cubic spline knots for interpolation at `x` (FITPACK `s = 0`, odd degree).
fn knots(x: &[f64]) -> Vec<f64> {
    let m = x.len();
    let mut t = vec![x[0]; K + 1];
    t.extend_from_slice(&x[2..m - 2]);
    t.extend(std::iter::repeat_n(x[m - 1], K + 1));
    t
}

/// FITPACK's interval index `l` (0-based, `t[l] <= arg < t[l+1]`, `K <= l <= n-K-2`), after
/// clamping `arg` to `[t[K], t[n-K-1]]`.
fn interval(t: &[f64], x: f64) -> (usize, f64) {
    let n = t.len();
    let (tb, te) = (t[K], t[n - K - 1]);
    let mut arg = x;
    if arg < tb {
        arg = tb;
    }
    if arg > te {
        arg = te;
    }
    let mut l = K;
    while !(arg < t[l + 1] || l == n - K - 2) {
        l += 1;
    }
    (l, arg)
}

/// FITPACK `fpbspl`: the K+1 non-zero B-splines at `x` on interval `l` (0-based).
fn bspl(t: &[f64], l: usize, x: f64) -> [f64; K + 1] {
    let mut h = [0.0; K + 1];
    let mut hh = [0.0; K];
    h[0] = 1.0;
    for j in 1..=K {
        hh[..j].copy_from_slice(&h[..j]);
        h[0] = 0.0;
        for i in 1..=j {
            // 1-based li = l + i, lj = li - j with 1-based l = l0 + 1
            let li = l + i;
            let lj = li - j;
            if t[li] == t[lj] {
                h[i] = 0.0;
                continue;
            }
            let f = hh[i - 1] / (t[li] - t[lj]);
            h[i - 1] += f * (t[li] - x);
            h[i] = f * (x - t[lj]);
        }
    }
    h
}

fn collocation(x: &[f64], t: &[f64]) -> Vec<Vec<f64>> {
    let m = x.len();
    let mut a = vec![vec![0.0; m]; m];
    for (i, &xi) in x.iter().enumerate() {
        let (l, arg) = interval(t, xi);
        let h = bspl(t, l, arg);
        for (k, v) in h.iter().enumerate() {
            a[i][l - K + k] = *v;
        }
    }
    a
}

/// Solve `A X = B` for several right-hand sides (columns of `b`, row-major `m x r`).
fn solve(a: &[Vec<f64>], b: &mut [Vec<f64>]) -> Result<(), SplineError> {
    let m = a.len();
    let mut a: Vec<Vec<f64>> = a.to_vec();
    for c in 0..m {
        let p = (c..m)
            .max_by(|&i, &j| a[i][c].abs().total_cmp(&a[j][c].abs()))
            .ok_or(SplineError::Singular)?;
        if a[p][c] == 0.0 {
            return Err(SplineError::Singular);
        }
        a.swap(c, p);
        b.swap(c, p);
        for i in c + 1..m {
            let f = a[i][c] / a[c][c];
            if f == 0.0 {
                continue;
            }
            for j in c..m {
                a[i][j] -= f * a[c][j];
            }
            for j in 0..b[i].len() {
                b[i][j] -= f * b[c][j];
            }
        }
    }
    for c in (0..m).rev() {
        for j in 0..b[c].len() {
            let mut s = b[c][j];
            for k in c + 1..m {
                s -= a[c][k] * b[k][j];
            }
            b[c][j] = s / a[c][c];
        }
    }
    Ok(())
}

/// `RectBivariateSpline(x, y, z, kx=3, ky=3, s=0)`.
#[derive(Debug, Clone, PartialEq)]
pub struct RectBivariateSpline {
    tx: Vec<f64>,
    ty: Vec<f64>,
    /// Coefficients, `c[i * ny + j]` (FITPACK order).
    c: Vec<f64>,
    ny: usize,
}

impl RectBivariateSpline {
    /// Interpolant of `z[i][j] = f(x[i], y[j])` (`z` row-major, `x.len() * y.len()`).
    pub fn new(x: &[f64], y: &[f64], z: &[f64]) -> Result<Self, SplineError> {
        let (mx, my) = (x.len(), y.len());
        if mx < 4 || my < 4 {
            return Err(SplineError::TooFewPoints);
        }
        if z.len() != mx * my {
            return Err(SplineError::Shape);
        }
        if x.windows(2).any(|w| w[1] <= w[0]) || y.windows(2).any(|w| w[1] <= w[0]) {
            return Err(SplineError::NotIncreasing);
        }
        let (tx, ty) = (knots(x), knots(y));
        let (ax, ay) = (collocation(x, &tx), collocation(y, &ty));
        // Ax T = Z  (T: mx x my)
        let mut tmat: Vec<Vec<f64>> = (0..mx).map(|i| z[i * my..(i + 1) * my].to_vec()).collect();
        solve(&ax, &mut tmat)?;
        // Ay C^T = T^T  (C^T: my x mx)
        let mut ct: Vec<Vec<f64>> = (0..my)
            .map(|j| (0..mx).map(|i| tmat[i][j]).collect())
            .collect();
        solve(&ay, &mut ct)?;
        let mut c = vec![0.0; mx * my];
        for i in 0..mx {
            for j in 0..my {
                c[i * my + j] = ct[j][i];
            }
        }
        Ok(RectBivariateSpline { tx, ty, c, ny: my })
    }

    /// `ev(x, y)` (FITPACK `fpbisp` at one point).
    pub fn ev(&self, x: f64, y: f64) -> f64 {
        let (lx, ax) = interval(&self.tx, x);
        let (ly, ay) = interval(&self.ty, y);
        let h = bspl(&self.tx, lx, ax);
        let w = bspl(&self.ty, ly, ay);
        let mut sp = 0.0;
        for (i1, hv) in h.iter().enumerate() {
            let row = (lx - K + i1) * self.ny + (ly - K);
            for (j1, wv) in w.iter().enumerate() {
                sp += self.c[row + j1] * hv * wv;
            }
        }
        sp
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reproduces_grid_and_cubics() {
        let x: Vec<f64> = (0..7).map(|i| i as f64 * 0.5).collect();
        let y: Vec<f64> = (0..6).map(|i| -1.0 + i as f64 * 0.7).collect();
        let f = |a: f64, b: f64| 1.0 + a - 2.0 * b + a * a * b - 0.3 * a * a * a + b * b * b;
        let z: Vec<f64> = x
            .iter()
            .flat_map(|&a| y.iter().map(move |&b| f(a, b)))
            .collect();
        let s = RectBivariateSpline::new(&x, &y, &z).expect("spline");
        for &a in &x {
            for &b in &y {
                assert!((s.ev(a, b) - f(a, b)).abs() < 1e-12);
            }
        }
        // a bicubic polynomial is reproduced exactly between the nodes
        assert!((s.ev(1.23, 0.37) - f(1.23, 0.37)).abs() < 1e-12);
    }
}
