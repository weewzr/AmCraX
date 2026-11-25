//! Heat-integration (pinch) analysis of one `SimulationResult` (port of Python
//! `heat_integration/analysis.py`). The result is the JSON of Python's
//! `HeatIntegrationResult.model_dump()`.

use super::pinch::{Curve, PinchResult, problem_table};
use super::streams::{ASSUMPTIONS, extract_streams};
use crate::error::EngineError;
use crate::process::result::{SimulationResult, get_or, jf, jo, molar_mass};
use crate::props::FluidProps;
use crate::pyops::{fmt_f, fmt_g, linspace, py_repr, py_sum};
use crate::species::Species;
use serde_json::{Value, json};

const C0: f64 = 273.15;
/// ASSUMPTION: overall U of the FEHE (gas-gas), W/(m2 K).
pub const U_ASSUMED_W_M2K: f64 = 50.0;
/// Range of U, W/(m2 K).
pub const U_RANGE_W_M2K: (f64, f64) = (10.0, 100.0);
/// `U_NOTE`.
pub const U_NOTE: &str = "ASSUMPTION: overall U for a gas-gas exchanger, central 50 W/(m2 K), range 10-100 W/(m2 K) (typical order of magnitude for gas-gas service; not taken from a verified textbook table). Area = UA/U is an order-of-magnitude sizing estimate, not a design.";

fn arr(v: &[f64]) -> Value {
    Value::Array(v.iter().map(|x| jf(*x)).collect())
}

fn arr_c(v: &[f64]) -> Value {
    Value::Array(v.iter().map(|x| jf(x - C0)).collect())
}

fn targets(label: &str, curves: &[&Curve], dt: f64) -> Result<(Value, PinchResult), EngineError> {
    let r = problem_table(curves, dt)?;
    let b = &r.boundaries_shifted_k;
    let rows: Vec<Value> = (0..b.len().saturating_sub(1))
        .map(|i| {
            json!({
                "T_shifted_hi_C": jf(b[i] - C0), "T_shifted_lo_C": jf(b[i + 1] - C0),
                "deficit_kW": jf(r.interval_deficit_kw[i]), "cascade_out_kW": jf(r.cascade_kw[i + 1]),
            })
        })
        .collect();
    let c = |x: Option<f64>| jo(x.map(|v| v - C0));
    let t = json!({
        "label": label, "dT_min_K": jf(dt), "hot_utility_kW": jf(r.hot_utility_kw),
        "cold_utility_kW": jf(r.cold_utility_kw), "total_hot_streams_kW": jf(r.total_hot_kw),
        "total_cold_streams_kW": jf(r.total_cold_kw),
        "heat_recovery_kW": jf(r.total_cold_kw - r.hot_utility_kw),
        "pinch_shifted_C": c(r.pinch_shifted_k), "pinch_hot_C": c(r.pinch_hot_k()), "pinch_cold_C": c(r.pinch_cold_k()),
        "threshold_problem": r.threshold,
        "energy_balance_residual_kW": jf((r.hot_utility_kw - r.cold_utility_kw) - (r.total_cold_kw - r.total_hot_kw)),
        "hot_composite_H_kW": arr(&r.hot_composite.0), "hot_composite_T_C": arr_c(&r.hot_composite.1),
        "cold_composite_H_kW": arr(&r.cold_composite.0), "cold_composite_T_C": arr_c(&r.cold_composite.1),
        "gcc_H_kW": arr(&r.cascade_kw), "gcc_T_shifted_C": arr_c(&r.boundaries_shifted_k), "problem_table": rows,
    });
    Ok((t, r))
}

fn hi_stream(c: &Curve, included: &[&str]) -> Value {
    let hot = c.kind == "hot";
    json!({
        "id": c.id, "name": c.name, "kind": c.kind,
        "supply_temperature_C": jf((if hot { c.t_max_k() } else { c.t_min_k() }) - C0),
        "target_temperature_C": jf((if hot { c.t_min_k() } else { c.t_max_k() }) - C0),
        "duty_kW": jf(c.duty_kw()), "included_in": included,
        "curve_T_C": arr_c(&c.t_k), "curve_H_kW": arr(&c.h_kw),
    })
}

