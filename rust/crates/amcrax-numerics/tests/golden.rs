//! Golden-table tests: every routine of amcrax-numerics against the reference tables generated
//! once by `rust/golden/generate_numerics_golden.py` (NumPy / SciPy). Each table states its
//! comparison rule; the rule is applied here. The SHA-256 of every table is checked first.

use amcrax_numerics::interp::{Bilinear, OutOfRange, Pchip, interp_linear};
use amcrax_numerics::ode::{Event, OdeOptions, OdeSolution, OdeStatus, dopri5};
use amcrax_numerics::poly::cubic_real_roots;
use amcrax_numerics::qmc::{Sobol, latin_hypercube};
use amcrax_numerics::random::{Pcg64, SeedSequence};
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq};
use amcrax_numerics::stats;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::cell::RefCell;
use std::path::PathBuf;

fn golden_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../golden/numerics")
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn manifest() -> Value {
    let text = std::fs::read_to_string(golden_dir().join("MANIFEST.json")).expect("MANIFEST.json");
    serde_json::from_str(&text).expect("MANIFEST.json parses")
}

/// Load a table after checking its SHA-256 against the manifest.
fn load(name: &str) -> Value {
    let file = format!("{name}.json");
    let bytes = std::fs::read(golden_dir().join(&file)).unwrap_or_else(|e| panic!("{file}: {e}"));
    let want = manifest()["files"][&file]["sha256"]
        .as_str()
        .unwrap_or_else(|| panic!("{file} missing from MANIFEST.json"))
        .to_string();
    assert_eq!(
        hex(&Sha256::digest(&bytes)),
        want,
        "{file}: SHA-256 differs from MANIFEST.json"
    );
    serde_json::from_slice(&bytes).unwrap_or_else(|e| panic!("{file}: {e}"))
}

fn f(v: &Value) -> f64 {
    match v {
        Value::Number(n) => n.as_f64().expect("float"),
        Value::String(s) => match s.as_str() {
            "nan" => f64::NAN,
            "inf" => f64::INFINITY,
            "-inf" => f64::NEG_INFINITY,
            other => panic!("unexpected float string {other}"),
        },
        other => panic!("not a float: {other}"),
    }
}

fn fv(v: &Value) -> Vec<f64> {
    v.as_array().expect("array").iter().map(f).collect()
}

fn fm(v: &Value) -> Vec<Vec<f64>> {
    v.as_array().expect("array").iter().map(fv).collect()
}

fn u64v(v: &Value) -> Vec<u64> {
    v.as_array()
        .expect("array")
        .iter()
        .map(|x| x.as_u64().expect("u64"))
        .collect()
}

fn u32v(v: &Value) -> Vec<u32> {
    u64v(v)
        .into_iter()
        .map(|x| u32::try_from(x).expect("u32"))
        .collect()
}

fn same(a: f64, b: f64) -> bool {
    a.to_bits() == b.to_bits() || (a.is_nan() && b.is_nan())
}

fn assert_bits(got: &[f64], want: &[f64], what: &str) {
    assert_eq!(got.len(), want.len(), "{what}: length");
    for (i, (g, w)) in got.iter().zip(want).enumerate() {
        assert!(
            same(*g, *w),
            "{what}[{i}]: got {g:e} ({:#018x}), want {w:e} ({:#018x})",
            g.to_bits(),
            w.to_bits()
        );
    }
}

fn seed_sequence(entry: &Value) -> SeedSequence {
    SeedSequence::from_words(&u32v(&entry["entropy_words"]), &[])
}

