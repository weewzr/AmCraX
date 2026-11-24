//! Stage 4 comparisons: fluid properties, process flowsheet (and, in later blocks, heat
//! integration and separation) against `rust/golden/stage4/` (written by
//! `rust/golden/generate_stage4_golden.py`) and against the stored results in `results/`.
//!
//! Gates (see `rust/README.md`):
//!
//! * CoolProp back end on the dense grid: 1e-10 relative (enthalpies relative to
//!   max(|h|, 1 J/mol): the enthalpy zero is CoolProp's default reference state, identical on
//!   both sides); identical success or failure of every call.
//! * flowsheet: stream flows and compositions 1e-10 relative; temperatures 1e-6 K; duties
//!   1e-9 relative to max(|Q|, largest |H| of the block's streams) (a duty is a difference of
//!   stream enthalpies, so its rounding scale is that of the enthalpies); stream enthalpies
//!   1e-9 relative; KPIs 1e-9 relative; pressures 1e-12 relative (pure arithmetic on the
//!   inputs); closure residuals 1e-12 absolute (they are rounding noise by construction);
//!   texts, flags, error classes identical.

use super::{Acc, Golden, Report, num, py_error};
use crate::economics::reference::EconomicsData;
use crate::error::EngineError;
use crate::odata::OValue;
use crate::process::flowsheet::{eos_from_name, run_python_case};
use crate::process::result::{CaseInputs, SimulationResult};
use crate::props::{FluidProps, Query, TablesBackend};
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;

/// The `tables` back end from `coolprop_states.json`.
pub fn tables_backend(g: &Golden) -> Result<TablesBackend, EngineError> {
    let v = g.load("coolprop_states.json")?;
    TablesBackend::from_states(&v["states"])
}

/// Whether a Rust error corresponds to a recorded Python exception class.
pub fn error_class_matches(py: &str, e: &EngineError) -> bool {
    match py {
        "FlowsheetSpecError" => matches!(e, EngineError::Spec(_)),
        "ValueError" | "KeyError" | "TypeError" | "ZeroDivisionError" => {
            matches!(e, EngineError::Domain(_) | EngineError::Property(_))
        }
        "RuntimeError" => matches!(e, EngineError::Numerical(_) | EngineError::Bracket(_)),
        _ => false,
    }
}

/// The CoolProp back end against the dense grid of Python CoolProp values.
pub fn props(g: &Golden, b: &dyn FluidProps) -> Result<Report, EngineError> {
    let t = g.load("coolprop_grid.json")?;
    let mut rep = Report::new(&format!("props ({})", b.backend()));
    let mut groups: BTreeMap<String, Acc> = BTreeMap::new();
    let mut errs = Acc::exact("CP-OUTCOME", "success or failure of every CoolProp call");
    for row in t["rows"].as_array().into_iter().flatten() {
        let txt = |i: usize| row[i].as_str().unwrap_or("");
        let q = Query::from_parts(txt(0), txt(1), txt(2), txt(3), num(&row[4]), num(&row[5]))?;
        let case = q.describe();
        let id = format!("CP-{}-{}-{}-{}", txt(0), txt(1), txt(2), txt(3));
        let r = b.value(&q);
        match (&row[6], r) {
            (Value::Object(_), Err(_)) => errs.add_bool(&case, true, String::new),
            (Value::Object(o), Ok(v)) => errs.add_bool(&case, false, || {
                format!("python failed ({:?}), rust returned {v:e}", o.get("error"))
            }),
            (pv, Err(e)) => errs.add_bool(&case, false, || {
                format!("python returned {pv}, rust failed: {e}")
            }),
            (pv, Ok(v)) => {
                errs.add_bool(&case, true, String::new);
                let scale = if txt(1).starts_with("Hmolar") {
                    1.0
                } else {
                    0.0
                };
                groups
                    .entry(id.clone())
                    .or_insert_with(|| {
                        Acc::rel(
                            &id,
                            &format!("{} {} ({}, phase {})", txt(0), txt(1), txt(2), txt(3)),
                            1e-10,
                        )
                        .note("relative; enthalpies relative to max(|h|, 1 J/mol)")
                    })
                    .add_scaled(&case, v, num(pv), scale);
            }
        }
    }
    for (_, a) in groups {
        rep.push(a);
    }
    rep.push(errs);
    Ok(rep)
}

/// Accumulators of one flowsheet comparison (golden or stored).
struct FsAcc {
    flows: Acc,
    temps: Acc,
    enth: Acc,
    duties: Acc,
    kpis: Acc,
    press: Acc,
    other: Acc,
    closure: Acc,
    text: Acc,
    keys: Acc,
}

impl FsAcc {
    fn new(prefix: &str, what: &str) -> FsAcc {
        let id = |s: &str| format!("{prefix}-{s}");
        FsAcc {
            flows: Acc::rel(
                &id("FLOWS"),
                &format!("{what}: stream flows, compositions, extents"),
                1e-10,
            ),
            temps: Acc::abs(
                &id("T"),
                &format!("{what}: temperatures and approaches (K)"),
                1e-6,
            ),
            enth: Acc::rel(&id("H"), &format!("{what}: stream enthalpy flows"), 1e-9),
            duties: Acc::rel(
                &id("DUTY"),
                &format!("{what}: block duties, powers, basis offsets"),
                1e-9,
            )
            .note("relative to max(|Q|, largest |H| of the block's streams)"),
            kpis: Acc::rel(&id("KPI"), &format!("{what}: KPIs"), 1e-9),
            press: Acc::rel(&id("P"), &format!("{what}: pressures"), 1e-12),
            other: Acc::rel(
                &id("OTHER"),
                &format!("{what}: conversion, K_eq, dew sum, other details"),
                1e-10,
            ),
            closure: Acc::abs(
                &id("CLOSURE"),
                &format!("{what}: mass and energy closure residuals"),
                1e-12,
            ),
            text: Acc::exact(
                &id("TEXT"),
                &format!("{what}: names, phases, flags, messages, notes"),
            ),
            keys: Acc::exact(
                &id("KEYS"),
                &format!("{what}: same fields and null pattern"),
            ),
        }
    }
    fn push(self, rep: &mut Report) {
        for a in [
            self.flows,
            self.temps,
            self.enth,
            self.duties,
            self.kpis,
            self.press,
            self.other,
            self.closure,
            self.text,
            self.keys,
        ] {
            rep.push(a);
        }
    }
}

