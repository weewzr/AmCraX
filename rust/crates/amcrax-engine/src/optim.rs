//! Optimisation objectives and Pareto analysis (port of Python `optimisation/evaluate.py` and
//! `optimisation/pareto.py`, and the constraint functions of `optimisation/problems.py`).
//!
//! `evaluate_result` is the batch objective of the optimiser: one `SimulationResult` to the flat
//! dict of LCOH (legacy `compute_lcoh`), carbon intensity (`environmental.carbon_intensity`, the
//! simplified accounting, not an LCA), KPIs and the cracked-gas compression to the PSA feed
//! pressure. The optimiser itself (SciPy `differential_evolution` with Sobol initialisation and a
//! `NonlinearConstraint`, SLSQP polish, epsilon-constraint SLSQP) stays in Python.

use crate::carbon::embedded_factors;
use crate::economics::lcoh::{EconAssumptions, LcohInput, compute_lcoh};
use crate::economics::reference::EconomicsData;
use crate::error::EngineError;
use crate::odata::OValue;
use crate::process::result::{LHV_KJ_PER_MOL, SimulationResult, jf, jo, molar_mass};
use crate::pyops::py_max;
use crate::separation::{SepParams, compression_power_kw};
use crate::species::Species;
use serde_json::{Map, Value, json};

/// `PARETO_OBJECTIVES` in dict order.
pub const PARETO_OBJECTIVES: [(&str, &str); 5] = [
    ("lcoh_USD_per_kg", "min"),
    ("lhv_efficiency", "max"),
    ("h2_yield_overall", "max"),
    ("carbon_intensity_kgCO2e_per_kgH2", "min"),
    ("nh3_conversion", "max"),
];

/// `OVERLAYS`: (suffix, heat_source, nh3_route).
pub const OVERLAYS: [(&str, &str, &str); 4] = [
    ("", "ammonia", "grey"),
    ("ng_grey", "natural_gas", "grey"),
    ("nh3_green", "ammonia", "green"),
    ("ng_green", "natural_gas", "green"),
];

fn env_num(f: &OValue, path: &[&str]) -> Result<f64, EngineError> {
    f.num_v("environmental.yaml", path)
}

/// `environmental.carbon_intensity(result, "<route>/<heating>", grid=grid)`: (total, breakdown
/// [upstream_ammonia, transport, electricity, external_heat], h2_product_kg_h).
pub fn env_carbon_intensity(
    res: &SimulationResult,
    route: &str,
    heat: &str,
    grid: &str,
) -> Result<(f64, [f64; 4], f64), EngineError> {
    let f = embedded_factors();
    let k = &res.kpis;
    let h2 = match k.h2_product_kg_h {
        Some(v) => v,
        None => k
            .h2_product_kmol_h
            .map(|v| v * molar_mass(Species::H2))
            .ok_or_else(|| EngineError::Domain("SimulationResult has no H2 product flow".into()))?,
    };
    if h2.is_nan() || h2 <= 0.0 {
        return Err(EngineError::Domain(
            "H2 product flow must be > 0 to compute a carbon intensity".into(),
        ));
    }
    let nh3_kmol = match res.stream("FEED").and_then(|s| {
        s.component_mole_flow_kmol_h
            .iter()
            .find(|x| x.0 == "NH3")
            .map(|x| x.1)
    }) {
        Some(v) => v,
        None => res.inputs.feed_total_kmol_h * (1.0 - res.inputs.feed_h2o_mole_frac),
    };
    let nh3_kg = nh3_kmol * molar_mass(Species::NH3);
    let deficit = match k.net_fuel_heat_deficit_kw {
        Some(v) => v,
        None => match (k.total_external_heating_kw, k.tailgas_combustion_heat_kw) {
            (Some(a), Some(b)) => a - b,
            _ => {
                return Err(EngineError::Domain(
                    "SimulationResult lacks net_fuel_heat_deficit_kW".into(),
                ));
            }
        },
    };
    let deficit = py_max(0.0, deficit);
    let pump = match k.pump_power_kw {
        Some(v) if v != 0.0 => v,
        _ => 0.0,
    };
    let ef_nh3 = env_num(f, &["upstream_ammonia", route])?;
    let ef_grid = env_num(f, &["electricity", grid])?;
    let ef_ship = env_num(f, &["transport", "ship_ef"])?;
    let dist = env_num(f, &["transport", "distance_km"])?;
    let ef_ng = env_num(f, &["heating", "natural_gas_combustion"])?;
    let eta_f = env_num(f, &["heating", "fired_heater_efficiency_lhv"])?;
    let eta_e = env_num(f, &["heating", "electric_heater_efficiency"])?;
    let mut elec = pump;
    let mut heat_kg_h = 0.0;
    let fuel_kw = deficit / eta_f;
    let lhv_kg = LHV_KJ_PER_MOL[1].1 / molar_mass(Species::NH3) * 1000.0;
    let ship = ef_ship * dist / 1000.0;
    match heat {
        "natural_gas" => {
            let ng = fuel_kw * 3600.0 / 1e6;
            heat_kg_h = ng / 1000.0 * ef_ng;
        }
        "self_firing" => {
            let fuel = fuel_kw * 3600.0 / lhv_kg;
            heat_kg_h = fuel * (ef_nh3 + ship);
        }
        "electric" => elec += deficit / eta_e,
        other => {
            return Err(EngineError::Domain(format!(
                "unknown heating option {other:?}"
            )));
        }
    }
    let br = [
        nh3_kg * ef_nh3 / h2,
        nh3_kg * ship / h2,
        elec * ef_grid / h2,
        heat_kg_h / h2,
    ];
    Ok((br[0] + br[1] + br[2] + br[3], br, h2))
}

