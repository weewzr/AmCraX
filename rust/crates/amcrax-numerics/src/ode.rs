//! Explicit Dormand-Prince 5(4) integration with dense output and event location, written as a
//! port of `scipy.integrate.solve_ivp(method="RK45")`.
//!
//! # Method
//!
//! * Tableau: Dormand and Prince (1980), the coefficients of SciPy's `RK45` class (`C`, `A`,
//!   `B`, `E`), seven stages with the FSAL property (the last stage is `f(t + h, y_new)`).
//! * Dense output: SciPy's fourth-order interpolant (`P` matrix, Shampine 1986),
//!   `y(t_old + x h) = y_old + h * Q p(x)`, `Q = K^T P`, `p = (x, x^2, x^3, x^4)`.
//! * Initial step: Hairer, Norsett and Wanner, Section II.4, as SciPy's `select_initial_step`
//!   (one extra RHS evaluation).
//!
//! # Step-size controller (identical to SciPy `RungeKutta._step_impl`)
//!
//! * error scale per component: `sc_i = atol_i + max(|y_i|, |y_new_i|) * rtol`;
//! * error norm: RMS of `(K^T E)_i h / sc_i`;
//! * accepted when the norm is `< 1`; the next step is `h * min(10, 0.9 * norm^(-1/5))`
//!   (`10` when the norm is 0), limited to `h` (factor <= 1) after a rejection in the same step;
//! * rejected otherwise, retried with `h * max(0.2, 0.9 * norm^(-1/5))`;
//! * the step is limited to `max_step`, and integration fails when `h` falls below
//!   `10 * |nextafter(t) - t|`;
//! * `rtol` below `100 * f64::EPSILON` is raised to that value (SciPy warns and does the same).
//!
//! # Events
//!
//! As `solve_ivp`: an event `g(t, y)` is active in a step when its sign changes between the step
//! ends in the requested direction (`g <= 0 <= g_new` is "up", `g >= 0 >= g_new` is "down"). Its
//! time is found by [`crate::roots::brentq`] on the dense output with `xtol = rtol = 4 eps`. An
//! event with `terminal = Some(k)` stops the integration at its k-th occurrence; the solution is
//! then truncated at the event time.
//!
//! # Agreement with SciPy
//!
//! The number of RHS evaluations and of accepted steps agree with SciPy. The values agree to a
//! small fraction of the requested tolerance but are not bit-identical: NumPy forms the stage
//! sums, the error estimate and the dense-output matrix with BLAS dot products whose summation
//! order differs from the left-to-right sums used here (see `rust/golden/numerics/dopri5.json`).

use crate::roots::{BrentError, BrentOptions, brentq_try};
use std::fmt;

const SAFETY: f64 = 0.9;
const MIN_FACTOR: f64 = 0.2;
const MAX_FACTOR: f64 = 10.0;
/// `-1 / (error_estimator_order + 1)` with `error_estimator_order = 4`.
const ERROR_EXPONENT: f64 = -1.0 / 5.0;