fn block_scale(py: &Value, bid: &str) -> f64 {
    let mut s = 0.0_f64;
    if let Some(st) = py["streams"].as_object() {
        for v in st.values() {
            let touches =
                v["source_block"].as_str() == Some(bid) || v["dest_block"].as_str() == Some(bid);
            if touches {
                s = s.max(num(&v["enthalpy_flow_kW"]).abs());
            }
        }
    }
    s
}

fn max_h(py: &Value) -> f64 {
    py["streams"]
        .as_object()
        .map(|m| {
            m.values()
                .map(|v| num(&v["enthalpy_flow_kW"]).abs())
                .fold(0.0, f64::max)
        })
        .unwrap_or(0.0)
}

fn same_text(acc: &mut Acc, case: &str, p: &Value, r: &Value) {
    acc.add_bool(case, p == r, || format!("python {p} rust {r}"));
}

/// Compare one leaf (number, null, string, bool) with the accumulator `a`.
/// A JSON number or a golden non-finite marker.
pub fn is_num(v: &Value) -> bool {
    v.is_number() || matches!(v.as_str(), Some("nan" | "inf" | "-inf"))
}

/// Compare one numeric leaf (`null` on both sides is equal; Rust writes NaN as `null`).
pub fn leaf(a: &mut Acc, keys: &mut Acc, case: &str, p: &Value, r: &Value, scale: f64) {
    if p.is_null() && r.is_null() {
        keys.add_bool(case, true, String::new);
    } else if is_num(p) && (is_num(r) || r.is_null()) {
        keys.add_bool(case, true, String::new);
        let rv = if r.is_null() { f64::NAN } else { num(r) };
        a.add_scaled(case, rv, num(p), scale);
    } else {
        keys.add_bool(case, false, || format!("python {p} rust {r}"));
    }
}

fn compare_map(
    acc: &mut FsAcc,
    case: &str,
    p: &Value,
    r: &Value,
    f: &mut dyn FnMut(&mut FsAcc, &str, &str, &Value, &Value),
) {
    let Some(pm) = p.as_object() else {
        acc.keys
            .add_bool(case, p == r, || format!("python {p} rust {r}"));
        return;
    };
    let rm = r.as_object();
    acc.keys
        .add_bool(case, rm.is_some_and(|m| m.len() == pm.len()), || {
            format!(
                "field sets differ: python {:?} rust {:?}",
                pm.keys().collect::<Vec<_>>(),
                rm.map(|m| m.keys().collect::<Vec<_>>())
            )
        });
    for (k, pv) in pm {
        let rv = rm.and_then(|m| m.get(k)).unwrap_or(&Value::Null);
        f(acc, &format!("{case}/{k}"), k, pv, rv);
    }
}

/// Compare a Rust flowsheet result (as JSON) with a Python result.
fn compare_result(acc: &mut FsAcc, case: &str, py: &Value, rs: &Value) {
    let hmax = max_h(py);
    for k in [
        "schema_version",
        "case_id",
        "source",
        "model_file",
        "notes",
        "inputs",
    ] {
        same_text(&mut acc.text, &format!("{case}/{k}"), &py[k], &rs[k]);
    }
    for k in ["converged", "has_errors", "has_warnings", "messages"] {
        same_text(
            &mut acc.text,
            &format!("{case}/status/{k}"),
            &py["status"][k],
            &rs["status"][k],
        );
    }
    compare_map(
        acc,
        &format!("{case}/streams"),
        &py["streams"],
        &rs["streams"],
        &mut |a, c, _sid, ps, rsv| {
            compare_map(a, c, ps, rsv, &mut |a, c2, field, pv, rv| match field {
                "temperature_C" => leaf(&mut a.temps, &mut a.keys, c2, pv, rv, 0.0),
                "pressure_bar" => leaf(&mut a.press, &mut a.keys, c2, pv, rv, 0.0),
                "enthalpy_flow_kW" => leaf(&mut a.enth, &mut a.keys, c2, pv, rv, 0.0),
                "mole_flow_kmol_h" | "mass_flow_kg_h" => {
                    leaf(&mut a.flows, &mut a.keys, c2, pv, rv, 0.0)
                }
                "mole_frac" | "mass_frac" | "component_mole_flow_kmol_h" => {
                    compare_map(a, c2, pv, rv, &mut |a, c3, _, x, y| {
                        leaf(&mut a.flows, &mut a.keys, c3, x, y, 0.0)
                    })
                }
                "vapor_fraction" => leaf(&mut a.text, &mut a.keys, c2, pv, rv, 0.0),
                _ => same_text(&mut a.text, c2, pv, rv),
            })
        },
    );
    compare_map(
        acc,
        &format!("{case}/blocks"),
        &py["blocks"],
        &rs["blocks"],
        &mut |a, c, bid, pb, rb| {
            let sc = block_scale(py, bid);
            compare_map(a, c, pb, rb, &mut |a, c2, field, pv, rv| match field {
                "duty_kW" | "power_kW" => leaf(&mut a.duties, &mut a.keys, c2, pv, rv, sc),
                "outlet_temperature_C" => leaf(&mut a.temps, &mut a.keys, c2, pv, rv, 0.0),
                "outlet_pressure_bar" => leaf(&mut a.press, &mut a.keys, c2, pv, rv, 0.0),
                "details" => compare_map(a, c2, pv, rv, &mut |a, c3, dk, x, y| {
                    if x.is_string() && !matches!(x.as_str(), Some("nan" | "inf" | "-inf")) {
                        same_text(&mut a.text, c3, x, y)
                    } else if dk.ends_with("_C") || dk.ends_with("_K") {
                        leaf(&mut a.temps, &mut a.keys, c3, x, y, 0.0)
                    } else if dk.ends_with("_kW") {
                        leaf(&mut a.duties, &mut a.keys, c3, x, y, sc)
                    } else if dk == "extent_kmol_h" || dk == "air_kmol_h" {
                        leaf(&mut a.flows, &mut a.keys, c3, x, y, 0.0)
                    } else {
                        leaf(&mut a.other, &mut a.keys, c3, x, y, 0.0)
                    }
                }),
                _ => same_text(&mut a.text, c2, pv, rv),
            })
        },
    );
    compare_map(
        acc,
        &format!("{case}/kpis"),
        &py["kpis"],
        &rs["kpis"],
        &mut |a, c, _, pv, rv| leaf(&mut a.kpis, &mut a.keys, c, pv, rv, 0.0),
    );
    compare_map(
        acc,
        &format!("{case}/balances"),
        &py["balances"],
        &rs["balances"],
        &mut |a, c, k, pv, rv| {
            if k.ends_with("_closure_rel") {
                leaf(&mut a.closure, &mut a.keys, c, pv, rv, 0.0)
            } else if k.starts_with("energy") {
                leaf(&mut a.duties, &mut a.keys, c, pv, rv, hmax)
            } else {
                leaf(&mut a.flows, &mut a.keys, c, pv, rv, 0.0)
            }
        },
    );
}