/// `compression_requirement(result, required_bar)`: (P(S7), required, power kW, stages).
pub fn compression_requirement(
    p: &SepParams,
    res: &SimulationResult,
    required_bar: Option<f64>,
) -> Result<(Option<f64>, f64, f64, u32), EngineError> {
    let req = match required_bar {
        Some(v) => v,
        None => p.raw.num(
            "separation.yaml",
            &["psa", "feed_pressure_requirement_bar", "default"],
        )?,
    };
    let Some(s7) = res.stream("S7").filter(|s| s.pressure_bar.is_some()) else {
        return Ok((None, req, 0.0, 0));
    };
    let ps = s7.pressure_bar.unwrap_or(f64::NAN);
    if ps >= req {
        return Ok((Some(ps), req, 0.0, 0));
    }
    let comp: Vec<(Species, f64)> = s7
        .component_mole_flow_kmol_h
        .iter()
        .filter(|(_, v)| *v != 0.0 && *v > 0.0)
        .filter_map(|(k, v)| Species::from_name(k).map(|s| (s, *v)))
        .collect();
    let n = crate::pyops::py_sum(comp.iter().map(|x| x.1));
    let t = s7.temperature_c.unwrap_or(f64::NAN) + 273.15;
    let c = compression_power_kw(p, n, &comp, t, ps, req, None, None, None)?;
    Ok((Some(ps), req, c.power_kw, c.stages))
}

/// Options of [`evaluate_result`].
#[derive(Debug, Clone, PartialEq)]
pub struct EvalOpts {
    pub heat_source: String,
    pub nh3_route: String,
    pub grid: String,
    pub include_compression: bool,
    pub nh3_price_usd_per_t: Option<f64>,
}

impl Default for EvalOpts {
    fn default() -> Self {
        EvalOpts {
            heat_source: "ammonia".into(),
            nh3_route: "grey".into(),
            grid: "singapore_2024".into(),
            include_compression: true,
            nh3_price_usd_per_t: None,
        }
    }
}