const C: [f64; 6] = [0.0, 1.0 / 5.0, 3.0 / 10.0, 4.0 / 5.0, 8.0 / 9.0, 1.0];
const A: [[f64; 5]; 6] = [
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [1.0 / 5.0, 0.0, 0.0, 0.0, 0.0],
    [3.0 / 40.0, 9.0 / 40.0, 0.0, 0.0, 0.0],
    [44.0 / 45.0, -56.0 / 15.0, 32.0 / 9.0, 0.0, 0.0],
    [
        19372.0 / 6561.0,
        -25360.0 / 2187.0,
        64448.0 / 6561.0,
        -212.0 / 729.0,
        0.0,
    ],
    [
        9017.0 / 3168.0,
        -355.0 / 33.0,
        46732.0 / 5247.0,
        49.0 / 176.0,
        -5103.0 / 18656.0,
    ],
];
const B: [f64; 6] = [
    35.0 / 384.0,
    0.0,
    500.0 / 1113.0,
    125.0 / 192.0,
    -2187.0 / 6784.0,
    11.0 / 84.0,
];
const E: [f64; 7] = [
    -71.0 / 57600.0,
    0.0,
    71.0 / 16695.0,
    -71.0 / 1920.0,
    17253.0 / 339200.0,
    -22.0 / 525.0,
    1.0 / 40.0,
];
const P: [[f64; 4]; 7] = [
    [
        1.0,
        -8048581381.0 / 2820520608.0,
        8663915743.0 / 2820520608.0,
        -12715105075.0 / 11282082432.0,
    ],
    [0.0, 0.0, 0.0, 0.0],
    [
        0.0,
        131558114200.0 / 32700410799.0,
        -68118460800.0 / 10900136933.0,
        87487479700.0 / 32700410799.0,
    ],
    [
        0.0,
        -1754552775.0 / 470086768.0,
        14199869525.0 / 1410260304.0,
        -10690763975.0 / 1880347072.0,
    ],
    [
        0.0,
        127303824393.0 / 49829197408.0,
        -318862633887.0 / 49829197408.0,
        701980252875.0 / 199316789632.0,
    ],
    [
        0.0,
        -282668133.0 / 205662961.0,
        2019193451.0 / 616988883.0,
        -1453857185.0 / 822651844.0,
    ],
    [
        0.0,
        40617522.0 / 29380423.0,
        -110615467.0 / 29380423.0,
        69997945.0 / 29380423.0,
    ],
];

/// Right-hand side `dy/dt = f(t, y)` of an ODE system with `N` states.
pub trait OdeRhs<const N: usize> {
    /// Write `f(t, y)` into `dy`. An `Err` stops the integration.
    fn eval(&mut self, t: f64, y: &[f64; N], dy: &mut [f64; N]) -> Result<(), String>;
}

impl<const N: usize, F> OdeRhs<N> for F
where
    F: FnMut(f64, &[f64; N], &mut [f64; N]) -> Result<(), String>,
{
    fn eval(&mut self, t: f64, y: &[f64; N], dy: &mut [f64; N]) -> Result<(), String> {
        self(t, y, dy)
    }
}

/// Event function `g(t, y)`.
pub type EventFn<'a, const N: usize> = Box<dyn FnMut(f64, &[f64; N]) -> f64 + 'a>;

/// An event located during the integration (SciPy `events=`).
pub struct Event<'a, const N: usize> {
    /// The event function; an event occurs where it crosses zero.
    pub g: EventFn<'a, N>,
    /// `None`: record only. `Some(k)`: stop at the k-th occurrence (SciPy `terminal = k`,
    /// `terminal = True` is `Some(1)`).
    pub terminal: Option<u32>,
    /// `> 0`: only upward crossings, `< 0`: only downward crossings, `0`: both.
    pub direction: f64,
}

impl<'a, const N: usize> Event<'a, N> {
    /// An event that stops the integration at its first occurrence when `terminal` is true.
    pub fn new(g: impl FnMut(f64, &[f64; N]) -> f64 + 'a, terminal: bool, direction: f64) -> Self {
        Event {
            g: Box::new(g),
            terminal: if terminal { Some(1) } else { None },
            direction,
        }
    }
}

/// Options of [`dopri5`].
#[derive(Debug, Clone, PartialEq)]
pub struct OdeOptions<const N: usize> {
    /// Relative tolerance (values below `100 * f64::EPSILON` are raised to it, as SciPy does).
    pub rtol: f64,
    /// Absolute tolerance per state (must be >= 0).
    pub atol: [f64; N],
    /// Initial step; `None` selects it automatically (SciPy `first_step=None`).
    pub first_step: Option<f64>,
    /// Largest allowed step (SciPy `max_step`, default infinity).
    pub max_step: f64,
    /// Guard on the number of step attempts (accepted plus rejected). SciPy has no such limit;
    /// exceeding it returns [`OdeError::TooManySteps`], which lets a caller fall back to an
    /// implicit solver.
    pub max_attempts: usize,
}

