//! Implicit Runge-Kutta method of the Radau IIA family of order 5, ported from SciPy's
//! `scipy/integrate/_ivp/radau.py` (Hairer and Wanner, Solving ODEs II, Sec. IV.8): the
//! simplified Newton iteration on the transformed collocation system (one real and one complex
//! linear system per iteration, `NEWTON_MAXITER = 6`), the third-order embedded error estimate
//! (with the extra solve after a rejection), the step-size predictor with the two-step
//! (Gustafsson) controller, Jacobian reuse and the cubic collocation dense output (used for
//! `t_eval` and event location).
//!
//! Differences from SciPy, all within the integration tolerance: the Jacobian is a plain
//! forward difference (step `sqrt(eps) max(|y_j|, 1)`) instead of SciPy's adaptive `num_jac`; the
//! linear systems are solved by Gaussian elimination with partial pivoting (N is small); event
//! times are located by bisection on the dense output. It is the stiff fallback of the reactor
//! model (AmCraX integrates with DOPRI5 first, as SciPy's RK45).

use crate::ode::{Event, OdeError, OdeOptions, OdeRhs, OdeSolution, OdeStatus};

const NEWTON_MAXITER: usize = 6;
const MIN_FACTOR: f64 = 0.2;
const MAX_FACTOR: f64 = 10.0;

#[derive(Clone, Copy, Debug)]
struct Cx(f64, f64);

impl Cx {
    fn sub(self, o: Cx) -> Cx {
        Cx(self.0 - o.0, self.1 - o.1)
    }
    fn mul(self, o: Cx) -> Cx {
        Cx(self.0 * o.0 - self.1 * o.1, self.0 * o.1 + self.1 * o.0)
    }
    fn div(self, o: Cx) -> Cx {
        let d = o.0 * o.0 + o.1 * o.1;
        Cx(
            (self.0 * o.0 + self.1 * o.1) / d,
            (self.1 * o.0 - self.0 * o.1) / d,
        )
    }
    fn abs(self) -> f64 {
        self.0.hypot(self.1)
    }
}

struct Consts {
    c: [f64; 3],
    e: [f64; 3],
    mu_real: f64,
    mu_complex: Cx,
    t: [[f64; 3]; 3],
    ti: [[f64; 3]; 3],
    p: [[f64; 3]; 3],
}

fn consts() -> Consts {
    let s6 = 6f64.sqrt();
    let c3 = |e: f64| 3f64.powf(e);
    Consts {
        c: [(4.0 - s6) / 10.0, (4.0 + s6) / 10.0, 1.0],
        e: [
            (-13.0 - 7.0 * s6) / 3.0,
            (-13.0 + 7.0 * s6) / 3.0,
            -1.0 / 3.0,
        ],
        mu_real: 3.0 + c3(2.0 / 3.0) - c3(1.0 / 3.0),
        mu_complex: Cx(
            3.0 + 0.5 * (c3(1.0 / 3.0) - c3(2.0 / 3.0)),
            -0.5 * (c3(5.0 / 6.0) + c3(7.0 / 6.0)),
        ),
        t: [
            [
                0.09443876248897524,
                -0.1412552950209542,
                0.03002919410514742,
            ],
            [0.2502131229653333, 0.20412935229379994, -0.3829421127572619],
            [1.0, 1.0, 0.0],
        ],
        ti: [
            [4.178718591551904, 0.32768282076106237, 0.5233764454994495],
            [
                -4.178718591551904,
                -0.32768282076106237,
                0.47662355450055044,
            ],
            [0.5028726349457868, -2.571926949855605, 0.5960392048282249],
        ],
        p: [
            [
                13.0 / 3.0 + 7.0 * s6 / 3.0,
                -23.0 / 3.0 - 22.0 * s6 / 3.0,
                10.0 / 3.0 + 5.0 * s6,
            ],
            [
                13.0 / 3.0 - 7.0 * s6 / 3.0,
                -23.0 / 3.0 + 22.0 * s6 / 3.0,
                10.0 / 3.0 - 5.0 * s6,
            ],
            [1.0 / 3.0, -8.0 / 3.0, 10.0 / 3.0],
        ],
    }
}

/// SciPy `common.norm`: RMS.
fn norm<const N: usize>(x: &[f64; N]) -> f64 {
    let mut s = 0.0;
    for v in x {
        s += v * v;
    }
    (s / N as f64).sqrt()
}