/// `evaluate_result(result, heat_source, nh3_route, grid, include_compression, nh3_price)`.
pub fn evaluate_result(
    d: &EconomicsData,
    p: &SepParams,
    res: &SimulationResult,
    o: &EvalOpts,
) -> Result<Value, EngineError> {
    let k = &res.kpis;
    let (ps, req, w_comp, _) = if o.include_compression {
        let (a, b, c, s) = compression_requirement(p, res, None)?;
        (a, Some(b), c, s)
    } else {
        (None, None, 0.0, 0)
    };
    let mut a = EconAssumptions::defaults(d)?;
    a.compression_power_kw += w_comp;
    match o.heat_source.as_str() {
        "ammonia" => a.heat_import_mode = "ammonia_fuel".into(),
        "natural_gas" => a.heat_import_mode = "fired_heat".into(),
        "electric" => {
            let eta = embedded_factors().num_v(
                "environmental.yaml",
                &["heating", "electric_heater_efficiency"],
            )?;
            a.heat_import_mode = "fired_heat".into();
            a.fired_heat_price_usd_per_kj = a.electricity_price_usd_per_kwh / 3600.0 / eta;
        }
        other => {
            return Err(EngineError::Domain(format!(
                "unknown heat_source {other:?}; use one of ('ammonia', 'natural_gas', 'electric')"
            )));
        }
    }
    if let Some(pr) = o.nh3_price_usd_per_t {
        a.set("nh3_price_USD_per_t", &jf(pr))?;
    }
    let lc = compute_lcoh(d, &LcohInput::from_result_json(&res.to_json())?, &a)?;
    let heating = match o.heat_source.as_str() {
        "ammonia" => "self_firing",
        "natural_gas" => "natural_gas",
        _ => "electric",
    };
    let (ci_tot, br, h2_ci) = env_carbon_intensity(res, &o.nh3_route, heating, &o.grid)?;
    let grid_ef = embedded_factors().num_v("environmental.yaml", &["electricity", &o.grid])?;
    let ci_comp = w_comp * grid_ef / h2_ci;
    let num = |v: &Value| v.as_f64().unwrap_or(f64::NAN);
    let y_nh3 = res
        .stream("S5")
        .and_then(|s| s.mole_frac.iter().find(|x| x.0 == "NH3").map(|x| x.1));
    let mut out = Map::new();
    let mut put = |kk: &str, v: Value| {
        out.insert(kk.to_string(), v);
    };
    put("case_id", json!(res.case_id));
    put("source", json!(res.source));
    put("heat_source", json!(o.heat_source));
    put(
        "ci_scenario",
        json!(format!(
            "{}/{} grid={} (simplified carbon-intensity accounting, not an LCA)",
            o.nh3_route, heating, o.grid
        )),
    );
    put("lcoh_USD_per_kg", jf(num(&lc["lcoh_USD_per_kg"])));
    put("carbon_intensity_kgCO2e_per_kgH2", jf(ci_tot + ci_comp));
    put("lhv_efficiency", jo(k.lhv_efficiency));
    put("nh3_conversion", jo(k.nh3_conversion));
    put("h2_yield_overall", jo(k.h2_yield_overall));
    put("h2_product_kg_h", jo(k.h2_product_kg_h));
    put("h2_purity_mole_frac", jo(k.h2_purity_mole_frac));
    put(
        "nh3_feed_kg_per_kgH2",
        jf(num(&lc["kg_nh3_feed_per_kg_h2"])),
    );
    put(
        "nh3_total_kg_per_kgH2",
        jf(num(&lc["kg_nh3_feed_per_kg_h2"]) + num(&lc["kg_nh3_fuel_per_kg_h2"])),
    );
    put("total_external_heating_kW", jo(k.total_external_heating_kw));
    put("net_fuel_heat_deficit_kW", jo(k.net_fuel_heat_deficit_kw));
    put(
        "specific_heat_demand_kWh_per_kgH2",
        jo(k.specific_heat_demand_kwh_per_kgh2),
    );
    put("cracked_gas_nh3_mole_frac", jo(y_nh3));
    put("psa_feed_pressure_bar", jo(ps));
    put("psa_feed_pressure_requirement_bar", jo(req));
    put("compression_power_kW", jf(w_comp));
    put("pump_power_kW", jo(k.pump_power_kw));
    put("recovered_heat_kW", jo(k.recovered_heat_kw));
    if let Some(m) = lc["breakdown_USD_per_kg"].as_object() {
        for (c, v) in m {
            put(&format!("lcoh_{c}_USD_per_kg"), jf(num(v)));
        }
    }
    put("ci_upstream_ammonia", jf(br[0]));
    put("ci_transport", jf(br[1]));
    put("ci_electricity", jf(br[2] + ci_comp));
    put("ci_external_heat", jf(br[3]));
    if let Some(dt) = res.block("FEHE").and_then(|b| {
        b.details
            .iter()
            .find(|x| x.0 == "min_internal_dT_K")
            .and_then(|x| match &x.1 {
                crate::process::result::Detail::Num(v) => Some(*v),
                _ => None,
            })
    }) {
        put("fehe_min_internal_dT_K", jf(dt));
    }
    Ok(Value::Object(out))
}

/// `constraint_values(m, DEFAULT_CONSTRAINTS)` (g >= 0 satisfied): fehe_feasibility,
/// min_nh3_conversion, product_purity.
pub fn constraint_values(p: &SepParams, m: &Value) -> Result<Vec<(String, f64)>, EngineError> {
    let num = |k: &str| m[k].as_f64();
    let dt = num("fehe_min_internal_dT_K");
    let pmin = p
        .raw
        .num("separation.yaml", &["psa", "product_purity_spec", "value"])?;
    Ok(vec![
        (
            "fehe_feasibility".into(),
            dt.map(|v| v - 0.0).unwrap_or(0.0),
        ),
        (
            "min_nh3_conversion".into(),
            num("nh3_conversion").unwrap_or(f64::NAN) - 0.95,
        ),
        (
            "product_purity".into(),
            num("h2_purity_mole_frac").unwrap_or(f64::NAN) - pmin,
        ),
    ])
}

