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

/// A pair of accumulators for one quantity (numbers, and structure/decisions/errors).
fn pair(id: &str, quantity: &str) -> (Acc, Acc) {
    (
        Acc::rel(id, quantity, 1e-12),
        Acc::exact(
            &format!("{id}_structure"),
            &format!("{quantity}: keys, labels, booleans, None and errors"),
        ),
    )
}

/// Compare a fallible Rust result with a Python value or recorded exception.
fn cmp_result(
    nums: &mut Acc,
    exact: &mut Acc,
    case: &str,
    rust: Result<Value, EngineError>,
    python: &Value,
) {
    match (py_error(python), rust) {
        (Some(pe), r) => add_err_case(exact, case, pe, &r),
        (None, Err(e)) => exact.add_bool(case, false, || format!("rust error {e}")),
        (None, Ok(v)) => compare_tree(nums, exact, case, &v, python, false),
    }
}

/// Carbon pricing and the LCA factors it needs.
pub fn carbon(
    golden: &Golden,
    d: &EconomicsData,
    factors: &crate::odata::OValue,
    root: &Path,
) -> Result<Report, EngineError> {
    use crate::carbon::{
        CiFactors, CiInputs, RouteCaseOpts, actual_boundary, carbon_cost, carbon_intensity_h2,
        crossover_price, eu_ets_sgd_per_t, legislated_rate_sgd, n2o_at_ppmv, n2o_threshold_test,
        pair_threshold, route_case, route_gate_ef,
    };
    use crate::lca;
    let mut rep = Report::new("carbon");
    let t = golden.load("carbon.json")?;
    let s = summaries(&t)?;

    // ---------------------------------------------------------------------------- lca.py
    let (mut ln, mut lx) = pair(
        "carbon.lca_factors",
        "lca.py: route_spec (7 routes), blue_nh3_ef, green_nh3_ef, shipping, delivered factor, N2O/NO per MWh, \
         CCGT, SMR",
    );
    let l = &t["lca"];
    for (r, pv) in l["route_spec"].as_object().into_iter().flatten() {
        cmp_result(
            &mut ln,
            &mut lx,
            &format!("route_spec {r}"),
            lca::route_spec(r).map(|x| x.to_json()),
            pv,
        );
    }
    for c in arr(&l["blue_nh3_ef"]) {
        let a: Vec<f64> = arr(&c["args"]).iter().map(num).collect();
        let g = |i: usize, dv: f64| a.get(i).copied().unwrap_or(dv);
        let r = lca::blue_nh3_ef(g(0, 1.0), g(1, 0.0), g(2, 0.0), a.get(3).copied())
            .map(crate::economics::jf);
        cmp_result(
            &mut ln,
            &mut lx,
            &format!("blue_nh3_ef {}", c["args"]),
            r,
            &c["value"],
        );
    }
    for (k, pv) in l["green_nh3_ef"].as_object().into_iter().flatten() {
        let r = lca::green_nh3_ef(k).map(crate::economics::jf);
        cmp_result(&mut ln, &mut lx, &format!("green_nh3_ef {k}"), r, pv);
    }
    for c in arr(&l["ship_kg_per_kg_nh3"]) {
        ln.add(
            &format!("ship {} {}", c["distance_km"], c["ef"]),
            lca::ship_kg_per_kg_nh3(num(&c["distance_km"]), opt_num(&c["ef"])),
            num(&c["value"]),
        );
    }
    for c in arr(&l["delivered_nh3_ef"]) {
        let r = lca::delivered_nh3_ef(
            num(&c["ef_gate"]),
            num(&c["distance_km"]),
            opt_num(&c["boil_off"]),
            None,
        )
        .map(crate::economics::jf);
        let case = format!(
            "delivered {} {} {}",
            c["ef_gate"], c["distance_km"], c["boil_off"]
        );
        cmp_result(&mut ln, &mut lx, &case, r, &c["value"]);
    }
    let (n2o, n2o_e, no) = lca::n2o_nox_per_mwh();
    let pn = &l["n2o_noX_per_MWh"];
    ln.add("N2O_kg_per_MWh", n2o, num(&pn["N2O_kg_per_MWh"]));
    ln.add("N2O_kgCO2e_per_MWh", n2o_e, num(&pn["N2O_kgCO2e_per_MWh"]));
    ln.add("NO_kg_per_MWh", no, num(&pn["NO_kg_per_MWh"]));
    for c in arr(&l["ccgt_ci_kg_per_MWh"]) {
        ln.add(
            &format!("ccgt {} {}", c["eff"], c["leak"]),
            lca::ccgt_ci_kg_per_mwh(opt_num(&c["eff"]), num(&c["leak"])),
            num(&c["value"]),
        );
    }
    ln.add("smr ccs", lca::smr_h2_ci(true), num(&l["smr_h2_ci"]["ccs"]));
    ln.add(
        "smr unabated",
        lca::smr_h2_ci(false),
        num(&l["smr_h2_ci"]["unabated"]),
    );
    ln.add(
        "KG_H2_PER_KG_NH3",
        lca::KG_H2_PER_KG_NH3,
        num(&l["KG_H2_PER_KG_NH3"]),
    );
    rep.push(ln);
    rep.push(lx);

    // ---------------------------------------------------------------------------- misc
    let (mut mn, mut mx) = pair(
        "carbon.policy_and_factors",
        "legislated CPA rates by year, EU ETS context in SGD, CI factors of three grids, route gate factors",
    );
    let m = &t["misc"];
    for (y, pv) in m["legislated_rate_SGD"].as_object().into_iter().flatten() {
        mn.add(
            &format!("rate {y}"),
            legislated_rate_sgd(y.parse().unwrap_or(0)),
            num(pv),
        );
    }
    mn.add(
        "eu_ets_SGD_per_t",
        eu_ets_sgd_per_t(d),
        num(&m["eu_ets_SGD_per_t"]),
    );
    for (g, pv) in m["ci_factors"].as_object().into_iter().flatten() {
        cmp_result(
            &mut mn,
            &mut mx,
            &format!("ci_factors {g}"),
            CiFactors::from_factors(factors, g).map(|f| f.to_json()),
            pv,
        );
    }
    for (r, pv) in m["route_gate_ef"].as_object().into_iter().flatten() {
        cmp_result(
            &mut mn,
            &mut mx,
            &format!("route_gate_ef {r}"),
            route_gate_ef(r),
            pv,
        );
    }
    rep.push(mn);
    rep.push(mx);

    // ---------------------------------------------------------------------------- carbon intensity
    let (mut cn, mut cx) = pair(
        "carbon.intensity",
        "carbon_intensity_h2: three activity sets x five gate factors x three heating options (and an invalid one) \
         x distances x grids",
    );
    let mut ci_in = BTreeMap::new();
    for (k, v) in t["ci_inputs"].as_object().into_iter().flatten() {
        ci_in.insert(k.clone(), CiInputs::from_json(v)?);
    }
    for c in arr(&t["carbon_intensity"]) {
        let inp = ci_in
            .get(c["inputs"].as_str().unwrap_or(""))
            .ok_or_else(|| EngineError::data("carbon.json", "ci inputs"))?;
        let fc = CiFactors::from_factors(factors, c["grid"].as_str().unwrap_or(""))?;
        let r = carbon_intensity_h2(
            inp,
            num(&c["nh3_ef"]),
            c["heating"].as_str().unwrap_or(""),
            opt_num(&c["distance_km"]),
            &fc,
        );
        let case = format!(
            "{} ef={} {} d={} {}",
            c["inputs"], c["nh3_ef"], c["heating"], c["distance_km"], c["grid"]
        );
        cmp_result(&mut cn, &mut cx, &case, r, &c["value"]);
    }
    rep.push(cn);
    rep.push(cx);

    // ---------------------------------------------------------------------------- carbon cost
    let (mut kn, mut kx) = pair(
        "carbon.cost",
        "carbon_cost: Mode A, Mode B (price on the CI replacing the tax term), invalid mode and prices",
    );
    for c in arr(&t["carbon_cost"]) {
        let econ = &t["econs"][c["econ"].as_str().unwrap_or("")];
        let r = carbon_cost(
            econ,
            num(&c["ci"]),
            c["mode"].as_str().unwrap_or(""),
            num(&c["price"]),
        );
        let case = format!(
            "{} {} P={} CI={}",
            c["econ"], c["mode"], c["price"], c["ci"]
        );
        cmp_result(&mut kn, &mut kx, &case, r, &c["value"]);
    }
    rep.push(kn);
    rep.push(kx);

    // ---------------------------------------------------------------------------- Mode A
    let (mut an, mut ax) = pair(
        "carbon.actual_boundary",
        "actual_boundary (Mode A threshold test): years 2023-2030, N2O kg/h with GWP 265, natural-gas heat, \
         capacity, hours and tax overrides (including the full evaluate output)",
    );
    for c in arr(&t["actual_boundary"]) {
        let sm = get_summary(&s, c["summary"].as_str().unwrap_or(""))?;
        let r = Scenario::from_json(&c["scenario"]).and_then(|sc| {
            actual_boundary(
                d,
                sm,
                &sc,
                c["year"].as_i64().unwrap_or(2026),
                num(&c["n2o_kg_per_h"]),
                &overrides_of(&c["overrides"]),
            )
        });
        let case = format!(
            "{} {} {} n2o={} {}",
            c["summary"], c["scenario"], c["year"], c["n2o_kg_per_h"], c["overrides"]
        );
        cmp_result(&mut an, &mut ax, &case, r, &c["value"]);
    }
    rep.push(an);
    rep.push(ax);

    // ---------------------------------------------------------------------------- route cases
    let (mut rn, mut rx) = pair(
        "carbon.route_case",
        "route_case: six routes x Mode A and Mode B prices x CI level, custom gate factor, benchmark, overrides \
         (LCOH, carbon cost, break-even NH3 price, NPV)",
    );
    let opts_of = |c: &Value| -> RouteCaseOpts {
        let kw = &c["kwargs"];
        RouteCaseOpts {
            mode: c["mode"].as_str().unwrap_or("").to_string(),
            price_sgd_per_t: num(&c["price"]),
            ci_level: kw["ci_level"].as_str().unwrap_or("central").to_string(),
            nh3_ef_kg_per_kg: opt_num(&kw["nh3_ef_kg_per_kg"]),
            benchmark_usd_per_kg: opt_num(&kw["benchmark_USD_per_kg"]),
            benchmark_ci_kgco2e_per_kgh2: opt_num(&kw["benchmark_ci_kgCO2e_per_kgH2"])
                .unwrap_or(11.0),
            overrides: overrides_of(&kw["overrides"]),
        }
    };
    for c in arr(&t["route_case"]) {
        let sm = get_summary(&s, c["summary"].as_str().unwrap_or(""))?;
        let r = route_case(
            d,
            factors,
            sm,
            c["route"].as_str().unwrap_or(""),
            &opts_of(c),
        );
        let case = format!(
            "{} {} P={} {}",
            c["route"], c["mode"], c["price"], c["kwargs"]
        );
        cmp_result(&mut rn, &mut rx, &case, r, &c["value"]);
    }
    rep.push(rn);
    rep.push(rx);

    // ---------------------------------------------------------------------------- crossover, N2O
    let (mut xn, mut xx) = pair(
        "carbon.crossover_and_n2o",
        "crossover_price (all three branches), n2o_threshold_test on the stored Aspen baseline, n2o_at_ppmv",
    );
    for c in arr(&t["crossover_price"]) {
        let a: Vec<f64> = arr(&c["args"]).iter().map(num).collect();
        let v = crossover_price(a[0], a[1], a[2], a[3], a[4]);
        add_opt(
            &mut xn,
            &mut xx,
            &format!("crossover {}", c["args"]),
            v,
            &c["value"],
        );
    }
    let base_res = read_json(root, "results/simulations/baseline.json")?;
    let econ = evaluate(
        d,
        &Summary::extract(&base_res)?,
        &Scenario::Named("grey".into()),
        &Overrides::new(),
    )?;
    let tt = n2o_threshold_test(&base_res, &econ)?;
    compare_tree(
        &mut xn,
        &mut xx,
        "n2o_threshold_test",
        &tt,
        &t["n2o"]["threshold_test"],
        false,
    );
    let grid: Vec<(f64, f64)> = [0.15, 1.0, 50.0]
        .iter()
        .flat_map(|p| [(*p, 8000.0), (*p, 7000.0)])
        .collect();
    for (k, (p, h)) in grid.into_iter().enumerate() {
        let pv = &t["n2o"]["at_ppmv"][k];
        compare_tree(
            &mut xn,
            &mut xx,
            &format!("n2o_at_ppmv {p} {h}"),
            &n2o_at_ppmv(p, &tt, h)?,
            pv,
            false,
        );
    }
    rep.push(xn);
    rep.push(xx);

    // ---------------------------------------------------------------------------- test vectors
    let (mut vn, mut vx) = pair(
        "carbon.test_vectors",
        "the 18 vectors of results/research/carbon_pricing/test_vectors.json (carbon intensity, carbon cost, \
         crossover prices 33.106, 304.8 and 143.5 SGD/t)",
    );
    let tvs = read_json(root, "results/research/carbon_pricing/test_vectors.json")?;
    for v in arr(&tvs["vectors"]) {
        let id = v["id"].as_str().unwrap_or("");
        let i = &v["inputs"];
        let exp = &v["expected"];
        match v["function"].as_str().unwrap_or("") {
            "carbonIntensity" => {
                let r = carbon_intensity_h2(
                    &CiInputs::from_json(&i["x"])?,
                    num(&i["nh3_ef_kg_per_kg"]),
                    i["heating"].as_str().unwrap_or(""),
                    opt_num(&i["distance_km"]),
                    &CiFactors::from_json(&i["factors"])?,
                )?;
                compare_tree(&mut vn, &mut vx, id, &r, exp, false);
            }
            "carbonCost" => {
                let mut r = carbon_cost(
                    &i["econ"],
                    num(&i["ci_total_kgCO2e_per_kgH2"]),
                    i["mode"].as_str().unwrap_or(""),
                    num(&i["price_SGD_per_t"]),
                )?;
                let mut e = exp.clone();
                if let (Some(sub), Some(em)) = (exp["label_contains"].as_str(), e.as_object_mut()) {
                    let ok = r["label"].as_str().unwrap_or("").contains(sub);
                    vx.add_bool(&format!("{id} label"), ok, || {
                        format!("label lacks {sub:?}")
                    });
                    em.remove("label_contains");
                    if let Some(rm) = r.as_object_mut() {
                        rm.remove("label");
                    }
                }
                compare_tree(&mut vn, &mut vx, id, &r, &e, false);
            }
            _ => {
                let v2 = crossover_price(
                    num(&i["lcoh_a"]),
                    num(&i["ci_a"]),
                    num(&i["lcoh_b"]),
                    num(&i["ci_b"]),
                    num(&i["fx"]),
                );
                add_opt(&mut vn, &mut vx, id, v2, exp);
            }
        }
    }
    rep.push(vn);
    rep.push(vx);

    // ---------------------------------------------------------------------------- stored results
    let (mut sn, mut sx) = pair(
        "carbon.stored_results",
        "results/research/carbon_pricing: every route case of scenarios.json, its Mode A block, the pairwise \
         thresholds of thresholds.json, the route rows and comparators of carbon_intensity.json",
    );
    for (k, ok) in t["python_reproduces_stored"]
        .as_object()
        .into_iter()
        .flatten()
    {
        sx.add_bool(
            &format!("python reproduces {k}"),
            ok.as_bool() == Some(true),
            || "the Python reference does not reproduce the stored file".into(),
        );
    }
    let base = Summary::extract(&base_res)?;
    let sc = read_json(root, "results/research/carbon_pricing/scenarios.json")?;
    let bench_ci = num(&sc["benchmark_ci_smr_kgCO2e_per_kgH2"]);
    for (i, c) in arr(&sc["cases"]).iter().enumerate() {
        let hyp = c["mode"] == "hypothetical_lca";
        let o = RouteCaseOpts {
            mode: c["mode"].as_str().unwrap_or("").to_string(),
            price_sgd_per_t: if hyp {
                num(&c["carbon_price_SGD_per_tCO2e"])
            } else {
                0.0
            },
            benchmark_ci_kgco2e_per_kgh2: if hyp { bench_ci } else { 11.0 },
            ..RouteCaseOpts::default()
        };
        let r = route_case(d, factors, &base, c["route"].as_str().unwrap_or(""), &o)?;
        compare_tree(
            &mut sn,
            &mut sx,
            &format!("scenarios.json cases[{i}]"),
            &r,
            c,
            false,
        );
    }
    let ma = &sc["mode_a_actual_boundary"];
    let mut ab = actual_boundary(
        d,
        &base,
        &Scenario::Named("grey".into()),
        2026,
        0.0,
        &Overrides::new(),
    )?;
    if let Some(m) = ab.as_object_mut() {
        m.remove("econ");
    }
    compare_tree(
        &mut sn,
        &mut sx,
        "mode_a reference_plant_self_firing",
        &ab,
        &ma["reference_plant_self_firing"],
        false,
    );
    compare_tree(
        &mut sn,
        &mut sx,
        "mode_a n2o_threshold_test",
        &tt,
        &ma["n2o_threshold_test"],
        false,
    );
    let hours = num(&econ["assumptions"]["economic"]["operating_hours_h_per_yr"]);
    compare_tree(
        &mut sn,
        &mut sx,
        "mode_a n2o_at_ahmad_0p15_ppmv",
        &n2o_at_ppmv(0.15, &tt, hours)?,
        &ma["n2o_at_ahmad_0p15_ppmv_transferred"],
        false,
    );
    let mut ngo = Overrides::new();
    ngo.insert("heat_fuel".into(), Value::String("natural_gas".into()));
    let ng = actual_boundary(d, &base, &Scenario::Named("grey".into()), 2026, 0.0, &ngo)?;
    let ngv = &ma["natural_gas_heat_variant"];
    sn.add(
        "mode_a ng direct",
        num(&ng["direct_tCO2e_per_yr"]),
        num(&ngv["direct_tCO2e_per_yr"]),
    );
    sn.add(
        "mode_a ng fraction",
        num(&ng["threshold_fraction"]),
        num(&ngv["threshold_fraction"]),
    );
    sn.add(
        "mode_a ng capacity scale",
        crate::carbon::THRESHOLD_TCO2E_PER_YR / num(&ng["direct_tCO2e_per_yr"]),
        num(&ngv["capacity_scale_to_reach_threshold"]),
    );
    sx.add_bool("mode_a ng liable", ng["liable"] == ngv["liable"], || {
        "liable differs".into()
    });
    let th = read_json(root, "results/research/carbon_pricing/thresholds.json")?;
    for (i, row) in arr(&th["pairwise"]).iter().enumerate() {
        let r = pair_threshold(
            d,
            factors,
            &base,
            row["route"].as_str().unwrap_or(""),
            row["overtakes"].as_str().unwrap_or(""),
        )?;
        compare_tree(
            &mut sn,
            &mut sx,
            &format!("thresholds.json pairwise[{i}]"),
            &r,
            row,
            false,
        );
    }
    let cij = read_json(
        root,
        "results/research/carbon_pricing/carbon_intensity.json",
    )?;
    let fc = CiFactors::from_factors(factors, "singapore_2024")?;
    let inp = CiInputs::from_summary(&base);
    let ci_tot = |ef: f64, dist: Option<f64>| -> Result<f64, EngineError> {
        Ok(num(&carbon_intensity_h2(
            &inp,
            ef,
            "self_firing",
            dist,
            &fc,
        )?["total_kgCO2e_per_kgH2"]))
    };
    for (r, row) in cij["routes"].as_object().into_iter().flatten() {
        let sp = lca::route_spec(r)?;
        let case = format!("carbon_intensity.json routes.{r}");
        sn.add(
            &format!("{case} gate central"),
            sp.ef,
            num(&row["gate_ef_kgCO2e_per_kgNH3"]["central"]),
        );
        sn.add(
            &format!("{case} gate low"),
            sp.low,
            num(&row["gate_ef_kgCO2e_per_kgNH3"]["low"]),
        );
        sn.add(
            &format!("{case} gate high"),
            sp.high,
            num(&row["gate_ef_kgCO2e_per_kgNH3"]["high"]),
        );
        sn.add(
            &format!("{case} ci central"),
            ci_tot(sp.ef, None)?,
            num(&row["ci_kgCO2e_per_kgH2"]["central"]),
        );
        sn.add(
            &format!("{case} ci low"),
            ci_tot(sp.low, None)?,
            num(&row["ci_kgCO2e_per_kgH2"]["low"]),
        );
        sn.add(
            &format!("{case} ci high"),
            ci_tot(sp.high, None)?,
            num(&row["ci_kgCO2e_per_kgH2"]["high"]),
        );
        sn.add(
            &format!("{case} 2000 km"),
            ci_tot(sp.ef, Some(2000.0))?,
            num(&row["ci_at_distance_kgCO2e_per_kgH2"]["2000_km"]),
        );
        sn.add(
            &format!("{case} 12000 km"),
            ci_tot(sp.ef, Some(12000.0))?,
            num(&row["ci_at_distance_kgCO2e_per_kgH2"]["12000_km"]),
        );
        let br = carbon_intensity_h2(&inp, sp.ef, "self_firing", None, &fc)?;
        compare_tree(
            &mut sn,
            &mut sx,
            &format!("{case} breakdown"),
            &br["breakdown_kgCO2e_per_kgH2"],
            &row["breakdown_central"],
            false,
        );
        sx.add_bool(
            &format!("{case} label"),
            row["label"].as_str() == Some(sp.label.as_str()),
            || "label".into(),
        );
    }
    let ci0 = carbon_intensity_h2(&inp, 0.0, "self_firing", None, &fc)?;
    let x = (inp.nh3_feed_kg_h + num(&ci0["nh3_fuel_kg_h"])) / inp.h2_kg_h;
    sn.add(
        "carbon_intensity.json activity kg_nh3_total",
        x,
        num(&cij["activity"]["kg_nh3_total_per_kg_h2"]),
    );
    let ci0t = num(&ci0["total_kgCO2e_per_kgH2"]);
    for (key, vals) in [
        ("vs_smr_unabated", vec![10.0, 11.0, 12.0]),
        ("vs_smr_ccs", vec![3.4, 3.6, 5.3]),
    ] {
        for v in vals {
            let k = crate::pyops::fmt_g(v, 6);
            sn.add(
                &format!("breakeven_gate_ef {key} {k}"),
                (v - ci0t) / x,
                num(&cij["breakeven_gate_ef_kgCO2e_per_kgNH3"][key][k.as_str()]),
            );
        }
    }
    let ng = &cij["power_comparators_kgCO2e_per_MWh"]["ng_ccgt"];
    sn.add(
        "ng_ccgt central",
        lca::ccgt_ci_kg_per_mwh(None, 0.0),
        num(&ng["central"]),
    );
    sn.add(
        "ng_ccgt low_eff_0.50",
        lca::ccgt_ci_kg_per_mwh(Some(0.5), 0.0),
        num(&ng["low_eff_0.50"]),
    );
    sn.add(
        "ng_ccgt high_eff_0.60",
        lca::ccgt_ci_kg_per_mwh(Some(0.6), 0.0),
        num(&ng["high_eff_0.60"]),
    );
    for lk in [0.002, 0.015, 0.03] {
        let k = format!("leak_{}", crate::pyops::fmt_g(lk, 6));
        sn.add(
            &format!("ng_ccgt {k}"),
            lca::ccgt_ci_kg_per_mwh(None, lk),
            num(&ng[k.as_str()]),
        );
    }
    rep.push(sn);
    rep.push(sx);
    Ok(rep)
}