#[test]
fn manifest_hashes_match() {
    let m = manifest();
    let files = m["files"].as_object().expect("files");
    assert!(files.len() >= 9);
    for (name, entry) in files {
        let bytes = std::fs::read(golden_dir().join(name)).expect("table");
        assert_eq!(
            hex(&Sha256::digest(&bytes)),
            entry["sha256"].as_str().unwrap(),
            "{name}"
        );
        assert_eq!(
            bytes.len() as u64,
            entry["bytes"].as_u64().unwrap(),
            "{name}"
        );
    }
    let rs =
        std::fs::read(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/sobol_directions.rs"))
            .expect("sobol_directions.rs");
    assert_eq!(
        hex(&Sha256::digest(rs)),
        m["sobol_directions_rs"]["sha256"].as_str().unwrap(),
        "src/sobol_directions.rs differs from the exported SciPy table"
    );
}

// ------------------------------------------------------------------ brentq

fn brent_arith(name: &str) -> fn(f64) -> f64 {
    match name {
        "cubic" => |x| x * x * x - 2.0 * x - 5.0,
        "sqrt2" => |x| x * x - 2.0,
        "reciprocal" => |x| 1.0 / x - 3.0,
        "quintic_flat" => |x| x * x * x * x * x - 1e-3,
        "three_roots" => |x| (x - 1.1) * (x - 2.3) * (x - 3.7),
        "linear" => |x| 3.0 * x - 1.0,
        "shift_a" => |x| x - 2.0,
        "shift_b" => |x| x - 5.0,
        "no_root" => |x| x * x + 1.0,
        "steep_rational" => |x| (x - 0.7) / (x * x + 1e-4),
        other => panic!("unknown arith function {other}"),
    }
}

#[test]
fn brentq_matches_scipy_bitwise() {
    let t = load("brentq");
    assert_eq!(t["comparison"]["rule"], "bitwise");
    let cases = t["cases"].as_array().unwrap();
    for (ci, c) in cases.iter().enumerate() {
        let name = c["function"].as_str().unwrap();
        let what = format!("case {ci} ({name})");
        let trace: Vec<(f64, f64)> = c["trace"]
            .as_array()
            .unwrap()
            .iter()
            .map(|p| (f(&p[0]), f(&p[1])))
            .collect();
        let opts = BrentOptions {
            xtol: f(&c["xtol"]),
            rtol: f(&c["rtol"]),
            maxiter: c["maxiter"].as_u64().unwrap() as u32,
        };
        let calls: RefCell<Vec<(f64, f64)>> = RefCell::new(Vec::new());
        let result = if c["kind"] == "arith" {
            let g = brent_arith(name);
            brentq(
                |x| {
                    let v = g(x);
                    calls.borrow_mut().push((x, v));
                    v
                },
                f(&c["a"]),
                f(&c["b"]),
                opts,
            )
        } else {
            brentq(
                |x| {
                    let k = calls.borrow().len();
                    let (tx, tv) = trace[k];
                    assert!(
                        same(x, tx),
                        "{what}: call {k} asks x = {x:e}, SciPy asked {tx:e}"
                    );
                    calls.borrow_mut().push((x, tv));
                    tv
                },
                f(&c["a"]),
                f(&c["b"]),
                opts,
            )
        };
        let calls = calls.into_inner();
        assert_eq!(calls.len(), trace.len(), "{what}: number of calls");
        for (k, ((x, v), (tx, tv))) in calls.iter().zip(&trace).enumerate() {
            assert!(same(*x, *tx) && same(*v, *tv), "{what}: call {k} differs");
        }
        match (&c["error"], result) {
            (Value::String(e), Err(BrentError::SignError { .. })) if e == "sign" => {}
            (Value::Null, Ok(r)) | (Value::Null, Err(BrentError::NotConverged(r))) => {
                assert!(
                    same(r.x, f(&c["root"])),
                    "{what}: root {} vs {}",
                    r.x,
                    f(&c["root"])
                );
                assert_eq!(
                    r.function_calls as u64,
                    c["function_calls"].as_u64().unwrap(),
                    "{what}: calls"
                );
                assert_eq!(
                    r.converged,
                    c["converged"].as_bool().unwrap(),
                    "{what}: converged"
                );
                // SciPy leaves `iterations` uninitialised when an endpoint is an exact root
                let endpoint_root = trace.len() == 2 && (trace[0].1 == 0.0 || trace[1].1 == 0.0);
                if !endpoint_root {
                    assert_eq!(
                        r.iterations as u64,
                        c["iterations"].as_u64().unwrap(),
                        "{what}: iterations"
                    );
                }
            }
            (e, r) => panic!("{what}: SciPy error {e}, Rust {r:?}"),
        }
    }
    eprintln!("brentq: {} cases bit-identical to SciPy", cases.len());
}

// ------------------------------------------------------------------ DOPRI5

fn make_event<'a, const N: usize>(name: &str) -> Event<'a, N> {
    match name {
        "ground" => Event::new(|_t: f64, y: &[f64; N]| y[0], true, -1.0),
        "cross" => Event::new(|_t: f64, y: &[f64; N]| y[0], false, 0.0),
        "five_percent" => Event::new(|_t: f64, y: &[f64; N]| y[0] - 0.05, true, 0.0),
        // y1 of the two-state oscillator (only used with N = 2)
        "upcross" => Event::new(|_t: f64, y: &[f64; N]| y[N - 1], false, 1.0),
        other => panic!("unknown event {other}"),
    }
}

/// Returns the worst deviation from SciPy in tolerance units.
fn check_ode_case<const N: usize>(
    c: &Value,
    what: &str,
    rhs: fn(f64, &[f64; N], &mut [f64; N]) -> Result<(), String>,
    exact: Option<fn(f64) -> [f64; N]>,
    gate_scipy: f64,
    gate_exact: f64,
) -> f64 {
    let rtol = f(&c["rtol"]);
    let atol = f(&c["atol"]);
    let span = fv(&c["t_span"]);
    let y0v = fv(&c["y0"]);
    let mut y0 = [0.0; N];
    y0.copy_from_slice(&y0v);
    let opts = OdeOptions::<N>::new(rtol, atol);
    let ev_names: Vec<String> = c["events"]
        .as_array()
        .unwrap()
        .iter()
        .map(|e| e["name"].as_str().unwrap().to_string())
        .collect();
    let mut rhs_mut = rhs;

    // run 1: every step (no t_eval): number of steps and RHS evaluations
    let mut ev: Vec<Event<N>> = ev_names.iter().map(|n| make_event::<N>(n)).collect();
    let steps: OdeSolution<N> =
        dopri5(&mut rhs_mut, (span[0], span[1]), y0, None, &mut ev, &opts).unwrap();
    assert_eq!(
        steps.n_steps as u64,
        c["n_steps"].as_u64().unwrap(),
        "{what}: accepted steps"
    );
    assert_eq!(
        steps.nfev as u64,
        c["nfev"].as_u64().unwrap(),
        "{what}: nfev"
    );
    assert_eq!(
        steps.t.len(),
        c["step_t"].as_array().unwrap().len(),
        "{what}: step times"
    );

    // run 2: t_eval
    let t_eval = fv(&c["t_eval"]);
    let mut ev: Vec<Event<N>> = ev_names.iter().map(|n| make_event::<N>(n)).collect();
    let sol = dopri5(
        &mut rhs_mut,
        (span[0], span[1]),
        y0,
        Some(&t_eval),
        &mut ev,
        &opts,
    )
    .unwrap();
    let want_status = c["status"].as_i64().unwrap();
    let status = match sol.status {
        OdeStatus::Finished => 0,
        OdeStatus::TerminalEvent => 1,
    };
    assert_eq!(status, want_status, "{what}: status");
    assert_eq!(
        sol.nfev as u64,
        c["nfev"].as_u64().unwrap(),
        "{what}: nfev with t_eval"
    );
    assert_bits(&sol.t, &fv(&c["t"]), &format!("{what}: t"));
    let ys = fm(&c["y"]);
    let mut worst: f64 = 0.0;
    for (k, (yr, yw)) in sol.y.iter().zip(&ys).enumerate() {
        for i in 0..N {
            let units = (yr[i] - yw[i]).abs() / (atol + rtol * yw[i].abs());
            worst = worst.max(units);
            assert!(
                units <= gate_scipy,
                "{what}: y[{k}][{i}] = {} vs SciPy {} ({units:.3} units)",
                yr[i],
                yw[i]
            );
        }
    }
    // events
    let te_want = c["t_events"].as_array().unwrap();
    let ye_want = c["y_events"].as_array().unwrap();
    assert_eq!(sol.t_events.len(), te_want.len(), "{what}: event lists");
    for (e, (tr, tw)) in sol.t_events.iter().zip(te_want).enumerate() {
        let tw = fv(tw);
        assert_eq!(tr.len(), tw.len(), "{what}: occurrences of event {e}");
        for (a, b) in tr.iter().zip(&tw) {
            let units = (a - b).abs() / (atol + rtol * b.abs());
            worst = worst.max(units);
            assert!(
                units <= gate_scipy,
                "{what}: event {e} at {a} vs SciPy {b} ({units:.3} units)"
            );
        }
        let yw = fm(&ye_want[e]);
        for (yr, yw) in sol.y_events[e].iter().zip(&yw) {
            for i in 0..N {
                let units = (yr[i] - yw[i]).abs() / (atol + rtol * yw[i].abs());
                worst = worst.max(units);
                assert!(
                    units <= gate_scipy,
                    "{what}: event {e} state {i} ({units:.3} units)"
                );
            }
        }
    }
    // analytic solution
    if let Some(ex) = exact {
        let mut ymax = [0.0_f64; N];
        for y in &sol.y {
            for i in 0..N {
                ymax[i] = ymax[i].max(y[i].abs());
            }
        }
        for (t, y) in sol.t.iter().zip(&sol.y) {
            let e = ex(*t);
            for i in 0..N {
                let units = (y[i] - e[i]).abs() / (atol + rtol * ymax[i]);
                assert!(
                    units <= gate_exact,
                    "{what}: analytic error {units:.2} units at t = {t}"
                );
            }
        }
    }
    worst
}

#[test]
fn dopri5_matches_solve_ivp() {
    let t = load("dopri5");
    let gate_scipy = f(&t["comparison"]["scipy_gate_units"]);
    let gate_exact = f(&t["comparison"]["exact_gate_units"]);
    let cases = t["cases"].as_array().unwrap();
    let mut worst: f64 = 0.0;
    for (ci, c) in cases.iter().enumerate() {
        let p = c["problem"].as_str().unwrap();
        let what = format!("case {ci} ({p}, rtol {})", f(&c["rtol"]));
        let w = match p {
            "decay" | "decay_backward" => check_ode_case::<1>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = -y[0];
                    Ok(())
                },
                Some(|t| [(-t).exp()]),
                gate_scipy,
                gate_exact,
            ),
            "exp_sin" => check_ode_case::<1>(
                c,
                &what,
                |t, y, dy| {
                    dy[0] = y[0] * t.cos();
                    Ok(())
                },
                Some(|t| [t.sin().exp()]),
                gate_scipy,
                gate_exact,
            ),
            "oscillator" => check_ode_case::<2>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = y[1];
                    dy[1] = -y[0];
                    Ok(())
                },
                Some(|t| [t.cos(), -t.sin()]),
                gate_scipy,
                gate_exact,
            ),
            "van_der_pol" => check_ode_case::<2>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = y[1];
                    dy[1] = (1.0 - y[0] * y[0]) * y[1] - y[0];
                    Ok(())
                },
                None,
                gate_scipy,
                gate_exact,
            ),
            "lotka_volterra" => check_ode_case::<2>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = 1.5 * y[0] - y[0] * y[1];
                    dy[1] = -3.0 * y[1] + y[0] * y[1];
                    Ok(())
                },
                None,
                gate_scipy,
                gate_exact,
            ),
            "ballistic" => check_ode_case::<2>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = y[1];
                    dy[1] = -9.81;
                    Ok(())
                },
                Some(|t| [10.0 - 0.5 * 9.81 * t * t, -9.81 * t]),
                gate_scipy,
                gate_exact,
            ),
            "sqrt_drop" => check_ode_case::<1>(
                c,
                &what,
                |_t, y, dy| {
                    dy[0] = -0.8 / y[0];
                    Ok(())
                },
                Some(|t| [(1.0 - 1.6 * t).sqrt()]),
                gate_scipy,
                gate_exact,
            ),
            other => panic!("unknown problem {other}"),
        };
        worst = worst.max(w);
    }
    eprintln!(
        "dopri5: {} cases, same nfev and step counts as SciPy, worst deviation {worst:.2e} tolerance units (gate {gate_scipy})",
        cases.len()
    );
}

