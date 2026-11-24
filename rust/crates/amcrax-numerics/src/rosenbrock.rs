//! A linearly implicit (Rosenbrock) solver for stiff systems: the two-stage, second-order,
//! L-stable ROS2 method of Verwer, Spee, Blom and Hundsdorfer (1999, SIAM J. Sci. Comput. 20,
//! 1456), `gamma = 1 + 1/sqrt(2)`:
//!
//! ```text
//! (I - gamma h J) k1 = f(t, y)
//! (I - gamma h J) k2 = f(t + h, y + h k1) - 2 k1
//! y_new = y + 3/2 h k1 + 1/2 h k2
//! ```
//!
//! The Jacobian is formed by forward differences at every step (N + 1 evaluations), the linear
//! systems are solved by Gaussian elimination with partial pivoting. The local error is
//! estimated by the difference to the embedded first-order solution `y + h k1`, which is
//! conservative for the second-order result; the step size follows the elementary controller
//! `h_new = h * min(5, max(0.2, 0.9 / sqrt(err)))`. Output points (`t_eval`) are hit exactly (the
//! step is shortened to land on them), and event times are located by bisection on the step
//! length of a single ROS2 step from the step start.
//!
//! It is the stiff fallback of the reactor model (AmCraX uses DOPRI5 first, as SciPy's RK45, and
//! switches when the explicit method exceeds its step-attempt guard); it does not reproduce a
//! SciPy method step by step, so its results are compared with the reference within the
//! tolerances of the integration, not bitwise.

use crate::ode::{Event, OdeError, OdeOptions, OdeRhs, OdeSolution, OdeStatus};

const GAMMA: f64 = 1.0 + std::f64::consts::FRAC_1_SQRT_2;

fn rms<const N: usize>(x: &[f64; N]) -> f64 {
    let mut s = 0.0;
    for v in x {
        s += v * v;
    }
    (s / N as f64).sqrt()
}

/// Solve `m x = b` in place (Gaussian elimination with partial pivoting); `false` if singular.
fn solve<const N: usize>(m: &mut [[f64; N]; N], b: &mut [f64; N]) -> bool {
    for c in 0..N {
        let mut p = c;
        for r in c + 1..N {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c] == 0.0 || !m[p][c].is_finite() {
            return false;
        }
        m.swap(c, p);
        b.swap(c, p);
        for r in c + 1..N {
            let f = m[r][c] / m[c][c];
            if f != 0.0 {
                for k in c..N {
                    m[r][k] -= f * m[c][k];
                }
                b[r] -= f * b[c];
            }
        }
    }
    for c in (0..N).rev() {
        let mut s = b[c];
        for k in c + 1..N {
            s -= m[c][k] * b[k];
        }
        b[c] = s / m[c][c];
    }
    true
}

struct Stepper<'r, const N: usize, R: OdeRhs<N> + ?Sized> {
    rhs: &'r mut R,
    nfev: usize,
}

impl<const N: usize, R: OdeRhs<N> + ?Sized> Stepper<'_, N, R> {
    fn f(&mut self, t: f64, y: &[f64; N]) -> Result<[f64; N], OdeError> {
        let mut dy = [0.0; N];
        self.nfev += 1;
        self.rhs
            .eval(t, y, &mut dy)
            .map_err(|message| OdeError::Rhs { t, message })?;
        Ok(dy)
    }

    fn jacobian(&mut self, t: f64, y: &[f64; N], f0: &[f64; N]) -> Result<[[f64; N]; N], OdeError> {
        let mut j = [[0.0; N]; N];
        let sq = f64::EPSILON.sqrt();
        for c in 0..N {
            let d = sq * y[c].abs().max(1e-8);
            let mut yp = *y;
            yp[c] += d;
            let d = yp[c] - y[c];
            let fp = self.f(t, &yp)?;
            for r in 0..N {
                j[r][c] = (fp[r] - f0[r]) / d;
            }
        }
        Ok(j)
    }

    /// One ROS2 step of length `h`: `(y_new, error estimate)`.
    fn step(
        &mut self,
        t: f64,
        y: &[f64; N],
        f0: &[f64; N],
        jac: &[[f64; N]; N],
        h: f64,
    ) -> Result<Option<([f64; N], [f64; N])>, OdeError> {
        let mut m = [[0.0; N]; N];
        for r in 0..N {
            for c in 0..N {
                let id = if r == c { 1.0 } else { 0.0 };
                m[r][c] = id - GAMMA * h * jac[r][c];
            }
        }
        let mut k1 = *f0;
        let mut m1 = m;
        if !solve(&mut m1, &mut k1) {
            return Ok(None);
        }
        let mut y1 = *y;
        for i in 0..N {
            y1[i] += h * k1[i];
        }
        let f1 = self.f(t + h, &y1)?;
        let mut k2 = [0.0; N];
        for i in 0..N {
            k2[i] = f1[i] - 2.0 * k1[i];
        }
        let mut m2 = m;
        if !solve(&mut m2, &mut k2) {
            return Ok(None);
        }
        let mut yn = *y;
        let mut err = [0.0; N];
        for i in 0..N {
            yn[i] += 1.5 * h * k1[i] + 0.5 * h * k2[i];
            err[i] = 0.5 * h * (k1[i] + k2[i]);
        }
        Ok(Some((yn, err)))
    }
}