/// `_lmtd(d1, d2)`.
fn lmtd(d1: f64, d2: f64) -> Option<f64> {
    if d1 <= 0.0 || d2 <= 0.0 {
        return None;
    }
    Some(if (d1 - d2).abs() < 1e-9 {
        d1
    } else {
        (d1 - d2) / (d1 / d2).ln()
    })
}

fn block_duty(res: &SimulationResult, bid: &str) -> Option<f64> {
    res.block(bid).and_then(|b| b.duty_kw)
}

/// FEHE assessment (`_fehe`) and the values the analysis reuses.
struct Fehe {
    json: Value,
    present: bool,
    duty_kw: f64,
    duty_source: String,
    cold_in_c: f64,
    cold_out_c: f64,
    min_dt: f64,
    cross: bool,
    violation: bool,
}

fn fehe(
    res: &SimulationResult,
    feed: &Curve,
    cracked: &Curve,
    dt: f64,
) -> Result<Fehe, EngineError> {
    let t = |sid: &str| {
        res.stream(sid)
            .and_then(|s| s.temperature_c)
            .map(|v| v + C0)
    };
    let t5 = t("S5").ok_or_else(|| EngineError::Domain("S5 temperature".into()))?;
    let t2 = match t("S2") {
        Some(v) => v,
        None => match feed.t_switch_k.filter(|v| *v != 0.0) {
            Some(v) => v,
            None => feed.t_min_k(),
        },
    };
    let present = res.inputs.heat_integration && t("S3").is_some() && t("S6").is_some();
    let (t3, t6, q, src) = if present {
        let t3 = t("S3").unwrap_or(f64::NAN);
        let t6 = t("S6").unwrap_or(f64::NAN);
        let q_sim = block_duty(res, "FEHE");
        let q = match q_sim {
            Some(v) => v.abs(),
            None => feed.h_at(t3) - feed.h_at(t2),
        };
        let src = if q_sim.is_some() {
            "FEHE block duty (simulation result)"
        } else {
            "model cold-side enthalpy change S2->S3"
        };
        (t3, t6, q, src.to_string())
    } else {
        let t3 = t5 - res.inputs.fehe_hot_end_approach_k;
        let q = feed.h_at(t3) - feed.h_at(t2);
        let t6 = cracked.t_at(cracked.h_at(t5) - q);
        (
            t3,
            t6,
            q,
            "MODEL ESTIMATE (FEHE absent in simulation): cold outlet = S5 T - fehe_hot_end_approach_K, duty from model H-T curves"
                .to_string(),
        )
    };
    let qs = linspace(0.0, q, 201);
    let (hh5, hc3) = (cracked.h_at(t5), feed.h_at(t3));
    let th: Vec<f64> = qs.iter().map(|x| cracked.t_at(hh5 - x)).collect();
    let tc: Vec<f64> = qs.iter().map(|x| feed.t_at(hc3 - x)).collect();
    let dts: Vec<f64> = th.iter().zip(tc.iter()).map(|(a, b)| a - b).collect();
    let lm = lmtd(t5 - t3, t6 - t2);
    let mut ua_seg = None;
    if dts.iter().all(|d| *d > 0.0) {
        let mut terms = Vec::with_capacity(qs.len() - 1);
        for i in 0..qs.len() - 1 {
            terms.push((qs[i + 1] - qs[i]) / lmtd(dts[i], dts[i + 1]).unwrap_or(f64::NAN));
        }
        ua_seg = Some(py_sum(terms));
    }
    let ua_lm = lm.filter(|v| *v != 0.0).map(|l| q / l);
    let ua_for_area = ua_seg.or(ua_lm);
    let area = ua_for_area.map(|u| u * 1000.0 / U_ASSUMED_W_M2K);
    let area_rng: Vec<f64> = match ua_for_area {
        Some(u) => vec![u * 1000.0 / U_RANGE_W_M2K.1, u * 1000.0 / U_RANGE_W_M2K.0],
        None => vec![],
    };
    // numpy min (NaN propagates)
    let dmin = dts.iter().copied().fold(f64::INFINITY, |m, x| {
        if x.is_nan() || m.is_nan() {
            f64::NAN
        } else if x < m {
            x
        } else {
            m
        }
    });
    let every10 = |v: &[f64], c0: f64| -> Value {
        Value::Array(v.iter().step_by(10).map(|x| jf(x - c0)).collect())
    };
    let json = json!({
        "present_in_simulation": present, "duty_kW": jf(q), "duty_source": src,
        "hot_in_C": jf(t5 - C0), "hot_out_C": jf(t6 - C0), "cold_in_C": jf(t2 - C0), "cold_out_C": jf(t3 - C0),
        "hot_end_approach_K": jf(t5 - t3), "cold_end_approach_K": jf(t6 - t2),
        "min_internal_approach_K": jf(dmin), "temperature_cross": dmin < 0.0, "approach_violation": dmin < dt,
        "lmtd_K": jo(lm), "ua_lmtd_kW_K": jo(ua_lm), "ua_segmented_kW_K": jo(ua_seg),
        "U_assumed_W_m2K": U_ASSUMED_W_M2K, "U_range_W_m2K": [U_RANGE_W_M2K.0, U_RANGE_W_M2K.1],
        "area_m2": jo(area), "area_range_m2": arr(&area_rng), "U_note": U_NOTE,
        "hot_side_duty_model_kW": jf(cracked.h_at(t5) - cracked.h_at(t6)),
        "cold_side_duty_model_kW": jf(feed.h_at(t3) - feed.h_at(t2)),
        "profile_duty_kW": every10(&qs, 0.0), "profile_hot_T_C": every10(&th, C0), "profile_cold_T_C": every10(&tc, C0),
    });
    Ok(Fehe {
        json,
        present,
        duty_kw: q,
        duty_source: src,
        cold_in_c: t2 - C0,
        cold_out_c: t3 - C0,
        min_dt: dmin,
        cross: dmin < 0.0,
        violation: dmin < dt,
    })
}

