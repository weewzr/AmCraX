//! Stage 5, second part: end use and LCA (and, in later blocks, catalyst economics, the
//! calibration end to end and the design grid) against `rust/golden/stage5/` and the stored
//! results under `results/research`.
//!
//! The study documents are compared as trees: every number (relative, 1e-9 of max(|x|, 1)),
//! integer and flag (identical), identifier and computed label (identical) and the structure
//! (same fields, lengths and null pattern). Python fields that hold only static prose (method
//! statements, notes, limitations, source descriptions) are not produced by the Rust drivers and
//! are counted under `-PROSE`, which is informational.

use super::stage4::{TreeAcc, is_num, unsign_zeros};
use super::{Acc, Golden, Report, num, py_error};
use crate::economics::reference::EconomicsData;
use crate::enduse::{self as eu, CostOpts, Ctx, PowerOpts};
use crate::error::EngineError;
use serde_json::{Value, json};
use std::path::Path;

/// Whether a Python value is prose only (strings, or containers of strings).
fn is_prose(v: &Value) -> bool {
    match v {
        Value::String(_) => true,
        Value::Array(a) => !a.is_empty() && a.iter().all(is_prose),
        Value::Object(m) => !m.is_empty() && m.values().all(is_prose),
        _ => false,
    }
}

/// Compare a Python tree with a Rust tree that may leave out prose fields.
pub fn partial_tree(
    acc: &mut TreeAcc,
    prose: &mut Acc,
    path: &str,
    p: &Value,
    r: &Value,
    scale: f64,
) {
    match p {
        Value::Object(pm) => {
            let Some(rm) = r.as_object() else {
                acc.keys
                    .add_bool(path, false, || format!("python object, rust {r}"));
                return;
            };
            for (k, pv) in pm {
                let sub = format!("{path}/{k}");
                match rm.get(k) {
                    Some(rv) => partial_tree(acc, prose, &sub, pv, rv, scale),
                    None if k == "provenance" || is_prose(pv) => {
                        prose.add_bool(&sub, true, String::new)
                    }
                    None => acc.keys.add_bool(&sub, false, || "missing in rust".into()),
                }
            }
            for k in rm.keys() {
                if !pm.contains_key(k) {
                    acc.keys
                        .add_bool(&format!("{path}/{k}"), false, || "only in rust".into());
                }
            }
        }
        Value::Array(pa) => {
            let Some(ra) = r.as_array().filter(|ra| ra.len() == pa.len()) else {
                acc.keys.add_bool(path, false, || {
                    format!(
                        "array lengths differ: python {} rust {:?}",
                        pa.len(),
                        r.as_array().map(Vec::len)
                    )
                });
                return;
            };
            for (i, (pv, rv)) in pa.iter().zip(ra.iter()).enumerate() {
                partial_tree(acc, prose, &format!("{path}[{i}]"), pv, rv, scale);
            }
        }
        Value::Bool(_) => acc
            .dec
            .add_bool(path, p == r, || format!("python {p} rust {r}")),
        Value::Null => acc
            .keys
            .add_bool(path, r.is_null(), || format!("python null rust {r}")),
        Value::String(s) if !matches!(s.as_str(), "nan" | "inf" | "-inf") => {
            let same = p == r
                || r.as_str()
                    .is_some_and(|rs| unsign_zeros(rs) == unsign_zeros(s));
            acc.text
                .add_bool(path, same, || format!("python {p} rust {r}"))
        }
        Value::Number(n) if n.is_i64() || n.is_u64() => {
            acc.dec.add_bool(path, is_num(r) && num(r) == num(p), || {
                format!("python {p} rust {r}")
            })
        }
        _ => {
            if is_num(r) || r.is_null() {
                let rv = if r.is_null() { f64::NAN } else { num(r) };
                acc.num.add_scaled(path, rv, num(p), scale);
            } else {
                acc.keys
                    .add_bool(path, false, || format!("python {p} rust {r}"));
            }
        }
    }
}

fn error_ok(cls: &str, e: &EngineError) -> bool {
    match cls {
        "ValueError" | "KeyError" | "TypeError" | "ZeroDivisionError" | "FileNotFoundError" => {
            matches!(e, EngineError::Domain(_) | EngineError::Data { .. })
        }
        "RuntimeError" => matches!(e, EngineError::Numerical(_) | EngineError::Bracket(_)),
        _ => false,
    }
}

fn opt(a: &Value, k: &str) -> Option<f64> {
    a.get(k).filter(|v| !v.is_null()).map(num)
}

fn power_opts(a: &Value) -> PowerOpts {
    PowerOpts {
        case: a["case"].as_str().unwrap_or("baseline").to_string(),
        gain_scale: opt(a, "gain_scale").unwrap_or(1.0),
        eta_h2_fuel: opt(a, "eta_h2_fuel"),
        heat_fuel_efficiency: opt(a, "heat_fuel_efficiency").unwrap_or(1.0),
    }
}

fn kind_y(a: &Value) -> (String, Option<f64>) {
    (a["kind"].as_str().unwrap_or("").to_string(), opt(a, "y_h2"))
}

