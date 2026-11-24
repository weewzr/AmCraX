"""Generate the golden reference tables for the amcrax-numerics crate.

The tables are produced ONCE by Python (NumPy and SciPy are the reference
implementations) and committed. They are never regenerated from Rust. The Rust
tests in rust/crates/amcrax-numerics/tests/golden.rs read them, check the SHA-256
recorded in MANIFEST.json and compare the Rust results with the stated
comparison rule (bitwise or a justified tolerance) that each table carries.

Run from the repository root with the project virtual environment:

    python rust/golden/generate_numerics_golden.py

Only the standard library, NumPy and SciPy are imported. Floats are written with
repr(), the shortest string that round-trips to the same float64 (at most 17
significant digits). Non-finite floats are written as the strings "nan", "inf"
and "-inf". Files are written with LF line endings.

The script also exports the Joe-Kuo direction numbers that SciPy ships
(scipy/stats/_sobol_direction_numbers.npz, from new-joe-kuo-6.21201) for the
first SOBOL_EXPORT_DIMS dimensions into
rust/crates/amcrax-numerics/src/sobol_directions.rs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.stats import qmc

HERE = Path(__file__).resolve().parent
RUST_DIR = HERE.parent
OUT_DIR = HERE / "numerics"
SOBOL_RS = RUST_DIR / "crates" / "amcrax-numerics" / "src" / "sobol_directions.rs"
SOBOL_EXPORT_DIMS = 1111
GENERATOR = "rust/golden/generate_numerics_golden.py"

META = {
    "generator": GENERATOR,
    "python": platform.python_version(),
    "numpy": np.__version__,
    "scipy": scipy.__version__,
    "platform": f"{platform.system()} {platform.machine()}",
}


def enc(o):
    """Convert to JSON-safe Python objects; floats keep full precision."""
    if isinstance(o, dict):
        return {str(k): enc(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [enc(v) for v in o]
    if isinstance(o, np.ndarray):
        return enc(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if math.isnan(f):
            return "nan"
        if math.isinf(f):
            return "inf" if f > 0 else "-inf"
        return f
    return o


def write_table(name: str, body: dict, manifest: dict) -> None:
    table = {"meta": dict(META, table=name), **body}
    text = json.dumps(enc(table), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    path = OUT_DIR / f"{name}.json"
    path.write_bytes(data)
    manifest["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    print(f"wrote {path.relative_to(RUST_DIR.parent)} ({len(data)} bytes)")


# --------------------------------------------------------------------------- brentq

# Functions evaluated identically in Rust ("arith": only +, -, *, / so the values
# are bit-identical in both languages) or replayed from the recorded trace
# ("replay": transcendental functions whose libm results may differ by one ulp
# between platforms; Rust checks that it asks for exactly the recorded x values
# and receives the recorded f values, which proves iterate-for-iterate identity).
BRENT_ARITH = {
    "cubic": (lambda x: x * x * x - 2.0 * x - 5.0, "x*x*x - 2*x - 5"),
    "sqrt2": (lambda x: x * x - 2.0, "x*x - 2"),
    "reciprocal": (lambda x: 1.0 / x - 3.0, "1/x - 3"),
    "quintic_flat": (lambda x: x * x * x * x * x - 1e-3, "x*x*x*x*x - 1e-3"),
    "three_roots": (lambda x: (x - 1.1) * (x - 2.3) * (x - 3.7), "(x - 1.1)*(x - 2.3)*(x - 3.7)"),
    "linear": (lambda x: 3.0 * x - 1.0, "3*x - 1"),
    "shift_a": (lambda x: x - 2.0, "x - 2"),
    "shift_b": (lambda x: x - 5.0, "x - 5"),
    "no_root": (lambda x: x * x + 1.0, "x*x + 1"),
    "steep_rational": (lambda x: (x - 0.7) / (x * x + 1e-4), "(x - 0.7)/(x*x + 1e-4)"),
}
BRENT_REPLAY = {
    "exp": (lambda x: math.exp(x) - 2.0, "exp(x) - 2"),
    "cos_fixed_point": (lambda x: math.cos(x) - x, "cos(x) - x"),
    "atan": (lambda x: math.atan(x - 0.3), "atan(x - 0.3)"),
    "log": (lambda x: math.log(x) - 0.5, "log(x) - 0.5"),
    "tanh_step": (lambda x: math.tanh(5.0 * (x - 0.123)), "tanh(5*(x - 0.123))"),
    "sin_pi": (lambda x: math.sin(x), "sin(x)"),
    "x_exp_x": (lambda x: x * math.exp(x) - 1.0, "x*exp(x) - 1"),
}
XTOL = 2e-12
RTOL = 4 * np.finfo(float).eps


def brent_cases():
    c = []

    def add(fname, a, b, xtol=XTOL, rtol=RTOL, maxiter=100):
        c.append((fname, a, b, xtol, rtol, maxiter))

    add("cubic", 2.0, 3.0)
    add("cubic", 3.0, 2.0)
    add("cubic", -100.0, 1000.0)
    add("cubic", 2.0, 3.0, xtol=1e-6)
    add("cubic", 2.0, 3.0, rtol=1e-6)
    add("cubic", 2.0, 3.0, maxiter=3)
    add("cubic", 2.0945514815423, 2.0945514815424)
    add("sqrt2", 0.0, 2.0)
    add("sqrt2", 1.0, 1e6)
    add("reciprocal", 0.1, 1.0)
    add("quintic_flat", -1.0, 2.0)
    add("three_roots", 1.9, 3.0)
    add("three_roots", 0.0, 10.0)
    add("linear", -5.0, 5.0)
    add("shift_a", 2.0, 5.0)
    add("shift_b", 2.0, 5.0)
    add("no_root", -1.0, 1.0)
    add("steep_rational", 0.01, 10.0)
    add("steep_rational", 0.01, 10.0, xtol=1e-9, maxiter=500)
    add("exp", -1.0, 3.0)
    add("cos_fixed_point", 0.0, 1.0)
    add("atan", -10.0, 50.0)
    add("log", 0.5, 5.0)
    add("log", 0.5, 5.0, xtol=0.02)
    add("tanh_step", -1.0, 1.0)
    add("sin_pi", 3.0, 4.0)
    add("x_exp_x", 0.0, 1.0)
    add("x_exp_x", 0.0, 1.0, maxiter=4)
    return c


def gen_brentq(manifest):
    cases = []
    for fname, a, b, xtol, rtol, maxiter in brent_cases():
        kind = "arith" if fname in BRENT_ARITH else "replay"
        f, expr = (BRENT_ARITH if kind == "arith" else BRENT_REPLAY)[fname]
        trace = []

        def g(x, f=f, trace=trace):
            v = f(x)
            trace.append([x, v])
            return v

        case = {"function": fname, "expr": expr, "kind": kind, "a": a, "b": b,
                "xtol": xtol, "rtol": rtol, "maxiter": maxiter}
        try:
            root, r = brentq(g, a, b, xtol=xtol, rtol=rtol, maxiter=maxiter, full_output=True, disp=False)
            case.update(error=None, root=root, iterations=r.iterations,
                        function_calls=r.function_calls, converged=bool(r.converged), flag=r.flag)
        except ValueError as exc:
            case.update(error="sign" if "different signs" in str(exc) else "value", message=str(exc))
        case["trace"] = trace
        cases.append(case)
    write_table("brentq", {
        "description": "scipy.optimize.brentq(f, a, b, xtol, rtol, maxiter, full_output=True, disp=False)",
        "comparison": {"rule": "bitwise",
                       "why": "exact port of SciPy brentq.c: the same IEEE operations in the same order give the same "
                              "iterates; root, iterations, function calls, flag and the full evaluation trace must be identical"},
        "defaults": {"xtol": XTOL, "rtol": RTOL, "maxiter": 100},
        "cases": cases,
    }, manifest)
    return len(cases)


# --------------------------------------------------------------------------- DOPRI5

def rhs_decay(t, y):
    return [-y[0]]


def rhs_exp_sin(t, y):
    return [y[0] * math.cos(t)]


def rhs_osc(t, y):
    return [y[1], -y[0]]


def rhs_vdp(t, y):
    return [y[1], (1.0 - y[0] * y[0]) * y[1] - y[0]]


def rhs_lv(t, y):
    return [1.5 * y[0] - y[0] * y[1], -3.0 * y[1] + y[0] * y[1]]


def rhs_ballistic(t, y):
    return [y[1], -9.81]


def rhs_sqrt_drop(t, y):
    return [-0.8 / y[0]]


ODE_PROBLEMS = {
    "decay": dict(rhs=rhs_decay, y0=[1.0], span=(0.0, 10.0), expr="y' = -y",
                  exact=lambda t: [math.exp(-t)]),
    "decay_backward": dict(rhs=rhs_decay, y0=[math.exp(-10.0)], span=(10.0, 0.0), expr="y' = -y, integrated from t=10 to t=0",
                           exact=lambda t: [math.exp(-t)]),
    "exp_sin": dict(rhs=rhs_exp_sin, y0=[1.0], span=(0.0, 10.0), expr="y' = y cos t",
                    exact=lambda t: [math.exp(math.sin(t))]),
    "oscillator": dict(rhs=rhs_osc, y0=[1.0, 0.0], span=(0.0, 20.0), expr="y0' = y1, y1' = -y0",
                       exact=lambda t: [math.cos(t), -math.sin(t)]),
    "van_der_pol": dict(rhs=rhs_vdp, y0=[2.0, 0.0], span=(0.0, 20.0), expr="mu = 1", exact=None),
    "lotka_volterra": dict(rhs=rhs_lv, y0=[10.0, 5.0], span=(0.0, 15.0), expr="a=1.5, b=1, c=3, d=1", exact=None),
    "ballistic": dict(rhs=rhs_ballistic, y0=[10.0, 0.0], span=(0.0, 10.0), expr="h' = v, v' = -9.81",
                      exact=lambda t: [10.0 - 0.5 * 9.81 * t * t, -9.81 * t]),
    "sqrt_drop": dict(rhs=rhs_sqrt_drop, y0=[1.0], span=(0.0, 1.0), expr="p' = -0.8/p (p^2 = 1 - 1.6 t)",
                      exact=lambda t: [math.sqrt(1.0 - 1.6 * t)]),
}


def ev_ground(t, y):
    return y[0]


ev_ground.terminal = True
ev_ground.direction = -1


def ev_cross(t, y):
    return y[0]


ev_cross.terminal = False
ev_cross.direction = 0


def ev_five_percent(t, y):
    return y[0] - 0.05


ev_five_percent.terminal = True
ev_five_percent.direction = 0


def ev_upcross(t, y):
    return y[1]


ev_upcross.terminal = False
ev_upcross.direction = 1


EVENTS = {
    "ground": (ev_ground, "y0 = 0, terminal, direction -1", True, -1),
    "cross": (ev_cross, "y0 = 0, not terminal, direction 0", False, 0),
    "five_percent": (ev_five_percent, "y0 - 0.05 = 0, terminal, direction 0", True, 0),
    "upcross": (ev_upcross, "y1 = 0, not terminal, direction +1", False, 1),
}

ODE_CASES = [
    ("decay", (), [(1e-6, 1e-9), (1e-10, 1e-12), (1e-3, 1e-6)]),
    ("decay_backward", (), [(1e-6, 1e-12), (1e-10, 1e-14)]),
    ("exp_sin", (), [(1e-6, 1e-9), (1e-10, 1e-12)]),
    ("oscillator", (), [(1e-6, 1e-9), (1e-10, 1e-12)]),
    ("oscillator", ("cross", "upcross"), [(1e-8, 1e-10)]),
    ("van_der_pol", (), [(1e-6, 1e-9), (1e-10, 1e-12)]),
    ("lotka_volterra", (), [(1e-6, 1e-9), (1e-10, 1e-12)]),
    ("ballistic", ("ground",), [(1e-6, 1e-9), (1e-10, 1e-12)]),
    ("sqrt_drop", ("five_percent",), [(1e-8, 1e-12)]),
]
ODE_GATE_SCIPY = 0.05  # in units of (atol + rtol*|y|)
ODE_GATE_EXACT = 200.0  # in units of (atol + rtol*max|y|)


def gen_dopri5(manifest):
    cases = []
    for pname, evnames, tols in ODE_CASES:
        p = ODE_PROBLEMS[pname]
        a, b = p["span"]
        t_eval = list(np.linspace(a, b, 41))
        for rtol, atol in tols:
            events = [EVENTS[e][0] for e in evnames] or None
            r_steps = solve_ivp(p["rhs"], (a, b), p["y0"], method="RK45", rtol=rtol, atol=atol, events=events)
            r = solve_ivp(p["rhs"], (a, b), p["y0"], method="RK45", rtol=rtol, atol=atol, t_eval=t_eval, events=events)
            case = {"problem": pname, "expr": p["expr"], "y0": p["y0"], "t_span": [a, b], "rtol": rtol, "atol": atol,
                    "events": [{"name": e, "expr": EVENTS[e][1], "terminal": EVENTS[e][2], "direction": EVENTS[e][3]}
                               for e in evnames],
                    "t_eval": t_eval, "status": int(r.status), "nfev": int(r.nfev),
                    "n_steps": int(len(r_steps.t) - 1), "step_t": r_steps.t, "t": r.t, "y": r.y.T,
                    "t_events": [list(te) for te in (r.t_events or [])],
                    "y_events": [[list(v) for v in ye] for ye in (r.y_events or [])]}
            if p["exact"] is not None:
                ex = np.array([p["exact"](t) for t in r.t])
                ymax = np.max(np.abs(r.y.T), axis=0)
                units = np.max(np.abs(r.y.T - ex) / (atol + rtol * ymax))
                case["scipy_exact_error_units"] = float(units)
                assert units < ODE_GATE_EXACT, (pname, rtol, units)
            cases.append(case)
    write_table("dopri5", {
        "description": "scipy.integrate.solve_ivp(method='RK45', rtol, atol, t_eval, events): Dormand-Prince 5(4) with "
                       "the 4th-order dense output and brentq event location",
        "comparison": {
            "rule": "tolerance",
            "scipy_gate_units": ODE_GATE_SCIPY,
            "exact_gate_units": ODE_GATE_EXACT,
            "why": "same method, same step-size controller and the same initial-step rule as SciPy RK45, so the number "
                   "of RHS evaluations and of accepted steps must be identical. The values are not bit-identical because "
                   "NumPy forms the stage sums and the error estimate with BLAS dot products whose summation order "
                   "differs; the error estimate is a strongly cancelling sum, so the step sizes differ in the last "
                   "digits. Gate: |y_rust - y_scipy| <= scipy_gate_units * (atol + rtol*|y_scipy|) at every t_eval point "
                   "(observed during development: below 0.002 units), the same for event times with |t| in place "
                   "of |y|; and against the analytic solution |y - y_exact| <= exact_gate_units * (atol + rtol*max|y|), "
                   "the same bound that SciPy's own solution satisfies (scipy_exact_error_units)."},
        "cases": cases,
    }, manifest)
    return len(cases)


# --------------------------------------------------------------------------- interpolation

def gen_pchip(manifest):
    rng = np.random.default_rng(3)
    data = [
        ("two_points", [0.0, 1.0], [1.0, 3.0]),
        ("three_points", [0.0, 1.0, 2.0], [0.0, 1.0, 0.5]),
        ("flat_segments", [0.0, 1.0, 2.0, 3.0, 4.0, 5.0], [0.0, 0.0, 1.0, 1.0, 0.0, 2.0]),
        ("random_nonuniform", np.cumsum(rng.random(12) + 0.1), rng.standard_normal(12)),
        ("smooth_monotone", np.linspace(300.0, 900.0, 25), np.log(np.linspace(300.0, 900.0, 25)) ** 2),
        ("edge_overshoot", [0.0, 0.1, 1.0, 1.05], [0.0, 1.0, 1.1, 5.0]),
        ("sign_change_edges", [0.0, 1.0, 1.5, 4.0], [2.0, 1.0, 3.0, -1.0]),
        ("negative_x", [-5.0, -2.0, -1.5, 0.0, 3.5], [10.0, 4.0, 4.5, -2.0, -2.5]),
        ("large_values", [1e3, 2e3, 5e3, 1e4], [1e8, 3e8, 2e9, 2.1e9]),
    ]
    cases = []
    for name, x, y in data:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        pc = PchipInterpolator(x, y)
        span = x[-1] - x[0]
        xs = np.concatenate([np.linspace(x[0] - 0.25 * span, x[-1] + 0.25 * span, 101), x,
                             (x[:-1] + x[1:]) / 2])
        cases.append({"name": name, "x": x, "y": y, "derivatives": pc.derivative()(x), "x_eval": xs,
                      "y_eval": pc(xs)})
    write_table("pchip", {
        "description": "scipy.interpolate.PchipInterpolator(x, y) (extrapolate=True) evaluated at x_eval; derivatives "
                       "at the knots from PchipInterpolator.derivative()",
        "comparison": {"rule": "bitwise", "derivative_rule": "tolerance", "derivative_rel": 1e-12,
                       "why": "exact port of _find_derivatives, _edge_case, CubicHermiteSpline coefficients and PPoly "
                              "evaluation (power sum in SciPy's order), so y_eval is compared bit for bit. The knot "
                              "derivatives are compared as |d_rust - d_scipy| <= 1e-12 * max|d_scipy| because SciPy "
                              "re-evaluates them through the derivative polynomial (rounding at the right end of "
                              "each interval)"},
        "cases": cases,
    }, manifest)
    return len(cases)


def bilinear_browser(xs, ys, g, x, y, clamp):
    """Formula of frontend/src/sim/pfr.ts viscosity() (clamp=False) and process.ts locate() (clamp=True)."""

    def locate(v, q):
        n = len(v)
        i = 0
        while i < n - 2 and q > v[i + 1]:
            i += 1
        qc = q
        if clamp:
            qc = v[0] if q < v[0] else (v[n - 1] if q > v[n - 1] else q)
        return i, (qc - v[i]) / (v[i + 1] - v[i])

    i, ti = locate(xs, x)
    j, tj = locate(ys, y)
    return (1 - ti) * ((1 - tj) * g[i][j] + tj * g[i][j + 1]) + ti * ((1 - tj) * g[i + 1][j] + tj * g[i + 1][j + 1])


def gen_interp(manifest):
    rng = np.random.default_rng(4)
    lin = []
    sets = [
        ("random", np.cumsum(rng.random(30) + 0.01), rng.standard_normal(30) * 1e3),
        ("duplicates", np.array([0.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 4.0]), np.array([0.0, 1.0, 5.0, 2.0, 7.0, 8.0, 9.0, 1.0])),
        ("single", np.array([2.0]), np.array([7.5])),
        ("equal_values", np.array([0.0, 1.0, 2.0]), np.array([4.0, 4.0, 4.0])),
    ]
    for name, xp, fp in sets:
        lo, hi = xp[0] - 1.0, xp[-1] + 1.0
        xs = np.concatenate([rng.uniform(lo, hi, 200), xp, [np.nan, lo, hi]])
        lin.append({"name": name, "xp": xp, "fp": fp, "x": xs, "y": np.interp(xs, xp, fp)})
    bil = []
    tk = [600.0, 650.0, 700.0, 775.0, 850.0, 1000.0]
    xx = [0.0, 0.25, 0.5, 0.75, 1.0]
    g = [[1e-5 * (1.0 + 0.002 * (t - 600.0)) * (1.0 + 0.3 * x * x) for x in xx] for t in tk]
    pts = [(float(a), float(b)) for a, b in zip(rng.uniform(550.0, 1050.0, 150), rng.uniform(-0.2, 1.2, 150))]
    pts += [(t, x) for t in tk for x in xx]
    for clamp in (False, True):
        bil.append({"name": "clamp" if clamp else "extrapolate", "clamp": clamp, "xs": tk, "ys": xx, "z": g,
                    "points": pts, "values": [bilinear_browser(tk, xx, g, a, b, clamp) for a, b in pts]})
    write_table("interp", {
        "description": "linear: numpy.interp(x, xp, fp) (left = fp[0], right = fp[-1]). bilinear: the formula of the "
                       "browser model (frontend/src/sim/pfr.ts viscosity, clamp=false; frontend/src/sim/process.ts "
                       "locate, clamp=true), evaluated in Python with the same IEEE operations",
        "comparison": {"rule": "bitwise", "why": "same operations in the same order (numpy compiled_interp; TS expression)"},
        "linear": lin,
        "bilinear": bil,
    }, manifest)
    return len(lin) + len(bil)


# --------------------------------------------------------------------------- cubic roots

def gen_cubic(manifest):
    rng = np.random.default_rng(11)
    polys = []
    # (a) three distinct real roots
    for roots in ([1.0, 2.0, 3.0], [-4.0, 0.5, 9.0], [0.001, 1.0, 1000.0], [-1e-3, 2e-3, 0.7],
                  [0.05, 0.3, 0.95], [-2.5, -1.0, -0.2]):
        r1, r2, r3 = roots
        polys.append(("roots_" + "_".join(repr(v) for v in roots),
                      -(r1 + r2 + r3), r1 * r2 + r1 * r3 + r2 * r3, -(r1 * r2 * r3)))
    for k in range(8):
        r = np.sort(rng.uniform(-10.0, 10.0, 3))
        polys.append((f"random_three_{k}", -(r[0] + r[1] + r[2]), r[0] * r[1] + r[0] * r[2] + r[1] * r[2],
                      -(r[0] * r[1] * r[2])))
    # (b) one real root and a complex pair
    for k in range(6):
        re_, im_, rr = rng.uniform(-3, 3), rng.uniform(0.5, 3), rng.uniform(-5, 5)
        s = re_ * re_ + im_ * im_
        polys.append((f"complex_pair_{k}", -(2 * re_ + rr), s + 2 * re_ * rr, -(s * rr)))
    polys.append(("z3_minus_1", 0.0, 0.0, -1.0))
    polys.append(("depressed", 0.0, -3.0, 1.0))
    # (c) Peng-Robinson compressibility cubics Z^3 - (1-B) Z^2 + (A - 3B^2 - 2B) Z - (AB - B^2 - B^3)
    for A, B in ((0.01, 0.002), (0.05, 0.01), (0.2, 0.03), (0.3, 0.02), (0.45, 0.04), (1.2, 0.08),
                 (0.08, 0.005), (2.0, 0.15)):
        polys.append((f"pr_A{A}_B{B}", -(1.0 - B), A - 3 * B ** 2 - 2 * B, -(A * B - B ** 2 - B ** 3)))
    cases = []
    for name, a2, a1, a0 in polys:
        r = np.roots([1.0, a2, a1, a0])
        im = np.abs(r.imag)
        real = np.sort(r[im < 1e-10].real)
        cplx = r[im >= 1e-10]
        # keep only unambiguous cases: complex parts well away from zero, real roots well separated
        assert np.all(np.abs(cplx.imag) > 1e-6), name
        if len(real) > 1:
            assert np.min(np.diff(real)) > 1e-6, name
        cases.append({"name": name, "a2": float(a2), "a1": float(a1), "a0": float(a0), "real_roots": real,
                      "complex_roots": [[float(z.real), float(z.imag)] for z in cplx]})
    write_table("cubic_roots", {
        "description": "real roots of the monic cubic z^3 + a2 z^2 + a1 z + a0 from numpy.roots (companion-matrix "
                       "eigenvalues), classified as real when |imag| < 1e-10 (the rule of peng_robinson._z_root)",
        "comparison": {"rule": "tolerance", "rel": 1e-10,
                       "why": "Rust uses the analytic (trigonometric / Cardano) solution with Newton polishing, NumPy "
                              "uses eigenvalues; both are backward stable, so for these well-separated roots they agree "
                              "far below 1e-10 * max(1, |z|). The number of real roots must be identical"},
        "cases": cases,
    }, manifest)
    return len(cases)


# --------------------------------------------------------------------------- statistics

def gen_stats(manifest):
    rng = np.random.default_rng(1)
    qs = [0.0, 0.01, 0.05, 0.1, 0.25, 1.0 / 3.0, 0.5, 0.75, 0.9, 0.95, 0.975, 0.99, 1.0]
    cases = []
    for n in (1, 2, 3, 7, 8, 9, 16, 100, 127, 128, 129, 1000, 4097, 10000):
        x = rng.standard_normal(n) * 10.0 + 3.0
        cases.append({"name": f"normal_{n}", "x": x})
    cases.append({"name": "ties", "x": np.array([3.0, 1.0, 2.0, 2.0, 2.0, 5.0, 1.0, 4.0, 4.0, 0.5])})
    cases.append({"name": "lognormal_2048", "x": rng.lognormal(0.0, 1.5, 2048)})
    cases.append({"name": "large_offset_300", "x": 1e9 + rng.random(300)})
    for c in cases:
        x = c["x"]
        c["mean"] = np.mean(x)
        c["sum"] = np.sum(x)
        c["var0"] = np.var(x)
        c["var1"] = np.var(x, ddof=1) if len(x) > 1 else float("nan")
        c["std1"] = np.std(x, ddof=1) if len(x) > 1 else float("nan")
        c["median"] = np.median(x)
        c["q"] = qs
        c["quantiles"] = np.quantile(x, qs)
    write_table("stats", {
        "description": "numpy.sum, mean, var(ddof=0, 1), std(ddof=1), median and quantile(method='linear') of "
                       "float64 vectors",
        "comparison": {"rule": "bitwise",
                       "why": "port of NumPy's pairwise summation (blocks of 128, 8 accumulators), the two-pass "
                              "variance and the 'linear' quantile with NumPy's _lerp branch at gamma >= 0.5"},
        "cases": cases,
    }, manifest)
    return len(cases)


# --------------------------------------------------------------------------- PCG64 / SeedSequence

def u32_words(n: int):
    if n == 0:
        return [0]
    out = []
    while n > 0:
        out.append(n & 0xFFFFFFFF)
        n >>= 32
    return out


def gen_rng(manifest):
    seeds = [0, 1, 42, 12345, 20261123, 2 ** 32, 2 ** 64 + 7, 2 ** 128 - 1, 2 ** 200 + 5]
    streams = []
    for s in seeds:
        g = np.random.default_rng(s)
        ss = np.random.SeedSequence(s)
        raw = np.random.PCG64(s)
        streams.append({
            "seed_decimal": str(s), "entropy_words": u32_words(s),
            "pool": ss.pool, "state_u32_8": ss.generate_state(8), "state_u64_4": ss.generate_state(4, np.uint64),
            "next_u64_16": [int(v) for v in raw.random_raw(16)],
            "random_1000": g.random(1000),
            "uniform_2_7.5_100": g.uniform(2.0, 7.5, 100),
        })
    spawns = []
    for s in (20261123, 7):
        root = np.random.SeedSequence(s)
        kids = root.spawn(3)
        more = root.spawn(2)
        entry = {"seed_decimal": str(s), "entropy_words": u32_words(s), "children": []}
        for k in kids + more:
            grand = k.spawn(2)
            entry["children"].append({
                "spawn_key": list(k.spawn_key), "pool": k.pool,
                "random_100": np.random.default_rng(k).random(100),
                "grandchildren": [{"spawn_key": list(gk.spawn_key), "random_50": np.random.default_rng(gk).random(50)}
                                  for gk in grand]})
        spawns.append(entry)
    long_streams = []
    for s in (0, 12345, 20261123):
        v = np.random.default_rng(s).random(1_000_000)
        long_streams.append({"seed_decimal": str(s), "entropy_words": u32_words(s), "n": 1_000_000,
                             "sha256_le_f64": hashlib.sha256(v.astype("<f8").tobytes()).hexdigest(),
                             "last": float(v[-1])})
    shuffles = []
    for s in (3, 20261123):
        for n in (1, 2, 5, 17, 100):
            a = np.arange(n)
            np.random.default_rng(s).shuffle(a)
            shuffles.append({"seed_decimal": str(s), "entropy_words": u32_words(s), "n": n, "result": a})
    write_table("pcg64", {
        "description": "numpy.random.SeedSequence (pool, generate_state, spawn), PCG64.random_raw, "
                       "default_rng(seed).random(n), .uniform(low, high, n), and Generator.shuffle(arange(n))",
        "comparison": {"rule": "bitwise",
                       "why": "PCG64 (XSL-RR 128/64) and SeedSequence are integer algorithms ported exactly; random() "
                              "is (next_u64 >> 11) * 2^-53 and uniform is low + (high - low) * random(). Shuffle "
                              "(Fisher-Yates with random_interval) matches for this NumPy version but is NOT promised "
                              "bit-identical across NumPy versions; normal draws are not implemented bit-identically"},
        "streams": streams,
        "spawn": spawns,
        "long_streams": long_streams,
        "shuffles": shuffles,
    }, manifest)
    return len(streams) + len(spawns) + len(long_streams) + len(shuffles)


# --------------------------------------------------------------------------- Sobol and LHS

def gen_sobol(manifest):
    unscr = []
    for d, m in ((1, 10), (2, 10), (3, 8), (8, 8), (21, 9), (40, 7), (100, 6), (SOBOL_EXPORT_DIMS, 3)):
        pts = qmc.Sobol(d, scramble=False).random_base2(m)
        unscr.append({"d": d, "m": m, "points": pts})
    scr = []
    for d, m, seed in ((1, 6, 5), (2, 6, 1), (6, 8, 20261123), (21, 7, 7), (34, 6, 123)):
        pts = qmc.Sobol(d, scramble=True, rng=seed).random_base2(m)
        scr.append({"d": d, "m": m, "seed_decimal": str(seed), "entropy_words": u32_words(seed), "points": pts})
    cont = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for scramble, seed in ((False, None), (True, 99)):
            eng = qmc.Sobol(5, scramble=scramble, rng=seed)
            first = eng.random(3)
            second = eng.random(11)
            third = eng.random(1)
            cont.append({"d": 5, "scramble": scramble, "seed_decimal": None if seed is None else str(seed),
                         "entropy_words": None if seed is None else u32_words(seed),
                         "draws": [3, 11, 1], "points": [first, second, third]})
    write_table("sobol", {
        "description": "scipy.stats.qmc.Sobol(d, scramble, rng=seed) (bits=30): random_base2(m), and successive "
                       "random(n) calls. With an integer rng SciPy uses Generator(PCG64(SeedSequence(seed).spawn(1)[0]))",
        "comparison": {"rule": "bitwise",
                       "why": "unscrambled: Joe-Kuo direction numbers (SciPy's table) and the Gray-code recurrence are "
                              "integer operations, the scale 2^-30 is exact. Scrambled: SciPy's LMS + digital shift "
                              "with bits from Generator.integers(0, 2, dtype=uint32), ported exactly; this agreement "
                              "holds for the recorded SciPy/NumPy versions and is promised only statistically across "
                              "versions"},
        "unscrambled": unscr,
        "scrambled": scr,
        "continuation": cont,
    }, manifest)
    lhs = []
    for d, n, seed, scramble in ((1, 1, 3, True), (3, 10, 7, True), (5, 64, 20261123, True), (2, 1000, 42, True),
                                 (4, 16, 5, False)):
        pts = qmc.LatinHypercube(d, scramble=scramble, rng=seed).random(n)
        lhs.append({"d": d, "n": n, "seed_decimal": str(seed), "entropy_words": u32_words(seed),
                    "scramble": scramble, "points": pts})
    write_table("lhs", {
        "description": "scipy.stats.qmc.LatinHypercube(d, scramble, rng=seed).random(n) (strength 1, no optimization)",
        "comparison": {"rule": "bitwise",
                       "why": "(perm - u)/n with u from Generator.uniform and perm from Generator.shuffle, ported "
                              "exactly for the recorded NumPy version; promised only statistically (stratification) "
                              "across NumPy versions, because shuffling is not a stable NumPy stream"},
        "cases": lhs,
    }, manifest)
    return len(unscr) + len(scr) + len(cont), len(lhs)


def export_sobol_directions(manifest):
    import scipy.stats as st
    z = np.load(os.path.join(os.path.dirname(st.__file__), "_sobol_direction_numbers.npz"))
    poly = [int(v) for v in z["poly"][:SOBOL_EXPORT_DIMS]]
    vinit = z["vinit"][:SOBOL_EXPORT_DIMS]
    starts = [0]
    flat = []
    for d in range(SOBOL_EXPORT_DIMS):
        m = poly[d].bit_length() - 1
        flat.extend(int(v) for v in vinit[d][:m])
        starts.append(len(flat))

    def rows(vals, per):
        out = []
        for i in range(0, len(vals), per):
            out.append("    " + ", ".join(str(v) for v in vals[i:i + per]) + ",")
        return "\n".join(out)

    text = (
        "// @generated by rust/golden/generate_numerics_golden.py from SciPy "
        f"{scipy.__version__} (scipy/stats/_sobol_direction_numbers.npz).\n"
        "// Do not edit by hand. Joe-Kuo direction numbers (new-joe-kuo-6.21201), first "
        f"{SOBOL_EXPORT_DIMS} dimensions.\n"
        "// Copyright (c) 2008, Frances Y. Kuo and Stephen Joe. All rights reserved. Redistribution and use in\n"
        "// source and binary forms, with or without modification, are permitted provided that the copyright notice,\n"
        "// this list of conditions and the disclaimer below are retained. THIS DATA IS PROVIDED BY THE COPYRIGHT\n"
        "// HOLDERS AND CONTRIBUTORS \"AS IS\" AND ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED.\n"
        "// Source: https://web.maths.unsw.edu.au/~fkuo/sobol/ (BSD-style licence).\n"
        "\n"
        "/// Number of dimensions exported.\n"
        f"pub(crate) const MAX_DIM: usize = {SOBOL_EXPORT_DIMS};\n"
        "\n"
        "/// Primitive polynomial of each dimension (SciPy `poly`), degree = bit length - 1.\n"
        "#[rustfmt::skip]\n"
        f"pub(crate) static POLY: [u32; MAX_DIM] = [\n{rows(poly, 16)}\n];\n"
        "\n"
        "/// Start offset of each dimension's initial direction numbers in `VINIT` (length MAX_DIM + 1).\n"
        "#[rustfmt::skip]\n"
        f"pub(crate) static VINIT_START: [u32; MAX_DIM + 1] = [\n{rows(starts, 16)}\n];\n"
        "\n"
        "/// Initial direction numbers m_1..m_s of each dimension (SciPy `vinit`, first s entries).\n"
        "#[rustfmt::skip]\n"
        f"pub(crate) static VINIT: [u32; {len(flat)}] = [\n{rows(flat, 20)}\n];\n"
    )
    data = text.encode("utf-8")
    SOBOL_RS.write_bytes(data)
    manifest["sobol_directions_rs"] = {"path": "rust/crates/amcrax-numerics/src/sobol_directions.rs",
                                       "sha256": hashlib.sha256(data).hexdigest(), "dims": SOBOL_EXPORT_DIMS}
    print(f"wrote {SOBOL_RS.relative_to(RUST_DIR.parent)} ({len(data)} bytes)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"meta": dict(META, generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
                "policy": "generated once by Python and committed; never regenerated from Rust",
                "files": {}, "case_counts": {}}
    counts = manifest["case_counts"]
    counts["brentq"] = gen_brentq(manifest)
    counts["dopri5"] = gen_dopri5(manifest)
    counts["pchip"] = gen_pchip(manifest)
    counts["interp"] = gen_interp(manifest)
    counts["cubic_roots"] = gen_cubic(manifest)
    counts["stats"] = gen_stats(manifest)
    counts["pcg64"] = gen_rng(manifest)
    counts["sobol"], counts["lhs"] = gen_sobol(manifest)
    export_sobol_directions(manifest)
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    (OUT_DIR / "MANIFEST.json").write_bytes(text.encode("utf-8"))
    print("case counts:", counts)


if __name__ == "__main__":
    main()