fn h2_kg_h(res: &SimulationResult) -> Option<f64> {
    if let Some(v) = res.kpis.h2_product_kg_h.filter(|v| *v != 0.0) {
        return Some(v);
    }
    let s = res.stream("H2PROD")?;
    let h2 = get_or(&s.component_mole_flow_kmol_h, "H2", 0.0);
    if h2 != 0.0 {
        Some(h2 * molar_mass(Species::H2))
    } else {
        None
    }
}

#[allow(clippy::too_many_arguments)]
fn row(
    id: &str,
    label: &str,
    heat: f64,
    cool: f64,
    rec: f64,
    tail: f64,
    red: f64,
    spec: Option<f64>,
    basis: &str,
) -> Value {
    json!({
        "id": id, "label": label, "external_heating_kW": jf(heat), "external_cooling_kW": jf(cool),
        "process_heat_recovered_kW": jf(rec), "tailgas_heat_used_kW": jf(tail),
        "reduction_vs_no_recovery": jf(red), "specific_heat_demand_kWh_per_kgH2": jo(spec), "basis": basis,
    })
}

/// `analyse(result, dT_min_K)`: the JSON of Python's `HeatIntegrationResult`.
pub fn analyse(
    props: &dyn FluidProps,
    result: &SimulationResult,
    dt_min_k: f64,
) -> Result<Value, EngineError> {
    if dt_min_k <= 0.0 {
        return Err(EngineError::Domain("dT_min_K must be > 0".into()));
    }
    let x = extract_streams(props, result)?;
    let (feed, rxn, cracked) = (&x.feed, &x.reaction, &x.cracked);
    let mut warnings = x.warnings.clone();
    let mut notes: Vec<String> = Vec::new();
    let h2 = h2_kg_h(result);
    if !result.status.converged {
        warnings.push(
            "Input simulation is not marked converged: heat-integration numbers inherit that status.".into(),
        );
    }
    let process = [feed, rxn, cracked];
    let (tp, rp) = targets("Process streams only", &process, dt_min_k)?;
    let mut tf: Option<(Value, PinchResult)> = None;
    if let Some(fl) = &x.flue {
        tf = Some(targets(
            "Process streams + tail-gas flue gas",
            &[feed, rxn, cracked, fl],
            dt_min_k,
        )?);
    }
    let fe = fehe(result, feed, cracked, dt_min_k)?;
    if fe.cross {
        warnings.push(format!(
            "FEHE temperature cross: minimum internal approach {} K < 0.",
            fmt_f(fe.min_dt, 1)
        ));
    } else if fe.violation {
        warnings.push(format!(
            "FEHE minimum internal approach {} K is below dT_min = {} K.",
            fmt_f(fe.min_dt, 1),
            py_repr(dt_min_k)
        ));
    }
    let total_cold = feed.duty_kw() + rxn.duty_kw();
    let total_hot = cracked.duty_kw();
    let spec = |q: f64| h2.map(|h| q / h);
    let red = |q: f64| {
        if total_cold <= 0.0 {
            0.0
        } else {
            1.0 - q / total_cold
        }
    };
    let mut rows = vec![row(
        "a",
        "(a) No heat recovery",
        total_cold,
        total_hot,
        0.0,
        0.0,
        0.0,
        spec(total_cold),
        "Model H-T curves: all cold duties (S1->S4 + reaction) external; all cracked-gas heat to cooling.",
    )];
    let qf = fe.duty_kw;
    let heat_b = total_cold - qf;
    rows.push(row(
        "b",
        "(b) Feed/effluent exchanger only",
        heat_b,
        total_hot - qf,
        qf,
        0.0,
        red(heat_b),
        spec(heat_b),
        &format!(
            "FEHE duty: {}; remaining duties from model H-T curves.",
            fe.duty_source
        ),
    ));
    if let Some(flue) = &x.flue {
        let (t1, t2, t3, t4) = (
            feed.t_min_k(),
            fe.cold_in_c + C0,
            fe.cold_out_c + C0,
            feed.t_max_k(),
        );
        let mut resid: Vec<Curve> = vec![rxn.clone()];
        if t2 > t1 + 1e-6 {
            resid.push(feed.slice(t1, t2, Some("VAPORISER_DUTY"))?);
        }
        if t4 > t3 + 1e-6 {
            resid.push(feed.slice(t3, t4, Some("TRIM_HEATER_DUTY"))?);
        }
        let mut all: Vec<&Curve> = resid.iter().collect();
        all.push(flue);
        let rc = problem_table(&all, dt_min_k)?;
        let resid_total = py_sum(resid.iter().map(Curve::duty_kw));
        let used = resid_total - rc.hot_utility_kw;
        rows.push(row(
            "c",
            "(c) FEHE + tail-gas firing",
            rc.hot_utility_kw,
            total_hot - qf,
            qf,
            used,
            red(rc.hot_utility_kw),
            spec(rc.hot_utility_kw),
            &format!(
                "Residual duties after FEHE (vaporiser S1->S2, trim heater S3->S4, isothermal reaction) vs flue gas {}->{} degC by problem table at dT_min: flue heat below T_reactor + dT_min cannot supply the reaction heat. Unused flue heat {} kW (leaves via stack/flue cooler).",
                fmt_f(flue.t_max_k() - C0, 0),
                fmt_f(flue.t_min_k() - C0, 0),
                fmt_f(flue.duty_kw() - used, 1)
            ),
        ));
    }
    rows.push(row(
        "d1",
        &format!(
            "(d) Pinch target, process only (dT_min {} K)",
            fmt_g(dt_min_k, 6)
        ),
        rp.hot_utility_kw,
        rp.cold_utility_kw,
        rp.total_cold_kw - rp.hot_utility_kw,
        0.0,
        red(rp.hot_utility_kw),
        spec(rp.hot_utility_kw),
        "Problem-table target (minimum utilities), process streams only.",
    ));
    if let Some((_, rf)) = &tf {
        let flue_used = rp.hot_utility_kw - rf.hot_utility_kw;
        rows.push(row(
            "d2",
            &format!("(d) Pinch target incl. tail-gas flue gas (dT_min {} K)", fmt_g(dt_min_k, 6)),
            rf.hot_utility_kw,
            rp.cold_utility_kw,
            rp.total_cold_kw - rp.hot_utility_kw,
            flue_used,
            red(rf.hot_utility_kw),
            spec(rf.hot_utility_kw),
            &format!(
                "Problem-table target with flue gas as a hot stream. Process cooling = process-only target; unused flue heat {} kW.",
                fmt_f(rf.cold_utility_kw - rp.cold_utility_kw, 1)
            ),
        ));
        if rf.hot_utility_kw > 1e-6 {
            notes.push(format!(
                "Even at the pinch target with tail-gas firing, {} kW must be imported (e.g. by burning extra NH3 or H2, or electric heating).",
                fmt_f(rf.hot_utility_kw, 1)
            ));
        } else {
            notes.push(
                "At the pinch target the tail-gas flue gas covers all heating: no external heat import needed.".into(),
            );
        }
    }

    // consistency of model curves vs simulated block duties (reported, never tuned)
    let mut checks: Vec<(String, f64, Option<f64>, Option<f64>)> = Vec::new();
    let mut chk = |item: &str, model: f64, sim: Option<f64>| {
        let rel = match sim {
            Some(s) if s != 0.0 => Some((model - s) / s.abs()),
            _ => None,
        };
        checks.push((item.to_string(), model, sim, rel));
    };
    let bd = |b: &str| block_duty(result, b);
    let fehe_term = if fe.present {
        bd("FEHE")
            .filter(|v| *v != 0.0)
            .map(f64::abs)
            .unwrap_or(0.0)
    } else {
        0.0
    };
    let sim_feed = match (bd("VAPORIZR"), bd("HEATER")) {
        (Some(v), Some(h)) => Some(v + h + fehe_term),
        _ => None,
    };
    chk(
        "Feed heating S1->S4 (VAPORIZR+FEHE cold+HEATER)",
        feed.duty_kw(),
        sim_feed,
    );
    if let Some(t2) = result.stream("S2").and_then(|s| s.temperature_c) {
        chk(
            "Vaporiser S1->S2",
            feed.h_at(t2 + C0) - feed.h_at(feed.t_min_k()),
            bd("VAPORIZR"),
        );
    }
    let sim_hot = bd("COOLER").map(|c| c.abs() + fehe_term);
    chk(
        "Cracked gas S5->S7 (FEHE hot+COOLER)",
        cracked.duty_kw(),
        sim_hot,
    );
    if let Some(fl) = &x.flue {
        chk(
            "Flue gas FLUE->STACK (FLUEHX)",
            fl.duty_kw(),
            bd("FLUEHX").map(f64::abs),
        );
    }
    for (item, _, _, rel) in &checks {
        if let Some(r) = rel
            && r.abs() > 0.03
        {
            warnings.push(format!(
                "Model vs simulated duty differ by {} % for '{item}' (different property methods/reference; reported, not adjusted).",
                fmt_f(100.0 * r, 1)
            ));
        }
    }
    let mut streams = vec![
        hi_stream(feed, &["process", "with_flue"]),
        hi_stream(rxn, &["process", "with_flue"]),
        hi_stream(cracked, &["process", "with_flue"]),
    ];
    if let Some(fl) = &x.flue {
        streams.push(hi_stream(fl, &["with_flue"]));
    }
    notes.push("Targets are thermodynamic minima (problem table); they are not an exchanger network design.".into());
    let mut assumptions: Vec<String> = ASSUMPTIONS.iter().map(|s| s.to_string()).collect();
    assumptions.push(U_NOTE.to_string());
    Ok(json!({
        "case_id": result.case_id, "source": "python_model", "input_source": result.source,
        "dT_min_K": jf(dt_min_k), "reactor_temperature_C": jf(x.t_reactor_k - C0), "h2_product_kg_h": jo(h2),
        "reaction_duty_source": x.reaction_source,
        "feed_saturation_temperature_C": jf(x.feed_meta.t_sat_k - C0),
        "feed_latent_heat_kW": jf(x.feed_meta.latent_heat_kw),
        "streams": streams, "targets_process": tp, "targets_with_flue": tf.map(|t| t.0).unwrap_or(Value::Null),
        "configurations": rows, "fehe": fe.json,
        "consistency": checks.iter().map(|(i, m, s, r)| json!({
            "item": i, "model_kW": jf(*m), "simulated_kW": jo(*s), "rel_deviation": jo(*r)})).collect::<Vec<_>>(),
        "assumptions": assumptions, "warnings": warnings, "notes": notes,
    }))
}