// ------------------------------------------------------------------ interpolation

#[test]
fn pchip_matches_scipy_bitwise() {
    let t = load("pchip");
    let drel = f(&t["comparison"]["derivative_rel"]);
    let cases = t["cases"].as_array().unwrap();
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let p = Pchip::new(&fv(&c["x"]), &fv(&c["y"])).unwrap();
        assert_bits(&p.eval_many(&fv(&c["x_eval"])), &fv(&c["y_eval"]), name);
        let dw = fv(&c["derivatives"]);
        let scale = dw.iter().fold(0.0_f64, |a, b| a.max(b.abs()));
        for (a, b) in p.derivatives().iter().zip(&dw) {
            assert!(
                (a - b).abs() <= drel * scale,
                "{name}: derivative {a} vs {b}"
            );
        }
    }
    eprintln!("pchip: {} cases bit-identical to SciPy", cases.len());
}

#[test]
fn linear_and_bilinear_match_bitwise() {
    let t = load("interp");
    let lin = t["linear"].as_array().unwrap();
    for c in lin {
        let (xp, fp) = (fv(&c["xp"]), fv(&c["fp"]));
        let got: Vec<f64> = fv(&c["x"])
            .iter()
            .map(|&x| interp_linear(x, &xp, &fp))
            .collect();
        assert_bits(&got, &fv(&c["y"]), c["name"].as_str().unwrap());
    }
    let bil = t["bilinear"].as_array().unwrap();
    for c in bil {
        let mode = if c["clamp"].as_bool().unwrap() {
            OutOfRange::Clamp
        } else {
            OutOfRange::Extrapolate
        };
        let b = Bilinear::new(&fv(&c["xs"]), &fv(&c["ys"]), &fm(&c["z"]), mode).unwrap();
        let got: Vec<f64> = fm(&c["points"])
            .iter()
            .map(|p| b.eval(p[0], p[1]))
            .collect();
        assert_bits(&got, &fv(&c["values"]), c["name"].as_str().unwrap());
    }
    eprintln!(
        "interp: {} linear and {} bilinear cases bit-identical",
        lin.len(),
        bil.len()
    );
}