/// The flowsheet against the golden cases and the stored Python results.
pub fn flowsheet(g: &Golden, b: &dyn FluidProps, root: &Path) -> Result<Report, EngineError> {
    let t = g.load("flowsheet.json")?;
    let mut rep = Report::new(&format!("flowsheet (properties: {})", b.backend()));
    let mut acc = FsAcc::new("FS", "flowsheet vs Python");
    let mut outcome = Acc::exact(
        "FS-OUTCOME",
        "flowsheet: success, or the same exception class",
    );
    let mut results: BTreeMap<String, Value> = BTreeMap::new();
    for c in t["cases"].as_array().into_iter().flatten() {
        let id = c["id"].as_str().unwrap_or("?").to_string();
        let py = &c["result"];
        let inputs = CaseInputs::from_value(&c["inputs"]);
        let eos = eos_from_name(c["eos"].as_str().unwrap_or(""));
        let rust = match (inputs, eos) {
            (Ok(i), Ok(e)) => run_python_case(&i, e, b),
            (Err(e), _) | (_, Err(e)) => Err(e),
        };
        match (py_error(py), rust) {
            (Some(cls), Err(e)) => {
                let ok = error_class_matches(cls, &e);
                outcome.add_bool(&id, ok, || format!("python {cls}, rust {e}"));
                if cls == "ValueError"
                    && py["message"]
                        .as_str()
                        .is_some_and(|m| m.contains("mole fractions must be finite"))
                {
                    rep.findings.push(format!(
                        "{id}: Python raises ValueError ('{}'); the Rust port raises the same ({e}). Python \
                         defect recorded in rust/README.md (equilibrium state at the upper bracket end).",
                        py["message"].as_str().unwrap_or("").chars().take(60).collect::<String>()
                    ));
                }
            }
            (Some(cls), Ok(_)) => outcome.add_bool(&id, false, || {
                format!("python raised {cls}, rust succeeded")
            }),
            (None, Err(e)) => {
                outcome.add_bool(&id, false, || format!("python succeeded, rust failed: {e}"))
            }
            (None, Ok(r)) => {
                outcome.add_bool(&id, true, String::new);
                let rj = r.to_json();
                compare_result(&mut acc, &id, py, &rj);
                results.insert(id, rj);
            }
        }
    }
    acc.push(&mut rep);
    rep.push(outcome);
    let mut st = FsAcc::new("FS-STORED", "flowsheet vs stored results/simulations");
    let mut found = Acc::exact(
        "FS-STORED-PRESENT",
        "stored Python results found and recomputed",
    );
    for s in t["stored"].as_array().into_iter().flatten() {
        let file = s["file"].as_str().unwrap_or("");
        let case = s["case"].as_str().unwrap_or("");
        let stored: Result<Value, String> = std::fs::read_to_string(root.join(file))
            .map_err(|e| e.to_string())
            .and_then(|txt| serde_json::from_str::<Value>(&txt).map_err(|e| e.to_string()));
        match (stored, results.get(case)) {
            (Ok(sv), Some(rj)) => {
                found.add_bool(file, true, String::new);
                compare_result(&mut st, file, &sv, rj);
            }
            (Err(e), _) => found.add_bool(file, false, || format!("cannot read {file}: {e}")),
            (_, None) => found.add_bool(file, false, || format!("case {case} did not run")),
        }
        if s["reproduced_1e12"].as_bool() != Some(true) {
            rep.findings.push(format!(
                "{file}: the Python reference at generation did not reproduce the stored file (max rel. deviation {})",
                num(&s["python_max_rel_dev"])
            ));
        }
    }
    st.push(&mut rep);
    rep.push(found);
    if let Some((e, t, m)) = b.lookup_stats() {
        rep.findings.push(format!(
            "tables back end after the flowsheet cases: {e} exact lookups, {t} first-order Taylor lookups (within \
             1e-7 relative of a recorded state), {m} misses"
        ));
    }
    Ok(rep)
}