/// One direct call of `enduse.json`.
fn enduse_call(ctx: &Ctx, f: &str, a: &Value) -> Result<Value, EngineError> {
    let fc = || num(&a["conversion"]);
    Ok(match f {
        "cracked_share_for_h2_fraction" => {
            json!(eu::cracked_share_for_h2_fraction(num(&a["y_h2"]), fc())?)
        }
        "h2_fraction_of_blend" => json!(eu::h2_fraction_of_blend(num(&a["f"]), fc())),
        "alpha_of_cracked_share" => json!(eu::alpha_of_cracked_share(num(&a["f"]), fc())),
        "fuel_lhv_mj_per_kg_nh3_fed" => json!(eu::fuel_lhv_mj_per_kg_nh3_fed(num(&a["f"]), fc())),
        "load_cracker" => ctx.cracker(a["case"].as_str().unwrap_or(""))?.to_json(),
        "power_activity" => {
            let (k, y) = kind_y(a);
            eu::power_activity(ctx, &k, y, &power_opts(a))?.to_json()
        }
        "power_cost" => {
            let (k, y) = kind_y(a);
            let act = eu::power_activity(ctx, &k, y, &PowerOpts::default())?;
            let mut o = CostOpts::new(&ctx.p);
            if let Some(v) = opt(a, "hours") {
                o.hours = v;
            }
            if let Some(v) = opt(a, "discount") {
                o.discount = v;
            }
            if let Some(v) = opt(a, "life") {
                o.life = v;
            }
            if let Some(v) = opt(a, "mass_basis_kg_s") {
                o.mass_basis_kg_s = v;
            }
            if let Some(v) = opt(a, "electricity_price") {
                o.electricity_price = v;
            }
            if let Some(v) = a["unpurified_full_correlation"].as_bool() {
                o.unpurified_full_correlation = v;
            }
            if let Some(v) = opt(a, "cracker_capex_factor") {
                o.cracker_capex_factor = v;
            }
            if let Some(v) = opt(a, "plant_capex_factor") {
                o.plant_capex_factor = v;
            }
            if let Some(v) = opt(a, "extra_capex_USD_per_kW") {
                o.extra_capex_usd_per_kw = v;
            }
            eu::power_cost(ctx, &act, num(&a["nh3_price"]), &o)?.to_json()
        }
        "hydrogen_activity" => {
            eu::hydrogen_activity(ctx, a["case"].as_str().unwrap_or(""), "h", "lab", "note")?
                .to_json()
        }
        "hydrogen_cost" => eu::hydrogen_cost(
            ctx,
            a["case"].as_str().unwrap_or(""),
            num(&a["nh3_price"]),
            opt(a, "hours"),
            opt(a, "electricity"),
            a["capex_mode"].as_str().unwrap_or("reference"),
        )?
        .to_json(),
        "hydrogen_activity_purification" => {
            let (act, cost) = eu::hydrogen_activity_purification(
                ctx,
                a["config_id"].as_str().unwrap_or(""),
                a["grade_key"].as_str().unwrap_or(""),
                "i",
                "l",
            )?;
            json!({"activity": act.to_json(), "cost": cost})
        }
        "carbon_intensity" => {
            let (k, y) = kind_y(a);
            let act = eu::power_activity(ctx, &k, y, &PowerOpts::default())?;
            eu::ci_json(&eu::carbon_intensity(
                &act,
                num(&a["route_ef"]),
                num(&a["distance_km"]),
                opt(a, "grid"),
                opt(a, "boil_off"),
                opt(a, "ship_ef"),
            ))
        }
        "breakeven_ef" => {
            let (k, y) = kind_y(a);
            let act = eu::power_activity(ctx, &k, y, &PowerOpts::default())?;
            json!(eu::breakeven_ef(
                &act,
                num(&a["alt_ci"]),
                num(&a["distance_km"]),
                None
            ))
        }
        other => {
            return Err(EngineError::data(
                "enduse.json",
                format!("unknown function {other}"),
            ));
        }
    })
}

fn read_json(root: &Path, rel: &str) -> Result<Value, EngineError> {
    let t = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    serde_json::from_str(&t).map_err(|e| EngineError::data(rel, e.to_string()))
}

const NOTE: &str = "relative to max(|x|, 1): costs, intensities, efficiencies and percentage points of order 1 to 1000; \
                    brentq roots (xtol 1e-12 or 2e-12) and pow() of the C library agree far inside the gate";

