//! Stage 5 comparisons against `rust/golden/stage5/` (written by
//! `rust/golden/generate_stage5_golden.py`) and against the stored results in `results/`.
//!
//! Catalyst studies (`catalyst`): catalyst masses 1e-5 relative (the stage 2 gate of
//! `catalyst_mass_for_conversion`, brentq xtol 1e-6 W and rtol 1e-6) and the quantities that
//! scale with the mass (bed volume, catalyst cost and the LCOH and REC that contain it) 1e-5
//! relative; flowsheet, heat and economics quantities at a given mass 1e-9 relative (stage 4
//! duty and KPI gates); heat accounting on stored results 1e-10 relative (stage 4 heat gate);
//! the feasible temperature set and the cost-optimal temperatures identical.

use super::stage4::{
    FsAcc, TreeAcc, compare_result, error_class_matches, key_scale, tree, tree_with,
};
use super::{Acc, Golden, Report, num, py_error};
use crate::catalyst::{self as cc, Ctx, CurveOpts, DesignOpts};
use crate::error::EngineError;
use crate::process::result::SimulationResult;
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;

/// Keys of an LCOH-curve row that scale with the catalyst mass.
const MASS_KEYS: [&str; 6] = [
    "W_kg",
    "bed_volume_m3",
    "catalyst_USD_per_kg",
    "lcoh_USD_per_kg",
    "rec_USD_per_kg",
    "lcoh_SGD_per_kg",
];

fn curve_rows(
    acc_w: &mut Acc,
    acc_f: &mut Acc,
    keys: &mut Acc,
    case: &str,
    py: &[Value],
    rs: &[Value],
) {
    let pt: Vec<f64> = py.iter().map(|r| num(&r["T_C"])).collect();
    let rt: Vec<f64> = rs.iter().map(|r| num(&r["T_C"])).collect();
    keys.add_bool(&format!("{case}/T_set"), pt == rt, || {
        format!("python T {pt:?} rust T {rt:?}")
    });
    if pt != rt {
        return;
    }
    for (p, r) in py.iter().zip(rs.iter()) {
        let c = format!("{case}/T{}", num(&p["T_C"]));
        if let Some(m) = p.as_object() {
            for (k, v) in m {
                if !super::stage4::is_num(v) {
                    continue;
                }
                let rv = num(&r[k]);
                if MASS_KEYS.contains(&k.as_str()) {
                    acc_w.add_scaled(&format!("{c}/{k}"), rv, num(v), key_scale(k));
                } else {
                    acc_f.add_scaled(&format!("{c}/{k}"), rv, num(v), key_scale(k));
                }
            }
        }
    }
}

fn base_opts(hi: bool) -> CurveOpts {
    CurveOpts {
        hi,
        ..CurveOpts::default()
    }
}

fn read_value(root: &Path, rel: &str) -> Result<Value, EngineError> {
    let t = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    serde_json::from_str(&t).map_err(|e| EngineError::data(rel, e.to_string()))
}

fn aspen_result(root: &Path, rel: &str) -> Result<SimulationResult, EngineError> {
    // parsed in file order (the Python dicts iterate in document order)
    let raw = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    let ov: crate::odata::OValue =
        serde_json::from_str(&raw).map_err(|e| EngineError::data(rel, e.to_string()))?;
    let node = if ov.get("aspen").is_null() {
        ov
    } else {
        ov.get("aspen").get("flowsheet_result").clone()
    };
    SimulationResult::from_ov(&node)
}

/// Parse the stored CSV of the design curves (header row, plain comma-separated fields).
fn read_csv(root: &Path, rel: &str) -> Result<Vec<Vec<(String, String)>>, EngineError> {
    let t = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    let mut lines = t.lines();
    let head: Vec<String> = lines
        .next()
        .unwrap_or("")
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    Ok(lines
        .filter(|l| !l.trim().is_empty())
        .map(|l| {
            head.iter()
                .cloned()
                .zip(l.split(',').map(|s| s.trim().to_string()))
                .collect()
        })
        .collect())
}

