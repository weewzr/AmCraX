//! Special functions with SciPy's floating-point behaviour.
//!
//! [`ndtri`] is the Cephes inverse of the standard normal CDF as shipped in SciPy (`xsf`
//! `cephes/ndtri.h`, used by `scipy.special.ndtri` and `scipy.stats.norm.ppf`): the same three
//! rational approximations, the same branch points and the same Horner evaluation order
//! (`polevl`, `p1evl`). Checked bitwise against SciPy 1.18.1 on 250,006 arguments (uniform in
//! (0, 1) and log-uniform down to 1e-300) before the port, and against the stage 3 golden table.

const S2PI: f64 = 2.5066282746310007;
// 0.135... = exp(-2)
const EXPM2: f64 = 0.1353352832366127;

const P0: [f64; 5] = [
    -59.96335010141079,
    98.00107541859997,
    -56.67628574690703,
    13.931260938727968,
    -1.2391658386738125,
];
const Q0: [f64; 8] = [
    1.9544885833814176,
    4.676279128988815,
    86.36024213908905,
    -225.46268785411937,
    200.26021238006066,
    -82.03722561683334,
    15.90562251262117,
    -1.1833162112133,
];
const P1: [f64; 9] = [
    4.0554489230596245,
    31.525109459989388,
    57.16281922464213,
    44.08050738932008,
    14.684956192885803,
    2.1866330685079025,
    -0.1402560791713545,
    -0.03504246268278482,
    -0.0008574567851546854,
];
const Q1: [f64; 8] = [
    15.779988325646675,
    45.39076351288792,
    41.3172038254672,
    15.04253856929075,
    2.504649462083094,
    -0.14218292285478779,
    -0.03808064076915783,
    -0.0009332594808954574,
];
const P2: [f64; 9] = [
    3.2377489177694603,
    6.915228890689842,
    3.9388102529247444,
    1.3330346081580755,
    0.20148538954917908,
    0.012371663481782003,
    0.00030158155350823543,
    2.6580697468673755E-06,
    6.239745391849833E-09,
];
const Q2: [f64; 8] = [
    6.02427039364742,
    3.6798356385616087,
    1.3770209948908132,
    0.21623699359449663,
    0.013420400608854318,
    0.00032801446468212774,
    2.8924786474538068E-06,
    6.790194080099813E-09,
];

#[inline]
fn polevl(x: f64, c: &[f64]) -> f64 {
    let mut a = c[0];
    for k in &c[1..] {
        a = a * x + k;
    }
    a
}

#[inline]
fn p1evl(x: f64, c: &[f64]) -> f64 {
    let mut a = x + c[0];
    for k in &c[1..] {
        a = a * x + k;
    }
    a
}

/// `scipy.special.ndtri(y)`: x with `Phi(x) = y` (`-inf` at 0, `inf` at 1, NaN outside [0, 1]).
pub fn ndtri(y0: f64) -> f64 {
    if y0 == 0.0 {
        return f64::NEG_INFINITY;
    }
    if y0 == 1.0 {
        return f64::INFINITY;
    }
    if !(0.0..=1.0).contains(&y0) {
        return f64::NAN;
    }
    let mut code = true;
    let mut y = y0;
    if y > 1.0 - EXPM2 {
        y = 1.0 - y;
        code = false;
    }
    if y > EXPM2 {
        y -= 0.5;
        let y2 = y * y;
        let x = y + y * (y2 * polevl(y2, &P0) / p1evl(y2, &Q0));
        return x * S2PI;
    }
    let x = (-2.0 * y.ln()).sqrt();
    let x0 = x - x.ln() / x;
    let z = 1.0 / x;
    let x1 = if x < 8.0 {
        z * polevl(z, &P1) / p1evl(z, &Q1)
    } else {
        z * polevl(z, &P2) / p1evl(z, &Q2)
    };
    let x = x0 - x1;
    if code { -x } else { x }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_values() {
        assert_eq!(ndtri(0.5), 0.0);
        assert!((ndtri(0.975) - 1.959_963_984_540_054).abs() < 1e-15);
        assert!((ndtri(0.025) + 1.959_963_984_540_054).abs() < 1e-15);
        assert_eq!(ndtri(0.0), f64::NEG_INFINITY);
        assert!(ndtri(1.5).is_nan());
        assert!((ndtri(1e-300) + 37.0470962993612).abs() < 1e-11);
    }
}