fn nums(v: &Value) -> Vec<f64> {
    arr(v).iter().map(num).collect()
}

fn matrix(v: &Value) -> Vec<Vec<f64>> {
    arr(v).iter().map(nums).collect()
}

/// Uncertainty-quantification estimators on fixed output matrices exported from Python, the
/// Sobol' base samples of the studies, the distributions' PPFs.
pub fn uq(golden: &Golden) -> Result<Report, EngineError> {
    use crate::uq::{
        bootstrap_ci, bootstrap_indices, indices_from_outputs, lognorm_ppf, norm_ppf, sobol_base,
        tri_ppf,
    };
    let mut rep = Report::new("uq");
    let t = golden.load("uq.json")?;
    let mut ix = Acc::rel(
        "uq.sobol_indices",
        "indices_from_outputs on fixed Python output matrices (Ishigami N=1024, random N=500 k=4, constant): S, ST, V",
        1e-12,
    );
    let mut ci = Acc::rel(
        "uq.bootstrap_ci",
        "bootstrap_ci percentile intervals of S and ST (NumPy index stream reproduced)",
        1e-12,
    );
    let mut idx = Acc::exact(
        "uq.bootstrap_index_stream",
        "default_rng(seed).integers(0, N, N): first two resamples identical",
    );
    for e in arr(&t["estimators"]) {
        let name = e["name"].as_str().unwrap_or("");
        let (fa, fb, fab) = (nums(&e["fA"]), nums(&e["fB"]), matrix(&e["fAB"]));
        let (s, st, v) = indices_from_outputs(&fa, &fb, &fab);
        ix.add(&format!("{name} V"), v, num(&e["V"]));
        for (k, (a, b)) in s.iter().zip(nums(&e["S"])).enumerate() {
            ix.add(&format!("{name} S[{k}]"), *a, b);
        }
        for (k, (a, b)) in st.iter().zip(nums(&e["ST"])).enumerate() {
            ix.add(&format!("{name} ST[{k}]"), *a, b);
        }
        let nb = e["n_boot"].as_u64().unwrap_or(0) as usize;
        let seed = e["seed"].as_u64().unwrap_or(0);
        let c = bootstrap_ci(&fa, &fb, &fab, nb, seed, 0.95);
        for (lab, rust, py) in [("S_ci", &c.s, &e["S_ci"]), ("ST_ci", &c.st, &e["ST_ci"])] {
            for (k, (r, p)) in rust.iter().zip(matrix(py)).enumerate() {
                ci.add(&format!("{name} {lab}[{k}] lo"), r[0], p[0]);
                ci.add(&format!("{name} {lab}[{k}] hi"), r[1], p[1]);
            }
        }
        let ri = bootstrap_indices(fa.len(), 2, seed);
        for (k, p) in arr(&e["first_bootstrap_idx"]).iter().enumerate() {
            let pv: Vec<u64> = arr(p).iter().filter_map(Value::as_u64).collect();
            idx.add_bool(&format!("{name} draw {k}"), ri.get(k) == Some(&pv), || {
                "bootstrap indices differ".into()
            });
        }
    }
    rep.push(ix);
    rep.push(ci);
    rep.push(idx);

    let mut sbx = Acc::exact(
        "uq.sobol_base",
        "sobol_base(n, d, 20261123): SHA-256 of the float64 bytes of [A | B] identical to Python (bit for bit)",
    );
    for b in arr(&t["sobol_base"]) {
        let (n, d) = (
            b["n"].as_u64().unwrap_or(0) as usize,
            b["d"].as_u64().unwrap_or(0) as usize,
        );
        let (a, bb) = sobol_base(n, d, crate::uq::SEED)?;
        let mut bytes = Vec::with_capacity(n * 2 * d * 8);
        for (ra, rb) in a.iter().zip(&bb) {
            for x in ra.iter().chain(rb) {
                bytes.extend_from_slice(&x.to_le_bytes());
            }
        }
        let h = crate::provenance::sha256_hex(&bytes);
        let want = b["sha256_le_f8"].as_str().unwrap_or("");
        sbx.add_bool(&format!("n={n} d={d}"), h == want, || {
            format!(
                "sha256 {h} != {want}; first row rust {:?} python {}",
                a[0], b["first_rows"][0]
            )
        });
    }
    rep.push(sbx);

    let mut dist = Acc::rel(
        "uq.distributions",
        "triang.ppf (5 shapes), lognorm.ppf (2 sigmas), ndtri and norm.ppf on 3008 probabilities incl. 1e-12, 1-1e-12, 1e-300",
        1e-12,
    )
    .note("sqrt is correctly rounded; ndtri uses log, exp only in lognorm (libm may differ by an ulp)");
    let u = nums(&t["normal"]["u"]);
    for tr in arr(&t["triang_ppf"]) {
        let (lo, md, hi) = (num(&tr["lo"]), num(&tr["mode"]), num(&tr["hi"]));
        for (q, p) in u.iter().zip(nums(&tr["values"])) {
            dist.add(
                &format!("triang({lo},{md},{hi}) q={q}"),
                tri_ppf(*q, lo, md, hi),
                p,
            );
        }
    }
    for lg in arr(&t["lognorm_ppf"]) {
        let s = num(&lg["s"]);
        for (q, p) in u.iter().zip(nums(&lg["values"])) {
            dist.add(&format!("lognorm({s}) q={q}"), lognorm_ppf(*q, s, 1.0), p);
        }
    }
    for (q, p) in u.iter().zip(nums(&t["normal"]["ndtri"])) {
        dist.add(
            &format!("ndtri q={q}"),
            amcrax_numerics::special::ndtri(*q),
            p,
        );
    }
    for (q, p) in u.iter().zip(nums(&t["normal"]["norm_ppf"])) {
        dist.add(&format!("norm.ppf q={q}"), norm_ppf(*q), p);
    }
    rep.push(dist);

    let mut fl = Acc::exact(
        "uq.python_reproduces_stored",
        "the tagged Python recomputes the stored gsa_sobol.json case and monte_carlo.json means identically",
    );
    for (k, ok) in t["python_reproduces_stored"]
        .as_object()
        .into_iter()
        .flatten()
    {
        fl.add_bool(k, ok.as_bool() == Some(true), || "not reproduced".into());
    }
    rep.push(fl);
    Ok(rep)
}