/// Catalyst comparison: masses, LCOH curves and optima, design points, heat accounting on the
/// stored Aspen results, kinetic flowsheets, and the stored `catalyst_comparison` files.
pub fn catalyst(g: &Golden, ctx: &Ctx, root: &Path) -> Result<Report, EngineError> {
    let t = g.load("catalyst.json")?;
    let mut rep = Report::new(&format!(
        "catalyst studies (properties: {})",
        ctx.props.backend()
    ));
    let mut outcome = Acc::exact(
        "CAT-OUTCOME",
        "catalyst calls: success, or the same exception class",
    );
    // ---- masses
    let mut mw = Acc::rel("CAT-MASS-W", "required_mass_kg (PFR mass search)", 1e-5)
        .note("relative; brentq xtol 1e-6 W, rtol 1e-6 on 2-point PFR runs (stage 2 gate)");
    let mut xeq = Acc::abs(
        "CAT-XEQ",
        "ideal-gas equilibrium conversion of the NH3 feed",
        1e-10,
    );
    for m in t["masses"].as_array().into_iter().flatten() {
        let cid = m["catalyst_id"].as_str().unwrap_or("");
        let (tc, p, x) = (num(&m["T_C"]), num(&m["P_bar"]), num(&m["X"]));
        let case = format!("{cid}/T{tc}/P{p}/X{x}");
        match (
            cc::required_mass_kg(ctx, cid, tc, p, x),
            cc::eq_conversion(tc, p),
        ) {
            (Ok(w), Ok(e)) => {
                outcome.add_bool(&case, true, String::new);
                mw.add(&case, w, num(&m["W_kg"]));
                xeq.add(&case, e, num(&m["X_eq"]));
            }
            (Err(e), _) | (_, Err(e)) => {
                outcome.add_bool(&case, false, || format!("rust failed: {e}"))
            }
        }
    }
    rep.push(mw);
    rep.push(xeq);
    // ---- curves and optima
    let mut cw = Acc::rel(
        "CAT-CURVE-MASS",
        "LCOH curves: mass and the quantities that scale with it",
        1e-5,
    )
    .note("relative (key scales as HI-NUM); W from the PFR mass search (1e-5)");
    let mut cf = Acc::rel(
        "CAT-CURVE-FLOWSHEET",
        "LCOH curves: flowsheet, heat and fuel quantities",
        1e-9,
    )
    .note("relative (key scales as HI-NUM)");
    let mut ck = Acc::exact(
        "CAT-CURVE-TSET",
        "LCOH curves: identical feasible temperature set",
    );
    let mut rust_curves: Vec<(String, bool, Vec<Value>)> = Vec::new();
    let grid: Vec<f64> = t["T_grid"]
        .as_array()
        .into_iter()
        .flatten()
        .map(num)
        .collect();
    for c in t["curves"].as_array().into_iter().flatten() {
        let cid = c["catalyst_id"].as_str().unwrap_or("").to_string();
        let hi = c["heat_integration"].as_bool().unwrap_or(true);
        let case = format!("{cid}/{}", if hi { "HI" } else { "noHI" });
        match cc::lcoh_curve(ctx, &cid, &grid, &base_opts(hi)) {
            Ok(r) => {
                outcome.add_bool(&case, true, String::new);
                curve_rows(
                    &mut cw,
                    &mut cf,
                    &mut ck,
                    &case,
                    c["rows"].as_array().map(Vec::as_slice).unwrap_or(&[]),
                    &r,
                );
                rust_curves.push((cid, hi, r));
            }
            Err(e) => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
        }
    }
    let mut opt_t = Acc::exact(
        "CAT-OPT-T",
        "cost-optimal temperature (5 K grid and 1 K refinement) and grid-bound flag",
    );
    for o in t["optima"].as_array().into_iter().flatten() {
        let cid = o["catalyst_id"].as_str().unwrap_or("");
        let hi = o["heat_integration"].as_bool().unwrap_or(true);
        let case = format!("{cid}/{}", if hi { "HI" } else { "noHI" });
        let Some((_, _, rc)) = rust_curves.iter().find(|x| x.0 == cid && x.1 == hi) else {
            continue;
        };
        let Some(oc) = cc::optimum(rc) else {
            opt_t.add_bool(&case, false, || "rust curve empty".into());
            continue;
        };
        opt_t.add_bool(
            &format!("{case}/coarse"),
            num(&oc["T_C"]) == num(&o["coarse"]["T_C"]),
            || format!("python {} rust {}", o["coarse"]["T_C"], oc["T_C"]),
        );
        let rgrid: Vec<f64> = (-5..=5).map(|k| num(&oc["T_C"]) + k as f64).collect();
        match cc::lcoh_curve(ctx, cid, &rgrid, &base_opts(hi)) {
            Ok(loc) => {
                curve_rows(
                    &mut cw,
                    &mut cf,
                    &mut ck,
                    &format!("{case}/refine"),
                    o["refined_rows"]
                        .as_array()
                        .map(Vec::as_slice)
                        .unwrap_or(&[]),
                    &loc,
                );
                if let Some(ro) = cc::optimum(&loc) {
                    let same = num(&ro["T_C"]) == num(&o["refined"]["T_C"])
                        && ro["at_grid_bound"] == o["refined"]["at_grid_bound"];
                    opt_t.add_bool(&format!("{case}/refined"), same, || {
                        format!("python {} rust {}", o["refined"]["T_C"], ro["T_C"])
                    });
                }
            }
            Err(e) => outcome.add_bool(&format!("{case}/refine"), false, || {
                format!("rust failed: {e}")
            }),
        }
    }
    rep.push(cw);
    rep.push(cf);
    rep.push(ck);
    rep.push(opt_t);
    // ---- design points at the golden mass
    let note = "relative; key scales as HI-NUM; the catalyst mass is the golden input";
    let mut ds = TreeAcc::new(
        "CAT-DESIGN",
        "design_point (flowsheet, heat, fired duty, economics, carbon)",
        1e-9,
        note,
    );
    let mut rust_designs: Vec<(Value, Value)> = Vec::new();
    for d in t["designs"].as_array().into_iter().flatten() {
        let cid = d["catalyst_id"].as_str().unwrap_or("");
        let hi = d["heat_integration"].as_bool().unwrap_or(true);
        let kind = d["kind"].as_str().unwrap_or("");
        let case = format!(
            "{kind}/{cid}/{}/T{}",
            if hi { "HI" } else { "noHI" },
            num(&d["T_C"])
        );
        let o = DesignOpts {
            heat_integration: hi,
            w_kg: Some(num(&d["W_kg"])),
            ..DesignOpts::default()
        };
        let res = match d["result_file"].as_str() {
            Some(f) => Some(aspen_result(root, f)?),
            None => None,
        };
        match cc::design_point(
            ctx,
            cid,
            num(&d["T_C"]),
            num(&d["P_bar"]),
            num(&d["X"]),
            &o,
            res.as_ref(),
        ) {
            Ok(r) => {
                outcome.add_bool(&case, true, String::new);
                tree(&mut ds, &case, "", &d["out"], &r);
                rust_designs.push((d.clone(), r));
            }
            Err(e) => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
        }
    }
    ds.push(&mut rep);
    // ---- heat accounting on stored results
    let mut pa = TreeAcc::new(
        "CAT-PINCH",
        "heat_accounting on the stored Aspen results, dT_min 10-50 K",
        1e-10,
        note,
    );
    for p in t["pinch_dT"].as_array().into_iter().flatten() {
        let f = p["result_file"].as_str().unwrap_or("");
        let case = format!("{f}/dT{}", num(&p["dT_min_K"]));
        let res = aspen_result(root, f)?;
        match cc::heat_accounting(ctx, &res, num(&p["dT_min_K"])) {
            Ok(mut r) => {
                outcome.add_bool(&case, true, String::new);
                // an FEHE approach warning decided on a tie (minimum internal approach equal to
                // dT_min within 1e-9 K, stage 4): adopt Python's warning list and report it
                if p["out"]["warnings"] != r["warnings"] {
                    let strip = |v: &Value| -> Vec<Value> {
                        v.as_array()
                            .into_iter()
                            .flatten()
                            .filter(|w| !w.as_str().is_some_and(|s| s.starts_with("FEHE ")))
                            .cloned()
                            .collect()
                    };
                    let dt = num(&p["dT_min_K"]);
                    let rmin = crate::heat::analyse(ctx.props, &res, dt)
                        .map(|a| num(&a["fehe"]["min_internal_approach_K"]))
                        .unwrap_or(f64::NAN);
                    if strip(&p["out"]["warnings"]) == strip(&r["warnings"])
                        && (rmin - dt).abs() <= 1e-9
                    {
                        rep.findings.push(format!(
                            "{case}: FEHE approach warning decided on a tie (Rust minimum internal approach {rmin:e} K, dT_min {dt} K); Python's warning list adopted"
                        ));
                        r["warnings"] = p["out"]["warnings"].clone();
                    }
                }
                tree(&mut pa, &case, "", &p["out"], &r);
            }
            Err(e) => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
        }
    }
    pa.push(&mut rep);
    // ---- kinetic flowsheets
    let mut fa = FsAcc::new(
        "CAT-FS",
        "kinetic_flowsheet (cracker at the kinetic conversion)",
    );
    for f in t["flowsheets"].as_array().into_iter().flatten() {
        let hi = f["heat_integration"].as_bool().unwrap_or(true);
        let case = format!("kinetic_flowsheet/T{}/{}", num(&f["T_C"]), hi);
        match cc::kinetic_flowsheet(
            ctx,
            num(&f["T_C"]),
            num(&f["P_bar"]),
            num(&f["X"]),
            hi,
            0.85,
        ) {
            Ok(r) => {
                outcome.add_bool(&case, true, String::new);
                compare_result(&mut fa, &case, &f["result"], &r.to_json());
            }
            Err(e) => match py_error(&f["result"]) {
                Some(cls) => {
                    outcome.add_bool(&case, error_class_matches(cls, &e), || format!("{e}"))
                }
                None => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
            },
        }
    }
    fa.push(&mut rep);
    rep.push(outcome);
    // ---- stored results
    let mut sw = Acc::rel(
        "CAT-STORED-CURVES-MASS",
        "stored catalyst_design_curves.csv: mass-dependent columns",
        1e-5,
    );
    let mut sf = Acc::rel(
        "CAT-STORED-CURVES-FLOWSHEET",
        "stored catalyst_design_curves.csv: other numeric columns",
        1e-9,
    );
    let mut sk = Acc::exact(
        "CAT-STORED-CURVES-ROWS",
        "stored catalyst_design_curves.csv: same rows (catalyst, HI, T)",
    );
    let rows = read_csv(
        root,
        "results/research/catalyst_comparison/catalyst_design_curves.csv",
    )?;
    let mut flat: Vec<(String, bool, &Value)> = Vec::new();
    for (cid, hi, r) in &rust_curves {
        for row in r {
            flat.push((cid.clone(), *hi, row));
        }
    }
    sk.add_bool("row count", rows.len() == flat.len(), || {
        format!("stored {} rust {}", rows.len(), flat.len())
    });
    for (i, (srow, (cid, hi, r))) in rows.iter().zip(flat.iter()).enumerate() {
        let get = |k: &str| {
            srow.iter()
                .find(|x| x.0 == k)
                .map(|x| x.1.as_str())
                .unwrap_or("")
        };
        let same = get("catalyst_id") == cid
            && get("heat_integration") == if *hi { "True" } else { "False" }
            && get("T_C").parse::<f64>().ok() == r["T_C"].as_f64();
        sk.add_bool(&format!("row{i}"), same, || {
            format!(
                "stored {} {} {}",
                get("catalyst_id"),
                get("heat_integration"),
                get("T_C")
            )
        });
        for (k, v) in srow {
            let Ok(sv) = v.parse::<f64>() else { continue };
            if matches!(k.as_str(), "T_C") {
                continue;
            }
            let rv = num(&r[k.as_str()]);
            if MASS_KEYS.contains(&k.as_str()) {
                sw.add_scaled(&format!("row{i}/{k}"), rv, sv, key_scale(k));
            } else {
                sf.add_scaled(&format!("row{i}/{k}"), rv, sv, key_scale(k));
            }
        }
    }
    rep.push(sw);
    rep.push(sf);
    rep.push(sk);
    let mut sd = TreeAcc::new(
        "CAT-STORED-DESIGNS",
        "stored catalyst_comparison.json rows (design points at the stored mass)",
        1e-9,
        note,
    );
    let stored = read_value(
        root,
        "results/research/catalyst_comparison/catalyst_comparison.json",
    )?;
    for s in stored["rows"].as_array().into_iter().flatten() {
        let is_aspen = s["source_type"].as_str() == Some("aspen");
        let found = rust_designs.iter().find(|(d, _)| {
            let k = d["kind"].as_str().unwrap_or("");
            matches!(k, "python_optimum" | "aspen" | "fixed_ni")
                && (k == "aspen") == is_aspen
                && d["catalyst_id"] == s["catalyst_id"]
                && d["heat_integration"] == s["heat_integration"]
                && num(&d["T_C"]) == num(&s["T_C"])
        });
        let id = s["row_id"].as_str().unwrap_or("?");
        match found {
            Some((_, r)) => {
                if let (Some(sm), Some(rm)) = (s.as_object(), r.as_object()) {
                    for (k, v) in sm {
                        if let Some(rv) = rm.get(k) {
                            tree_with(&mut sd, &format!("{id}/{k}"), k, v, rv, &|_, key| {
                                key_scale(key)
                            });
                        }
                    }
                }
            }
            None => sd.keys.add_bool(id, false, || {
                "no Rust design point for this stored row".into()
            }),
        }
    }
    sd.push(&mut rep);
    for s in t["stored"].as_array().into_iter().flatten() {
        if num(&s["python_max_rel_dev"]) != 0.0 {
            rep.findings.push(format!(
                "{}: the Python reference at generation did not reproduce the stored file exactly (max rel. {})",
                s["file"].as_str().unwrap_or(""),
                num(&s["python_max_rel_dev"])
            ));
        }
    }
    if let Some((e, tl, m)) = ctx.props.lookup_stats() {
        rep.findings.push(format!(
            "tables back end: {e} exact, {tl} Taylor lookups, {m} misses"
        ));
    }
    Ok(rep)
}