/// End use and LCA: direct calls of the pathway functions, the three study drivers against the
/// Python rerun (golden) and against the stored files.
pub fn enduse(g: &Golden, d: &EconomicsData, root: &Path) -> Result<Report, EngineError> {
    use crate::enduse_study as st;
    let t = g.load("enduse.json")?;
    let ctx = Ctx::new(d, root)?;
    let mut rep = Report::new("end use and LCA");
    // ---- module constants
    let mut par = Acc::rel("EU-PARAMS", "enduse.params constants", 1e-15);
    for (k, v) in ctx.p.named() {
        match t["params"].get(k) {
            Some(pv) => par.add(k, v, num(pv)),
            None => par.add_bool(k, false, || "not in golden".into()),
        }
    }
    rep.push(par);
    // ---- direct calls
    let mut calls = TreeAcc::new(
        "EU-CALL",
        "pathway functions (direct calls)",
        1e-12,
        "relative to max(|x|, 1)",
    );
    let mut prose = Acc::exact(
        "EU-CALL-PROSE",
        "prose fields not reproduced (none expected)",
    );
    let mut outcome = Acc::exact("EU-CALL-OUTCOME", "success, or the same exception class");
    for (i, c) in t["calls"].as_array().into_iter().flatten().enumerate() {
        let f = c["fn"].as_str().unwrap_or("");
        let case = format!("{f}#{i} {}", c["args"]);
        match (py_error(&c["out"]), enduse_call(&ctx, f, &c["args"])) {
            (Some(cls), Err(e)) => outcome.add_bool(&case, error_ok(cls, &e), || {
                format!("python {cls}, rust {e}")
            }),
            (Some(cls), Ok(_)) => outcome.add_bool(&case, false, || format!("python raised {cls}")),
            (None, Err(e)) => outcome.add_bool(&case, false, || format!("rust failed: {e}")),
            (None, Ok(r)) => {
                outcome.add_bool(&case, true, String::new);
                partial_tree(&mut calls, &mut prose, &case, &c["out"], &r, 1.0);
            }
        }
    }
    calls.push(&mut rep);
    rep.push(outcome);
    // ---- the drivers
    // a failing driver is a failed check (the other drivers are still compared)
    let mut run_ok = Acc::exact("EU-RUN", "the three study drivers run to completion");
    let lca = st::lca_run(&ctx).unwrap_or_else(|e| {
        run_ok.add_bool("lca_run", false, || e.to_string());
        st::LcaRun {
            results: Value::Null,
            assumptions: Value::Null,
            validation: Value::Null,
        }
    });
    let empty = || st::EnduseRun {
        results: Value::Null,
        assumptions: Value::Null,
        validation: Vec::new(),
    };
    let eur = st::enduse_run(&ctx, root).unwrap_or_else(|e| {
        run_ok.add_bool("enduse_run", false, || e.to_string());
        empty()
    });
    let thr = if eur.results.is_null() {
        run_ok.add_bool("enduse_threshold", false, || "enduse_run failed".into());
        None
    } else {
        st::enduse_threshold(&ctx, root, &eur)
            .map_err(|e| run_ok.add_bool("enduse_threshold", false, || e.to_string()))
            .ok()
    };
    let thr = thr.unwrap_or(st::ThresholdRun {
        results: Value::Null,
        nox: Value::Null,
        validation: Vec::new(),
        csv: Vec::new(),
    });
    run_ok.add_bool("drivers", true, String::new);
    rep.push(run_ok);
    let runs = &t["runs"];
    let val_enduse = Value::Array(thr.validation.clone());
    let mut prose = Acc::exact(
        "EU-PROSE",
        "static prose fields of the Python documents (not reproduced; counted)",
    );
    let docs: [(&str, &str, &Value, &Value); 7] = [
        (
            "EU-LCA",
            "lca_results.json",
            &runs["lca_results.json"],
            &lca.results,
        ),
        (
            "EU-ENDUSE",
            "enduse_results.json",
            &runs["enduse_results.json"],
            &eur.results,
        ),
        (
            "EU-ENDUSE-ASSUMPTIONS",
            "enduse assumptions.json",
            &runs["assumptions.json"],
            &eur.assumptions,
        ),
        (
            "EU-THRESHOLD",
            "turbine_threshold.json",
            &runs["turbine_threshold.json"],
            &thr.results,
        ),
        (
            "EU-NOX",
            "nox_n2o_blends.json",
            &runs["nox_n2o_blends.json"],
            &thr.nox,
        ),
        (
            "EU-VAL-LCA",
            "validation/lca.json",
            &runs["validation/lca.json"],
            &lca.validation,
        ),
        (
            "EU-VAL-ENDUSE",
            "validation/enduse.json",
            &runs["validation/enduse.json"],
            &val_enduse,
        ),
    ];
    for (id, what, p, r) in docs {
        let mut acc = TreeAcc::new(id, &format!("{what} against the Python rerun"), 1e-9, NOTE);
        partial_tree(&mut acc, &mut prose, what, p, r, 1.0);
        acc.push(&mut rep);
    }
    // LCA factor register
    let mut fac = TreeAcc::new(
        "EU-LCA-FACTORS",
        "lca.FACTORS values (assumptions register)",
        0.0,
        "identical",
    );
    let rf = Value::Object(
        st::lca_factor_values()
            .into_iter()
            .map(|(k, v)| (k.to_string(), v))
            .collect(),
    );
    partial_tree(
        &mut fac,
        &mut prose,
        "FACTORS",
        &runs["lca_assumptions_factors"],
        &rf,
        1.0,
    );
    fac.push(&mut rep);
    // CSV tables of the threshold study
    let mut csv = TreeAcc::new(
        "EU-CSV",
        "enduse_threshold CSV tables (sensitivities, two-way map)",
        1e-9,
        NOTE,
    );
    for (name, rows) in &thr.csv {
        let key = format!("enduse_threshold/{name}");
        partial_tree(
            &mut csv,
            &mut prose,
            &key,
            &t["csv_rows"][key.as_str()],
            &Value::Array(rows.clone()),
            1.0,
        );
    }
    csv.push(&mut rep);
    rep.push(prose);
    // ---- the stored files
    let mut sp = Acc::exact(
        "EU-STORED-PY",
        "the Python rerun reproduces the stored result files (generator check)",
    );
    for s in t["stored"].as_array().into_iter().flatten() {
        let ok = num(&s["max"]) == 0.0
            && s["other"].as_array().is_some_and(Vec::is_empty)
            && s["only"].as_array().is_some_and(Vec::is_empty);
        sp.add_bool(s["file"].as_str().unwrap_or(""), ok, || format!("{s}"));
    }
    rep.push(sp);
    let mut stp = Acc::exact(
        "EU-STORED-PROSE",
        "stored files: static prose fields (counted)",
    );
    let stored: [(&str, &str, &Value); 7] = [
        (
            "EU-STORED-LCA",
            "results/research/lca/lca_results.json",
            &lca.results,
        ),
        (
            "EU-STORED-LCA-ASSUMPTIONS",
            "results/research/lca/assumptions.json",
            &lca.assumptions,
        ),
        (
            "EU-STORED-ENDUSE",
            "results/research/enduse/enduse_results.json",
            &eur.results,
        ),
        (
            "EU-STORED-THRESHOLD",
            "results/research/enduse/turbine_threshold.json",
            &thr.results,
        ),
        (
            "EU-STORED-NOX",
            "results/research/enduse/nox_n2o_blends.json",
            &thr.nox,
        ),
        (
            "EU-STORED-VAL-LCA",
            "results/research/validation/lca.json",
            &lca.validation,
        ),
        (
            "EU-STORED-VAL-ENDUSE",
            "results/research/validation/enduse.json",
            &val_enduse,
        ),
    ];
    for (id, rel, r) in stored {
        let p = read_json(root, rel)?;
        let mut acc = TreeAcc::new(id, &format!("{rel} (stored)"), 1e-9, NOTE);
        partial_tree(&mut acc, &mut stp, rel, &p, r, 1.0);
        acc.push(&mut rep);
    }
    rep.push(stp);
    rep.findings.push(
        "The LCA Monte Carlo draws uniform variates only (Generator.uniform = low + (high - low) * random()), \
         so it does not depend on the ziggurat or on exp/log of the C library; it is compared at the value gate."
            .into(),
    );
    Ok(rep)
}

