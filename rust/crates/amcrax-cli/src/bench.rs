//! `amcrax bench`: wall-clock timings of the Rust engine for the stage 3 benchmark (the Python
//! side is `rust/bench/bench_python.py`; both run in the same GitHub Actions job so the hardware
//! is identical). Timing: `std::time::Instant`, median of the repetitions stated per item.

use amcrax_engine::economics::reference::EconomicsData;
use amcrax_engine::economics::singapore::{
    Overrides, Scenario, Summary, evaluate, evaluate_prepared, prepare,
};
use amcrax_engine::kinetics::KineticsRegistry;
use amcrax_engine::reactor::{PfrInput, SolverOptions, simulate_pfr};
use amcrax_engine::studies::kinetic::{KpSetup, kinetic_propagation};
use serde_json::{Value, json};
use std::path::Path;
use std::time::Instant;

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(f64::total_cmp);
    let n = v.len();
    if n == 0 {
        f64::NAN
    } else if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

fn time<F: FnMut() -> Result<(), String>>(
    reps: usize,
    mut f: F,
) -> Result<(f64, Vec<f64>), String> {
    let mut v = Vec::with_capacity(reps);
    for _ in 0..reps {
        let t0 = Instant::now();
        f()?;
        v.push(t0.elapsed().as_secs_f64());
    }
    Ok((median(v.clone()), v))
}

/// Peak resident memory of this process, kB (Linux `VmHWM`), if available.
pub fn peak_rss_kb() -> Option<u64> {
    let s = std::fs::read_to_string("/proc/self/status").ok()?;
    s.lines()
        .find(|l| l.starts_with("VmHWM:"))
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|x| x.parse().ok())
}

/// The PFR cases of the benchmark (same as `bench_python.py`).
pub fn pfr_cases() -> Vec<(&'static str, PfrInput)> {
    let mut iso = PfrInput::new("ru_takahashi_microkinetic", 50.0);
    iso.n_tubes = 50;
    let mut adi = iso.clone();
    adi.mode = "adiabatic".into();
    adi.t_in_c = 650.0;
    let mut ext = iso.clone();
    ext.mode = "external".into();
    ext.t_wall_c = Some(700.0);
    ext.u_w_m2k = Some(100.0);
    vec![("isothermal", iso), ("adiabatic", adi), ("external", ext)]
}