// ===================================================================================== MCMC
/// (grid index, chains) of a main calibration run.
type MainRun = (usize, Vec<Vec<Vec<f64>>>);
fn f64s(v: &Value) -> Vec<f64> {
    v.as_array().into_iter().flatten().map(num).collect()
}

fn mat(v: &Value) -> Vec<Vec<f64>> {
    v.as_array().into_iter().flatten().map(f64s).collect()
}

fn sha_le(x: &[f64]) -> String {
    let mut b = Vec::with_capacity(x.len() * 8);
    for v in x {
        b.extend_from_slice(&v.to_le_bytes());
    }
    crate::provenance::sha256_hex(&b)
}

fn point_of(p: &Value) -> crate::calibration::Point {
    crate::calibration::Point {
        t_c: num(&p["T_C"]),
        sv_h_inv: num(&p["SV_h_inv"]),
        y_nh3: num(&p["y_NH3"]),
        y_h2: num(&p["y_H2"]),
        y_ar: num(&p["y_Ar"]),
    }
}

/// MCMC: NumPy normal stream and spawn, R-hat and ESS, adaptive Metropolis chain for chain, the
/// FITPACK spline, the PFR grid of the calibration, the recorded chains of the calibration and the
/// stored `takahashi_calibration_*.json` (posterior, diagnostics, predictive check, synthetic
/// recovery).
pub fn mcmc(
    g: &Golden,
    reg: &crate::kinetics::KineticsRegistry,
    root: &Path,
    grid_stride: usize,
) -> Result<Report, EngineError> {
    use crate::calibration::{self as cal, Generator, Posterior, Surrogate};
    use amcrax_numerics::random::{Pcg64, SeedSequence};
    let t = g.load("mcmc.json")?;
    let mut rep = Report::new("MCMC calibration");
    // ---- normal stream
    let mut zig = Acc::exact(
        "MC-NORMAL",
        "Generator.standard_normal stream (first 50 draws bitwise, SHA-256 of 10^6 draws)",
    );
    for c in t["ziggurat"]["checks"].as_array().into_iter().flatten() {
        let seed = c["seed"].as_u64().unwrap_or(0);
        let n = c["n"].as_u64().unwrap_or(0) as usize;
        let mut r = Pcg64::from_seed(seed as u128);
        let x: Vec<f64> = (0..n).map(|_| r.standard_normal()).collect();
        let first = f64s(&c["first"]);
        zig.add_bool(
            &format!("seed{seed}/first50"),
            x[..first.len()] == first[..],
            || "first draws differ".into(),
        );
        let want = c["sha256_le_f8"].as_str().unwrap_or("");
        zig.add_bool(&format!("seed{seed}/sha256"), sha_le(&x) == want, || {
            "SHA-256 differs".into()
        });
    }
    rep.push(zig);
    let mut sp = Acc::exact(
        "MC-SPAWN",
        "Generator.spawn children: normal, standard_normal, random streams bitwise",
    );
    let mut root_g = Generator::new(20261123);
    let kids = root_g.spawn(4);
    for (k, s) in kids
        .into_iter()
        .zip(t["spawn"].as_array().into_iter().flatten())
    {
        let mut b = k.bg;
        let nn: Vec<f64> = (0..5).map(|_| b.normal(0.0, 2.0)).collect();
        let sn: Vec<f64> = (0..3).map(|_| b.standard_normal()).collect();
        let u = b.random();
        let ok = nn == f64s(&s["normal_0_2"])
            && sn == f64s(&s["standard_normal_3"])
            && u == num(&s["random"]);
        sp.add_bool(&format!("child{}", s["child"]), ok, || {
            "stream differs".into()
        });
    }
    for (k, s) in root_g
        .spawn(2)
        .into_iter()
        .zip(t["spawn_second"].as_array().into_iter().flatten())
    {
        let mut b = k.bg;
        let sn: Vec<f64> = (0..3).map(|_| b.standard_normal()).collect();
        sp.add_bool(
            &format!("second/child{}", s["child"]),
            sn == f64s(&s["standard_normal_3"]),
            || "stream differs".into(),
        );
    }
    rep.push(sp);
    // ---- diagnostics
    let mut dg = Acc::rel(
        "MC-DIAGNOSTICS",
        "rank-normalised split R-hat and bulk ESS on fixed arrays",
        1e-10,
    )
    .note("relative; FFT autocovariance (radix-2 here, pocketfft in NumPy)");
    for (i, a) in t["diagnostics"]
        .as_array()
        .into_iter()
        .flatten()
        .enumerate()
    {
        let c = mat(&a["chains"]);
        dg.add(
            &format!("array{i}/rhat"),
            crate::mcmc::rhat(&c),
            num(&a["rhat"]),
        );
        dg.add(
            &format!("array{i}/ess_bulk"),
            crate::mcmc::ess_bulk(&c),
            num(&a["ess_bulk"]),
        );
    }
    rep.push(dg);
    // ---- adaptive Metropolis on a Gaussian target
    let mut am = Acc::rel("MC-AM-CHAIN", "adaptive Metropolis chain for chain (states and log densities)", 1e-12)
        .note("relative to max(|x|, 1); same normal and uniform streams, Cholesky by hand (LAPACK in NumPy)");
    let mut am_acc = Acc::exact("MC-AM-ACCEPT", "adaptive Metropolis acceptance rate");
    for a in t["adaptive_metropolis"].as_array().into_iter().flatten() {
        let si = mat(&a["Sinv"]);
        let logp = |th: &[f64]| -> f64 {
            if th[0] > 4.0 {
                return f64::NEG_INFINITY;
            }
            // float(-0.5 * th @ Si @ th): (th @ Si) then @ th
            let v: Vec<f64> = (0..3)
                .map(|j| (0..3).fold(0.0, |s, i| s + th[i] * si[i][j]))
                .collect();
            -0.5 * (0..3).fold(0.0, |s, i| s + v[i] * th[i])
        };
        let cov0 = if a["cov0"].is_null() {
            None
        } else {
            Some(mat(&a["cov0"]))
        };
        let mut rng = Pcg64::from_seed(a["seed"].as_u64().unwrap_or(0) as u128);
        let r = crate::mcmc::adaptive_metropolis(
            logp,
            &f64s(&a["x0"]),
            a["n_iter"].as_u64().unwrap_or(0) as usize,
            &mut rng,
            a["adapt_start"].as_u64().unwrap_or(0) as usize,
            a["burn_in"].as_u64().unwrap_or(0) as usize,
            cov0.as_deref(),
            1e-8,
        );
        let pc = mat(&a["chain"]);
        let case = format!("seed{}", a["seed"]);
        for (i, (p, q)) in pc.iter().zip(r.chain.iter()).enumerate() {
            for k in 0..3 {
                am.add_scaled(&format!("{case}/t{i}/{k}"), q[k], p[k], 1.0);
            }
        }
        for (i, (p, q)) in f64s(&a["logp"]).iter().zip(r.logp.iter()).enumerate() {
            am.add_scaled(&format!("{case}/logp{i}"), *q, *p, 1.0);
        }
        am_acc.add(&case, r.accept_rate, num(&a["accept_rate"]));
    }
    rep.push(am);
    rep.push(am_acc);
    // ---- calibration grids, spline
    let c = &t["calibration"];
    let lns = f64s(&c["LNS_GRID"]);
    let de = f64s(&c["DE_GRID"]);
    let grids: Vec<Vec<Vec<Vec<f64>>>> = c["grids"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|gr| gr.as_array().into_iter().flatten().map(mat).collect())
        .collect();
    let surs: Vec<Surrogate> = grids
        .iter()
        .map(|gr| Surrogate::new(&lns, &de, gr))
        .collect::<Result<_, _>>()?;
    let mut spl = Acc::abs(
        "MC-SPLINE",
        "bicubic logit(X) spline vs SciPy RectBivariateSpline (s = 0), dense points",
        1e-10,
    )
    .note("absolute on logit(X) (|logit| <= 16.1); FITPACK Givens solve against collocation LU");
    for s in t["spline"].as_array().into_iter().flatten() {
        let gi = s["grid"].as_u64().unwrap_or(0) as usize;
        let k = s["point_index"].as_u64().unwrap_or(0) as usize;
        for ((x, y), e) in f64s(&s["x"])
            .iter()
            .zip(f64s(&s["y"]).iter())
            .zip(f64s(&s["ev"]).iter())
        {
            spl.add(
                &format!("grid{gi}/({x},{y})"),
                surs[gi].ev_logit(k, *x, *y),
                *e,
            );
        }
    }
    rep.push(spl);
    // grid identification from the stored results (order of construction in the script)
    let mut grid_spec: Vec<(String, String)> = Vec::new();
    let mut stored_cal: BTreeMap<String, Value> = BTreeMap::new();
    for key in ["ni", "ru"] {
        let sv = read_value(
            root,
            &format!("results/research/uq/takahashi_calibration_{key}.json"),
        )?;
        let jc = sv["calibrated_constant"]
            .as_str()
            .unwrap_or("k")
            .trim_start_matches('k')
            .to_string();
        grid_spec.push((key.to_string(), jc));
        if !sv["rds_shift_as_specified"].is_null() {
            grid_spec.push((
                key.to_string(),
                sv["rds_constant"]
                    .as_str()
                    .unwrap_or("k")
                    .trim_start_matches('k')
                    .to_string(),
            ));
        }
        stored_cal.insert(key.to_string(), sv);
    }
    let cat = |key: &str| -> (&'static str, f64) {
        if key == "ni" {
            ("ni_takahashi_microkinetic", 773.15)
        } else {
            ("ru_takahashi_microkinetic", 723.15)
        }
    };
    let mut gx = Acc::abs("MC-PFR-GRID", "PFR outlet conversion on the calibration grid (subset) vs Python LSODA", 1e-7)
        .note("absolute in X; LSODA rtol 1e-8 against DOPRI5 rtol 1e-10 (stage 2 PFR gate); nodes where Python failed are skipped");
    let sopt = crate::reactor::SolverOptions::default();
    for (gi, (key, jc)) in grid_spec.iter().enumerate() {
        let (cid, tref) = cat(key);
        let base = reg.get(cid)?.params.clone();
        let pts: Vec<crate::calibration::Point> = c["points"][key.as_str()]
            .as_array()
            .into_iter()
            .flatten()
            .map(point_of)
            .collect();
        for i in (0..lns.len()).step_by(grid_stride) {
            for j in (0..de.len()).step_by(grid_stride) {
                let ov = cal::overrides(&base, jc, tref, reg.r_kin_j_mol_k, lns[i], de[j]);
                for (k, p) in pts.iter().enumerate() {
                    let py = grids[gi][i][j][k];
                    if py == 1e-7 || !py.is_finite() {
                        continue;
                    }
                    if let Ok(x) = cal::x_direct(reg, &sopt, cid, &ov, p) {
                        gx.add(&format!("grid{gi}/{i},{j}/{k}"), x, py);
                    } else {
                        gx.add_bool(&format!("grid{gi}/{i},{j}/{k}"), false, || {
                            "rust PFR failed".into()
                        });
                    }
                }
            }
        }
    }
    rep.push(gx);
    // ---- the recorded chains
    let mut ch = Acc::rel(
        "MC-CHAINS",
        "calibration chains: first/last states of each chain, SHA-256 of the chain array",
        1e-12,
    )
    .note("relative to max(|x|, 1); chain for chain on the Python PFR grid");
    let mut sha_ok = Acc::info(
        "MC-CHAINS-SHA",
        "calibration chains bitwise (SHA-256 of the float64 array; 1 = differs; reported, not gated)",
    );
    let mut summ = Acc::abs(
        "MC-SUMMARY",
        "posterior summaries (mean, sd, p5, p50, p95 of ln s, dE, ln sigma_d; sigma_d)",
        1e-9,
    );
    let mut dia = Acc::rel(
        "MC-RUN-DIAG",
        "R-hat and bulk ESS of the calibration runs",
        1e-9,
    );
    let mut acc_rate = Acc::abs(
        "MC-RUN-ACCEPT",
        "acceptance rates of the calibration runs",
        1e-12,
    );
    let names = ["ln_s", "dE_kJ_mol", "ln_sigma_d"];
    let mut main_runs: BTreeMap<String, MainRun> = BTreeMap::new();
    let mut syn_hits: BTreeMap<String, [usize; 2]> = BTreeMap::new();
    let seed = c["SEED"].as_u64().unwrap_or(0) as u128;
    for (ri, r) in c["runs"].as_array().into_iter().flatten().enumerate() {
        let gi = r["grid"].as_u64().unwrap_or(0) as usize;
        let key = grid_spec.get(gi).map(|x| x.0.clone()).unwrap_or_default();
        let idx: Vec<usize> = r["idx"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_u64)
            .map(|v| v as usize)
            .collect();
        let post = Posterior {
            sur: &surs[gi],
            idx: idx.clone(),
            y: f64s(&r["y"]),
            de_sd: num(&r["dE_sd"]),
            lns_grid: (lns[0], lns[lns.len() - 1]),
            de_grid: (de[0], de[de.len() - 1]),
        };
        let ent = r["rng"]["entropy"].as_u64().unwrap_or(0) as u128;
        let mut ss = SeedSequence::new(ent);
        ss.set_children_spawned(r["rng"]["n_children_spawned"].as_u64().unwrap_or(0));
        let bg = Pcg64::from_seed_sequence(&SeedSequence::new(ent));
        let mut rng = Generator { ss, bg };
        let n_iter = r["n_iter"].as_u64().unwrap_or(0) as usize;
        let out = cal::run_chains(&post, &mut rng, n_iter, num(&r["dE_sd_init"]));
        let case = format!(
            "run{ri}/{key}/seed{ent}/spawned{}",
            r["rng"]["n_children_spawned"]
        );
        let head = &r["head"];
        let tail = &r["tail"];
        for m in 0..4 {
            let n = out.c[m].len();
            for s in 0..5 {
                for k in 0..3 {
                    ch.add_scaled(
                        &format!("{case}/c{m}/h{s}/{k}"),
                        out.c[m][s][k],
                        num(&head[m][s][k]),
                        1.0,
                    );
                    ch.add_scaled(
                        &format!("{case}/c{m}/t{s}/{k}"),
                        out.c[m][n - 5 + s][k],
                        num(&tail[m][s][k]),
                        1.0,
                    );
                }
            }
        }
        let flatv: Vec<f64> = out.c.iter().flatten().flatten().copied().collect();
        sha_ok.add(
            &case,
            if sha_le(&flatv) == r["sha256_le_f8"].as_str().unwrap_or("") {
                0.0
            } else {
                1.0
            },
            0.0,
        );
        let (sm, sig) = cal::summarise(&out.c);
        for (k, nme) in names.iter().enumerate() {
            for (q, lab) in ["mean", "sd", "p5", "p50", "p95"].iter().enumerate() {
                summ.add(
                    &format!("{case}/{nme}/{lab}"),
                    sm[k][q],
                    num(&r["summary"][nme][lab]),
                );
            }
            dia.add(
                &format!("{case}/{nme}/rhat"),
                out.diag[k].0,
                num(&r["diag"][nme]["rhat"]),
            );
            dia.add(
                &format!("{case}/{nme}/ess"),
                out.diag[k].1,
                num(&r["diag"][nme]["ess_bulk"]),
            );
        }
        for (q, lab) in ["mean", "p5", "p50", "p95"].iter().enumerate() {
            summ.add(
                &format!("{case}/sigma_d/{lab}"),
                sig[q],
                num(&r["summary"]["sigma_d"][lab]),
            );
        }
        for (m, a) in out.acc.iter().enumerate() {
            acc_rate.add(&format!("{case}/c{m}"), *a, num(&r["acc"][m]));
        }
        // synthetic recovery runs: fresh default_rng(SEED + 100 + k), 8000 iterations
        if ent >= seed + 100 && ent < seed + 120 {
            let fl = cal::flat(&out.c);
            let star = [0.5, 10.0];
            let e = syn_hits.entry(key.clone()).or_insert([0, 0]);
            for j in 0..2 {
                let col: Vec<f64> = fl.iter().map(|row| row[j]).collect();
                let (a, b) = (
                    amcrax_numerics::stats::quantile(&col, 0.05),
                    amcrax_numerics::stats::quantile(&col, 0.95),
                );
                if a <= star[j] && star[j] <= b {
                    e[j] += 1;
                }
            }
        }
        if (ent == seed || ent == seed + 1) && r["rng"]["n_children_spawned"].as_u64() == Some(0) {
            main_runs.insert(key.clone(), (gi, out.c));
        }
    }
    rep.push(ch);
    rep.push(sha_ok);
    rep.push(summ);
    rep.push(dia);
    rep.push(acc_rate);
    // ---- stored results: posterior, synthetic coverage, predictive check, thinned posterior CSV
    let mut st = Acc::abs(
        "MC-STORED",
        "stored takahashi_calibration_*.json: posterior, predictive check (Rust chains)",
        1e-9,
    );
    let mut stx = Acc::exact(
        "MC-STORED-COUNTS",
        "stored coverage counts, inside-90 flags, synthetic recovery hits",
    );
    for key in ["ni", "ru"] {
        let sv = &stored_cal[key];
        let Some((gi, cmain)) = main_runs.get(key) else {
            stx.add_bool(key, false, || "main run not found".into());
            continue;
        };
        let (sm, _) = cal::summarise(cmain);
        for (k, nme) in names.iter().enumerate() {
            for (q, lab) in ["mean", "sd", "p5", "p50", "p95"].iter().enumerate() {
                st.add(
                    &format!("{key}/posterior/{nme}/{lab}"),
                    sm[k][q],
                    num(&sv["posterior"][nme][lab]),
                );
            }
        }
        if let Some(h) = syn_hits.get(key) {
            stx.add_bool(
                &format!("{key}/synthetic/ln_s"),
                h[0] as f64 == num(&sv["synthetic_recovery"]["coverage"]["ln_s"]),
                || format!("rust {}", h[0]),
            );
            stx.add_bool(
                &format!("{key}/synthetic/dE"),
                h[1] as f64 == num(&sv["synthetic_recovery"]["coverage"]["dE_kJ_mol"]),
                || format!("rust {}", h[1]),
            );
        }
        // posterior predictive (thin = flat[::max(1, N // 2000)], prng = default_rng(SEED))
        let fl = cal::flat(cmain);
        let step = (fl.len() / 2000).max(1);
        let thin: Vec<&Vec<f64>> = fl.iter().step_by(step).collect();
        let pts = c["points"][key].as_array().map(Vec::len).unwrap_or(0);
        let all: Vec<usize> = (0..pts).collect();
        let mu: Vec<Vec<f64>> = thin
            .iter()
            .map(|th| surs[*gi].eval(th[0], th[1], &all))
            .collect();
        let mut prng = Pcg64::from_seed(seed);
        let mut pred = vec![vec![0.0; pts]; thin.len()];
        for (r, th) in thin.iter().enumerate() {
            let sdv = (cal::SIGMA_R.powi(2) + th[2].exp().powi(2)).sqrt();
            for k in 0..pts {
                pred[r][k] = mu[r][k] + prng.standard_normal() * sdv;
            }
        }
        for (k, p) in sv["posterior_predictive"]
            .as_array()
            .into_iter()
            .flatten()
            .enumerate()
        {
            let col: Vec<f64> = pred.iter().map(|r| r[k]).collect();
            let mcol: Vec<f64> = mu.iter().map(|r| r[k]).collect();
            let q = |x: &[f64], v: f64| amcrax_numerics::stats::quantile(x, v);
            let (lo, med, hi) = (q(&col, 0.05), q(&col, 0.5), q(&col, 0.95));
            st.add(&format!("{key}/ppc{k}/median"), med, num(&p["median"]));
            st.add(&format!("{key}/ppc{k}/p5"), lo, num(&p["p5"]));
            st.add(&format!("{key}/ppc{k}/p95"), hi, num(&p["p95"]));
            st.add(
                &format!("{key}/ppc{k}/model_median"),
                amcrax_numerics::stats::median(&mcol),
                num(&p["model_median_no_noise"]),
            );
            let obs = num(&p["observed"]);
            stx.add_bool(
                &format!("{key}/ppc{k}/inside_90"),
                (lo <= obs && obs <= hi) == p["inside_90"].as_bool().unwrap_or(false),
                || "flag differs".into(),
            );
        }
        // thinned posterior CSV
        let csv = std::fs::read_to_string(
            root.join(format!("results/research/uq/takahashi_posterior_{key}.csv")),
        )
        .unwrap_or_default();
        let rows: Vec<Vec<f64>> = csv
            .lines()
            .skip(1)
            .map(|l| l.split(',').filter_map(|s| s.trim().parse().ok()).collect())
            .collect();
        let tstep = (fl.len() / 2000).max(1);
        let rthin: Vec<&Vec<f64>> = fl.iter().step_by(tstep).collect();
        stx.add_bool(
            &format!("{key}/posterior_csv_rows"),
            rows.len() == rthin.len(),
            || format!("stored {} rust {}", rows.len(), rthin.len()),
        );
        for (i, (a, b)) in rows.iter().zip(rthin.iter()).enumerate() {
            for k in 0..3 {
                st.add(
                    &format!("{key}/csv{i}/{k}"),
                    b[k],
                    a.get(k).copied().unwrap_or(f64::NAN),
                );
            }
        }
    }
    rep.push(st);
    rep.push(stx);
    for s in t["stored"].as_array().into_iter().flatten() {
        if num(&s["python_max_rel_dev"]) != 0.0
            || s["posterior_csv_identical"].as_bool() != Some(true)
        {
            rep.findings.push(format!(
                "{}: the Python reference at generation reproduced the stored file with max rel. deviation {} (csv identical: {})",
                s["file"].as_str().unwrap_or(""),
                num(&s["python_max_rel_dev"]),
                s["posterior_csv_identical"]
            ));
        }
    }
    Ok(rep)
}