fn solve_real<const N: usize>(a: &[[f64; N]; N], b: &[f64; N]) -> Option<[f64; N]> {
    let mut m = *a;
    let mut x = *b;
    for c in 0..N {
        let mut p = c;
        for r in c + 1..N {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c] == 0.0 || !m[p][c].is_finite() {
            return None;
        }
        m.swap(c, p);
        x.swap(c, p);
        for r in c + 1..N {
            let f = m[r][c] / m[c][c];
            if f != 0.0 {
                for k in c..N {
                    m[r][k] -= f * m[c][k];
                }
                x[r] -= f * x[c];
            }
        }
    }
    for c in (0..N).rev() {
        let mut s = x[c];
        for k in c + 1..N {
            s -= m[c][k] * x[k];
        }
        x[c] = s / m[c][c];
    }
    Some(x)
}

fn solve_cx<const N: usize>(a: &[[Cx; N]; N], b: &[Cx; N]) -> Option<[Cx; N]> {
    let mut m = *a;
    let mut x = *b;
    for c in 0..N {
        let mut p = c;
        for r in c + 1..N {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c].abs() == 0.0 || !m[p][c].abs().is_finite() {
            return None;
        }
        m.swap(c, p);
        x.swap(c, p);
        for r in c + 1..N {
            let f = m[r][c].div(m[c][c]);
            for k in c..N {
                m[r][k] = m[r][k].sub(f.mul(m[c][k]));
            }
            x[r] = x[r].sub(f.mul(x[c]));
        }
    }
    for c in (0..N).rev() {
        let mut s = x[c];
        for k in c + 1..N {
            s = s.sub(m[c][k].mul(x[k]));
        }
        x[c] = s.div(m[c][c]);
    }
    Some(x)
}

/// Dense output of one step: `y(t) = y_old + Q [x, x^2, x^3]`, `x = (t - t_old) / h`.
struct Dense<const N: usize> {
    t_old: f64,
    h: f64,
    y_old: [f64; N],
    q: [[f64; 3]; N],
}

impl<const N: usize> Dense<N> {
    fn at(&self, t: f64) -> [f64; N] {
        let x = (t - self.t_old) / self.h;
        let p = [x, x * x, x * x * x];
        let mut y = self.y_old;
        for i in 0..N {
            y[i] += self.q[i][0] * p[0] + self.q[i][1] * p[1] + self.q[i][2] * p[2];
        }
        y
    }
}

struct Rhs<'r, const N: usize, R: OdeRhs<N> + ?Sized> {
    rhs: &'r mut R,
    nfev: usize,
}

impl<const N: usize, R: OdeRhs<N> + ?Sized> Rhs<'_, N, R> {
    fn f(&mut self, t: f64, y: &[f64; N]) -> Result<[f64; N], OdeError> {
        let mut dy = [0.0; N];
        self.nfev += 1;
        self.rhs
            .eval(t, y, &mut dy)
            .map_err(|message| OdeError::Rhs { t, message })?;
        Ok(dy)
    }

    fn jac(&mut self, t: f64, y: &[f64; N], f0: &[f64; N]) -> Result<[[f64; N]; N], OdeError> {
        let mut j = [[0.0; N]; N];
        let sq = f64::EPSILON.sqrt();
        for c in 0..N {
            let mut yp = *y;
            yp[c] += sq * y[c].abs().max(1.0);
            let d = yp[c] - y[c];
            let fp = self.f(t, &yp)?;
            for r in 0..N {
                j[r][c] = (fp[r] - f0[r]) / d;
            }
        }
        Ok(j)
    }
}

fn predict_factor(h_abs: f64, h_abs_old: Option<f64>, err: f64, err_old: Option<f64>) -> f64 {
    let multiplier = match (err_old, h_abs_old) {
        (Some(eo), Some(ho)) if err != 0.0 => h_abs / ho * (eo / err).powf(0.25),
        _ => 1.0,
    };
    multiplier.min(1.0) * err.powf(-0.25)
}