// ===================================================================================== ziggurat experiment
/// Replays NumPy's Windows libm values (in call order) while also evaluating the native ones.
struct Replay<'a> {
    wedge: &'a [(usize, usize, u64)],
    tail: &'a [(usize, u64, u64)],
    wi: usize,
    ti: usize,
    second: bool,
    draw: usize,
    misaligned: usize,
    n_exp_diff: usize,
    max_ulp_exp: u64,
    flips: Vec<(usize, usize)>,
    n_log: usize,
    n_log_diff: usize,
    max_ulp_log: u64,
    first_log_diff: Option<usize>,
}

fn ulp(a: f64, b: f64) -> u64 {
    (a.to_bits() as i64).abs_diff(b.to_bits() as i64)
}

impl amcrax_numerics::random::ZigMath for Replay<'_> {
    fn exp(&mut self, arg: f64, layer: usize, lhs: f64) -> f64 {
        let nat = arg.exp();
        let Some(&(d, l, b)) = self.wedge.get(self.wi) else {
            self.misaligned += 1;
            return nat;
        };
        self.wi += 1;
        if d != self.draw || l != layer {
            self.misaligned += 1;
        }
        let w = f64::from_bits(b);
        if w != nat {
            self.n_exp_diff += 1;
            self.max_ulp_exp = self.max_ulp_exp.max(ulp(w, nat));
            if (lhs < w) != (lhs < nat) {
                self.flips.push((self.draw, layer));
            }
        }
        w
    }
    fn log1p(&mut self, arg: f64) -> f64 {
        let nat = arg.ln_1p();
        let Some(&(d, b1, b2)) = self.tail.get(self.ti) else {
            self.misaligned += 1;
            return nat;
        };
        if d != self.draw {
            self.misaligned += 1;
        }
        let w = f64::from_bits(if self.second { b2 } else { b1 });
        if self.second {
            self.ti += 1;
        }
        self.second = !self.second;
        self.n_log += 1;
        if w != nat {
            self.n_log_diff += 1;
            self.max_ulp_log = self.max_ulp_log.max(ulp(w, nat));
            self.first_log_diff.get_or_insert(self.draw);
        }
        w
    }
    fn set_draw(&mut self, i: usize) {
        self.draw = i;
    }
}

fn sha_le(v: &[f64]) -> String {
    let b: Vec<u8> = v.iter().flat_map(|x| x.to_le_bytes()).collect();
    crate::provenance::sha256_hex(&b)
}

fn hex_u64(v: &Value) -> u64 {
    v.as_str()
        .and_then(|s| u64::from_str_radix(s, 16).ok())
        .unwrap_or(0)
}