/// A golden `SimulationResult` (sorted keys) as an ordered value (species in COMPONENTS order).
pub fn golden_result_ov(v: &Value) -> OValue {
    crate::process::result::ov_components_order(v)
}

// ===================================================================================== tree comparison
/// Accumulators of a generic JSON-tree comparison: numbers (relative, with a scale chosen from
/// the key), integers and booleans (decisions, identical), strings (identical), structure.
pub struct TreeAcc {
    pub num: Acc,
    pub dec: Acc,
    pub text: Acc,
    pub keys: Acc,
}

impl TreeAcc {
    /// Accumulators `PREFIX-NUM` (gate `gate`), `-DECISION`, `-TEXT`, `-KEYS`.
    pub fn new(prefix: &str, what: &str, gate: f64, note: &str) -> TreeAcc {
        TreeAcc {
            num: Acc::rel(&format!("{prefix}-NUM"), &format!("{what}: numbers"), gate).note(note),
            dec: Acc::exact(
                &format!("{prefix}-DECISION"),
                &format!("{what}: counts and flags (shells, units, feasibility, threshold, cross)"),
            ),
            text: Acc::exact(
                &format!("{prefix}-TEXT"),
                &format!("{what}: labels, sources, warnings, notes"),
            ),
            keys: Acc::exact(
                &format!("{prefix}-KEYS"),
                &format!("{what}: same fields, lengths, null pattern"),
            ),
        }
    }
    /// Push the four checks.
    pub fn push(self, rep: &mut Report) {
        for a in [self.num, self.dec, self.text, self.keys] {
            rep.push(a);
        }
    }
}

/// Scale of a relative comparison chosen from the key: temperatures in degC relative to
/// max(|x|, 273.15 K) (i.e. relative in kelvin), energies, powers, areas and money relative to
/// max(|x|, 1 unit), other quantities relative to max(|x|, 1e-6).
pub fn key_scale(key: &str) -> f64 {
    if matches!(key, "rel_deviation" | "reduction_vs_no_recovery") {
        // fractions of order 1 formed as differences of model and simulated duties: their
        // rounding noise is absolute (about 1e-16), so they are compared relative to max(|x|, 1)
        1.0
    } else if key.ends_with("_C") || key.contains("_C_") || key.contains("T_C") {
        273.15
    } else if ["kW", "m2", "USD", "SGD", "kWh"]
        .iter()
        .any(|u| key.contains(u))
    {
        1.0
    } else {
        1e-6
    }
}

/// Remove the sign of numbers that print as zero (`-0`, `-0.0`, `-0.00` ...): a text that
/// formats a rounding residue (for example "unused flue heat -0.0 kW" for -1e-14 kW) differs
/// between Python and Rust only in the sign of that residue.
pub fn unsign_zeros(s: &str) -> String {
    let b = s.as_bytes();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'-'
            && i + 1 < b.len()
            && b[i + 1] == b'0'
            && (i == 0 || !b[i - 1].is_ascii_digit())
        {
            let mut j = i + 2;
            if j < b.len() && b[j] == b'.' {
                j += 1;
                while j < b.len() && b[j] == b'0' {
                    j += 1;
                }
            }
            if j >= b.len() || !b[j].is_ascii_digit() {
                i += 1;
                continue;
            }
        }
        out.push(b[i] as char);
        i += 1;
    }
    out
}

/// Python and Rust FEHE flags that differ only because the minimum internal approach equals
/// the threshold within rounding (1e-9 K): the Rust flag (and the warning it produces) is taken
/// from Python and the tie is reported as a finding.
fn reconcile_fehe_ties(py: &Value, r: &mut Value, dt: f64, case: &str, findings: &mut Vec<String>) {
    let pmin = num(&py["fehe"]["min_internal_approach_K"]);
    let mut tied = false;
    for (flag, thr) in [("approach_violation", dt), ("temperature_cross", 0.0)] {
        if py["fehe"][flag] != r["fehe"][flag] && (pmin - thr).abs() <= 1e-9 {
            findings.push(format!(
                "{case}: FEHE {flag} decided on a tie (minimum internal approach {pmin:e} K, threshold {thr} K, \
                 Rust value {:e} K): Python {}, Rust {}; the decision is ill-conditioned at the threshold",
                num(&r["fehe"]["min_internal_approach_K"]),
                py["fehe"][flag],
                r["fehe"][flag]
            ));
            r["fehe"][flag] = py["fehe"][flag].clone();
            tied = true;
        }
    }
    if tied {
        let strip = |v: &Value| -> Vec<Value> {
            v.as_array()
                .into_iter()
                .flatten()
                .filter(|w| !w.as_str().is_some_and(|s| s.starts_with("FEHE ")))
                .cloned()
                .collect()
        };
        if strip(&py["warnings"]) == strip(&r["warnings"]) {
            r["warnings"] = py["warnings"].clone();
        }
    }
}

/// Compare two JSON trees (scales from [`key_scale`]).
pub fn tree(acc: &mut TreeAcc, path: &str, key: &str, p: &Value, r: &Value) {
    tree_with(acc, path, key, p, r, &|_, k| key_scale(k));
}