impl<const N: usize> OdeOptions<N> {
    /// Options with a scalar `atol` for every state and SciPy's other defaults.
    pub fn new(rtol: f64, atol: f64) -> Self {
        OdeOptions {
            rtol,
            atol: [atol; N],
            first_step: None,
            max_step: f64::INFINITY,
            max_attempts: 1_000_000,
        }
    }
}

/// How the integration ended (SciPy `status`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OdeStatus {
    /// The end of the interval was reached (SciPy status 0).
    Finished,
    /// A terminal event occurred (SciPy status 1).
    TerminalEvent,
}

/// Result of [`dopri5`] (SciPy `OdeResult` without the dense-output object).
#[derive(Debug, Clone, PartialEq)]
pub struct OdeSolution<const N: usize> {
    /// Output times: every step end (including `t0`) when no `t_eval` is given, else the
    /// `t_eval` values reached.
    pub t: Vec<f64>,
    /// States at `t`.
    pub y: Vec<[f64; N]>,
    /// Event times, one list per event.
    pub t_events: Vec<Vec<f64>>,
    /// States at the event times.
    pub y_events: Vec<Vec<[f64; N]>>,
    /// End condition.
    pub status: OdeStatus,
    /// Number of RHS evaluations (SciPy `nfev`).
    pub nfev: usize,
    /// Accepted steps.
    pub n_steps: usize,
    /// Rejected step attempts.
    pub n_rejected: usize,
}

/// Failure of [`dopri5`].
#[derive(Debug, Clone, PartialEq)]
pub enum OdeError {
    /// Invalid tolerances, interval, first step or `t_eval`.
    InvalidInput(String),
    /// The right-hand side returned an error.
    Rhs { t: f64, message: String },
    /// The step size fell below `10 * |nextafter(t) - t|` (SciPy "Required step size is less
    /// than spacing between numbers.").
    StepTooSmall { t: f64 },
    /// More than `max_attempts` step attempts.
    TooManySteps { t: f64, attempts: usize },
    /// An event time could not be located.
    Event { index: usize, message: String },
}

impl fmt::Display for OdeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OdeError::InvalidInput(m) => write!(f, "invalid input: {m}"),
            OdeError::Rhs { t, message } => {
                write!(f, "right-hand side failed at t = {t}: {message}")
            }
            OdeError::StepTooSmall { t } => write!(
                f,
                "required step size is less than spacing between numbers (t = {t})"
            ),
            OdeError::TooManySteps { t, attempts } => {
                write!(f, "more than {attempts} step attempts (t = {t})")
            }
            OdeError::Event { index, message } => {
                write!(f, "event {index} could not be located: {message}")
            }
        }
    }
}

impl std::error::Error for OdeError {}

/// Python's `min(a, b)`: `b` if `b < a`, else `a`.
#[inline]
fn py_min(a: f64, b: f64) -> f64 {
    if b < a { b } else { a }
}

/// Python's `max(a, b)`: `b` if `b > a`, else `a`.
#[inline]
fn py_max(a: f64, b: f64) -> f64 {
    if b > a { b } else { a }
}

/// `numpy.maximum`: NaN if either argument is NaN.
#[inline]
fn np_maximum(a: f64, b: f64) -> f64 {
    if a.is_nan() || b.is_nan() {
        f64::NAN
    } else if a >= b {
        a
    } else {
        b
    }
}

/// SciPy `common.norm`: `np.linalg.norm(x) / x.size ** 0.5`.
#[inline]
fn rms<const N: usize>(x: &[f64; N]) -> f64 {
    let mut s = 0.0;
    for v in x {
        s += v * v;
    }
    s.sqrt() / (N as f64).sqrt()
}

/// Dense output of one step (SciPy `RkDenseOutput`).
#[derive(Debug, Clone)]
struct DenseStep<const N: usize> {
    t_old: f64,
    h: f64,
    y_old: [f64; N],
    q: [[f64; 4]; N],
}

impl<const N: usize> DenseStep<N> {
    fn new(t_old: f64, t: f64, y_old: [f64; N], k: &[[f64; N]; 7]) -> Self {
        let mut q = [[0.0; 4]; N];
        for i in 0..N {
            for c in 0..4 {
                let mut s = 0.0;
                for j in 0..7 {
                    s += k[j][i] * P[j][c];
                }
                q[i][c] = s;
            }
        }
        DenseStep {
            t_old,
            h: t - t_old,
            y_old,
            q,
        }
    }