/// The platform experiment on NumPy's normal stream: the ziggurat's `exp` and `log1p` values of
/// this machine against those of the Windows machine that produced the reference, and a replay
/// of the stream with the Windows values substituted (which must reproduce NumPy's Windows stream
/// bit for bit if the libm values are the only difference).
pub fn ziggurat(g: &Golden) -> Result<Report, EngineError> {
    let t = g.load("ziggurat.json")?;
    let mut rep = Report::new("ziggurat platform experiment");
    let mut align = Acc::exact(
        "ZIG-ALIGN",
        "replay consumes the recorded exp/log1p calls at the same draw and layer, all of them",
    );
    let mut replay = Acc::exact(
        "ZIG-REPLAY",
        "SHA-256 of 10^6 draws with the Windows exp/log1p values substituted equals NumPy's Windows stream",
    );
    let mut native = Acc::info(
        "ZIG-NATIVE-DRAWS",
        "draws of the native stream (this platform's libm) that differ from the replayed Windows stream",
    );
    let target = format!("{} {}", std::env::consts::OS, std::env::consts::ARCH);
    for s in t["seeds"].as_array().into_iter().flatten() {
        let seed = s["seed"].as_u64().unwrap_or(0);
        let n = s["n"].as_u64().unwrap_or(0) as usize;
        let wedge: Vec<(usize, usize, u64)> = s["wedge"]
            .as_array()
            .into_iter()
            .flatten()
            .map(|e| {
                (
                    e[0].as_u64().unwrap_or(0) as usize,
                    e[1].as_u64().unwrap_or(0) as usize,
                    hex_u64(&e[2]),
                )
            })
            .collect();
        let tail: Vec<(usize, u64, u64)> = s["tail"]
            .as_array()
            .into_iter()
            .flatten()
            .map(|e| {
                (
                    e[0].as_u64().unwrap_or(0) as usize,
                    hex_u64(&e[1]),
                    hex_u64(&e[2]),
                )
            })
            .collect();
        let want = s["sha256_le_f8"].as_str().unwrap_or("");
        let mut rp = Replay {
            wedge: &wedge,
            tail: &tail,
            wi: 0,
            ti: 0,
            second: false,
            draw: 0,
            misaligned: 0,
            n_exp_diff: 0,
            max_ulp_exp: 0,
            flips: Vec::new(),
            n_log: 0,
            n_log_diff: 0,
            max_ulp_log: 0,
            first_log_diff: None,
        };
        let mut gr = crate::calibration::Generator::new(seed as u128);
        let rv = gr.bg.standard_normal_vec_with(n, &mut rp);
        let mut gn = crate::calibration::Generator::new(seed as u128);
        let nv = gn
            .bg
            .standard_normal_vec_with(n, &mut amcrax_numerics::random::NativeMath);
        let case = format!("seed {seed}");
        align.add_bool(
            &case,
            rp.misaligned == 0 && rp.wi == wedge.len() && rp.ti == tail.len(),
            || {
                format!(
                    "misaligned {}, wedge {}/{}, tail {}/{}",
                    rp.misaligned,
                    rp.wi,
                    wedge.len(),
                    rp.ti,
                    tail.len()
                )
            },
        );
        let rsha = sha_le(&rv);
        replay.add_bool(&case, rsha == want, || format!("replay {rsha} want {want}"));
        let ndiff = rv
            .iter()
            .zip(&nv)
            .filter(|(a, b)| a.to_bits() != b.to_bits())
            .count();
        let first = rv
            .iter()
            .zip(&nv)
            .position(|(a, b)| a.to_bits() != b.to_bits());
        native.add(&case, ndiff as f64, 0.0);
        let nsha = sha_le(&nv);
        let branch = match first {
            None => "none".to_string(),
            Some(i) => {
                if let Some((d, l)) = rp.flips.iter().find(|f| f.0 == i) {
                    format!(
                        "wedge test of layer {l} at draw {d}: exp() differs and flips the acceptance"
                    )
                } else if rp.first_log_diff == Some(i) {
                    "tail (layer 0): log1p() differs and changes the returned value".to_string()
                } else {
                    "a later draw shifted by an earlier difference (see the counts)".to_string()
                }
            }
        };
        rep.findings.push(format!(
            "{case} on {target}: native SHA-256 {} the Windows reference ({}); exp() differs from the Windows value in \
             {} of {} wedge tests (max {} ulp) and flips {} acceptance decisions; log1p() differs in {} of {} tail calls \
             (max {} ulp); {} of {} draws differ, the first at draw {} ({}).",
            if nsha == want { "equals" } else { "differs from" },
            t["platform"].as_str().unwrap_or("?"),
            rp.n_exp_diff,
            wedge.len(),
            rp.max_ulp_exp,
            rp.flips.len(),
            rp.n_log_diff,
            rp.n_log,
            rp.max_ulp_log,
            ndiff,
            n,
            first.map(|i| i.to_string()).unwrap_or_else(|| "none".into()),
            branch
        ));
    }
    rep.push(align);
    rep.push(replay);
    rep.push(native);
    Ok(rep)
}

// ===================================================================================== catalyst economics
fn design_kw(a: &Value) -> crate::catalyst_econ::DesignKw {
    use crate::catalyst_econ::{DesignKw, U};
    let mut k = DesignKw::default();
    if let Some(m) = a["mode"].as_str() {
        k.mode = m.into();
    }
    if !a["U_case"].is_null() {
        k.u = U::from_json(&a["U_case"]);
    }
    if let Some(h) = a["hi"].as_bool() {
        k.hi = h;
    }
    if !a["scenario"].is_null() {
        k.scenario = a["scenario"].clone();
    }
    if let Some(o) = a["econ_overrides"].as_object() {
        k.econ_overrides = Some(o.clone());
    }
    if let Some(v) = opt(a, "kinetic_factor") {
        k.kinetic_factor = v;
    }
    k.w_kg = opt(a, "W_kg");
    k
}

fn opt_json(v: Option<Value>) -> Value {
    v.unwrap_or(Value::Null)
}