/// Compare two JSON trees with a scale function of (path, key).
pub fn tree_with(
    acc: &mut TreeAcc,
    path: &str,
    key: &str,
    p: &Value,
    r: &Value,
    scale: &dyn Fn(&str, &str) -> f64,
) {
    match p {
        Value::Object(pm) => {
            let Some(rm) = r.as_object() else {
                acc.keys
                    .add_bool(path, false, || format!("python object, rust {r}"));
                return;
            };
            let same = pm.len() == rm.len() && pm.keys().all(|k| rm.contains_key(k));
            acc.keys.add_bool(path, same, || {
                format!(
                    "fields differ: python {:?} rust {:?}",
                    pm.keys().collect::<Vec<_>>(),
                    rm.keys().collect::<Vec<_>>()
                )
            });
            for (k, pv) in pm {
                let rv = rm.get(k).unwrap_or(&Value::Null);
                tree_with(acc, &format!("{path}/{k}"), k, pv, rv, scale);
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
                tree_with(acc, &format!("{path}[{i}]"), key, pv, rv, scale);
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
                acc.num.add_scaled(path, rv, num(p), scale(path, key));
            } else {
                acc.keys
                    .add_bool(path, false, || format!("python {p} rust {r}"));
            }
        }
    }
}

fn arg(a: &Value, k: &str) -> f64 {
    num(&a[k])
}

fn opt_arg(a: &Value, k: &str) -> Option<f64> {
    a.get(k).filter(|v| !v.is_null()).map(num)
}

fn jopt(v: Option<f64>) -> Value {
    crate::process::result::jo(v)
}

/// One exchanger.py call of the golden table.
fn exchanger_call(d: &EconomicsData, f: &str, a: &Value) -> Result<Value, EngineError> {
    use crate::heat::exchanger as hx;
    use crate::process::result::jf;
    let th = |a: &Value| {
        (
            arg(a, "T_hot_in"),
            arg(a, "T_hot_out"),
            arg(a, "T_cold_in"),
            arg(a, "T_cold_out"),
        )
    };
    let opts = |a: &Value| hx::SizeOptions {
        ua_kw_k: opt_arg(a, "ua_kW_K"),
        p_barg: opt_arg(a, "P_barg").unwrap_or(19.5),
        material: a["material"].as_str().unwrap_or("SS/SS").to_string(),
        correlation: a["correlation"].as_str().unwrap_or("turton").to_string(),
        counter_current: a["counter_current"].as_bool().unwrap_or(false),
        cepci_target: opt_arg(a, "cepci_target"),
    };
    Ok(match f {
        "lmtd" => jf(hx::lmtd(arg(a, "dT1"), arg(a, "dT2"))?),
        "f_12" => jopt(hx::f_12(arg(a, "P"), arg(a, "R"))?),
        "f_correction" => {
            let (p, q, r, s) = th(a);
            jopt(hx::f_correction(p, q, r, s, arg(a, "n_shells") as u32)?)
        }
        "shells_needed" => {
            let (p, q, r, s) = th(a);
            let (n, fv) = hx::shells_needed(p, q, r, s)?;
            serde_json::json!([n, jf(fv)])
        }
        "turton_cost" => hx::turton_cost(
            arg(a, "area_m2"),
            arg(a, "P_barg"),
            a["material"].as_str().unwrap_or(""),
            a["kind"].as_str().unwrap_or(""),
            hx::CEPCI_TARGET_CENTRAL,
            arg(a, "min_units") as u32,
        )?,
        "towler_cost" => hx::towler_cost(
            arg(a, "area_m2"),
            a["material"].as_str().unwrap_or(""),
            a["kind"].as_str().unwrap_or(""),
            arg(a, "cepci_target"),
            arg(a, "min_units") as u32,
        )?,
        "indirect_factor" => jf(hx::indirect_factor(d)?),
        "annual_charge_factor" => jf(hx::annual_charge_factor(d, opt_arg(a, "crf"))),
        "capital_for_annual" => jf(hx::capital_for_annual(
            d,
            arg(a, "annual_USD_per_yr"),
            opt_arg(a, "crf"),
        )),
        "annualised_cost" => jf(hx::annualised_cost(
            d,
            arg(a, "capital_USD"),
            opt_arg(a, "crf"),
        )),
        "breakeven_crf" => jf(hx::breakeven_crf(
            d,
            arg(a, "annual_saving_USD_per_yr"),
            arg(a, "capital_USD"),
        )?),
        "size_and_cost" => {
            let u = match &a["U_case"] {
                Value::String(s) => hx::UCase::Key(s.clone()),
                v => hx::UCase::Value(num(v)),
            };
            hx::size_and_cost(
                d,
                arg(a, "duty_kW"),
                arg(a, "T_hot_in"),
                arg(a, "T_hot_out"),
                arg(a, "T_cold_in"),
                arg(a, "T_cold_out"),
                &u,
                &opts(a),
            )?
        }
        "breakeven_U" => jopt(hx::breakeven_u(
            d,
            arg(a, "duty_kW"),
            arg(a, "T_hot_in"),
            arg(a, "T_hot_out"),
            arg(a, "T_cold_in"),
            arg(a, "T_cold_out"),
            arg(a, "tci_breakeven_USD"),
            &opts(a),
        )?),
        other => {
            return Err(EngineError::data(
                "heat.json",
                format!("unknown exchanger function {other}"),
            ));
        }
    })
}

fn sim_input(src: &Value, fs: &Value, root: &Path) -> Result<SimulationResult, EngineError> {
    if let Some(cid) = src["flowsheet_case"].as_str() {
        let c = fs["cases"]
            .as_array()
            .and_then(|v| v.iter().find(|c| c["id"].as_str() == Some(cid)))
            .ok_or_else(|| EngineError::data("flowsheet.json", format!("no case {cid}")))?;
        return SimulationResult::from_sorted_value(&c["result"]);
    }
    let file = src["file"].as_str().unwrap_or("");
    let text = std::fs::read_to_string(root.join(file))
        .map_err(|e| EngineError::data(file, e.to_string()))?;
    SimulationResult::from_json_text(&text)
}