    fn eval(&self, t: f64) -> [f64; N] {
        let x = (t - self.t_old) / self.h;
        let p0 = x;
        let p1 = p0 * x;
        let p2 = p1 * x;
        let p3 = p2 * x;
        let p = [p0, p1, p2, p3];
        let mut y = [0.0; N];
        for i in 0..N {
            let mut s = 0.0;
            for c in 0..4 {
                s += self.q[i][c] * p[c];
            }
            y[i] = self.h * s + self.y_old[i];
        }
        y
    }
}

fn call_rhs<const N: usize, R: OdeRhs<N> + ?Sized>(
    rhs: &mut R,
    t: f64,
    y: &[f64; N],
    nfev: &mut usize,
) -> Result<[f64; N], OdeError> {
    let mut dy = [0.0; N];
    *nfev += 1;
    rhs.eval(t, y, &mut dy)
        .map_err(|message| OdeError::Rhs { t, message })?;
    Ok(dy)
}

#[allow(clippy::too_many_arguments)]
fn select_initial_step<const N: usize, R: OdeRhs<N> + ?Sized>(
    rhs: &mut R,
    t0: f64,
    y0: &[f64; N],
    t_bound: f64,
    max_step: f64,
    f0: &[f64; N],
    direction: f64,
    rtol: f64,
    atol: &[f64; N],
    nfev: &mut usize,
) -> Result<f64, OdeError> {
    let interval_length = (t_bound - t0).abs();
    if interval_length == 0.0 {
        return Ok(0.0);
    }
    let mut scale = [0.0; N];
    let mut ys = [0.0; N];
    let mut fs = [0.0; N];
    for i in 0..N {
        scale[i] = atol[i] + y0[i].abs() * rtol;
        ys[i] = y0[i] / scale[i];
        fs[i] = f0[i] / scale[i];
    }
    let d0 = rms(&ys);
    let d1 = rms(&fs);
    let mut h0 = if d0 < 1e-5 || d1 < 1e-5 {
        1e-6
    } else {
        0.01 * d0 / d1
    };
    h0 = py_min(h0, interval_length);
    let hd = h0 * direction;
    let mut y1 = [0.0; N];
    for i in 0..N {
        y1[i] = y0[i] + hd * f0[i];
    }
    let f1 = call_rhs(rhs, t0 + h0 * direction, &y1, nfev)?;
    let mut df = [0.0; N];
    for i in 0..N {
        df[i] = (f1[i] - f0[i]) / scale[i];
    }
    let d2 = rms(&df) / h0;
    let h1 = if d1 <= 1e-15 && d2 <= 1e-15 {
        py_max(1e-6, h0 * 1e-3)
    } else {
        (0.01 / py_max(d1, d2)).powf(1.0 / 5.0)
    };
    Ok(py_min(
        py_min(py_min(100.0 * h0, h1), interval_length),
        max_step,
    ))
}