// ------------------------------------------------------------------ cubic roots

#[test]
fn cubic_roots_match_numpy() {
    let t = load("cubic_roots");
    let rel = f(&t["comparison"]["rel"]);
    let cases = t["cases"].as_array().unwrap();
    let mut worst: f64 = 0.0;
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let r = cubic_real_roots(f(&c["a2"]), f(&c["a1"]), f(&c["a0"]));
        let want = fv(&c["real_roots"]);
        assert_eq!(r.len(), want.len(), "{name}: number of real roots");
        for (a, b) in r.as_slice().iter().zip(&want) {
            let d = (a - b).abs() / b.abs().max(1.0);
            worst = worst.max(d);
            assert!(d <= rel, "{name}: root {a} vs numpy {b}");
        }
    }
    eprintln!(
        "cubic_roots: {} cases, worst relative difference {worst:.2e} (gate {rel})",
        cases.len()
    );
}

// ------------------------------------------------------------------ statistics

#[test]
fn stats_match_numpy_bitwise() {
    let t = load("stats");
    let cases = t["cases"].as_array().unwrap();
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let x = fv(&c["x"]);
        let checks = [
            ("sum", stats::sum(&x)),
            ("mean", stats::mean(&x)),
            ("var0", stats::var(&x, 0)),
            ("var1", stats::var(&x, 1)),
            ("std1", stats::std(&x, 1)),
            ("median", stats::median(&x)),
        ];
        for (key, got) in checks {
            let want = f(&c[key]);
            assert!(same(got, want), "{name} {key}: {got:e} vs numpy {want:e}");
        }
        assert_bits(
            &stats::quantiles(&x, &fv(&c["q"])),
            &fv(&c["quantiles"]),
            &format!("{name} quantiles"),
        );
    }
    eprintln!("stats: {} cases bit-identical to NumPy", cases.len());
}

