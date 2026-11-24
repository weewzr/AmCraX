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
            Ok(r) => {
                outcome.add_bool(&case, true, String::new);
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