/// Integrate `dy/dt = rhs(t, y)` from `t_span.0` to `t_span.1` (either direction) with the
/// Dormand-Prince 5(4) pair; see the module documentation for the algorithm.
///
/// `t_eval` (optional) must lie within the interval and be strictly monotonic in the integration
/// direction; the solution is then reported only there (through the dense output). Events are
/// located as in SciPy `solve_ivp`.
pub fn dopri5<const N: usize, R: OdeRhs<N> + ?Sized>(
    rhs: &mut R,
    t_span: (f64, f64),
    y0: [f64; N],
    t_eval: Option<&[f64]>,
    events: &mut [Event<'_, N>],
    opts: &OdeOptions<N>,
) -> Result<OdeSolution<N>, OdeError> {
    let (t0, tf) = t_span;
    if !t0.is_finite() || !tf.is_finite() {
        return Err(OdeError::InvalidInput("t_span must be finite".into()));
    }
    if opts.atol.iter().any(|a| *a < 0.0 || a.is_nan()) || opts.rtol.is_nan() {
        return Err(OdeError::InvalidInput("`atol` must be positive".into()));
    }
    if opts.max_step.is_nan() || opts.max_step <= 0.0 {
        return Err(OdeError::InvalidInput("`max_step` must be positive".into()));
    }
    let rtol = np_maximum(opts.rtol, 100.0 * f64::EPSILON);
    let atol = opts.atol;
    let direction = if tf != t0 { (tf - t0).signum() } else { 1.0 };

    // t_eval checks and orientation (ascending copy with a cursor, as solve_ivp)
    let mut t_eval_sorted: Vec<f64> = Vec::new();
    let mut t_eval_i = 0usize;
    if let Some(te) = t_eval {
        let (lo, hi) = (t0.min(tf), t0.max(tf));
        if te.iter().any(|v| !(lo..=hi).contains(v)) {
            return Err(OdeError::InvalidInput(
                "values in `t_eval` are not within `t_span`".into(),
            ));
        }
        let sorted_ok = te.windows(2).all(|w| {
            if tf > t0 {
                w[1] - w[0] > 0.0
            } else {
                w[1] - w[0] < 0.0
            }
        });
        if !sorted_ok {
            return Err(OdeError::InvalidInput(
                "values in `t_eval` are not properly sorted".into(),
            ));
        }
        t_eval_sorted = te.to_vec();
        if tf > t0 {
            t_eval_i = 0;
        } else {
            t_eval_sorted.reverse();
            t_eval_i = t_eval_sorted.len();
        }
    }

    let mut nfev = 0usize;
    let mut t = t0;
    let mut y = y0;
    let mut f = call_rhs(rhs, t, &y, &mut nfev)?;
    let mut h_abs = match opts.first_step {
        None => select_initial_step(
            rhs,
            t0,
            &y0,
            tf,
            opts.max_step,
            &f,
            direction,
            rtol,
            &atol,
            &mut nfev,
        )?,
        Some(h) => {
            if h <= 0.0 || h.is_nan() {
                return Err(OdeError::InvalidInput(
                    "`first_step` must be positive".into(),
                ));
            }
            if h > (tf - t0).abs() {
                return Err(OdeError::InvalidInput("`first_step` exceeds bounds".into()));
            }
            h
        }
    };

    let n_ev = events.len();
    let mut g: Vec<f64> = events.iter_mut().map(|e| (e.g)(t0, &y0)).collect();
    let mut event_count = vec![0u32; n_ev];
    let mut t_events: Vec<Vec<f64>> = vec![Vec::new(); n_ev];
    let mut y_events: Vec<Vec<[f64; N]>> = vec![Vec::new(); n_ev];

    let mut ts: Vec<f64> = Vec::new();
    let mut ys: Vec<[f64; N]> = Vec::new();
    if t_eval.is_none() {
        ts.push(t0);
        ys.push(y0);
    }

    let mut k = [[0.0; N]; 7];
    let mut n_steps = 0usize;
    let mut n_rejected = 0usize;
    let mut attempts = 0usize;

    if t0 == tf {
        // SciPy finishes immediately without taking a step.
        if !t_eval_sorted.is_empty() {
            ts.extend(t_eval_sorted.iter().copied());
            ys.extend(t_eval_sorted.iter().map(|_| y0));
        }
        return Ok(OdeSolution {
            t: ts,
            y: ys,
            t_events,
            y_events,
            status: OdeStatus::Finished,
            nfev,
            n_steps,
            n_rejected,
        });
    }

    loop {
        // ---- one step of RungeKutta._step_impl
        let min_step = 10.0
            * (if direction > 0.0 {
                t.next_up()
            } else {
                t.next_down()
            } - t)
                .abs();
        let mut h_try = if h_abs > opts.max_step {
            opts.max_step
        } else if h_abs < min_step {
            min_step
        } else {
            h_abs
        };
        let mut step_rejected = false;
        let (t_new, y_new, f_new) = loop {
            if h_try < min_step {
                return Err(OdeError::StepTooSmall { t });
            }
            attempts += 1;
            if attempts > opts.max_attempts {
                return Err(OdeError::TooManySteps {
                    t,
                    attempts: opts.max_attempts,
                });
            }
            let mut h = h_try * direction;
            let mut t_new = t + h;
            if direction * (t_new - tf) > 0.0 {
                t_new = tf;
            }
            h = t_new - t;
            h_try = h.abs();

            // rk_step
            k[0] = f;
            for s in 1..6 {
                let mut ystage = [0.0; N];
                for i in 0..N {
                    let mut acc = 0.0;
                    for j in 0..s {
                        acc += k[j][i] * A[s][j];
                    }
                    ystage[i] = y[i] + acc * h;
                }
                k[s] = call_rhs(rhs, t + C[s] * h, &ystage, &mut nfev)?;
            }
            let mut y_new = [0.0; N];
            for i in 0..N {
                let mut acc = 0.0;
                for j in 0..6 {
                    acc += k[j][i] * B[j];
                }
                y_new[i] = y[i] + h * acc;
            }
            let f_new = call_rhs(rhs, t + h, &y_new, &mut nfev)?;
            k[6] = f_new;

            let mut err = [0.0; N];
            for i in 0..N {
                let scale = atol[i] + np_maximum(y[i].abs(), y_new[i].abs()) * rtol;
                let mut acc = 0.0;
                for j in 0..7 {
                    acc += k[j][i] * E[j];
                }
                err[i] = acc * h / scale;
            }
            let error_norm = rms(&err);

            if error_norm < 1.0 {
                let mut factor = if error_norm == 0.0 {
                    MAX_FACTOR
                } else {
                    py_min(MAX_FACTOR, SAFETY * error_norm.powf(ERROR_EXPONENT))
                };
                if step_rejected {
                    factor = py_min(1.0, factor);
                }
                h_try *= factor;
                break (t_new, y_new, f_new);
            }
            h_try *= py_max(MIN_FACTOR, SAFETY * error_norm.powf(ERROR_EXPONENT));
            step_rejected = true;
            n_rejected += 1;
        };
        n_steps += 1;
        h_abs = h_try;
        let t_old = t;
        let y_old = y;
        t = t_new;
        y = y_new;
        f = f_new;
        let mut finished = direction * (t - tf) >= 0.0;
        let mut terminal = false;
        let mut dense: Option<DenseStep<N>> = None;

        // ---- events (solve_ivp: find_active_events / handle_events)
        if n_ev > 0 {
            let g_new: Vec<f64> = events.iter_mut().map(|e| (e.g)(t, &y)).collect();
            let mut active: Vec<usize> = Vec::new();
            for i in 0..n_ev {
                let up = g[i] <= 0.0 && g_new[i] >= 0.0;
                let down = g[i] >= 0.0 && g_new[i] <= 0.0;
                let dir = events[i].direction;
                if (up && dir > 0.0) || (down && dir < 0.0) || ((up || down) && dir == 0.0) {
                    active.push(i);
                }
            }
            if !active.is_empty() {
                let sol = dense.get_or_insert_with(|| DenseStep::new(t_old, t, y_old, &k));
                for &i in &active {
                    event_count[i] += 1;
                }
                let mut roots: Vec<f64> = Vec::with_capacity(active.len());
                for &i in &active {
                    let ev = &mut events[i];
                    let root = brentq_try(
                        |tt| Ok::<f64, ()>((ev.g)(tt, &sol.eval(tt))),
                        t_old,
                        t,
                        BrentOptions {
                            xtol: 4.0 * f64::EPSILON,
                            rtol: 4.0 * f64::EPSILON,
                            maxiter: 100,
                        },
                    )
                    .map_err(|e: BrentError<()>| OdeError::Event {
                        index: i,
                        message: match e {
                            BrentError::SignError { .. } => {
                                "f(a) and f(b) must have different signs".to_string()
                            }
                            BrentError::NanValue { .. } => "event function returned NaN".into(),
                            BrentError::NotConverged(_) => "brentq did not converge".into(),
                            _ => "brentq failed".into(),
                        },
                    })?;
                    roots.push(root.x);
                }
                let reached =
                    |i: usize, cnt: &[u32]| events[i].terminal.is_some_and(|m| cnt[i] >= m);
                if active.iter().any(|&i| reached(i, &event_count)) {
                    let mut order: Vec<usize> = (0..active.len()).collect();
                    // np.argsort (quicksort, not stable; ties between events are not expected)
                    if t > t_old {
                        order.sort_by(|&a, &b| roots[a].total_cmp(&roots[b]));
                    } else {
                        order.sort_by(|&a, &b| roots[b].total_cmp(&roots[a]));
                    }
                    let act_sorted: Vec<usize> = order.iter().map(|&o| active[o]).collect();
                    let roots_sorted: Vec<f64> = order.iter().map(|&o| roots[o]).collect();
                    let cut = act_sorted
                        .iter()
                        .position(|&i| reached(i, &event_count))
                        .unwrap_or(act_sorted.len() - 1);
                    active = act_sorted[..=cut].to_vec();
                    roots = roots_sorted[..=cut].to_vec();
                    terminal = true;
                }
                for (&e, &te) in active.iter().zip(roots.iter()) {
                    t_events[e].push(te);
                    y_events[e].push(sol.eval(te));
                }
                if terminal {
                    let te = *roots.last().unwrap_or(&t);
                    t = te;
                    y = sol.eval(te);
                    finished = true;
                }
            }
            g = g_new;
        }

        // ---- output
        if t_eval.is_none() {
            ts.push(t);
            ys.push(y);
        } else {
            let (lo_i, hi_i, new_i) = if direction > 0.0 {
                let new_i = t_eval_sorted.partition_point(|v| *v <= t);
                (t_eval_i, new_i, new_i)
            } else {
                let new_i = t_eval_sorted.partition_point(|v| *v < t);
                (new_i, t_eval_i, new_i)
            };
            if hi_i > lo_i {
                let sol = dense.get_or_insert_with(|| DenseStep::new(t_old, t_new, y_old, &k));
                if direction > 0.0 {
                    for &te in &t_eval_sorted[lo_i..hi_i] {
                        ts.push(te);
                        ys.push(sol.eval(te));
                    }
                } else {
                    for &te in t_eval_sorted[lo_i..hi_i].iter().rev() {
                        ts.push(te);
                        ys.push(sol.eval(te));
                    }
                }
                t_eval_i = new_i;
            }
        }

        if finished {
            return Ok(OdeSolution {
                t: ts,
                y: ys,
                t_events,
                y_events,
                status: if terminal {
                    OdeStatus::TerminalEvent
                } else {
                    OdeStatus::Finished
                },
                nfev,
                n_steps,
                n_rejected,
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn decay(_t: f64, y: &[f64; 1], dy: &mut [f64; 1]) -> Result<(), String> {
        dy[0] = -y[0];
        Ok(())
    }

    #[test]
    fn tableau_is_consistent() {
        for s in 0..6 {
            let row: f64 = A[s].iter().sum();
            assert!((row - C[s]).abs() < 1e-15, "row {s}");
        }
        assert!((B.iter().sum::<f64>() - 1.0).abs() < 1e-15);
        assert!(E.iter().sum::<f64>().abs() < 1e-15);
        // dense output reproduces y_new at x = 1: sum_k P[j][k] = B[j] (B[6] = 0)
        for j in 0..7 {
            let s: f64 = P[j].iter().sum();
            let bj = if j < 6 { B[j] } else { 0.0 };
            assert!((s - bj).abs() < 1e-14, "P row {j}");
        }
    }

    #[test]
    fn exponential_decay_accuracy() {
        let opts = OdeOptions::new(1e-10, 1e-12);
        let sol = dopri5(&mut decay, (0.0, 5.0), [1.0], None, &mut [], &opts).unwrap();
        assert_eq!(sol.status, OdeStatus::Finished);
        assert_eq!(*sol.t.last().unwrap(), 5.0);
        for (t, y) in sol.t.iter().zip(&sol.y) {
            assert!((y[0] - (-t).exp()).abs() < 1e-9);
        }
        assert_eq!(sol.nfev, 2 + 6 * (sol.n_steps + sol.n_rejected));
    }

    #[test]
    fn t_eval_includes_both_ends() {
        let opts = OdeOptions::new(1e-8, 1e-10);
        let te = [0.0, 0.5, 1.0, 2.0];
        let sol = dopri5(&mut decay, (0.0, 2.0), [1.0], Some(&te), &mut [], &opts).unwrap();
        assert_eq!(sol.t, te.to_vec());
        assert_eq!(sol.y[0][0], 1.0);
        assert!((sol.y[3][0] - (-2.0_f64).exp()).abs() < 1e-8);
    }

    #[test]
    fn backward_integration() {
        let opts = OdeOptions::new(1e-10, 1e-14);
        let te = [3.0, 2.0, 1.0, 0.0];
        let sol = dopri5(
            &mut decay,
            (3.0, 0.0),
            [(-3.0_f64).exp()],
            Some(&te),
            &mut [],
            &opts,
        )
        .unwrap();
        assert_eq!(sol.t, te.to_vec());
        assert!((sol.y[3][0] - 1.0).abs() < 1e-8);
    }

    #[test]
    fn terminal_event_ballistic() {
        let mut rhs = |_t: f64, y: &[f64; 2], dy: &mut [f64; 2]| -> Result<(), String> {
            dy[0] = y[1];
            dy[1] = -9.81;
            Ok(())
        };
        let mut ev = [Event::new(|_t: f64, y: &[f64; 2]| y[0], true, -1.0)];
        let opts = OdeOptions::new(1e-8, 1e-10);
        let sol = dopri5(&mut rhs, (0.0, 10.0), [10.0, 0.0], None, &mut ev, &opts).unwrap();
        assert_eq!(sol.status, OdeStatus::TerminalEvent);
        let t_hit = (2.0 * 10.0 / 9.81_f64).sqrt();
        assert!((sol.t_events[0][0] - t_hit).abs() < 1e-10);
        assert_eq!(*sol.t.last().unwrap(), sol.t_events[0][0]);
        assert!(sol.y_events[0][0][0].abs() < 1e-9);
    }

    #[test]
    fn rhs_error_is_reported() {
        let mut rhs = |t: f64, _y: &[f64; 1], dy: &mut [f64; 1]| -> Result<(), String> {
            if t > 0.5 {
                return Err("outside model domain".into());
            }
            dy[0] = 1.0;
            Ok(())
        };
        let opts = OdeOptions::new(1e-6, 1e-9);
        let e = dopri5(&mut rhs, (0.0, 1.0), [0.0], None, &mut [], &opts).unwrap_err();
        assert!(matches!(e, OdeError::Rhs { .. }));
    }

    #[test]
    fn too_many_steps_guard() {
        let mut opts = OdeOptions::new(1e-12, 1e-14);
        opts.max_attempts = 5;
        let e = dopri5(&mut decay, (0.0, 100.0), [1.0], None, &mut [], &opts).unwrap_err();
        assert!(matches!(e, OdeError::TooManySteps { .. }));
    }

    #[test]
    fn invalid_t_eval() {
        let opts = OdeOptions::new(1e-6, 1e-9);
        let e = dopri5(
            &mut decay,
            (0.0, 1.0),
            [1.0],
            Some(&[0.5, 0.2]),
            &mut [],
            &opts,
        );
        assert!(matches!(e, Err(OdeError::InvalidInput(_))));
        let e = dopri5(&mut decay, (0.0, 1.0), [1.0], Some(&[2.0]), &mut [], &opts);
        assert!(matches!(e, Err(OdeError::InvalidInput(_))));
    }

    #[test]
    fn max_step_is_respected() {
        let mut opts = OdeOptions::new(1e-6, 1e-9);
        opts.max_step = 0.01;
        let sol = dopri5(&mut decay, (0.0, 1.0), [1.0], None, &mut [], &opts).unwrap();
        for w in sol.t.windows(2) {
            assert!(w[1] - w[0] <= 0.01 + 1e-15);
        }
    }
}