/// Heat integration (analysis and exchanger) against the golden tables and the stored results.
pub fn heat(
    g: &Golden,
    b: &dyn FluidProps,
    d: &EconomicsData,
    root: &Path,
) -> Result<Report, EngineError> {
    let t = g.load("heat.json")?;
    let fs = g.load("flowsheet.json")?;
    let mut rep = Report::new(&format!("heat integration (properties: {})", b.backend()));
    let note = "relative; temperatures (degC) to max(|x|, 273.15 K), kW, m2, USD to max(|x|, 1), others to max(|x|, 1e-6)";
    let mut hi = TreeAcc::new("HI", "heat-integration analysis vs Python", 1e-10, note);
    let mut outcome = Acc::exact(
        "HI-OUTCOME",
        "analysis: success, or the same exception class",
    );
    for c in t["cases"].as_array().into_iter().flatten() {
        let id = c["id"].as_str().unwrap_or("?");
        let py = &c["result"];
        let rust = sim_input(&c["input"], &fs, root)
            .and_then(|res| crate::heat::analyse(b, &res, num(&c["dT_min_K"])));
        match (py_error(py), rust) {
            (Some(cls), Err(e)) => outcome.add_bool(id, error_class_matches(cls, &e), || {
                format!("python {cls}, rust {e}")
            }),
            (Some(cls), Ok(_)) => {
                outcome.add_bool(id, false, || format!("python raised {cls}, rust succeeded"))
            }
            (None, Err(e)) => {
                outcome.add_bool(id, false, || format!("python succeeded, rust failed: {e}"))
            }
            (None, Ok(mut r)) => {
                outcome.add_bool(id, true, String::new);
                reconcile_fehe_ties(py, &mut r, num(&c["dT_min_K"]), id, &mut rep.findings);
                tree(&mut hi, id, "", py, &r);
            }
        }
    }
    hi.push(&mut rep);
    rep.push(outcome);
    let mut st = TreeAcc::new(
        "HI-STORED",
        "analysis vs stored results/simulations/heat_integration_*.json",
        1e-10,
        note,
    );
    for s in t["stored"].as_array().into_iter().flatten() {
        let file = s["file"].as_str().unwrap_or("");
        let src = serde_json::json!({"file": s["input_file"]});
        let stored = std::fs::read_to_string(root.join(file))
            .map_err(|e| EngineError::data(file, e.to_string()))
            .and_then(|txt| {
                serde_json::from_str::<Value>(&txt)
                    .map_err(|e| EngineError::data(file, e.to_string()))
            })?;
        let r = sim_input(&src, &fs, root)
            .and_then(|res| crate::heat::analyse(b, &res, num(&s["dT_min_K"])))?;
        tree(&mut st, file, "", &stored, &r);
    }
    st.push(&mut rep);
    let mut hx = TreeAcc::new(
        "HX",
        "exchanger sizing, cost, break-even (exchanger.py) vs Python",
        1e-10,
        "relative (scale as HI-NUM); breakeven_U bisects until hi/lo < 1 + 1e-10, so one flipped final decision stays below the gate",
    );
    let mut hx_out = Acc::exact(
        "HX-OUTCOME",
        "exchanger calls: success, or the same exception class",
    );
    for (i, c) in t["exchanger"].as_array().into_iter().flatten().enumerate() {
        let f = c["fn"].as_str().unwrap_or("?");
        let case = format!("{f}#{i}");
        let py = &c["out"];
        match (py_error(py), exchanger_call(d, f, &c["args"])) {
            (Some(cls), Err(e)) => hx_out.add_bool(&case, error_class_matches(cls, &e), || {
                format!("python {cls}, rust {e}")
            }),
            (Some(cls), Ok(_)) => hx_out.add_bool(&case, false, || {
                format!("python raised {cls}, rust succeeded")
            }),
            (None, Err(e)) => hx_out.add_bool(&case, false, || {
                format!("python succeeded, rust failed: {e}")
            }),
            (None, Ok(r)) => {
                hx_out.add_bool(&case, true, String::new);
                tree(&mut hx, &case, f, py, &r);
            }
        }
    }
    hx.push(&mut rep);
    rep.push(hx_out);
    if let Some((e, tl, m)) = b.lookup_stats() {
        rep.findings.push(format!(
            "tables back end (cumulative on this back end): {e} exact lookups, {tl} first-order Taylor lookups \
             (within 1e-7 relative of a recorded state), {m} misses"
        ));
    }
    Ok(rep)
}

// ===================================================================================== separation
/// A golden mapping (keys sorted by serde_json) back in the Python order: species in
/// `COMPONENTS` order, other keys after them in key order.
fn ordered_map(v: &Value) -> Vec<(String, f64)> {
    let mut out: Vec<(String, f64)> = v
        .as_object()
        .map(|m| m.iter().map(|(k, x)| (k.clone(), num(x))).collect())
        .unwrap_or_default();
    out.sort_by_key(|(k, _)| {
        crate::species::Species::from_name(k)
            .map(|s| s.index())
            .unwrap_or(99)
    });
    out
}

fn opt_i(a: &Value, k: &str) -> Option<i64> {
    a.get(k).and_then(Value::as_i64)
}

fn opt_s(a: &Value, k: &str) -> Option<String> {
    a.get(k).and_then(Value::as_str).map(str::to_string)
}

fn jflow(m: &[(String, f64)]) -> Value {
    Value::Object(
        m.iter()
            .map(|(k, v)| (k.clone(), crate::separation::jnf(*v)))
            .collect(),
    )
}