fn econ_call(e: &crate::catalyst_econ::Econ, f: &str, a: &Value) -> Result<Value, EngineError> {
    use crate::catalyst_econ as ce;
    let s = |k: &str| a[k].as_str().unwrap_or("").to_string();
    let fx = e.ctx.econ.reference.fx_sgd_per_usd;
    Ok(match f {
        "price_table" => Value::Array(e.price_table()?),
        "published_tea_prices" => Value::Array(e.published_tea_prices()?),
        "price" => json!(e.price(&s("name"), &s("scenario"))?),
        "ru_metal_floor" => json!(e.ru_metal_floor(num(&a["wt_pct_ru"]), None)?),
        "catalyst_cost" => e.catalyst_cost(
            num(&a["W_kg"]),
            num(&a["price"]),
            num(&a["lifetime_yr"]),
            num(&a["annual_h2_kg"]),
        ),
        "state" => e
            .state(
                num(&a["T_C"]),
                ce::P_BAR,
                ce::X_TARGET,
                a["hi"].as_bool().unwrap_or(true),
            )?
            .v
            .clone(),
        "hx_size_ratio" => {
            json!(e.hx_size_ratio(num(&a["fehe_tci_USD"]), num(&a["nh3_feed_kmol_h"]))?)
        }
        "design" => opt_json(e.design(
            &s("cid"),
            num(&a["T_C"]),
            num(&a["price"]),
            num(&a["lifetime_yr"]),
            &design_kw(a),
            None,
        )?),
        "optimise" => opt_json(e.optimise(
            &s("cid"),
            num(&a["price"]),
            num(&a["lifetime_yr"]),
            a["refine"].as_bool().unwrap_or(true),
            None,
            &design_kw(a),
        )?),
        "compare" => {
            let kw = design_kw(a);
            let lo = e.optimise(
                &s("low"),
                e.price(
                    &crate::catalyst::catalyst(&s("low"))?.price_key.to_string(),
                    "central",
                )?,
                2.0,
                true,
                None,
                &kw,
            )?;
            let rf = e.optimise(
                &s("ref"),
                e.price(
                    &crate::catalyst::catalyst(&s("ref"))?.price_key.to_string(),
                    "central",
                )?,
                2.0,
                true,
                None,
                &kw,
            )?;
            match (lo, rf) {
                (Some(l), Some(r)) => ce::compare(&l, &r, fx)?,
                _ => Value::Null,
            }
        }
        "kinetics_label" => {
            let ids: Vec<String> = a["cids"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|v| v.as_str().map(String::from))
                .collect();
            let refs: Vec<&str> = ids.iter().map(String::as_str).collect();
            ce::kinetics_label(e, &refs)?
        }
        other => {
            return Err(EngineError::data(
                "catalyst_economics.json",
                format!("unknown function {other}"),
            ));
        }
    })
}

const CE_NOTE: &str = "relative to max(|x|, 1); 1e-5 is the catalyst-mass gate of the PFR mass search (brentq xtol 1e-6 \
                       on W), inherited by the catalyst cost, the mass-driven reactor CAPEX and the LCOH";