// ------------------------------------------------------------------ PCG64 and SeedSequence

#[test]
fn pcg64_streams_match_numpy_bitwise() {
    let t = load("pcg64");
    let streams = t["streams"].as_array().unwrap();
    for s in streams {
        let seed = s["seed_decimal"].as_str().unwrap();
        let ss = seed_sequence(s);
        assert_eq!(ss.pool().to_vec(), u32v(&s["pool"]), "seed {seed}: pool");
        assert_eq!(
            ss.generate_state_u32(8),
            u32v(&s["state_u32_8"]),
            "seed {seed}: generate_state u32"
        );
        assert_eq!(
            ss.generate_state_u64(4),
            u64v(&s["state_u64_4"]),
            "seed {seed}: generate_state u64"
        );
        let mut raw = Pcg64::from_seed_sequence(&ss);
        let got: Vec<u64> = (0..16).map(|_| raw.next_u64()).collect();
        assert_eq!(got, u64v(&s["next_u64_16"]), "seed {seed}: random_raw");
        let mut g = Pcg64::from_seed_sequence(&ss);
        assert_bits(
            &g.random_vec(1000),
            &fv(&s["random_1000"]),
            &format!("seed {seed}: random"),
        );
        let u: Vec<f64> = (0..100).map(|_| g.uniform(2.0, 7.5)).collect();
        assert_bits(
            &u,
            &fv(&s["uniform_2_7.5_100"]),
            &format!("seed {seed}: uniform"),
        );
    }
    let spawns = t["spawn"].as_array().unwrap();
    for s in spawns {
        let mut root = seed_sequence(s);
        let mut kids = root.spawn(3);
        kids.extend(root.spawn(2));
        let want = s["children"].as_array().unwrap();
        assert_eq!(kids.len(), want.len());
        for (k, w) in kids.iter_mut().zip(want) {
            assert_eq!(k.spawn_key().to_vec(), u64v(&w["spawn_key"]), "spawn key");
            assert_eq!(k.pool().to_vec(), u32v(&w["pool"]), "child pool");
            let mut g = Pcg64::from_seed_sequence(k);
            assert_bits(&g.random_vec(100), &fv(&w["random_100"]), "child stream");
            for (gk, gw) in k
                .spawn(2)
                .iter()
                .zip(w["grandchildren"].as_array().unwrap())
            {
                assert_eq!(
                    gk.spawn_key().to_vec(),
                    u64v(&gw["spawn_key"]),
                    "grandchild key"
                );
                let mut g = Pcg64::from_seed_sequence(gk);
                assert_bits(
                    &g.random_vec(50),
                    &fv(&gw["random_50"]),
                    "grandchild stream",
                );
            }
        }
    }
    let longs = t["long_streams"].as_array().unwrap();
    for s in longs {
        let n = s["n"].as_u64().unwrap() as usize;
        let mut g = Pcg64::from_seed_sequence(&seed_sequence(s));
        let mut h = Sha256::new();
        let mut last = 0.0;
        for _ in 0..n {
            last = g.random();
            h.update(last.to_le_bytes());
        }
        assert_eq!(
            hex(&h.finalize()),
            s["sha256_le_f64"].as_str().unwrap(),
            "1e6-draw stream digest"
        );
        assert!(same(last, f(&s["last"])));
    }
    let shuffles = t["shuffles"].as_array().unwrap();
    for s in shuffles {
        let n = s["n"].as_u64().unwrap();
        let mut g = Pcg64::from_seed_sequence(&seed_sequence(s));
        let mut a: Vec<u64> = (0..n).collect();
        g.shuffle(&mut a);
        assert_eq!(a, u64v(&s["result"]), "shuffle n = {n}");
    }
    eprintln!(
        "pcg64: {} streams, {} spawn trees, {} streams of 1e6 draws, {} shuffles bit-identical to NumPy",
        streams.len(),
        spawns.len(),
        longs.len(),
        shuffles.len()
    );
}