/// One separation call of the golden table.
fn separation_call(
    p: &crate::separation::SepParams,
    f: &str,
    a: &Value,
    root: &Path,
) -> Result<Value, EngineError> {
    use crate::separation as s;
    let jn = s::jnf;
    let species = |v: &Value| -> Result<Vec<(crate::species::Species, f64)>, EngineError> {
        ordered_map(v)
            .into_iter()
            .map(|(k, x)| {
                crate::species::Species::from_name(&k)
                    .map(|sp| (sp, x))
                    .ok_or_else(|| EngineError::Domain(format!("unknown species {k}")))
            })
            .collect()
    };
    let leak = |a: &Value| s::LeakArgs {
        alpha_h2_n2: opt_arg(a, "alpha_H2_N2").unwrap_or(f64::INFINITY),
        ..s::LeakArgs::default()
    };
    Ok(match f {
        "compression_power_kW" => s::compression_power_kw(
            p,
            arg(a, "n_kmol_h"),
            &species(&a["composition"])?,
            arg(a, "T_in_K"),
            arg(a, "P_in_bar"),
            arg(a, "P_out_bar"),
            opt_i(a, "stages"),
            opt_arg(a, "eta"),
            opt_arg(a, "cp_J_molK"),
        )?
        .to_json(),
        "default_stages" => Value::from(s::default_stages(
            p,
            arg(a, "P_in_bar"),
            arg(a, "P_out_bar"),
        )?),
        "psa_performance" => {
            let args = s::PsaArgs {
                tailgas_pressure_bar: opt_arg(a, "tailgas_pressure_bar"),
                target_purity: opt_arg(a, "target_purity"),
                basis: opt_s(a, "basis").unwrap_or_else(|| "cho2026_5A".into()),
                h2_recovery: opt_arg(a, "h2_recovery"),
                required_feed_pressure_bar: opt_arg(a, "required_feed_pressure_bar"),
                feed_temperature_k: opt_arg(a, "feed_temperature_K").unwrap_or(313.15),
                compressor_eta: opt_arg(a, "compressor_eta"),
                compressor_stages: opt_i(a, "compressor_stages"),
            };
            s::psa_performance(
                p,
                &ordered_map(&a["feed_kmol_h"]),
                arg(a, "feed_pressure_bar"),
                &args,
            )?
        }
        "membrane_separator" => {
            let ma = s::MembraneArgs {
                permeate_pressure_bar: opt_arg(a, "permeate_pressure_bar"),
                t_k: opt_arg(a, "T_K"),
                permeability: opt_s(a, "permeability"),
                thickness_m: opt_arg(a, "thickness_m"),
                n_exponent: opt_arg(a, "n_exponent"),
                flux_multiplier: opt_arg(a, "flux_multiplier").unwrap_or(1.0),
                n_profile: opt_i(a, "n_profile").unwrap_or(41) as usize,
            };
            s::membrane_separator(
                p,
                &ordered_map(&a["feed_kmol_h"]),
                arg(a, "area_m2"),
                arg(a, "feed_pressure_bar"),
                &ma,
            )?
        }
        "area_for_recovery" => {
            let ma = s::MembraneArgs {
                permeate_pressure_bar: opt_arg(a, "permeate_pressure_bar"),
                t_k: opt_arg(a, "T_K"),
                ..s::MembraneArgs::default()
            };
            jopt(s::area_for_recovery(
                p,
                &ordered_map(&a["feed_kmol_h"]),
                arg(a, "target_recovery"),
                arg(a, "feed_pressure_bar"),
                &ma,
            )?)
        }
        "evaluate_product" => s::evaluate_product(
            &ordered_map(&a["y_ppm"]),
            a["grade"].as_str().unwrap_or(""),
            opt_arg(a, "h2_frac"),
            "computed",
        )?,
        "psa_tail_h2_fraction_from_point" => jn(s::psa_tail_h2_fraction_from_point(
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "recovery"),
            arg(a, "purity"),
        )?),
        "psa_split" => {
            let (pr, tl) = s::psa_split(
                &ordered_map(&a["feed_kmol_h"]),
                arg(a, "recovery"),
                arg(a, "purity"),
            )?;
            serde_json::json!([jflow(&pr), jflow(&tl)])
        }
        "psa_recovery_at_purity" => jn(s::psa_recovery_at_purity(
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "purity"),
            arg(a, "y_tail_h2"),
        )?),
        "pinch_recovery" => jn(s::pinch_recovery(
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "P_feed_bar"),
            arg(a, "P_perm_bar"),
        )?),
        "membrane_with_leakage" => s::membrane_with_leakage(
            p,
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "area_m2"),
            arg(a, "P_feed_bar"),
            arg(a, "P_perm_bar"),
            arg(a, "T_K"),
            &leak(a),
        )?,
        "membrane_area_for_recovery" => jopt(s::membrane_area_for_recovery(
            p,
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "R"),
            arg(a, "P_feed_bar"),
            arg(a, "P_perm_bar"),
            arg(a, "T_K"),
            &leak(a),
        )?),
        "required_selectivity" => jopt(s::required_selectivity(
            p,
            &ordered_map(&a["feed_kmol_h"]),
            arg(a, "area"),
            arg(a, "P_feed_bar"),
            arg(a, "P_perm_bar"),
            arg(a, "T_K"),
            arg(a, "n2_limit_ppm"),
            &s::LeakArgs::default(),
        )?),
        "lhv_kW" => jn(s::lhv_kw(&ordered_map(&a["flows_kmol_h"]))),
        "mass_kg_h" => jn(s::mass_kg_h(&ordered_map(&a["flows_kmol_h"]))?),
        "closure" => {
            let outs: Vec<Vec<(String, f64)>> = a["outs"]
                .as_array()
                .into_iter()
                .flatten()
                .map(ordered_map)
                .collect();
            s::closure(&ordered_map(&a["feed"]), &outs)?
        }
        "gas_compression_kWh_per_kg_h2" => jn(s::gas_compression_kwh_per_kg_h2(
            p,
            &ordered_map(&a["flows"]),
            arg(a, "T_K"),
            arg(a, "P_in_bar"),
            arg(a, "P_out_bar"),
            arg(a, "h2_kg_h"),
            None,
        )?),
        "h2_compression_kWh_per_kg" => jn(s::h2_compression_kwh_per_kg(
            p,
            arg(a, "P_in_bar"),
            arg(a, "P_out_bar"),
            313.15,
            None,
        )?),
        "ammonia_slip" => s::ammonia_slip(p, &ordered_map(&a["cracked_gas_kmol_h"]), None)?,
        "compare_purification" => {
            let file = a["file"].as_str().unwrap_or("");
            let text = std::fs::read_to_string(root.join(file))
                .map_err(|e| EngineError::data(file, e.to_string()))?;
            s::compare_purification(p, &SimulationResult::from_json_text(&text)?)?
        }
        other => {
            return Err(EngineError::data(
                "separation.json",
                format!("unknown function {other}"),
            ));
        }
    })
}