/// The ported studies against the stored Python results: the global sensitivity analysis
/// (`gsa`: output of [`crate::studies::gsa_study`]) against results/research/uq/gsa_sobol.json and
/// the Monte Carlo (`mc`, `mc_grey`: output of [`crate::studies::mc_singapore`]) against
/// results/research/singapore/monte_carlo.json and monte_carlo_samples_grey.csv.
pub fn studies(
    golden: &Golden,
    d: &EconomicsData,
    root: &Path,
    gsa: Option<&Value>,
    mc: Option<(&Value, &[f64])>,
) -> Result<Report, EngineError> {
    let mut rep = Report::new("studies");
    let t = golden.load("uq.json")?;
    let mut k = Acc::rel(
        "studies.gsa_constants",
        "lognormal CAPEX sigma (brentq), triangular 5-95 % width, catalyst price of the GSA script",
        1e-12,
    );
    let tornado = read_json(root, "results/research/singapore/tornado.json")?;
    let st = crate::studies::GsaSetup::new(d, &tornado)?;
    let gm = &t["gsa_module"];
    k.add("SIG_LN", st.sig_ln, num(&gm["SIG_LN"]));
    k.add("W_TRI", st.w_tri, num(&gm["W_TRI"]));
    k.add("CAT_PRICE", st.cat_price, num(&gm["CAT_PRICE"]));
    rep.push(k);
    if let Some(g) = gsa {
        let stored = read_json(root, "results/research/uq/gsa_sobol.json")?;
        let mut n = Acc::rel(
            "studies.gsa_sobol",
            "uq_gsa_sobol.py: every index, bootstrap interval, convergence value, V, mean, sd, p5, p95 of the 16 cases \
             and the dummy run (N = 8192, 1000 bootstraps) against results/research/uq/gsa_sobol.json",
            1e-10,
        )
        .note("Sobol' sample and bootstrap stream reproduced bit for bit; differences would come only from the model outputs");
        let mut x = Acc::exact(
            "studies.gsa_sobol_structure",
            "gsa_sobol.json: case keys, distribution descriptions, group members",
        );
        for (key, pv) in stored["cases"].as_object().into_iter().flatten() {
            compare_tree(&mut n, &mut x, key, &g["cases"][key.as_str()], pv, false);
        }
        compare_tree(
            &mut n,
            &mut x,
            "dummy_run_grey_HIon",
            &g["dummy_run_grey_HIon"],
            &stored["dummy_run_grey_HIon"],
            false,
        );
        rep.push(n);
        rep.push(x);
    }
    if let Some((m, grey)) = mc {
        let stored = read_json(root, "results/research/singapore/monte_carlo.json")?;
        let mut n = Acc::rel(
            "studies.monte_carlo",
            "economics_singapore.py Monte Carlo (5000 draws, 4 scenarios): percentiles and means against monte_carlo.json",
            1e-12,
        )
        .note("NumPy uniform, triangular and random streams reproduced exactly: an exact (not statistical) comparison");
        let mut x = Acc::exact(
            "studies.monte_carlo_structure",
            "monte_carlo.json results: keys",
        );
        compare_tree(&mut n, &mut x, "results", m, &stored["results"], false);
        rep.push(n);
        rep.push(x);
        let csv = std::fs::read_to_string(
            root.join("results")
                .join("research")
                .join("singapore")
                .join("monte_carlo_samples_grey.csv"),
        )
        .map_err(|e| EngineError::data("monte_carlo_samples_grey.csv", e.to_string()))?;
        let py: Vec<f64> = csv
            .lines()
            .skip(1)
            .filter(|l| !l.trim().is_empty())
            .map(|l| l.trim().parse::<f64>().unwrap_or(f64::NAN))
            .collect();
        let mut sm = Acc::rel(
            "studies.monte_carlo_samples",
            "the 5000 grey LCOH samples, sample for sample, against monte_carlo_samples_grey.csv",
            1e-12,
        );
        let mut sx = Acc::exact("studies.monte_carlo_sample_count", "number of samples");
        sx.add_bool("count", py.len() == grey.len(), || {
            format!("rust {} python {}", grey.len(), py.len())
        });
        for (i, (r, p)) in grey.iter().zip(&py).enumerate() {
            sm.add(&format!("sample {i}"), *r, *p);
        }
        rep.push(sm);
        rep.push(sx);
    }
    Ok(rep)
}

