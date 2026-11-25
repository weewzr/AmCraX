//! Real roots of cubic polynomials (analytic solution with Newton polishing).
//!
//! The Peng-Robinson compressibility equation is a monic cubic; Python solves it with
//! `numpy.roots` (companion-matrix eigenvalues) and keeps the roots with `|imag| < 1e-10`. The
//! analytic solution used here agrees with NumPy to about 1e-15 relative for well-separated roots
//! (verified at 1e-10 in `tests/golden.rs`). Near a double root both methods lose accuracy (about
//! `sqrt(eps)`), and the decision "one or three real roots" can differ between them; stage 1 checks
//! the Peng-Robinson root selection separately on its own tables.

/// Real roots of a cubic, counted with multiplicity, in ascending order.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CubicRoots {
    roots: [f64; 3],
    n: usize,
}

impl CubicRoots {
    /// The real roots (one or three values) in ascending order.
    pub fn as_slice(&self) -> &[f64] {
        &self.roots[..self.n]
    }

    /// Number of real roots (1 or 3).
    pub fn len(&self) -> usize {
        self.n
    }

    /// Always false (a real cubic has at least one real root); provided for API completeness.
    pub fn is_empty(&self) -> bool {
        self.n == 0
    }

    /// Smallest real root.
    pub fn min(&self) -> f64 {
        self.roots[0]
    }

    /// Largest real root.
    pub fn max(&self) -> f64 {
        self.roots[self.n - 1]
    }
}

#[inline]
fn cubic_value(z: f64, a2: f64, a1: f64, a0: f64) -> f64 {
    ((z + a2) * z + a1) * z + a0
}

/// Up to four Newton steps on the cubic, each kept only if it reduces |p(z)|.
fn polish(z: f64, a2: f64, a1: f64, a0: f64) -> f64 {
    let mut z = z;
    let mut fz = cubic_value(z, a2, a1, a0);
    for _ in 0..4 {
        if fz == 0.0 {
            break;
        }
        let dfz = (3.0 * z + 2.0 * a2) * z + a1;
        if dfz == 0.0 || !dfz.is_finite() {
            break;
        }
        let zn = z - fz / dfz;
        let fzn = cubic_value(zn, a2, a1, a0);
        if fzn.abs() < fz.abs() {
            z = zn;
            fz = fzn;
        } else {
            break;
        }
    }
    z
}

/// Real roots of the monic cubic `z^3 + a2 z^2 + a1 z + a0`.
///
/// Uses `Q = (a2^2 - 3 a1) / 9`, `R = (2 a2^3 - 9 a2 a1 + 27 a0) / 54`: three real roots
/// (trigonometric form) when `R^2 < Q^3`, otherwise one real root (Cardano, written to avoid
/// cancellation); `R^2 == Q^3` exactly gives a double root. Every root is then polished with
/// Newton's method on the original polynomial.
pub fn cubic_real_roots(a2: f64, a1: f64, a0: f64) -> CubicRoots {
    let q = (a2 * a2 - 3.0 * a1) / 9.0;
    let r = (2.0 * a2 * a2 * a2 - 9.0 * a2 * a1 + 27.0 * a0) / 54.0;
    let q3 = q * q * q;
    let r2 = r * r;
    let shift = a2 / 3.0;
    let mut out = [0.0; 3];
    let n = if r2 < q3 {
        // three distinct real roots
        let sq = q.sqrt();
        let cos_arg = (r / (sq * sq * sq)).clamp(-1.0, 1.0);
        let theta = cos_arg.acos();
        let two_pi = 2.0 * std::f64::consts::PI;
        out[0] = -2.0 * sq * (theta / 3.0).cos() - shift;
        out[1] = -2.0 * sq * ((theta + two_pi) / 3.0).cos() - shift;
        out[2] = -2.0 * sq * ((theta - two_pi) / 3.0).cos() - shift;
        3
    } else {
        let a = -r.signum() * (r.abs() + (r2 - q3).sqrt()).cbrt();
        let b = if a == 0.0 { 0.0 } else { q / a };
        out[0] = (a + b) - shift;
        if r2 == q3 && q != 0.0 {
            // double root
            out[1] = -0.5 * (a + b) - shift;
            out[2] = out[1];
            3
        } else if q == 0.0 && r == 0.0 {
            // triple root
            out[1] = out[0];
            out[2] = out[0];
            3
        } else {
            1
        }
    };
    for z in out.iter_mut().take(n) {
        *z = polish(*z, a2, a1, a0);
    }
    out[..n].sort_by(f64::total_cmp);
    CubicRoots { roots: out, n }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn three_known_roots() {
        let r = cubic_real_roots(-6.0, 11.0, -6.0);
        assert_eq!(r.len(), 3);
        for (got, want) in r.as_slice().iter().zip([1.0, 2.0, 3.0]) {
            assert!((got - want).abs() < 1e-14);
        }
    }

    #[test]
    fn one_real_root() {
        // (z - 2)(z^2 + 1) = z^3 - 2 z^2 + z - 2
        let r = cubic_real_roots(-2.0, 1.0, -2.0);
        assert_eq!(r.len(), 1);
        assert!((r.min() - 2.0).abs() < 1e-14);
    }

    #[test]
    fn triple_root() {
        // (z - 1)^3 = z^3 - 3 z^2 + 3 z - 1
        let r = cubic_real_roots(-3.0, 3.0, -1.0);
        assert!(r.as_slice().iter().all(|z| (z - 1.0).abs() < 1e-5));
    }

    #[test]
    fn roots_are_sorted_and_satisfy_polynomial() {
        for &(a2, a1, a0) in &[(0.3, -2.0, 0.1), (-0.98, 0.05, -0.001), (5.0, 1.0, -30.0)] {
            let r = cubic_real_roots(a2, a1, a0);
            let s = r.as_slice();
            for w in s.windows(2) {
                assert!(w[0] <= w[1]);
            }
            for &z in s {
                let scale =
                    1.0 + z.abs().powi(3) + a2.abs() * z * z + a1.abs() * z.abs() + a0.abs();
                assert!(cubic_value(z, a2, a1, a0).abs() < 1e-13 * scale);
            }
        }
    }
}