/// `non_dominated(F)` (all objectives minimised; duplicates are all kept).
pub fn non_dominated(f: &[Vec<f64>]) -> Vec<bool> {
    let n = f.len();
    let mut mask = vec![true; n];
    for i in 0..n {
        if !mask[i] {
            continue;
        }
        let dom = f.iter().any(|r| {
            r.iter().zip(f[i].iter()).all(|(a, b)| a <= b)
                && r.iter().zip(f[i].iter()).any(|(a, b)| a < b)
        });
        if dom {
            mask[i] = false;
        }
    }
    mask
}

/// A design-grid row: field name -> value (numbers, booleans, strings, null).
pub type Row = Map<String, Value>;

fn sense_of(metric: &str) -> &'static str {
    PARETO_OBJECTIVES
        .iter()
        .find(|x| x.0 == metric)
        .map(|x| x.1)
        .unwrap_or("min")
}

fn matrix(rows: &[&Row], metrics: &[&str], senses: &[&str]) -> Vec<Vec<f64>> {
    rows.iter()
        .map(|r| {
            metrics
                .iter()
                .zip(senses.iter())
                .map(|(m, s)| {
                    r[*m].as_f64().unwrap_or(f64::NAN) * if *s == "min" { 1.0 } else { -1.0 }
                })
                .collect()
        })
        .collect()
}

/// `front(rows, metrics, senses, feasible_only)`: the non-dominated rows sorted by the first metric.
pub fn front(rows: &[Row], metrics: &[&str], senses: &[&str], feasible_only: bool) -> Vec<Row> {
    let cand: Vec<&Row> = rows
        .iter()
        .filter(|r| {
            r["model_ok"].as_bool() == Some(true)
                && (r["feasible"].as_bool() == Some(true) || !feasible_only)
                && metrics
                    .iter()
                    .all(|m| !r.get(*m).is_none_or(Value::is_null))
        })
        .collect();
    if cand.is_empty() {
        return vec![];
    }
    let fm = matrix(&cand, metrics, senses);
    let nd = non_dominated(&fm);
    let mut pts: Vec<Row> = cand
        .iter()
        .zip(nd.iter())
        .filter(|x| *x.1)
        .map(|x| (*x.0).clone())
        .collect();
    let key = metrics[0];
    pts.sort_by(|a, b| {
        a[key]
            .as_f64()
            .unwrap_or(f64::NAN)
            .total_cmp(&b[key].as_f64().unwrap_or(f64::NAN))
    });
    pts
}

fn ranks(x: &[f64]) -> Vec<f64> {
    crate::mcmc::rankdata(x)
}

/// `scipy.stats.spearmanr(a, b).statistic` (Pearson correlation of the average ranks).
pub fn spearman(a: &[f64], b: &[f64]) -> f64 {
    let (ra, rb) = (ranks(a), ranks(b));
    let n = ra.len() as f64;
    let (ma, mb) = (ra.iter().sum::<f64>() / n, rb.iter().sum::<f64>() / n);
    let (mut sab, mut saa, mut sbb) = (0.0, 0.0, 0.0);
    for (x, y) in ra.iter().zip(rb.iter()) {
        sab += (x - ma) * (y - mb);
        saa += (x - ma) * (x - ma);
        sbb += (y - mb) * (y - mb);
    }
    sab / (saa * sbb).sqrt()
}