/// High-temperature (stiff) plug-flow cases against Python LSODA, with the stage 2 tolerances.
pub fn stiff(
    golden: &Golden,
    reg: &crate::kinetics::KineticsRegistry,
    sopt: &crate::reactor::SolverOptions,
) -> Result<Report, EngineError> {
    use crate::reactor::{PfrInput, simulate_pfr};
    let mut rep = Report::new("stiff");
    let t = golden.load("stiff.json")?;
    let mut xo = Acc::abs(
        "stiff.outlet_conversion",
        "PFR outlet conversion at 750-900 degC, 1 and 20 bar, 100-1000 kg (five rate laws)",
        1e-7,
    )
    .note("stage 2 gate: Python LSODA rtol 1e-8 against DOPRI5 rtol 1e-10 or, when DOPRI5 exceeds 2,000 step attempts, ROS2 rtol 1e-10");
    let mut to = Acc::abs("stiff.outlet_T", "outlet temperature, K", 1e-4);
    let mut po = Acc::abs("stiff.outlet_P", "outlet pressure, bar", 1e-6);
    let mut xp = Acc::abs(
        "stiff.profile_conversion",
        "conversion profile (3 points)",
        1e-6,
    );
    let mut ex = Acc::exact(
        "stiff.decisions",
        "errors and hydraulic-limit flags identical",
    );
    let mut n_ros2 = 0usize;
    let mut max_steps = 0usize;
    for c in arr(&t["cases"]) {
        let cid = c["catalyst_id"].as_str().unwrap_or("");
        let mut kw = c["kwargs"].clone();
        if let Some(m) = kw.as_object_mut() {
            m.insert("catalyst_id".into(), Value::String(cid.into()));
        }
        let case = format!("{cid} {}", c["kwargs"]);
        let inp: PfrInput = serde_json::from_value(kw)
            .map_err(|e| EngineError::data("stiff.json", e.to_string()))?;
        let r = simulate_pfr(reg, &inp, sopt);
        let pv = &c["result"];
        match (py_error(pv), r) {
            (Some(pe), r) => add_err_case(&mut ex, &case, pe, &r),
            (None, Err(e)) => ex.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(r)) => {
                if r.solver.method.starts_with("ROS2") {
                    n_ros2 += 1;
                }
                max_steps = max_steps.max(r.solver.n_steps);
                ex.add_bool(
                    &case,
                    r.outlet.hydraulic_limit == (pv["hydraulic_limit"] == true),
                    || "hydraulic flag differs".into(),
                );
                xo.add(&case, r.outlet.conversion, num(&pv["conversion"]));
                to.add(&case, r.outlet.t_c, num(&pv["T_C"]));
                po.add(&case, r.outlet.p_bar, num(&pv["P_bar"]));
                for (i, (a, b)) in r.conversion.iter().zip(nums(&pv["X_profile"])).enumerate() {
                    xp.add(&format!("{case} [{i}]"), *a, b);
                }
            }
        }
    }
    rep.findings.push(format!(
        "stiff cases: {n_ros2} of {} solved by the ROS2 fallback (DOPRI5 over 2,000 step attempts); largest step count {max_steps}",
        arr(&t["cases"]).len()
    ));
    rep.push(xo);
    rep.push(to);
    rep.push(po);
    rep.push(xp);
    rep.push(ex);
    Ok(rep)
}