// ===================================================================================== optimisation
/// The stored design grid (`results/optimisation/design_grid.csv`) as rows.
#[cfg(feature = "yaml")]
pub fn read_design_grid(root: &Path) -> Result<Vec<crate::optim::Row>, EngineError> {
    let rows = read_csv(root, "results/optimisation/design_grid.csv")?;
    Ok(rows
        .into_iter()
        .map(|r| {
            r.into_iter()
                .map(|(k, v)| {
                    let val = match v.as_str() {
                        "True" => Value::Bool(true),
                        "False" => Value::Bool(false),
                        "" => Value::Null,
                        s => s
                            .parse::<f64>()
                            .map(crate::process::result::jf)
                            .unwrap_or(Value::String(s.to_string())),
                    };
                    (k, val)
                })
                .collect()
        })
        .collect())
}

/// Optimisation: `evaluate_result` (the batch objective) and the constraints on every stored
/// simulation result against Python, and the Pareto fronts and objective conflicts recomputed
/// from the stored design grid against the stored `pareto.json` and `objective_conflicts.json`.
#[cfg(feature = "yaml")]
pub fn optimisation(
    g: &Golden,
    d: &crate::economics::reference::EconomicsData,
    p: &crate::separation::SepParams,
    root: &Path,
) -> Result<Report, EngineError> {
    use crate::optim::{EvalOpts, conflicts, constraint_values, evaluate_result, pareto};
    let t = g.load("optimisation.json")?;
    let mut rep = Report::new("optimisation objectives and Pareto analysis");
    let note = "relative; key scales as HI-NUM";
    let mut ev = TreeAcc::new(
        "OPT-EVAL",
        "evaluate_result (LCOH, CI, KPIs, compression) on the stored results",
        1e-9,
        note,
    );
    let mut cons = Acc::rel(
        "OPT-CONSTRAINTS",
        "constraint values g (FEHE, conversion, purity)",
        1e-9,
    );
    let mut outcome = Acc::exact(
        "OPT-OUTCOME",
        "evaluate_result: success, or the same exception class",
    );
    let mut cache: BTreeMap<String, SimulationResult> = BTreeMap::new();
    for (i, c) in t["calls"].as_array().into_iter().flatten().enumerate() {
        let file = c["file"].as_str().unwrap_or("");
        if !cache.contains_key(file) {
            cache.insert(file.to_string(), aspen_result(root, file)?);
        }
        let res = &cache[file];
        let a = &c["args"];
        let o = EvalOpts {
            heat_source: a["heat_source"].as_str().unwrap_or("ammonia").to_string(),
            nh3_route: a["nh3_route"].as_str().unwrap_or("grey").to_string(),
            include_compression: a["include_compression"].as_bool().unwrap_or(true),
            nh3_price_usd_per_t: a["nh3_price_USD_per_t"].as_f64(),
            ..EvalOpts::default()
        };
        let case = format!("{file}#{i}");
        match (py_error(&c["out"]), evaluate_result(d, p, res, &o)) {
            (Some(cls), Err(e)) => outcome.add_bool(&case, error_class_matches(cls, &e), || {
                format!("python {cls}, rust {e}")
            }),
            (Some(cls), Ok(_)) => outcome.add_bool(&case, false, || format!("python raised {cls}")),
            (None, Err(e)) => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
            (None, Ok(r)) => {
                outcome.add_bool(&case, true, String::new);
                tree(&mut ev, &case, "", &c["out"], &r);
                if let (Some(gp), Ok(gr)) = (c["constraints"].as_object(), constraint_values(p, &r))
                {
                    for (k, v) in gr {
                        cons.add_scaled(&format!("{case}/{k}"), v, num(&gp[&k]), 1e-6);
                    }
                }
            }
        }
    }
    ev.push(&mut rep);
    rep.push(cons);
    rep.push(outcome);
    // Pareto fronts and conflicts from the stored design grid
    let rows = read_design_grid(root)?;
    let par = pareto(&rows);
    let sp = read_value(root, "results/optimisation/pareto.json")?;
    let mut fr = Acc::exact(
        "OPT-PARETO",
        "Pareto fronts of the stored design grid: objectives, point sets and order, infeasible unconstrained points",
    );
    let keys = [
        "reactor_temperature_C",
        "reactor_pressure_bar",
        "psa_h2_recovery",
        "fehe_hot_end_approach_K",
    ];
    let pf = sp["fronts"].as_array().cloned().unwrap_or_default();
    let rf = par["fronts"].as_array().cloned().unwrap_or_default();
    fr.add_bool("number of fronts", pf.len() == rf.len(), || {
        format!("stored {} rust {}", pf.len(), rf.len())
    });
    for (a, b) in pf.iter().zip(rf.iter()) {
        let id = format!("{}", a["objectives"]);
        fr.add_bool(
            &format!("{id}/objectives"),
            a["objectives"] == b["objectives"],
            || format!("rust {}", b["objectives"]),
        );
        let pts = |v: &Value| -> Vec<Vec<f64>> {
            v.as_array()
                .into_iter()
                .flatten()
                .map(|r| keys.iter().map(|k| num(&r[*k])).collect())
                .collect()
        };
        fr.add_bool(
            &format!("{id}/points"),
            pts(&a["points"]) == pts(&b["points"]),
            || {
                format!(
                    "stored {:?} rust {:?}",
                    pts(&a["points"]),
                    pts(&b["points"])
                )
            },
        );
        fr.add_bool(
            &format!("{id}/unconstrained_infeasible"),
            pts(&a["unconstrained_front_infeasible_points"])
                == pts(&b["unconstrained_front_infeasible_points"]),
            || "differs".into(),
        );
    }
    fr.add_bool(
        "n_feasible",
        num(&sp["n_feasible"]) == num(&par["n_feasible"]),
        || format!("rust {}", par["n_feasible"]),
    );
    rep.push(fr);
    let sc = read_value(root, "results/optimisation/objective_conflicts.json")?;
    let rc = conflicts(&rows);
    let mut cf = Acc::exact(
        "OPT-CONFLICTS",
        "objective conflicts: non-dominated counts, distinct points, classification",
    );
    let mut rho = Acc::rel(
        "OPT-SPEARMAN",
        "Spearman rank correlation of each objective pair (minimisation sense)",
        1e-12,
    );
    let mut rng_acc = Acc::rel(
        "OPT-FRONT-RANGES",
        "ranges of the pairwise non-dominated sets",
        1e-15,
    );
    for (a, b) in sc["pairs"]
        .as_array()
        .into_iter()
        .flatten()
        .zip(rc["pairs"].as_array().into_iter().flatten())
    {
        let id = format!("{}", a["pair"]);
        rho.add(
            &id,
            num(&b["spearman_rho_min_sense"]),
            num(&a["spearman_rho_min_sense"]),
        );
        for k in [
            "n_feasible_points",
            "n_non_dominated",
            "n_distinct_non_dominated",
            "classification",
            "pair",
        ] {
            cf.add_bool(
                &format!("{id}/{k}"),
                a[k] == b[k] || num(&a[k]) == num(&b[k]),
                || format!("stored {} rust {}", a[k], b[k]),
            );
        }
        if let Some(m) = a["front_ranges"].as_object() {
            for (k, v) in m {
                for (x, y) in f64s(v).iter().zip(f64s(&b["front_ranges"][k]).iter()) {
                    rng_acc.add(&format!("{id}/{k}"), *y, *x);
                }
            }
        }
    }
    rep.push(cf);
    rep.push(rho);
    rep.push(rng_acc);
    rep.findings.push(
        "The optimiser (SciPy differential_evolution with Sobol initialisation, deferred updating and a NonlinearConstraint, \
         SLSQP polish, epsilon-constraint SLSQP) stays in Python; Rust provides the batch objective (`amcrax eval objective`) \
         and the grid search / Pareto analysis."
            .into(),
    );
    Ok(rep)
}