/// Integrate `dy/dt = f(t, y)` from `t_span.0` to `t_span.1 > t_span.0` with Radau IIA (order 5);
/// same inputs and result type as [`crate::ode::dopri5`].
pub fn radau5<const N: usize, R: OdeRhs<N> + ?Sized>(
    rhs: &mut R,
    t_span: (f64, f64),
    y0: [f64; N],
    t_eval: Option<&[f64]>,
    events: &mut [Event<'_, N>],
    opts: &OdeOptions<N>,
) -> Result<OdeSolution<N>, OdeError> {
    let k = consts();
    let (t0, tf) = t_span;
    if !t0.is_finite() || !tf.is_finite() || tf <= t0 {
        return Err(OdeError::InvalidInput("radau5 needs finite t0 < tf".into()));
    }
    let rtol = opts.rtol.max(100.0 * f64::EPSILON);
    let atol = opts.atol;
    let mut fr = Rhs { rhs, nfev: 0 };
    let mut t = t0;
    let mut y = y0;
    let mut f = fr.f(t, &y)?;
    // select_initial_step(order = 3)
    let interval = tf - t0;
    let mut h_abs = match opts.first_step {
        Some(h) => h,
        None => {
            let mut s0 = [0.0; N];
            let mut s1 = [0.0; N];
            for i in 0..N {
                let sc = atol[i] + y[i].abs() * rtol;
                s0[i] = y[i] / sc;
                s1[i] = f[i] / sc;
            }
            let (d0, d1) = (norm(&s0), norm(&s1));
            let h0 = if d0 < 1e-5 || d1 < 1e-5 {
                1e-6
            } else {
                0.01 * d0 / d1
            }
            .min(interval);
            let mut y1 = y;
            for i in 0..N {
                y1[i] += h0 * f[i];
            }
            let f1 = fr.f(t + h0, &y1)?;
            let mut s2 = [0.0; N];
            for i in 0..N {
                s2[i] = (f1[i] - f[i]) / (atol[i] + y[i].abs() * rtol);
            }
            let d2 = norm(&s2) / h0;
            let h1 = if d1 <= 1e-15 && d2 <= 1e-15 {
                (h0 * 1e-3).max(1e-6)
            } else {
                (0.01 / d1.max(d2)).powf(1.0 / 4.0)
            };
            (100.0 * h0).min(h1).min(interval).min(opts.max_step)
        }
    };
    let newton_tol = (10.0 * f64::EPSILON / rtol).max(0.03f64.min(rtol.sqrt()));
    let mut jm = fr.jac(t, &y, &f)?;
    let mut current_jac = true;
    let mut lu_valid = false;
    let mut m_real = [[0.0; N]; N];
    let mut m_cx = [[Cx(0.0, 0.0); N]; N];
    let mut h_abs_old: Option<f64> = None;
    let mut err_old: Option<f64> = None;
    let mut sol: Option<Dense<N>> = None;

    let teval: Vec<f64> = t_eval.map(<[f64]>::to_vec).unwrap_or_default();
    let mut next_eval = 0usize;
    let (mut out_t, mut out_y) = (Vec::new(), Vec::new());
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
    let (mut n_steps, mut n_rejected, mut attempts) = (0usize, 0usize, 0usize);
    let mut status = OdeStatus::Finished;

    'outer: while t < tf {
        let min_step = 10.0 * ((t.abs() * f64::EPSILON).max(f64::MIN_POSITIVE));
        // SciPy keeps the step proposed at entry as h_abs_old (before clipping and rejections)
        let h_entry = h_abs;
        let (mut ho, mut eo) = (h_abs_old, err_old);
        if h_abs > opts.max_step {
            h_abs = opts.max_step;
            ho = None;
            eo = None;
        } else if h_abs < min_step {
            h_abs = min_step;
            ho = None;
            eo = None;
        }
        let mut rejected = false;
        loop {
            attempts += 1;
            if attempts > opts.max_attempts {
                return Err(OdeError::TooManySteps {
                    t,
                    attempts: opts.max_attempts,
                });
            }
            if h_abs < min_step {
                return Err(OdeError::StepTooSmall { t });
            }
            let mut tn = t + h_abs;
            if tn > tf {
                tn = tf;
            }
            let h = tn - t;
            h_abs = h.abs();
            let mut z0 = [[0.0; N]; 3];
            if let Some(s) = &sol {
                for st in 0..3 {
                    let ys = s.at(t + h * k.c[st]);
                    for i in 0..N {
                        z0[st][i] = ys[i] - y[i];
                    }
                }
            }
            let mut scale = [0.0; N];
            for i in 0..N {
                scale[i] = atol[i] + y[i].abs() * rtol;
            }
            // Newton on the collocation system, Jacobian refreshed once if it fails
            let mut res;
            loop {
                if !lu_valid {
                    let mr = k.mu_real / h;
                    let mc = Cx(k.mu_complex.0 / h, k.mu_complex.1 / h);
                    for r in 0..N {
                        for c in 0..N {
                            let id = if r == c { 1.0 } else { 0.0 };
                            m_real[r][c] = mr * id - jm[r][c];
                            m_cx[r][c] = Cx(mc.0 * id - jm[r][c], mc.1 * id);
                        }
                    }
                    lu_valid = true;
                }
                res = collocation(
                    &mut fr, &k, t, &y, h, &z0, &scale, newton_tol, &m_real, &m_cx,
                )?;
                if res.0 {
                    break;
                }
                if current_jac {
                    break;
                }
                jm = fr.jac(t, &y, &f)?;
                current_jac = true;
                lu_valid = false;
            }
            let (converged, it, zz, rt) = res;
            if !converged {
                h_abs *= 0.5;
                lu_valid = false;
                n_rejected += 1;
                continue;
            }
            let mut yn = y;
            let mut ze = [0.0; N];
            for i in 0..N {
                yn[i] += zz[2][i];
                ze[i] = (zz[0][i] * k.e[0] + zz[1][i] * k.e[1] + zz[2][i] * k.e[2]) / h;
            }
            let mut rhs_e = [0.0; N];
            for i in 0..N {
                rhs_e[i] = f[i] + ze[i];
            }
            let mut error = solve_real(&m_real, &rhs_e).unwrap_or([f64::NAN; N]);
            let mut sc2 = [0.0; N];
            for i in 0..N {
                sc2[i] = atol[i] + y[i].abs().max(yn[i].abs()) * rtol;
            }
            let mut e = [0.0; N];
            for i in 0..N {
                e[i] = error[i] / sc2[i];
            }
            let mut en = norm(&e);
            let safety = 0.9 * (2 * NEWTON_MAXITER + 1) as f64 / (2 * NEWTON_MAXITER + it) as f64;
            if rejected && en > 1.0 {
                let mut ye = y;
                for i in 0..N {
                    ye[i] += error[i];
                }
                let fe = fr.f(t, &ye)?;
                for i in 0..N {
                    rhs_e[i] = fe[i] + ze[i];
                }
                error = solve_real(&m_real, &rhs_e).unwrap_or([f64::NAN; N]);
                for i in 0..N {
                    e[i] = error[i] / sc2[i];
                }
                en = norm(&e);
            }
            if !en.is_finite() || en > 1.0 {
                let fac = if en.is_finite() {
                    predict_factor(h_abs, ho, en, eo)
                } else {
                    MIN_FACTOR
                };
                h_abs *= MIN_FACTOR.max(safety * fac);
                lu_valid = false;
                rejected = true;
                n_rejected += 1;
                continue;
            }
            let (t_new, y_new, z, error_norm, n_iter, rate) = (tn, yn, zz, en, it, rt);
            let recompute_jac = n_iter > 2 && rate.is_some_and(|r| r > 1e-3);
            let mut factor = predict_factor(h_abs, ho, error_norm, eo);
            factor = MAX_FACTOR.min(safety * factor);
            if !recompute_jac && factor < 1.2 {
                factor = 1.0;
            } else {
                lu_valid = false;
            }
            let f_new = fr.f(t_new, &y_new)?;
            if recompute_jac {
                jm = fr.jac(t_new, &y_new, &f_new)?;
                current_jac = true;
            } else {
                current_jac = false;
            }
            h_abs_old = Some(h_entry);
            err_old = Some(error_norm);
            let h_step = t_new - t;
            h_abs *= factor;
            // dense output Q = Z^T P
            let mut q = [[0.0; 3]; N];
            for i in 0..N {
                for c in 0..3 {
                    q[i][c] = z[0][i] * k.p[0][c] + z[1][i] * k.p[1][c] + z[2][i] * k.p[2][c];
                }
            }
            let dense = Dense {
                t_old: t,
                h: h_step,
                y_old: y,
                q,
            };
            n_steps += 1;
            // events
            let mut stop: Option<(f64, [f64; N])> = None;
            for (kk, ev) in events.iter_mut().enumerate() {
                let gn = (ev.g)(t_new, &y_new);
                let go = g_old[kk];
                let up = go < 0.0 && gn >= 0.0;
                let down = go > 0.0 && gn <= 0.0;
                if (ev.direction >= 0.0 && up) || (ev.direction <= 0.0 && down) {
                    let (mut lo, mut hi) = (t, t_new);
                    for _ in 0..200 {
                        if hi - lo <= 4.0 * f64::EPSILON * hi.abs().max(1.0) {
                            break;
                        }
                        let mid = 0.5 * (lo + hi);
                        let gm = (ev.g)(mid, &dense.at(mid));
                        let crossed = if go < 0.0 { gm >= 0.0 } else { gm <= 0.0 };
                        if crossed {
                            hi = mid;
                        } else {
                            lo = mid;
                        }
                    }
                    let ye = dense.at(hi);
                    t_events[kk].push(hi);
                    y_events[kk].push(ye);
                    if ev.terminal.is_some() && stop.is_none_or(|s| hi < s.0) {
                        stop = Some((hi, ye));
                    }
                }
                g_old[kk] = gn;
            }
            let t_end = stop.map(|s| s.0).unwrap_or(t_new);
            while next_eval < teval.len() && teval[next_eval] <= t_end {
                let te = teval[next_eval];
                out_t.push(te);
                out_y.push(if te == t_new { y_new } else { dense.at(te) });
                next_eval += 1;
            }
            if let Some((te, ye)) = stop {
                if t_eval.is_none() {
                    out_t.push(te);
                    out_y.push(ye);
                }
                status = OdeStatus::TerminalEvent;
                break 'outer;
            }
            if t_eval.is_none() {
                out_t.push(t_new);
                out_y.push(y_new);
            }
            t = t_new;
            y = y_new;
            f = f_new;
            sol = Some(dense);
            break;
        }
    }
    Ok(OdeSolution {
        t: out_t,
        y: out_y,
        t_events,
        y_events,
        status,
        nfev: fr.nfev,
        n_steps,
        n_rejected,
    })
}