fn csv_opt(s: &str) -> Option<f64> {
    if s == "not_reached" {
        None
    } else {
        s.parse::<f64>().ok()
    }
}

fn add_opt_gate(nums: &mut Acc, exact: &mut Acc, case: &str, r: Option<f64>, p: Option<f64>) {
    match (r, p) {
        (Some(a), Some(b)) => nums.add(case, a, b),
        (None, None) => exact.add_bool(case, true, String::new),
        (a, b) => exact.add_bool(case, false, || format!("rust {a:?} python {b:?}")),
    }
}

/// The kinetic parameter propagation (`scripts/research/uq_kinetic_propagation.py`) against the
/// stored samples (results/research/uq/kinetic_param_propagation_samples.csv, draw for draw) and
/// the stored summaries (kinetic_param_propagation.json), with the reactor tolerances of stage 2.
/// `nominal`: the Rust `run_draw` of the nominal parameters per catalyst.
pub fn kinetic(
    root: &Path,
    res: &[crate::studies::kinetic::KpCatalyst],
    nominal: &[crate::studies::kinetic::DrawOut],
    complete: bool,
) -> Result<Report, EngineError> {
    use crate::studies::kinetic::{KP_CATS, TARGETS, case_summary, target_key};
    let mut rep = Report::new("kinetic_propagation");
    let csv = std::fs::read_to_string(
        root.join("results")
            .join("research")
            .join("uq")
            .join("kinetic_param_propagation_samples.csv"),
    )
    .map_err(|e| EngineError::data("kinetic_param_propagation_samples.csv", e.to_string()))?;
    let mut rows: BTreeMap<(String, String, usize), Vec<String>> = BTreeMap::new();
    for l in csv.lines().skip(1).filter(|l| !l.trim().is_empty()) {
        let f: Vec<String> = l.trim().split(',').map(str::to_string).collect();
        let i = f.get(2).and_then(|x| x.parse().ok()).unwrap_or(usize::MAX);
        rows.insert((f[0].clone(), f[1].clone(), i), f);
    }
    let mut par = Acc::rel(
        "kinetic.draws",
        "parameter draws k0, Ek, K1, K4 (Latin hypercube default_rng(20261123), norm.ppf), draw for draw",
        1e-12,
    )
    .note("LHS and ndtri bit for bit; NumPy's vectorised log/exp may differ from libm by an ulp");
    let mut xl = Acc::abs(
        "kinetic.X_lab",
        "laboratory conversions at 400, 450, 500 degC (W = 0.1 g, 1 atm, NH3/Ar), draw for draw",
        1e-7,
    )
    .note("stage 2 reactor gate (Python LSODA rtol 1e-8 against DOPRI5/ROS2 rtol 1e-10)");
    let mut tr = Acc::abs(
        "kinetic.T_required",
        "inlet temperature for X = 0.95 / 0.99 at 1 and 20 bar, W = 100 / 1000 kg per 100 kmol/h, draw for draw",
        0.05,
    )
    .note("stage 2 gate of the temperature search (brentq xtol 0.02 K on conversions that differ by up to 1e-7)");
    let mut ms = Acc::rel(
        "kinetic.catalyst_mass",
        "catalyst mass for 99 % of equilibrium at 600 degC, 20 bar, draw for draw",
        1e-5,
    )
    .note("stage 2 gate of the mass search (brentq xtol 1e-6 W)");
    let mut dec = Acc::exact(
        "kinetic.decisions",
        "reached / not reached of every target and mass, draws present in the stored file, C3 acceptance",
    );
    for (cid, cases, rate) in res {
        let short = KP_CATS
            .iter()
            .find(|c| c.0 == cid)
            .map(|c| c.1)
            .unwrap_or("");
        for (case, draws, outs) in cases {
            for (i, (d, o)) in draws.iter().zip(outs).enumerate() {
                let key = (cid.clone(), case.clone(), i);
                let Some(f) = rows.get(&key) else {
                    dec.add_bool(&format!("{cid} {case} {i}"), false, || {
                        "draw missing in the stored samples".into()
                    });
                    continue;
                };
                let c = format!("{short} {case} {i}");
                for (k, v) in d.iter().enumerate() {
                    par.add(
                        &format!("{c} p{k}"),
                        *v,
                        f[3 + k].parse().unwrap_or(f64::NAN),
                    );
                }
                for j in 0..3 {
                    xl.add(
                        &format!("{c} X{j}"),
                        o.x_lab[j],
                        f[7 + j].parse().unwrap_or(f64::NAN),
                    );
                }
                for k in 0..TARGETS.len() {
                    add_opt_gate(
                        &mut tr,
                        &mut dec,
                        &format!("{c} T{k}"),
                        o.t_req[k].0,
                        csv_opt(&f[10 + k]),
                    );
                }
                add_opt_gate(
                    &mut ms,
                    &mut dec,
                    &format!("{c} mass"),
                    o.m_frac99.filter(|m| *m != 0.0),
                    csv_opt(&f[18]),
                );
            }
            if complete {
                let n_stored = rows.keys().filter(|k| k.0 == *cid && k.1 == *case).count();
                dec.add_bool(
                    &format!("{cid} {case} count"),
                    n_stored == draws.len(),
                    || format!("rust {} draws, stored {n_stored}", draws.len()),
                );
            }
        }
        if complete {
            let stored = read_json(root, "results/research/uq/kinetic_param_propagation.json")?;
            let sc = &stored["catalysts"][cid.as_str()];
            let r_py = num(&sc["C3_acceptance_rate"]);
            dec.add_bool(&format!("{cid} C3 acceptance"), *rate == r_py, || {
                format!("rust {rate} python {r_py}")
            });
        }
    }
    // nominal parameters (stored nominal_outputs)
    let stored = read_json(root, "results/research/uq/kinetic_param_propagation.json")?;
    for (k, (cid, ..)) in KP_CATS.iter().enumerate() {
        let Some(o) = nominal.get(k) else { continue };
        let pn = &stored["catalysts"][*cid]["nominal_outputs"];
        for j in 0..3 {
            xl.add(
                &format!("{cid} nominal X{j}"),
                o.x_lab[j],
                num(&pn["X_lab"][j]),
            );
        }
        for (i, (p, w, x)) in TARGETS.iter().enumerate() {
            let pv = &pn["T_req"][target_key(*p, *w, *x).as_str()][0];
            add_opt_gate(
                &mut tr,
                &mut dec,
                &format!("{cid} nominal T{i}"),
                o.t_req[i].0,
                pv.as_f64(),
            );
        }
        add_opt_gate(
            &mut ms,
            &mut dec,
            &format!("{cid} nominal mass"),
            o.m_frac99,
            pn["m_frac99"].as_f64(),
        );
    }
    rep.push(par);
    rep.push(xl);
    rep.push(tr);
    rep.push(ms);
    rep.push(dec);
    if complete {
        let mut sp = Acc::rel(
            "kinetic.summary_params",
            "case summaries of the parameter draws",
            1e-12,
        );
        let mut sx = Acc::abs(
            "kinetic.summary_X_lab",
            "case summaries of the laboratory conversions",
            1e-7,
        );
        let mut stt = Acc::abs(
            "kinetic.summary_T_required",
            "case summaries (mean, sd, p5, p50, p95) of the required temperatures",
            0.05,
        );
        let mut sm = Acc::rel(
            "kinetic.summary_mass",
            "case summaries of the catalyst mass",
            1e-5,
        );
        let mut sn = Acc::exact(
            "kinetic.summary_counts",
            "n and n_not_reached of every summary",
        );
        for (cid, cases, _) in res {
            let t_lab = KP_CATS
                .iter()
                .find(|c| c.0 == cid)
                .map(|c| c.2)
                .unwrap_or([0.0; 3]);
            for (case, draws, outs) in cases {
                let r = case_summary(draws, outs, &t_lab);
                let p = &stored["catalysts"][cid.as_str()]["cases"][case.as_str()];
                for (key, rv) in r.as_object().into_iter().flatten() {
                    let pv = &p[key.as_str()];
                    if key == "n_draws" {
                        sn.add_bool(&format!("{cid} {case} n_draws"), rv == pv, || {
                            format!("{rv} vs {pv}")
                        });
                        continue;
                    }
                    let acc: &mut Acc = if key.starts_with("param_") {
                        &mut sp
                    } else if key.starts_with("X_lab") {
                        &mut sx
                    } else if key.starts_with("T_required") {
                        &mut stt
                    } else {
                        &mut sm
                    };
                    for f in ["n", "n_not_reached"] {
                        sn.add_bool(&format!("{cid} {case} {key} {f}"), rv[f] == pv[f], || {
                            format!("rust {} python {}", rv[f], pv[f])
                        });
                    }
                    for f in ["mean", "sd", "p5", "p50", "p95"] {
                        if !pv[f].is_null() {
                            acc.add(&format!("{cid} {case} {key} {f}"), num(&rv[f]), num(&pv[f]));
                        }
                    }
                }
            }
        }
        rep.push(sp);
        rep.push(sx);
        rep.push(stt);
        rep.push(sm);
        rep.push(sn);
    }
    Ok(rep)
}