// ------------------------------------------------------------------ Sobol and LHS

fn qmc_rng(entry: &Value) -> Pcg64 {
    let mut root = seed_sequence(entry);
    Pcg64::from_seed_sequence(&root.spawn(1)[0])
}

#[test]
fn sobol_matches_scipy_bitwise() {
    let t = load("sobol");
    let un = t["unscrambled"].as_array().unwrap();
    for c in un {
        let d = c["d"].as_u64().unwrap() as usize;
        let m = c["m"].as_u64().unwrap() as u32;
        let pts = Sobol::new(d).unwrap().random_base2(m).unwrap();
        let want = fm(&c["points"]);
        assert_eq!(pts.len(), want.len());
        for (k, (a, b)) in pts.iter().zip(&want).enumerate() {
            assert_bits(a, b, &format!("unscrambled d={d} point {k}"));
        }
    }
    let sc = t["scrambled"].as_array().unwrap();
    for c in sc {
        let d = c["d"].as_u64().unwrap() as usize;
        let m = c["m"].as_u64().unwrap() as u32;
        let mut rng = qmc_rng(c);
        let pts = Sobol::new_scrambled(d, &mut rng)
            .unwrap()
            .random_base2(m)
            .unwrap();
        let want = fm(&c["points"]);
        assert_eq!(pts.len(), want.len());
        for (k, (a, b)) in pts.iter().zip(&want).enumerate() {
            assert_bits(a, b, &format!("scrambled d={d} point {k}"));
        }
    }
    let cont = t["continuation"].as_array().unwrap();
    for c in cont {
        let d = c["d"].as_u64().unwrap() as usize;
        let mut s = if c["scramble"].as_bool().unwrap() {
            Sobol::new_scrambled(d, &mut qmc_rng(c)).unwrap()
        } else {
            Sobol::new(d).unwrap()
        };
        for (n, block) in c["draws"]
            .as_array()
            .unwrap()
            .iter()
            .zip(c["points"].as_array().unwrap())
        {
            let pts = s.random(n.as_u64().unwrap() as usize).unwrap();
            let want = fm(block);
            assert_eq!(pts.len(), want.len());
            for (a, b) in pts.iter().zip(&want) {
                assert_bits(a, b, "continuation");
            }
        }
    }
    eprintln!(
        "sobol: {} unscrambled (d up to {}), {} scrambled, {} continuation cases bit-identical to SciPy",
        un.len(),
        Sobol::MAX_DIM,
        sc.len(),
        cont.len()
    );
}

#[test]
fn lhs_matches_scipy_bitwise() {
    let t = load("lhs");
    let cases = t["cases"].as_array().unwrap();
    for c in cases {
        let d = c["d"].as_u64().unwrap() as usize;
        let n = c["n"].as_u64().unwrap() as usize;
        let pts = latin_hypercube(n, d, c["scramble"].as_bool().unwrap(), &mut qmc_rng(c));
        let want = fm(&c["points"]);
        assert_eq!(pts.len(), want.len());
        for (a, b) in pts.iter().zip(&want) {
            assert_bits(a, b, &format!("lhs d={d} n={n}"));
        }
    }
    eprintln!("lhs: {} cases bit-identical to SciPy", cases.len());
}