/// Catalyst economics (`research/catalyst_economics.py`): direct calls, the cost table and the
/// break-even searches of `scripts/research/catalyst_economics.py`, and the stored CSV tables.
pub fn catalyst_economics(
    g: &Golden,
    ctx: &crate::catalyst::Ctx,
    root: &Path,
) -> Result<Report, EngineError> {
    use crate::catalyst_econ as ce;
    use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
    let t = g.load("catalyst_economics.json")?;
    let e = ce::Econ::new(ctx, root)?;
    let fx = ctx.econ.reference.fx_sgd_per_usd;
    let mut rep = Report::new("catalyst economics");
    let mut calls = TreeAcc::new(
        "CE-CALL",
        "catalyst_economics functions (direct calls)",
        1e-5,
        CE_NOTE,
    );
    let mut exact = TreeAcc::new(
        "CE-CALL-NOMASS",
        "prices, costs, states, size ratios (no catalyst mass)",
        1e-9,
        "relative to max(|x|, 1)",
    );
    let mut prose = Acc::exact("CE-PROSE", "static prose fields (counted)");
    let mut outcome = Acc::exact("CE-CALL-OUTCOME", "success, or the same exception class");
    for (i, c) in t["calls"].as_array().into_iter().flatten().enumerate() {
        let f = c["fn"].as_str().unwrap_or("");
        let case = format!("{f}#{i} {}", c["args"]);
        match (py_error(&c["out"]), econ_call(&e, f, &c["args"])) {
            (Some(cls), Err(er)) => outcome.add_bool(&case, error_ok(cls, &er), || {
                format!("python {cls}, rust {er}")
            }),
            (Some(cls), Ok(_)) => outcome.add_bool(&case, false, || format!("python raised {cls}")),
            (None, Err(er)) => outcome.add_bool(&case, false, || format!("rust failed: {er}")),
            (None, Ok(r)) => {
                outcome.add_bool(&case, true, String::new);
                let acc = if matches!(f, "design" | "optimise" | "compare") {
                    &mut calls
                } else {
                    &mut exact
                };
                partial_tree(acc, &mut prose, &case, &c["out"], &r, 1.0);
            }
        }
    }
    exact.push(&mut rep);
    calls.push(&mut rep);
    rep.push(outcome);
    // ---- cost table (section 2 of the script)
    let mut cost = TreeAcc::new(
        "CE-COST-TABLE",
        "cost table: cost-optimal (reference mode) and fixed 100 kg designs",
        1e-5,
        CE_NOTE,
    );
    let asp = |cid: &str,
               hi: bool|
     -> Result<crate::process::result::SimulationResult, EngineError> {
        let tag = match cid {
            "ru_kum_temkin_pyzhev" => "kum_T499",
            "nire_ceo2_5ni1ru_lucentini_lhhw" => "luc5_T572",
            "nire_ceo2_2p5ni0p5ru_lucentini_lhhw" => "luc25_T576",
            "ni_takahashi_microkinetic" => "tni_T594",
            _ => "tru_T522",
        };
        let rel = format!(
            "results/research/aspen_kinetic/ci_{tag}_P20_W100_{}.json",
            if hi { "hi" } else { "nohi" }
        );
        let v = read_json(root, &rel)?;
        crate::process::result::SimulationResult::from_sorted_value(&v["aspen"]["flowsheet_result"])
    };
    let mut asp_states = std::collections::HashMap::new();
    let refkw = ce::DesignKw {
        mode: "reference".into(),
        ..ce::DesignKw::default()
    };
    for r in t["cost_table"].as_array().into_iter().flatten() {
        let cid = r["catalyst_id"].as_str().unwrap_or("");
        let p = num(&r["price_USD_per_kg"]);
        let l = num(&r["lifetime_yr"]);
        let case = format!("{cid}/{}/{l}", r["price_case"].as_str().unwrap_or(""));
        if !asp_states.contains_key(cid) {
            let st =
                e.state_from_result(&asp(cid, true)?, 20.0, crate::catalyst::FURNACE_EFFICIENCY)?;
            asp_states.insert(cid.to_string(), st);
        }
        let st = &asp_states[cid];
        let o = e.optimise(cid, p, l, true, None, &refkw)?;
        partial_tree(
            &mut cost,
            &mut prose,
            &format!("{case}/costopt"),
            &r["costopt"],
            &opt_json(o),
            1.0,
        );
        let fkw = ce::DesignKw {
            w_kg: Some(100.0),
            ..refkw.clone()
        };
        let fxd = e.design(cid, num(&st.v["T_C"]), p, l, &fkw, Some(st))?;
        partial_tree(
            &mut cost,
            &mut prose,
            &format!("{case}/fixed100kg"),
            &r["fixed100kg"],
            &opt_json(fxd),
            1.0,
        );
    }
    cost.push(&mut rep);
    // ---- break-even searches (section 4)
    let mut be = TreeAcc::new(
        "CE-BREAKEVEN",
        "cost-optimal designs and their comparison",
        1e-5,
        CE_NOTE,
    );
    let mut bp = Acc::abs(
        "CE-BE-PRICE-REOPT",
        "re-optimised break-even price, USD/kg (brentq xtol 0.05 on full re-optimisations)",
        0.05,
    )
    .note("absolute: both roots satisfy the same brentq stopping rule (xtol 0.05 USD/kg)");
    let mut bl = Acc::abs(
        "CE-BE-LIFE-REOPT",
        "re-optimised break-even lifetime, yr (brentq xtol 1e-3)",
        1e-3,
    );
    let mut bt = Acc::exact(
        "CE-BE-T",
        "temperature of the re-optimised design at the break-even price; existence of each root",
    );
    let mut f0a = Acc::rel(
        "CE-BE-F0",
        "LCOH(low, zero catalyst price) - LCOH(ref), USD/kg",
        1e-5,
    );
    let pcen = |cid: &str| -> Result<f64, EngineError> {
        e.price(crate::catalyst::catalyst(cid)?.price_key, "central")
    };
    for r in t["breakeven"].as_array().into_iter().flatten() {
        let mode = r["mode"].as_str().unwrap_or("");
        let cid = r["catalyst_id"].as_str().unwrap_or("");
        let case = format!("{mode}/{cid}");
        let kw = ce::DesignKw {
            mode: mode.into(),
            ..ce::DesignKw::default()
        };
        let rf = e
            .optimise(
                crate::catalyst::REFERENCE_NI,
                pcen(crate::catalyst::REFERENCE_NI)?,
                2.0,
                true,
                None,
                &kw,
            )?
            .unwrap_or(Value::Null);
        let lo = e
            .optimise(cid, pcen(cid)?, 2.0, true, None, &kw)?
            .unwrap_or(Value::Null);
        partial_tree(
            &mut be,
            &mut prose,
            &format!("{case}/low"),
            &r["low"],
            &lo,
            1.0,
        );
        partial_tree(
            &mut be,
            &mut prose,
            &format!("{case}/ref"),
            &r["ref"],
            &rf,
            1.0,
        );
        partial_tree(
            &mut be,
            &mut prose,
            &format!("{case}/compare"),
            &r["compare"],
            &ce::compare(&lo, &rf, fx)?,
            1.0,
        );
        let l_ref = num(&rf["lcoh_USD_per_kg"]);
        let f = |p: f64| -> Result<f64, EngineError> {
            let o = e
                .optimise(cid, p, 2.0, true, None, &kw)?
                .unwrap_or(Value::Null);
            Ok(num(&o["lcoh_USD_per_kg"]) - l_ref)
        };
        let f0 = f(0.0)?;
        f0a.add(
            &case,
            f0,
            num(&r["lcoh_low_at_zero_price_minus_ref_USD_per_kg"]),
        );
        let root_of = |fun: &dyn Fn(f64) -> Result<f64, EngineError>,
                       a: f64,
                       b: f64,
                       xtol: f64|
         -> Result<Option<f64>, EngineError> {
            match brentq_try(fun, a, b, BrentOptions::with_xtol(xtol)) {
                Ok(r) => Ok(Some(r.x)),
                Err(BrentError::Function(er)) => Err(er),
                Err(_) => Ok(None),
            }
        };
        let p_re = if f0 < 0.0 && 0.0 < f(2e5)? {
            root_of(&f, 0.0, 2e5, 0.05)?
        } else {
            None
        };
        let py_p = &r["breakeven_price_reoptimised_USD_per_kg"];
        bt.add_bool(
            &format!("{case}/price exists"),
            p_re.is_some() == !py_p.is_null(),
            || format!("rust {p_re:?} python {py_p}"),
        );
        if let (Some(pr), false) = (p_re, py_p.is_null()) {
            bp.add(&case, pr, num(py_p));
            let o = e
                .optimise(cid, pr, 2.0, true, None, &kw)?
                .unwrap_or(Value::Null);
            bt.add_bool(
                &format!("{case}/T"),
                num(&o["T_C"]) == num(&r["T_at_reoptimised_breakeven_C"]),
                || {
                    format!(
                        "rust {} python {}",
                        o["T_C"], r["T_at_reoptimised_breakeven_C"]
                    )
                },
            );
        }
        let gfun = |l: f64| -> Result<f64, EngineError> {
            let o = e
                .optimise(cid, pcen(cid)?, l, true, None, &kw)?
                .unwrap_or(Value::Null);
            Ok(num(&o["lcoh_USD_per_kg"]) - l_ref)
        };
        let l_re = if gfun(200.0)? < 0.0 && 0.0 < gfun(0.05)? {
            root_of(&gfun, 0.05, 200.0, 1e-3)?
        } else {
            None
        };
        let py_l = &r["breakeven_lifetime_reoptimised_yr"];
        bt.add_bool(
            &format!("{case}/lifetime exists"),
            l_re.is_some() == !py_l.is_null(),
            || format!("rust {l_re:?} python {py_l}"),
        );
        if let (Some(lr), false) = (l_re, py_l.is_null()) {
            bl.add(&case, lr, num(py_l));
        }
    }
    be.push(&mut rep);
    rep.push(f0a);
    rep.push(bp);
    rep.push(bl);
    rep.push(bt);
    rep.push(prose);
    // ---- the stored CSV tables of the script
    let mut sc = Acc::rel("CE-STORED-COST", "stored catalyst_cost_table.csv: cost-optimal T, W, catalyst cost, LCOH; fixed-100 kg costs", 1e-5).note(CE_NOTE);
    let rows = read_csv_rows(
        root,
        "results/research/catalyst_economics/catalyst_cost_table.csv",
    )?;
    for r in t["cost_table"].as_array().into_iter().flatten() {
        let cid = r["catalyst_id"].as_str().unwrap_or("");
        let case = r["price_case"].as_str().unwrap_or("");
        let l = num(&r["lifetime_yr"]);
        let Some(s) = rows.iter().find(|x| {
            x.get("catalyst_id").map(String::as_str) == Some(cid)
                && x.get("price_case").map(String::as_str) == Some(case)
                && x.get("lifetime_yr").and_then(|v| v.parse::<f64>().ok()) == Some(l)
        }) else {
            sc.add_bool(&format!("{cid}/{case}/{l}"), false, || {
                "row not in the stored table".into()
            });
            continue;
        };
        let pairs = [
            ("costopt_T_C", &r["costopt"]["T_C"]),
            ("costopt_W_kg", &r["costopt"]["W_kg"]),
            (
                "costopt_catalyst_USD_per_kg_H2",
                &r["costopt"]["catalyst_cost"]["USD_per_kg_H2"],
            ),
            ("costopt_lcoh_USD_per_kg", &r["costopt"]["lcoh_USD_per_kg"]),
            (
                "fixed100kg_catalyst_USD_per_kg_H2",
                &r["fixed100kg"]["catalyst_cost"]["USD_per_kg_H2"],
            ),
            (
                "fixed100kg_lcoh_USD_per_kg",
                &r["fixed100kg"]["lcoh_USD_per_kg"],
            ),
        ];
        for (col, v) in pairs {
            let st: f64 = s.get(col).and_then(|x| x.parse().ok()).unwrap_or(f64::NAN);
            sc.add_scaled(&format!("{cid}/{case}/{l}/{col}"), num(v), st, 1.0);
        }
    }
    rep.push(sc);
    Ok(rep)
}

/// A CSV file as rows of strings by header.
fn read_csv_rows(
    root: &Path,
    rel: &str,
) -> Result<Vec<std::collections::BTreeMap<String, String>>, EngineError> {
    let text = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    let mut lines = text.lines();
    let parse = |l: &str| -> Vec<String> {
        let mut out = Vec::new();
        let mut cur = String::new();
        let mut q = false;
        let mut it = l.chars().peekable();
        while let Some(c) = it.next() {
            match (c, q) {
                ('"', true) if it.peek() == Some(&'"') => {
                    cur.push('"');
                    it.next();
                }
                ('"', _) => q = !q,
                (',', false) => out.push(std::mem::take(&mut cur)),
                _ => cur.push(c),
            }
        }
        out.push(cur);
        out
    };
    let head = parse(lines.next().unwrap_or(""));
    Ok(lines
        .filter(|l| !l.trim().is_empty())
        .map(|l| head.iter().cloned().zip(parse(l)).collect())
        .collect())
}