/// Run the Rust benchmark items.
pub fn run(
    root: &Path,
    items: &[String],
    kinetic_draws: usize,
    threads: &[usize],
) -> Result<Value, String> {
    let s = |e: amcrax_engine::EngineError| e.to_string();
    let d = EconomicsData::embedded();
    let base: Value = serde_json::from_slice(
        &std::fs::read(root.join("results/simulations/baseline.json"))
            .map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    let sm = Summary::extract(&base).map_err(s)?;
    let mut out = serde_json::Map::new();
    let want = |k: &str| items.is_empty() || items.iter().any(|x| x == k);
    if want("economics") {
        let o = Overrides::new();
        let sc = Scenario::Named("grey".into());
        let (one, _) = time(2001, || evaluate(d, &sm, &sc, &o).map(|_| ()).map_err(s))?;
        let n = 100_000usize;
        let (batch, reps) = time(3, || {
            let mut acc = 0.0;
            for i in 0..n {
                let price = 300.0 + i as f64 * 0.005;
                let v = evaluate(d, &sm, &Scenario::Price(price), &o).map_err(s)?;
                acc += v["lcoh_USD_per_kg"].as_f64().unwrap_or(0.0);
            }
            std::hint::black_box(acc);
            Ok(())
        })?;
        let (batch_typed, _) = time(3, || {
            let mut acc = 0.0;
            for i in 0..n {
                let price = 300.0 + i as f64 * 0.005;
                let p = prepare(d, &Scenario::Price(price), &o).map_err(s)?;
                acc += evaluate_prepared(d, &sm, &p.a, &p.p, false)
                    .map_err(s)?
                    .lcoh_usd_per_kg;
            }
            std::hint::black_box(acc);
            Ok(())
        })?;
        out.insert(
            "economics".into(),
            json!({"one_evaluate_s": one, "one_evaluate_reps": 2001, "batch_n": n,
                   "batch_evaluate_dict_s": batch, "batch_reps": reps.len(),
                   "batch_evaluate_typed_s": batch_typed,
                   "note": "evaluate() builds the full Python-shaped dict; the typed path is what the studies use"}),
        );
    }
    if want("pfr") {
        let reg = KineticsRegistry::embedded();
        let so = SolverOptions::default();
        let mut m = serde_json::Map::new();
        for (name, c) in pfr_cases() {
            let (t, _) = time(21, || simulate_pfr(reg, &c, &so).map(|_| ()).map_err(s))?;
            m.insert(format!("one_{name}_s"), json!(t));
        }
        let n = 200usize;
        let (t, _) = time(3, || {
            for i in 0..n {
                let mut c = PfrInput::new("ru_takahashi_microkinetic", 50.0);
                c.n_tubes = 50;
                c.t_in_c = 500.0 + i as f64;
                simulate_pfr(reg, &c, &so).map_err(s)?;
            }
            Ok(())
        })?;
        m.insert("batch_n".into(), json!(n));
        m.insert("batch_isothermal_s".into(), json!(t));
        out.insert("pfr".into(), Value::Object(m));
    }
    if want("gsa") {
        let (t, _) = time(1, || crate::run_gsa(root).map(|_| ()))?;
        out.insert("gsa".into(), json!({"full_study_s": t, "reps": 1}));
    }
    if want("catalyst") {
        // one LCOH(T) curve of the catalyst comparison (59 temperatures: PFR mass search, kinetic
        // flowsheet, heat accounting, economics), fluid properties from the tables back end
        let g = amcrax_engine::verify::Golden::open(&root.join("rust/golden/stage5")).map_err(s)?;
        let b = amcrax_engine::verify::stage4::tables_backend(&g).map_err(s)?;
        let ctx = amcrax_engine::catalyst::Ctx {
            reg: KineticsRegistry::embedded(),
            sopt: SolverOptions::default(),
            econ: d,
            props: &b,
        };
        let grid: Vec<f64> = (0..59).map(|i| 470.0 + 5.0 * i as f64).collect();
        let (t, _) = time(1, || {
            amcrax_engine::catalyst::lcoh_curve(
                &ctx,
                "ru_kum_temkin_pyzhev",
                &grid,
                &amcrax_engine::catalyst::CurveOpts::default(),
            )
            .map(|_| ())
            .map_err(s)
        })?;
        out.insert(
            "catalyst".into(),
            json!({"lcoh_curve_59T_s": t, "reps": 1, "property_backend": "tables"}),
        );
    }
    if want("mcmc") {
        // four adaptive-Metropolis chains of 20,000 iterations on the bicubic surrogate of the
        // first calibration grid (the main Ni posterior)
        let g = amcrax_engine::verify::Golden::open(&root.join("rust/golden/stage5")).map_err(s)?;
        let t5 = g.load("mcmc.json").map_err(s)?;
        let c = &t5["calibration"];
        let v = |x: &Value| -> Vec<f64> {
            x.as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_f64)
                .collect()
        };
        let lns = v(&c["LNS_GRID"]);
        let de = v(&c["DE_GRID"]);
        let grid: Vec<Vec<Vec<f64>>> = c["grids"][0]
            .as_array()
            .into_iter()
            .flatten()
            .map(|r| r.as_array().into_iter().flatten().map(v).collect())
            .collect();
        let run = c["runs"]
            .as_array()
            .and_then(|r| r.iter().find(|x| x["grid"] == 0 && x["n_iter"] == 20000))
            .ok_or("no 20,000-iteration run on grid 0")?;
        let sur = amcrax_engine::calibration::Surrogate::new(&lns, &de, &grid).map_err(s)?;
        let post = amcrax_engine::calibration::Posterior {
            sur: &sur,
            idx: run["idx"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_u64)
                .map(|x| x as usize)
                .collect(),
            y: v(&run["y"]),
            de_sd: 20.0,
            lns_grid: (lns[0], lns[lns.len() - 1]),
            de_grid: (de[0], de[de.len() - 1]),
        };
        let (t, _) = time(1, || {
            let mut rng = amcrax_engine::calibration::Generator::new(20261123);
            let _ = amcrax_engine::calibration::run_chains(&post, &mut rng, 20000, 20.0);
            Ok(())
        })?;
        out.insert("mcmc".into(), json!({"run_chains_4x20000_s": t, "reps": 1}));
    }
    if want("catalyst_economics") {
        // cost-optimal designs (5 K grid refined on 1 K, exchanger mode, central prices, 2 yr) of
        // the five catalysts with fresh caches, fluid properties from the tables back end
        let g = amcrax_engine::verify::Golden::open(&root.join("rust/golden/stage5")).map_err(s)?;
        let b = amcrax_engine::verify::stage4::tables_backend(&g).map_err(s)?;
        let ctx = amcrax_engine::catalyst::Ctx {
            reg: KineticsRegistry::embedded(),
            sopt: SolverOptions::default(),
            econ: d,
            props: &b,
        };
        let (t, _) = time(1, || {
            let e = amcrax_engine::catalyst_econ::Econ::new(&ctx, root).map_err(s)?;
            let kw = amcrax_engine::catalyst_econ::DesignKw::default();
            for c in amcrax_engine::catalyst::catalysts().map_err(s)? {
                let p = e.price(c.price_key, "central").map_err(s)?;
                e.optimise(c.id, p, 2.0, true, None, &kw).map_err(s)?;
            }
            Ok(())
        })?;
        out.insert(
            "catalyst_economics".into(),
            json!({"optimise_5_catalysts_s": t, "reps": 1, "property_backend": "tables"}),
        );
    }
    if want("objective") {
        // the optimisation objective on a flowsheet result: evaluate_result (LCOH, carbon
        // intensity, compression) and the constraint values, stored baseline result, ammonia heat,
        // grey route (the flowsheet solve itself is not included)
        let raw = std::fs::read_to_string(root.join("results/simulations/baseline.json"))
            .map_err(|e| e.to_string())?;
        let ov: amcrax_engine::odata::OValue =
            serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        let res = amcrax_engine::process::SimulationResult::from_ov(&ov).map_err(s)?;
        let sp = amcrax_engine::separation::SepParams::embedded();
        let o = amcrax_engine::optim::EvalOpts::default();
        let (t, _) = time(2001, || {
            let m = amcrax_engine::optim::evaluate_result(d, sp, &res, &o).map_err(s)?;
            let g = amcrax_engine::optim::constraint_values(sp, &m).map_err(s)?;
            std::hint::black_box(g);
            Ok(())
        })?;
        out.insert(
            "objective".into(),
            json!({"evaluate_result_and_constraints_s": t, "reps": 2001}),
        );
    }
    if want("kinetic") {
        let reg = KineticsRegistry::embedded();
        let ky = amcrax_engine::odata::OValue::from_yaml(
            "kinetics.yaml",
            amcrax_engine::kinetics::EMBEDDED_YAML,
        )
        .map_err(s)?;
        let st = KpSetup::new(reg, &ky).map_err(s)?;
        let mut m = serde_json::Map::new();
        let mut first: Option<Vec<f64>> = None;
        for &th in threads {
            let t0 = Instant::now();
            let r = kinetic_propagation(&st, 4000, Some(kinetic_draws), th).map_err(s)?;
            let secs = t0.elapsed().as_secs_f64();
            let n_pfr: usize = r
                .iter()
                .flat_map(|c| c.1.iter().filter(|x| x.0 != "C3"))
                .flat_map(|c| c.2.iter())
                .map(|o| o.n_pfr)
                .sum();
            // determinism across thread counts
            let fp: Vec<f64> = r
                .iter()
                .flat_map(|c| c.1.iter())
                .flat_map(|c| c.2.iter())
                .flat_map(|o| o.x_lab)
                .collect();
            let same = match &first {
                None => {
                    first = Some(fp);
                    true
                }
                Some(f) => *f == fp,
            };
            m.insert(
                format!("threads_{th}"),
                json!({"seconds": secs, "pfr_solves": n_pfr, "identical_to_first_thread_count": same}),
            );
        }
        m.insert(
            "slice".into(),
            json!(format!("first {kinetic_draws} draws of C1 and C2 of both catalysts (4 x {kinetic_draws} draws)")),
        );
        out.insert("kinetic_slice".into(), Value::Object(m));
    }
    out.insert("peak_rss_kB".into(), json!(peak_rss_kb()));
    Ok(Value::Object(out))
}
