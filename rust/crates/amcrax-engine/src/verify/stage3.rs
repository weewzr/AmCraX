//! Stage 3 checks: economics (reference CAPEX, `evaluate`, break-even, legacy correlation, the
//! stored research results), carbon pricing and the uncertainty-quantification estimators (golden
//! tables in `rust/golden/stage3`).
//!
//! Python results are dicts; the Rust functions return the same dicts as JSON, and the comparison
//! walks both trees: every numeric leaf under the relative gate, every key, string (notes,
//! labels, hashes), boolean and `None` identical.

use super::{Acc, Golden, Report, error_matches, num, py_error};
use crate::economics::lcoh::{
    EconAssumptions, LcohInput, breakeven_ammonia_price, compute_lcoh, crf,
};
use crate::economics::reference::{EconomicsData, RefCapexArgs, crf_ref};
use crate::economics::singapore::{
    Overrides, Scenario, Summary, breakeven_nh3_price, default_electricity_usd_per_kwh,
    equipment_capex, evaluate, irr,
};
use crate::error::EngineError;
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;

pub(crate) fn arr(v: &Value) -> &[Value] {
    v.as_array().map(Vec::as_slice).unwrap_or(&[])
}

/// A leaf of a flattened JSON tree.
#[derive(Debug, Clone, PartialEq)]
pub(crate) enum Leaf {
    Num(f64),
    Other(Value),
}

/// Flatten a JSON tree into `path -> leaf` (`"nan"`, `"inf"`, `"-inf"` strings are numbers).
pub(crate) fn flatten(v: &Value) -> BTreeMap<String, Leaf> {
    fn go(v: &Value, p: &str, out: &mut BTreeMap<String, Leaf>) {
        match v {
            Value::Object(m) => {
                if m.is_empty() {
                    out.insert(
                        p.to_string(),
                        Leaf::Other(Value::Object(Default::default())),
                    );
                }
                for (k, x) in m {
                    go(x, &format!("{p}/{k}"), out);
                }
            }
            Value::Array(a) => {
                if a.is_empty() {
                    out.insert(p.to_string(), Leaf::Other(Value::Array(vec![])));
                }
                for (i, x) in a.iter().enumerate() {
                    go(x, &format!("{p}[{i}]"), out);
                }
            }
            Value::Number(n) => {
                out.insert(p.to_string(), Leaf::Num(n.as_f64().unwrap_or(f64::NAN)));
            }
            Value::String(s) if s == "nan" || s == "inf" || s == "-inf" => {
                out.insert(p.to_string(), Leaf::Num(num(v)));
            }
            other => {
                out.insert(p.to_string(), Leaf::Other(other.clone()));
            }
        }
    }
    let mut out = BTreeMap::new();
    go(v, "", &mut out);
    out
}

/// Compare two JSON trees: numbers under `nums`, keys and other leaves under `exact`.
/// With `python_keys_only` the Rust tree may hold more keys (partial Python records).
pub(crate) fn compare_tree(
    nums: &mut Acc,
    exact: &mut Acc,
    case: &str,
    rust: &Value,
    python: &Value,
    python_keys_only: bool,
) {
    let r = flatten(rust);
    let p = flatten(python);
    let mut missing = Vec::new();
    let mut other_bad = Vec::new();
    for (k, pv) in &p {
        match (r.get(k), pv) {
            (None, _) => missing.push(k.clone()),
            (Some(Leaf::Num(a)), Leaf::Num(b)) => nums.add(&format!("{case} {k}"), *a, *b),
            (Some(a), b) => {
                if a != b {
                    other_bad.push(format!("{k}: rust {a:?} python {b:?}"));
                }
            }
        }
    }
    let extra: Vec<&String> = if python_keys_only {
        Vec::new()
    } else {
        r.keys().filter(|k| !p.contains_key(*k)).collect()
    };
    let ok = missing.is_empty() && other_bad.is_empty() && extra.is_empty();
    exact.add_bool(case, ok, || {
        format!(
            "missing in rust {:?}; extra in rust {:?}; differing {:?}",
            &missing[..missing.len().min(5)],
            &extra[..extra.len().min(5)],
            &other_bad[..other_bad.len().min(3)]
        )
    });
}

fn add_err_case<T>(acc: &mut Acc, case: &str, py: &str, r: &Result<T, EngineError>) {
    let ok = matches!(r, Err(e) if error_matches(py, e));
    acc.add_bool(case, ok, || match r {
        Ok(_) => format!("python raised {py}, rust returned a value"),
        Err(e) => format!("python raised {py}, rust error {e}"),
    });
}