/// Result of the Newton iteration: `(converged, iterations, Z, rate)`.
type Newton<const N: usize> = (bool, usize, [[f64; N]; 3], Option<f64>);

/// SciPy `solve_collocation_system`.
#[allow(clippy::too_many_arguments)]
fn collocation<const N: usize, R: OdeRhs<N> + ?Sized>(
    fr: &mut Rhs<'_, N, R>,
    k: &Consts,
    t: f64,
    y: &[f64; N],
    h: f64,
    z0: &[[f64; N]; 3],
    scale: &[f64; N],
    tol: f64,
    m_real: &[[f64; N]; N],
    m_cx: &[[Cx; N]; N],
) -> Result<Newton<N>, OdeError> {
    let mr = k.mu_real / h;
    let mc = Cx(k.mu_complex.0 / h, k.mu_complex.1 / h);
    let mut w = [[0.0; N]; 3];
    for r in 0..3 {
        for i in 0..N {
            w[r][i] = k.ti[r][0] * z0[0][i] + k.ti[r][1] * z0[1][i] + k.ti[r][2] * z0[2][i];
        }
    }
    let mut z = *z0;
    let mut dw_norm_old: Option<f64> = None;
    let mut rate: Option<f64> = None;
    let mut converged = false;
    let mut iters = 0;
    for it in 0..NEWTON_MAXITER {
        iters = it + 1;
        let mut fv = [[0.0; N]; 3];
        let mut finite = true;
        for st in 0..3 {
            let mut ys = *y;
            for i in 0..N {
                ys[i] += z[st][i];
            }
            fv[st] = fr.f(t + h * k.c[st], &ys)?;
            finite &= fv[st].iter().all(|v| v.is_finite());
        }
        if !finite {
            break;
        }
        let mut f_real = [0.0; N];
        let mut f_cx = [Cx(0.0, 0.0); N];
        for i in 0..N {
            f_real[i] = fv[0][i] * k.ti[0][0] + fv[1][i] * k.ti[0][1] + fv[2][i] * k.ti[0][2]
                - mr * w[0][i];
            let re = fv[0][i] * k.ti[1][0] + fv[1][i] * k.ti[1][1] + fv[2][i] * k.ti[1][2];
            let im = fv[0][i] * k.ti[2][0] + fv[1][i] * k.ti[2][1] + fv[2][i] * k.ti[2][2];
            f_cx[i] = Cx(re, im).sub(mc.mul(Cx(w[1][i], w[2][i])));
        }
        let (Some(dr), Some(dc)) = (solve_real(m_real, &f_real), solve_cx(m_cx, &f_cx)) else {
            break;
        };
        let mut dw = [[0.0; N]; 3];
        let mut acc = 0.0;
        for i in 0..N {
            dw[0][i] = dr[i];
            dw[1][i] = dc[i].0;
            dw[2][i] = dc[i].1;
            for r in 0..3 {
                let v = dw[r][i] / scale[i];
                acc += v * v;
            }
        }
        let dw_norm = (acc / (3 * N) as f64).sqrt();
        if let Some(o) = dw_norm_old {
            rate = Some(dw_norm / o);
        }
        if let Some(r) = rate
            && (r >= 1.0 || r.powi((NEWTON_MAXITER - it) as i32) / (1.0 - r) * dw_norm > tol)
        {
            break;
        }
        for r in 0..3 {
            for i in 0..N {
                w[r][i] += dw[r][i];
            }
        }
        for r in 0..3 {
            for i in 0..N {
                z[r][i] = k.t[r][0] * w[0][i] + k.t[r][1] * w[1][i] + k.t[r][2] * w[2][i];
            }
        }
        if dw_norm == 0.0 || rate.is_some_and(|r| r / (1.0 - r) * dw_norm < tol) {
            converged = true;
            break;
        }
        dw_norm_old = Some(dw_norm);
    }
    Ok((converged, iters, z, rate))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stiff_linear_system() {
        let mut f = |t: f64, y: &[f64; 2], dy: &mut [f64; 2]| -> Result<(), String> {
            dy[0] = -1000.0 * (y[0] - t.cos());
            dy[1] = -y[1];
            Ok(())
        };
        let opts = OdeOptions::new(1e-10, 1e-12);
        let te = [0.0, 1.0, 2.0];
        let sol = radau5(&mut f, (0.0, 2.0), [1.0, 1.0], Some(&te), &mut [], &opts).unwrap();
        assert_eq!(sol.t, vec![0.0, 1.0, 2.0]);
        let y = sol.y[2];
        let exact1 = (1e6 * 2f64.cos() + 1e3 * 2f64.sin()) / (1e6 + 1.0);
        assert!((y[0] - exact1).abs() < 1e-8, "{} {}", y[0], exact1);
        assert!((y[1] - (-2f64).exp()).abs() < 1e-8);
        assert!(sol.n_steps < 2000, "{}", sol.n_steps);
    }

    #[test]
    fn robertson_is_solved() {
        // Robertson chemical kinetics, the classic stiff test
        let mut f = |_t: f64, y: &[f64; 3], dy: &mut [f64; 3]| -> Result<(), String> {
            dy[0] = -0.04 * y[0] + 1e4 * y[1] * y[2];
            dy[2] = 3e7 * y[1] * y[1];
            dy[1] = -dy[0] - dy[2];
            Ok(())
        };
        let mut o = OdeOptions::new(1e-8, 1e-12);
        o.atol = [1e-10, 1e-14, 1e-10];
        let sol = radau5(
            &mut f,
            (0.0, 40.0),
            [1.0, 0.0, 0.0],
            Some(&[40.0]),
            &mut [],
            &o,
        )
        .unwrap();
        let y = sol.y[0];
        assert!((y[0] - 0.7158270687).abs() < 1e-7, "{}", y[0]);
        assert!(sol.n_steps < 500, "{}", sol.n_steps);
    }

    #[test]
    fn terminal_event_on_dense_output() {
        let mut f = |_t: f64, _y: &[f64; 1], dy: &mut [f64; 1]| -> Result<(), String> {
            dy[0] = -1.0;
            Ok(())
        };
        let mut ev = [Event::new(|_t: f64, y: &[f64; 1]| y[0] - 0.5, true, 0.0)];
        let sol = radau5(
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