/// Separation and compression against the golden calls and the stored comparison files.
///
/// Gates: algebraic functions 1e-10 relative; the membrane ODE outputs at a given area 1e-7
/// relative (Python LSODA at rtol 1e-10 against DOPRI5 at rtol 1e-12: the global error of the
/// Python integration is about 10 x its local tolerance; permeated and retained N2 of the
/// finite-selectivity model are compared relative to the feed N2 because the permeate is the
/// small difference of two integrated flows); searches (membrane areas by brentq with
/// xtol 1e-6 m2 or 1e-9 m2, selectivity by 80 bisections of log alpha, and every quantity
/// evaluated at the found area) 1e-5 relative.
pub fn separation(
    g: &Golden,
    p: &crate::separation::SepParams,
    root: &Path,
) -> Result<Report, EngineError> {
    let t = g.load("separation.json")?;
    let mut rep = Report::new("separation and compression");
    let note = "relative; scales as HI-NUM";
    let mut alg = TreeAcc::new(
        "SEP",
        "algebraic separation and compression functions",
        1e-10,
        note,
    );
    let mut ode = TreeAcc::new(
        "SEP-ODE",
        "membrane ODE (fixed area)",
        1e-7,
        "relative; flows of the leakage model relative to the feed flow of the species",
    );
    let mut srch = TreeAcc::new(
        "SEP-SEARCH",
        "area and selectivity searches, values at the found area",
        1e-5,
        note,
    );
    let mut outcome = Acc::exact(
        "SEP-OUTCOME",
        "separation calls: success, or the same exception class",
    );
    let mut results: BTreeMap<String, Value> = BTreeMap::new();
    for (i, c) in t["calls"].as_array().into_iter().flatten().enumerate() {
        let f = c["fn"].as_str().unwrap_or("?");
        let case = format!("{f}#{i}");
        let py = &c["out"];
        let r = separation_call(p, f, &c["args"], root);
        match (py_error(py), r) {
            (Some(cls), Err(e)) => outcome.add_bool(&case, error_class_matches(cls, &e), || {
                format!("python {cls}, rust {e}")
            }),
            (Some(cls), Ok(_)) => outcome.add_bool(&case, false, || {
                format!("python raised {cls}, rust succeeded")
            }),
            (None, Err(e)) => outcome.add_bool(&case, false, || {
                format!("python succeeded, rust failed: {e}")
            }),
            (None, Ok(rv)) => {
                outcome.add_bool(&case, true, String::new);
                match f {
                    "membrane_separator" => tree(&mut ode, &case, f, py, &rv),
                    "membrane_with_leakage" => {
                        let feed = ordered_map(&c["args"]["feed_kmol_h"]);
                        let fh2 = crate::process::result::get_or(&feed, "H2", 0.0);
                        let fn2 = crate::process::result::get_or(&feed, "N2", 0.0);
                        let perm =
                            num(&py["permeate_kmol_h"]["H2"]) + num(&py["permeate_kmol_h"]["N2"]);
                        let sc = move |path: &str, key: &str| -> f64 {
                            if path.ends_with("_kmol_h/N2") {
                                fn2
                            } else if path.ends_with("_kmol_h/H2") {
                                fh2
                            } else if key == "n2_in_permeate_ppm" {
                                if perm > 0.0 { 1e6 * fn2 / perm } else { 1.0 }
                            } else {
                                key_scale(key)
                            }
                        };
                        tree_with(&mut ode, &case, f, py, &rv, &sc);
                    }
                    "area_for_recovery"
                    | "membrane_area_for_recovery"
                    | "required_selectivity"
                    | "compare_purification" => {
                        tree(&mut srch, &case, f, py, &rv);
                        if f == "compare_purification" {
                            results
                                .insert(c["args"]["file"].as_str().unwrap_or("").to_string(), rv);
                        }
                    }
                    _ => tree(&mut alg, &case, f, py, &rv),
                }
            }
        }
    }
    alg.push(&mut rep);
    ode.push(&mut rep);
    srch.push(&mut rep);
    rep.push(outcome);
    let mut st = TreeAcc::new(
        "SEP-STORED",
        "compare_purification vs stored results/simulations/separation_*.json",
        1e-5,
        note,
    );
    for s in t["stored"].as_array().into_iter().flatten() {
        let file = s["file"].as_str().unwrap_or("");
        let input = s["input_file"].as_str().unwrap_or("");
        let stored: Value = std::fs::read_to_string(root.join(file))
            .map_err(|e| EngineError::data(file, e.to_string()))
            .and_then(|txt| {
                serde_json::from_str(&txt).map_err(|e| EngineError::data(file, e.to_string()))
            })?;
        let mut sv = stored;
        if let Some(o) = sv.as_object_mut() {
            o.remove("metadata");
        }
        match results.get(input) {
            Some(rv) => tree(&mut st, file, "", &sv, rv),
            None => st
                .keys
                .add_bool(file, false, || format!("{input} was not recomputed")),
        }
    }
    st.push(&mut rep);
    Ok(rep)
}