fn overrides_of(v: &Value) -> Overrides {
    v.as_object().cloned().unwrap_or_default()
}

fn opt_num(v: &Value) -> Option<f64> {
    if v.is_null() { None } else { Some(num(v)) }
}

/// Compare an optional number (`None` on both sides is a match).
fn add_opt(nums: &mut Acc, exact: &mut Acc, case: &str, rust: Option<f64>, python: &Value) {
    match (rust, opt_num(python)) {
        (Some(a), Some(b)) => {
            nums.add(case, a, b);
            exact.add_bool(case, true, String::new);
        }
        (None, None) => exact.add_bool(case, true, String::new),
        (a, b) => exact.add_bool(case, false, || format!("rust {a:?} python {b:?}")),
    }
}

fn summaries(t: &Value) -> Result<BTreeMap<String, Summary>, EngineError> {
    let mut out = BTreeMap::new();
    for (k, v) in t["summaries"].as_object().into_iter().flatten() {
        out.insert(k.clone(), Summary::from_summary_json(v)?);
    }
    Ok(out)
}

fn get_summary<'a>(
    s: &'a BTreeMap<String, Summary>,
    name: &str,
) -> Result<&'a Summary, EngineError> {
    s.get(name)
        .ok_or_else(|| EngineError::data("economics.json", format!("summary {name}")))
}

fn read_json(root: &Path, rel: &str) -> Result<Value, EngineError> {
    let p = rel.split('/').fold(root.to_path_buf(), |p, s| p.join(s));
    let b = std::fs::read(&p).map_err(|e| EngineError::data(rel, e.to_string()))?;
    serde_json::from_slice(&b).map_err(|e| EngineError::data(rel, e.to_string()))
}

fn at_path<'a>(v: &'a Value, path: &[Value]) -> &'a Value {
    path.iter().fold(v, |v, k| match k {
        Value::String(s) => &v[s.as_str()],
        Value::Number(n) => &v[n.as_u64().unwrap_or(u64::MAX) as usize],
        _ => &Value::Null,
    })
}

/// Execute a stored-result recipe (see `generate_stage3_golden.py`, `recipe_value`).
fn run_recipe(
    d: &EconomicsData,
    s: &BTreeMap<String, Summary>,
    root: &Path,
    r: &Value,
) -> Result<Value, EngineError> {
    match r["kind"].as_str().unwrap_or("") {
        "evaluate" => {
            let e = evaluate(
                d,
                get_summary(s, r["summary"].as_str().unwrap_or(""))?,
                &Scenario::from_json(&r["scenario"])?,
                &overrides_of(&r["overrides"]),
            )?;
            Ok(at_path(&e, arr(&r["output"])).clone())
        }
        "breakeven" => {
            let v = breakeven_nh3_price(
                d,
                get_summary(s, r["summary"].as_str().unwrap_or(""))?,
                num(&r["target"]),
                &overrides_of(&r["overrides"]),
                r["metric"].as_str().unwrap_or("lcoh_USD_per_kg"),
            )?;
            Ok(crate::economics::jo(v))
        }
        "diff" => {
            let a = num(&run_recipe(d, s, root, &r["a"])?);
            let b = num(&run_recipe(d, s, root, &r["b"])?);
            Ok(crate::economics::jf(a - b))
        }
        "legacy" => {
            let res = read_json(root, r["file"].as_str().unwrap_or(""))?;
            let inp = LcohInput::from_result_json(&res)?;
            let kw: Vec<(String, Value)> = overrides_of(&r["assumptions"]).into_iter().collect();
            let a = EconAssumptions::with_overrides(d, &kw)?;
            let out = compute_lcoh(d, &inp, &a)?;
            Ok(at_path(&out, arr(&r["output"])).clone())
        }
        k => Err(EngineError::data(
            "economics.json",
            format!("recipe kind {k}"),
        )),
    }
}