/// Integrate `dy/dt = f(t, y)` from `t_span.0` to `t_span.1 > t_span.0` with ROS2 (see the module
/// documentation); same inputs and result type as [`crate::ode::dopri5`] (`first_step` and
/// `max_step` are honoured, `max_attempts` bounds the step attempts).
pub fn ros2<const N: usize, R: OdeRhs<N> + ?Sized>(
    rhs: &mut R,
    t_span: (f64, f64),
    y0: [f64; N],
    t_eval: Option<&[f64]>,
    events: &mut [Event<'_, N>],
    opts: &OdeOptions<N>,
) -> Result<OdeSolution<N>, OdeError> {
    let (t0, tf) = t_span;
    if !t0.is_finite() || !tf.is_finite() || tf <= t0 {
        return Err(OdeError::InvalidInput("ros2 needs t0 < tf (finite)".into()));
    }
    let rtol = opts.rtol.max(100.0 * f64::EPSILON);
    let mut st = Stepper { rhs, nfev: 0 };
    let mut t = t0;
    let mut y = y0;
    let mut f0 = st.f(t, &y)?;
    let mut out_t = Vec::new();
    let mut out_y = Vec::new();
    let teval: Vec<f64> = t_eval.map(<[f64]>::to_vec).unwrap_or_default();
    let mut next_eval = 0usize;
    if t_eval.is_none() {
        out_t.push(t);
        out_y.push(y);
    } else {
        while next_eval < teval.len() && teval[next_eval] <= t0 {
            if teval[next_eval] == t0 {
                out_t.push(t0);
                out_y.push(y0);
            }
            next_eval += 1;
        }
    }
    let mut t_events = vec![Vec::new(); events.len()];
    let mut y_events = vec![Vec::new(); events.len()];
    let mut g_old: Vec<f64> = events.iter_mut().map(|e| (e.g)(t, &y)).collect();
    // initial step
    let mut h = match opts.first_step {
        Some(h) => h,
        None => {
            let mut sy = [0.0; N];
            let mut sf = [0.0; N];
            for i in 0..N {
                let sc = opts.atol[i] + rtol * y[i].abs();
                sy[i] = y[i] / sc;
                sf[i] = f0[i] / sc;
            }
            let (d0, d1) = (rms(&sy), rms(&sf));
            if d0 < 1e-5 || d1 < 1e-5 {
                1e-6
            } else {
                0.01 * d0 / d1
            }
        }
    };
    h = h.min(opts.max_step).min(tf - t0);
    let (mut n_steps, mut n_rejected, mut attempts) = (0usize, 0usize, 0usize);
    let mut jac = st.jacobian(t, &y, &f0)?;
    let mut status = OdeStatus::Finished;
    while t < tf {
        attempts += 1;
        if attempts > opts.max_attempts {
            return Err(OdeError::TooManySteps {
                t,
                attempts: opts.max_attempts,
            });
        }
        let spacing = (t.abs() * f64::EPSILON).max(f64::MIN_POSITIVE);
        if h < 10.0 * spacing {
            return Err(OdeError::StepTooSmall { t });
        }
        // land on the next output point and on the end
        let mut target = tf;
        if next_eval < teval.len() && teval[next_eval] < target {
            target = teval[next_eval];
        }
        let hh = if t + h >= target { target - t } else { h };
        let Some((yn, err)) = st.step(t, &y, &f0, &jac, hh)? else {
            n_rejected += 1;
            h *= 0.25;
            continue;
        };
        let mut e = [0.0; N];
        for i in 0..N {
            e[i] = err[i] / (opts.atol[i] + rtol * y[i].abs().max(yn[i].abs()));
        }
        let en = rms(&e);
        if !en.is_finite() || en > 1.0 {
            n_rejected += 1;
            let fac = if en.is_finite() {
                (0.9 / en.sqrt()).max(0.2)
            } else {
                0.2
            };
            h = hh * fac;
            continue;
        }
        // accepted: events
        let tn = t + hh;
        let mut stop: Option<(f64, [f64; N])> = None;
        for (k, ev) in events.iter_mut().enumerate() {
            let gn = (ev.g)(tn, &yn);
            let go = g_old[k];
            let up = go < 0.0 && gn >= 0.0;
            let down = go > 0.0 && gn <= 0.0;
            let hit = (ev.direction >= 0.0 && up) || (ev.direction <= 0.0 && down);
            if hit {
                let (mut lo, mut hi) = (0.0, hh);
                let mut ye = yn;
                for _ in 0..200 {
                    if hi - lo <= 4.0 * f64::EPSILON * tn.abs().max(1.0) {
                        break;
                    }
                    let mid = 0.5 * (lo + hi);
                    let Some((ym, _)) = st.step(t, &y, &f0, &jac, mid)? else {
                        break;
                    };
                    let gm = (ev.g)(t + mid, &ym);
                    let crossed = if go < 0.0 { gm >= 0.0 } else { gm <= 0.0 };
                    if crossed {
                        hi = mid;
                        ye = ym;
                    } else {
                        lo = mid;
                    }
                }
                t_events[k].push(t + hi);
                y_events[k].push(ye);
                if ev.terminal.is_some() {
                    let te = t + hi;
                    if stop.is_none_or(|s| te < s.0) {
                        stop = Some((te, ye));
                    }
                }
            }
            g_old[k] = gn;
        }
        n_steps += 1;
        if let Some((te, ye)) = stop {
            if t_eval.is_none() {
                out_t.push(te);
                out_y.push(ye);
            }
            status = OdeStatus::TerminalEvent;
            break;
        }
        t = tn;
        y = yn;
        if next_eval < teval.len() && t == teval[next_eval] {
            out_t.push(t);
            out_y.push(y);
            next_eval += 1;
        } else if t_eval.is_none() {
            out_t.push(t);
            out_y.push(y);
        }
        let fac = if en == 0.0 {
            5.0
        } else {
            (0.9 / en.sqrt()).clamp(0.2, 5.0)
        };
        h = (hh * fac).min(opts.max_step);
        if t < tf {
            f0 = st.f(t, &y)?;
            jac = st.jacobian(t, &y, &f0)?;
        }
    }
    Ok(OdeSolution {
        t: out_t,
        y: out_y,
        t_events,
        y_events,
        status,
        nfev: st.nfev,
        n_steps,
        n_rejected,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stiff_linear_system() {
        // y1' = -1000 (y1 - cos t), exact solution approaches cos t; y2' = -y2
        let mut f = |t: f64, y: &[f64; 2], dy: &mut [f64; 2]| -> Result<(), String> {
            dy[0] = -1000.0 * (y[0] - t.cos());
            dy[1] = -y[1];
            Ok(())
        };
        let opts = OdeOptions::new(1e-8, 1e-10);
        let te = [0.0, 1.0, 2.0];
        let sol = ros2(&mut f, (0.0, 2.0), [1.0, 1.0], Some(&te), &mut [], &opts).unwrap();
        assert_eq!(sol.t, vec![0.0, 1.0, 2.0]);
        let y = sol.y[2];
        // quasi-steady y1 = (1000^2 cos t + 1000 sin t) / (1000^2 + 1)
        let exact1 = (1e6 * 2f64.cos() + 1e3 * 2f64.sin()) / (1e6 + 1.0);
        assert!((y[0] - exact1).abs() < 1e-6, "{} {}", y[0], exact1);
        assert!((y[1] - (-2f64).exp()).abs() < 1e-6);
        assert!(sol.n_steps < 5000, "{}", sol.n_steps);
    }

    #[test]
    fn terminal_event() {
        let mut f = |_t: f64, _y: &[f64; 1], dy: &mut [f64; 1]| -> Result<(), String> {
            dy[0] = -1.0;
            Ok(())
        };
        let mut ev = [Event::new(|_t: f64, y: &[f64; 1]| y[0] - 0.5, true, 0.0)];
        let sol = ros2(
            &mut f,
            (0.0, 2.0),
            [1.0],
            None,
            &mut ev,
            &OdeOptions::new(1e-8, 1e-10),
        )
        .unwrap();
        assert_eq!(sol.status, OdeStatus::TerminalEvent);
        assert!((sol.t_events[0][0] - 0.5).abs() < 1e-9);
    }
}
