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
use crate::error::EngineError;
use crate::odata::OValue;
use crate::process::flowsheet::{eos_from_name, run_python_case};
use crate::process::result::CaseInputs;
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
    Ok(rep)
}

/// A golden `SimulationResult` (sorted keys) as an ordered value (species in COMPONENTS order).
pub fn golden_result_ov(v: &Value) -> OValue {
    crate::process::result::ov_components_order(v)
}