/// Economics: reference CAPEX, `evaluate`, break-even, legacy correlation, stored results.
pub fn economics(golden: &Golden, d: &EconomicsData, root: &Path) -> Result<Report, EngineError> {
    let mut rep = Report::new("economics");
    let t = golden.load("economics.json")?;
    let s = summaries(&t)?;

    // ---------------------------------------------------------------------------- evaluate
    let mut ev = Acc::rel(
        "economics.evaluate",
        "singapore.evaluate: every numeric output (LCOH, REC, breakdown, annual costs, fixed-opex detail, \
         CAPEX items, NPV, IRR, payback, SGD fields, assumptions), all capex modes and override branches",
        1e-12,
    )
    .note("relative; identical operation order (Python sum as Neumaier), only libm pow may differ by an ulp");
    let mut evx = Acc::exact(
        "economics.evaluate_structure",
        "evaluate: identical keys, strings (notes, cost basis, provenance hash), booleans and None",
    );
    let mut eve = Acc::exact(
        "economics.evaluate_errors",
        "evaluate: KeyError (unknown override, scenario), ValueError (options, pydantic), ZeroDivisionError",
    );
    for c in arr(&t["evaluate"]) {
        let case = format!(
            "{} {} {}",
            c["summary"].as_str().unwrap_or(""),
            c["scenario"],
            c["overrides"]
        );
        let sm = get_summary(&s, c["summary"].as_str().unwrap_or(""))?;
        let r = Scenario::from_json(&c["scenario"])
            .and_then(|sc| evaluate(d, sm, &sc, &overrides_of(&c["overrides"])));
        match (py_error(&c["output"]), r) {
            (Some(pe), r) => add_err_case(&mut eve, &case, pe, &r),
            (None, Err(e)) => eve.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(v)) => {
                eve.add_bool(&case, true, String::new);
                compare_tree(&mut ev, &mut evx, &case, &v, &c["output"], false);
            }
        }
    }
    rep.push(ev);
    rep.push(evx);
    rep.push(eve);

    // ---------------------------------------------------------------------------- extract_summary
    let mut ex = Acc::rel(
        "economics.extract_summary",
        "extract_summary of every stored SimulationResult (results/simulations/*.json)",
        0.0,
    )
    .note("bitwise: the numbers are read, not computed (cooling duty: abs)");
    let mut exx = Acc::exact(
        "economics.extract_summary_structure",
        "extract_summary: keys and None",
    );
    for c in arr(&t["extract_summary"]) {
        let file = c["file"].as_str().unwrap_or("");
        let r = read_json(root, file).and_then(|v| Summary::extract(&v));
        match (py_error(&c["summary"]), r) {
            (Some(pe), r) => add_err_case(&mut exx, file, pe, &r),
            (None, Err(e)) => exx.add_bool(file, false, || format!("rust error {e}")),
            (None, Ok(sm)) => {
                compare_tree(&mut ex, &mut exx, file, &sm.to_json(), &c["summary"], false)
            }
        }
    }
    rep.push(ex);
    rep.push(exx);

    // ---------------------------------------------------------------------------- break-even
    let mut be = Acc::rel(
        "economics.breakeven_nh3_price",
        "breakeven_nh3_price: LCOH and REC targets, overrides (two evaluations, linear solve)",
        1e-12,
    );
    let mut bex = Acc::exact(
        "economics.breakeven_decisions",
        "breakeven_nh3_price: None (unreachable) and errors identical",
    );
    for c in arr(&t["breakeven"]) {
        let case = format!(
            "{} target={} {} {}",
            c["summary"].as_str().unwrap_or(""),
            c["target"],
            c["overrides"],
            c["metric"].as_str().unwrap_or("")
        );
        let r = breakeven_nh3_price(
            d,
            get_summary(&s, c["summary"].as_str().unwrap_or(""))?,
            num(&c["target"]),
            &overrides_of(&c["overrides"]),
            c["metric"].as_str().unwrap_or("lcoh_USD_per_kg"),
        );
        match (py_error(&c["value"]), r) {
            (Some(pe), r) => add_err_case(&mut bex, &case, pe, &r),
            (None, Err(e)) => bex.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(v)) => add_opt(&mut be, &mut bex, &case, v, &c["value"]),
        }
    }
    rep.push(be);
    rep.push(bex);

    // ---------------------------------------------------------------------------- CAPEX
    let mut rc = Acc::rel(
        "economics.reference_capex",
        "reference_capex (cho2026_itemised_v1): exponent, multiplier, location factor, exclusions, \
         catalyst-mass reactor driver, item size ratios",
        1e-12,
    );
    let mut rcx = Acc::exact(
        "economics.reference_capex_structure",
        "reference_capex: keys, items, basis text, errors",
    );
    for c in arr(&t["reference_capex"]) {
        let kw = &c["kwargs"];
        let feed = num(&c["nh3_feed_kmol_h"]);
        let case = format!("feed={feed} {kw}");
        let mut a = RefCapexArgs::new(feed);
        a.catalyst_mass_kg = opt_num(&kw["catalyst_mass_kg"]);
        a.reactor_size_driver = kw["reactor_size_driver"].as_str().map(str::to_string);
        a.item_size_ratio = kw["item_size_ratio"]
            .as_object()
            .map(|m| m.iter().map(|(k, v)| (k.clone(), num(v))).collect());
        a.exclude = arr(&kw["exclude"])
            .iter()
            .filter_map(|x| x.as_str().map(str::to_string))
            .collect();
        a.exponent = opt_num(&kw["exponent"]);
        if let Some(m) = opt_num(&kw["capex_multiplier"]) {
            a.capex_multiplier = m;
        }
        a.location_factor = opt_num(&kw["location_factor"]);
        let r = d.reference_capex(&a);
        match (py_error(&c["output"]), r) {
            (Some(pe), r) => add_err_case(&mut rcx, &case, pe, &r),
            (None, Err(e)) => rcx.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(v)) => compare_tree(&mut rc, &mut rcx, &case, &v, &c["output"], false),
        }
    }
    let ic = d.reference_item_costs()?.to_json();
    compare_tree(
        &mut rc,
        &mut rcx,
        "reference_item_costs",
        &ic,
        &t["reference_item_costs"],
        false,
    );
    rc.add(
        "reference_catalyst_mass_kg",
        d.reference_catalyst_mass_kg()?,
        num(&t["reference_catalyst_mass_kg"]),
    );
    rep.push(rc);
    rep.push(rcx);

    let mut eq = Acc::rel(
        "economics.equipment_capex",
        "equipment_capex (Phase 1 Farokhi basis): feed, location factor, exponent, multiplier",
        1e-12,
    );
    let mut eqx = Acc::exact(
        "economics.equipment_capex_structure",
        "equipment_capex: keys and basis",
    );
    for c in arr(&t["equipment_capex"]) {
        let case = format!(
            "feed={} lf={} n={} m={}",
            c["nh3_feed_kmol_h"], c["location_factor"], c["exponent"], c["capex_multiplier"]
        );
        let kw = vec![(
            "capex_multiplier".to_string(),
            c["capex_multiplier"].clone(),
        )];
        let a = EconAssumptions::with_overrides(d, &kw)?;
        let v = equipment_capex(
            d,
            num(&c["nh3_feed_kmol_h"]),
            &a,
            opt_num(&c["location_factor"]),
            opt_num(&c["exponent"]),
        )?;
        compare_tree(&mut eq, &mut eqx, &case, &v, &c["output"], false);
    }
    rep.push(eq);
    rep.push(eqx);

    // ---------------------------------------------------------------------------- helpers
    let mut hp = Acc::rel(
        "economics.helpers",
        "capital recovery factors (lcoh.crf, reference._crf), IRR bisection, default Singapore electricity price",
        1e-12,
    );
    let mut hpx = Acc::exact(
        "economics.helpers_decisions",
        "crf errors (life <= 0), IRR None",
    );
    hp.add(
        "default_electricity_USD_per_kWh",
        default_electricity_usd_per_kwh(d)?,
        num(&t["default_electricity_USD_per_kWh"]),
    );
    for c in arr(&t["crf"]) {
        let (i, n) = (num(&c["i"]), num(&c["n"]));
        let case = format!("i={i} n={n}");
        let r = crf(i, n);
        match (py_error(&c["lcoh_crf"]), r) {
            (Some(pe), r) => add_err_case(&mut hpx, &case, pe, &r),
            (None, Err(e)) => hpx.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(v)) => hp.add(&format!("lcoh.crf {case}"), v, num(&c["lcoh_crf"])),
        }
        if !c["reference_crf"].is_null() {
            hp.add(
                &format!("reference._crf {case}"),
                crf_ref(i, n),
                num(&c["reference_crf"]),
            );
        }
    }
    for c in arr(&t["irr"]) {
        let case = format!("irr capex={} net={} n={}", c["capex"], c["net"], c["n"]);
        let v = irr(
            num(&c["capex"]),
            num(&c["net"]),
            c["n"].as_i64().unwrap_or(0),
        );
        add_opt(&mut hp, &mut hpx, &case, v, &c["value"]);
    }
    rep.push(hp);
    rep.push(hpx);

    // ---------------------------------------------------------------------------- legacy
    let mut lg = Acc::rel(
        "economics.legacy_lcoh",
        "lcoh.compute_lcoh (legacy correlation; Ahmad, Chopra, Farokhi, fixed CAPEX; heat modes) and \
         breakeven_ammonia_price on stored SimulationResults",
        1e-12,
    );
    let mut lgx = Acc::exact(
        "economics.legacy_lcoh_structure",
        "compute_lcoh: keys, methods, errors, break-even None",
    );
    for c in arr(&t["legacy"]) {
        let file = c["file"].as_str().unwrap_or("");
        let case = format!("{file} {}", c["assumptions"]);
        let kw: Vec<(String, Value)> = overrides_of(&c["assumptions"]).into_iter().collect();
        let inp = LcohInput::from_result_json(&read_json(root, file)?)?;
        let r = EconAssumptions::with_overrides(d, &kw).and_then(|a| {
            let out = compute_lcoh(d, &inp, &a)?;
            Ok((a, out))
        });
        match (py_error(&c["output"]), r) {
            (Some(pe), r) => add_err_case(&mut lgx, &case, pe, &r),
            (None, Err(e)) => lgx.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok((a, out))) => {
                compare_tree(&mut lg, &mut lgx, &case, &out, &c["output"], false);
                for (tk, pv) in c["breakeven"].as_object().into_iter().flatten() {
                    let target: f64 = tk.parse().unwrap_or(f64::NAN);
                    let bc = format!("{case} breakeven target={tk}");
                    match (py_error(pv), breakeven_ammonia_price(d, &inp, &a, target)) {
                        (Some(pe), r) => add_err_case(&mut lgx, &bc, pe, &r),
                        (None, Err(e)) => lgx.add_bool(&bc, false, || format!("rust error {e}")),
                        (None, Ok(v)) => add_opt(&mut lg, &mut lgx, &bc, v, pv),
                    }
                }
            }
        }
    }
    rep.push(lg);
    rep.push(lgx);

    // ---------------------------------------------------------------------------- stored results
    let mut st = Acc::rel(
        "economics.stored_results",
        "every number of results/research/reference_scenario/{baseline,capex_audit}.json, \
         results/research/singapore/{scenario_results,tornado,breakeven_ammonia_price}.json and \
         results/simulations/economics_baseline*.json recomputed from its recipe and compared with the stored file",
        1e-12,
    )
    .note("baseline LCOH 4.015461254695034 USD/kg, CAPEX 7,666,560 USD, NPV -17.456 MUSD, break-even 320.0 USD/t, \
           fuel-efficiency envelope 4.037937 and 4.062672 are among these values");
    let mut stx = Acc::exact(
        "economics.stored_results_decisions",
        "stored results: None and booleans identical; Python reproduces the stored value",
    );
    let mut files: BTreeMap<String, Value> = BTreeMap::new();
    for c in arr(&t["stored"]) {
        let file = c["file"].as_str().unwrap_or("").to_string();
        if !files.contains_key(&file) {
            files.insert(file.clone(), read_json(root, &file)?);
        }
        let stored = at_path(&files[&file], arr(&c["path"])).clone();
        let case = format!("{file} {}", c["path"]);
        stx.add_bool(
            &format!("{case} python"),
            c["python_reproduces_stored"].as_bool() == Some(true),
            || "the Python reference does not reproduce the stored value".into(),
        );
        match run_recipe(d, &s, root, &c["recipe"]) {
            Err(e) => stx.add_bool(&case, false, || format!("rust error {e}")),
            Ok(v) => match (&v, &stored) {
                (Value::Number(_), Value::Number(_)) => st.add(&case, num(&v), num(&stored)),
                _ => stx.add_bool(&case, v == stored, || format!("rust {v} stored {stored}")),
            },
        }
    }
    rep.push(st);
    rep.push(stx);

    // ---------------------------------------------------------------------------- browser test vectors
    let mut tv = Acc::rel(
        "economics.simulator_test_vectors",
        "the 13 economics vectors of results/research/simulator/test_vectors.json (Python outputs)",
        1e-12,
    );
    let mut tvx = Acc::exact(
        "economics.simulator_test_vectors_structure",
        "test vectors: keys, booleans, None",
    );
    let tvs = read_json(root, "results/research/simulator/test_vectors.json")?;
    for v in arr(&tvs["vectors"])
        .iter()
        .filter(|v| v["kind"] == "economics")
    {
        let id = v["id"].as_str().unwrap_or("");
        let inp = &v["inputs"];
        let sm = Summary::from_summary_json(&inp["summary"])?;
        let r = evaluate(
            d,
            &sm,
            &Scenario::from_json(&inp["scenario"])?,
            &overrides_of(&inp["overrides"]),
        )?;
        let mut r2 = r.clone();
        if let Some(m) = r2.as_object_mut() {
            m.insert(
                "capex_total_USD".into(),
                r["capex"]["total_capex_USD"].clone(),
            );
        }
        compare_tree(&mut tv, &mut tvx, id, &r2, &v["python"], true);
    }
    rep.push(tv);
    rep.push(tvx);
    Ok(rep)
}