/// `conflicts(rows)`: per objective pair, Spearman rho (minimisation sense), the pairwise
/// non-dominated set and the classification.
pub fn conflicts(rows: &[Row]) -> Value {
    let feas: Vec<&Row> = rows
        .iter()
        .filter(|r| r["feasible"].as_bool() == Some(true))
        .collect();
    let mut out = Vec::new();
    for i in 0..PARETO_OBJECTIVES.len() {
        for j in i + 1..PARETO_OBJECTIVES.len() {
            let (a, sa) = PARETO_OBJECTIVES[i];
            let (b, sb) = PARETO_OBJECTIVES[j];
            let fm = matrix(&feas, &[a, b], &[sa, sb]);
            let c0: Vec<f64> = fm.iter().map(|r| r[0]).collect();
            let c1: Vec<f64> = fm.iter().map(|r| r[1]).collect();
            let rho = spearman(&c0, &c1);
            let nd = non_dominated(&fm);
            let mut uniq: Vec<(f64, f64)> = fm
                .iter()
                .zip(nd.iter())
                .filter(|x| *x.1)
                .map(|(r, _)| {
                    (
                        (r[0] * 1e9).round_ties_even() / 1e9,
                        (r[1] * 1e9).round_ties_even() / 1e9,
                    )
                })
                .collect();
            uniq.sort_by(|x, y| x.0.total_cmp(&y.0).then(x.1.total_cmp(&y.1)));
            uniq.dedup();
            let span = |m: &str| -> Value {
                let v: Vec<f64> = feas
                    .iter()
                    .zip(nd.iter())
                    .filter(|x| *x.1)
                    .map(|(r, _)| r[m].as_f64().unwrap_or(f64::NAN))
                    .collect();
                let mn = v.iter().copied().fold(f64::INFINITY, f64::min);
                let mx = v.iter().copied().fold(f64::NEG_INFINITY, f64::max);
                json!([mn, mx])
            };
            let mut cls = if rho < -0.3 {
                "conflict".to_string()
            } else if rho > 0.3 {
                "aligned".to_string()
            } else {
                "weak".to_string()
            };
            if uniq.len() <= 1 {
                cls = "no trade-off (single non-dominated point)".into();
            } else if cls != "conflict" && uniq.len() >= 3 {
                cls = format!(
                    "{cls} globally; local trade-off ({} distinct non-dominated points)",
                    uniq.len()
                );
            }
            let mut ranges = Map::new();
            ranges.insert(a.into(), span(a));
            ranges.insert(b.into(), span(b));
            out.push(json!({"pair": [a, b], "senses": [sa, sb], "spearman_rho_min_sense": rho,
                            "n_feasible_points": feas.len(), "n_non_dominated": nd.iter().filter(|x| **x).count(),
                            "n_distinct_non_dominated": uniq.len(), "front_ranges": Value::Object(ranges),
                            "classification": cls}));
        }
    }
    json!({"pairs": out})
}

/// `pareto(rows)`: the fronts of the conflicting pairs, the four LCOH-CI overlays and the triple.
pub fn pareto(rows: &[Row]) -> Value {
    let conf = conflicts(rows);
    let pairs: Vec<Vec<String>> = conf["pairs"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|p| {
            let c = p["classification"].as_str().unwrap_or("");
            c == "conflict" || c.contains("local trade-off")
        })
        .map(|p| {
            p["pair"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .collect();
    let mut fronts = Vec::new();
    let mk = |objs: Vec<&str>, senses: Vec<&str>, rows: &[Row]| -> (Vec<Row>, Vec<Row>) {
        let pts = front(rows, &objs, &senses, true);
        let unc: Vec<Row> = front(rows, &objs, &senses, false)
            .into_iter()
            .filter(|r| r["feasible"].as_bool() != Some(true))
            .collect();
        (pts, unc)
    };
    for p in &pairs {
        let objs: Vec<&str> = p.iter().map(String::as_str).collect();
        let senses: Vec<&str> = objs.iter().map(|m| sense_of(m)).collect();
        let (pts, unc) = mk(objs.clone(), senses.clone(), rows);
        fronts.push(
            json!({"objectives": objs, "senses": senses, "points": pts, "n_points": pts.len(),
                           "unconstrained_front_infeasible_points": unc}),
        );
    }
    for (suf, _, _) in OVERLAYS {
        let lk = if suf.is_empty() {
            "lcoh_USD_per_kg".to_string()
        } else {
            format!("lcoh_USD_per_kg_{suf}")
        };
        let ck = if suf.is_empty() {
            "carbon_intensity_kgCO2e_per_kgH2".to_string()
        } else {
            format!("carbon_intensity_{suf}")
        };
        let pts = front(rows, &[&lk, &ck], &["min", "min"], true);
        fronts.push(json!({"objectives": [lk, ck], "senses": ["min", "min"], "points": pts, "n_points": pts.len(),
                           "unconstrained_front_infeasible_points": []}));
    }
    let triple = [
        "lcoh_USD_per_kg",
        "carbon_intensity_kgCO2e_per_kgH2",
        "lhv_efficiency",
    ];
    let ts: Vec<&str> = triple.iter().map(|m| sense_of(m)).collect();
    let pts = front(rows, &triple, &ts, true);
    fronts.push(
        json!({"objectives": triple, "senses": ts, "points": pts, "n_points": pts.len(),
                       "unconstrained_front_infeasible_points": []}),
    );
    json!({"n_grid_points": rows.len(), "n_feasible": rows.iter().filter(|r| r["feasible"].as_bool() == Some(true)).count(),
           "conflicts": conf, "fronts": fronts})
}
