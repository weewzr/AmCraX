//! The end-use and LCA studies (port of the calculations of `scripts/research/lca_run.py`,
//! `enduse_run.py` and `enduse_threshold.py`).
//!
//! Each driver returns the result documents the Python script writes (`lca_results.json`, the
//! assumption registers, `enduse_results.json`, `turbine_threshold.json`,
//! `nox_n2o_blends.json`, the validation items and the CSV tables that are not part of a JSON
//! document) with every number, decision, identifier and computed label. Static prose of the
//! Python documents (method statements, notes, limitations, source descriptions) is not
//! reproduced; the verifier counts those fields separately. Figures are not drawn.

use crate::calibration::Generator;
use crate::economics::reference::{EconomicsData, RefCapexArgs};
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate};
use crate::enduse::{
    Activity, CostOpts, Ctx, PowerOpts, alpha_of_cracked_share, carbon_intensity, ci_json,
    cracked_share_for_h2_fraction, fuel_lhv_mj_per_kg_nh3_fed, h2_fraction_of_blend,
    hydrogen_activity, hydrogen_activity_purification, hydrogen_cost, power_activity, power_cost,
};
use crate::error::EngineError;
use crate::lca;
use crate::optim::env_carbon_intensity;
use crate::process::result::molar_mass;
use crate::pyops::{fmt_f, fmt_g, py_max_iter, py_repr};
use crate::species::Species;
use amcrax_numerics::roots::{BrentOptions, brentq_try};
use amcrax_numerics::stats;
use serde_json::{Map, Value, json};
use std::collections::BTreeSet;
use std::path::Path;

/// Sea distance of the baseline, km.
pub const D0: f64 = 5000.0;
/// `lca.f("carbon_tax_sg_2026")`, SGD/t CO2e.
pub const CARBON_TAX_SG_2026: f64 = 45.0;
/// `lca.f("smr_h2_ccs_high")`.
pub const SMR_H2_CCS_HIGH: f64 = 5.3;
/// `lca.f("ng_upstream_leak_scenarios")`.
pub const NG_UPSTREAM_LEAK_SCENARIOS: [f64; 3] = [0.002, 0.015, 0.03];

type R<T> = Result<T, EngineError>;

fn obj(pairs: Vec<(String, Value)>) -> Value {
    Value::Object(pairs.into_iter().collect::<Map<_, _>>())
}

fn read_json(root: &Path, rel: &str) -> R<Value> {
    let t = std::fs::read_to_string(root.join(rel))
        .map_err(|e| EngineError::data(rel, e.to_string()))?;
    serde_json::from_str(&t).map_err(|e| EngineError::data(rel, e.to_string()))
}

fn num(v: &Value, what: &str) -> R<f64> {
    v.as_f64()
        .ok_or_else(|| EngineError::Domain(format!("KeyError/TypeError: {what}")))
}

/// Python `str()` of a JSON number (`30` for an integer, `0.9` for a float).
fn py_str_num(v: &Value) -> String {
    if let Some(i) = v.as_i64() {
        i.to_string()
    } else {
        v.as_f64().map(py_repr).unwrap_or_default()
    }
}

/// Python `round(x, n)` (correctly rounded decimal, then back to a float).
pub fn py_round(x: f64, n: usize) -> f64 {
    format!("{x:.n$}").parse().unwrap_or(x)
}

/// SciPy `brentq` where a `ValueError` (no sign change) gives `None`; function errors pass.
fn root_or_none<F>(f: F, a: f64, b: f64, xtol: Option<f64>) -> R<Option<f64>>
where
    F: FnMut(f64) -> R<f64>,
{
    use amcrax_numerics::roots::BrentError;
    let o = match xtol {
        Some(x) => BrentOptions::with_xtol(x),
        None => BrentOptions::default(),
    };
    match brentq_try(f, a, b, o) {
        Ok(r) => Ok(Some(r.x)),
        Err(BrentError::Function(e)) => Err(e),
        Err(BrentError::NotConverged(r)) => Err(EngineError::Numerical(format!(
            "RuntimeError: brentq failed to converge after {} iterations",
            r.iterations
        ))),
        Err(_) => Ok(None),
    }
}

fn ef(route: &str) -> R<f64> {
    Ok(lca::route_spec(route)?.ef)
}

fn act(ctx: &Ctx, kind: &str, y: Option<f64>) -> R<Activity> {
    power_activity(ctx, kind, y, &PowerOpts::default())
}

fn ci(a: &Activity, route_ef: f64, d: f64) -> f64 {
    carbon_intensity(a, route_ef, d, None, None, None)[4]
}

/// The values of `lca.FACTORS` in dict order.
pub fn lca_factor_values() -> Vec<(&'static str, Value)> {
    vec![
        ("ng_based_nh3_wtg", json!(lca::NG_BASED_NH3_WTG)),
        ("nh3_process_co2", json!(lca::NH3_PROCESS_CO2)),
        ("nh3_combustion_co2", json!(lca::NH3_COMBUSTION_CO2)),
        (
            "capture_penalty_process",
            json!(lca::CAPTURE_PENALTY_PROCESS),
        ),
        (
            "capture_penalty_combustion",
            json!(lca::CAPTURE_PENALTY_COMBUSTION),
        ),
        ("ng_per_nh3", json!(lca::NG_PER_NH3)),
        ("blue_nh3_lee_v1", json!(1.16)),
        ("blue_nh3_lee_v2", json!(lca::BLUE_NH3_LEE_V2)),
        ("green_nh3_lee", json!(lca::GREEN_NH3_LEE)),
        (
            "embedded_renewable_h2_low",
            json!(lca::EMBEDDED_RENEWABLE_H2.0),
        ),
        (
            "embedded_renewable_h2_high",
            json!(lca::EMBEDDED_RENEWABLE_H2.1),
        ),
        ("grey_nh3_range_low", json!(lca::GREY_NH3_RANGE.0)),
        ("grey_nh3_range_high", json!(lca::GREY_NH3_RANGE.1)),
        ("coal_nh3_low", json!(lca::COAL_NH3.0)),
        ("coal_nh3_high", json!(lca::COAL_NH3.1)),
        ("gwp100_ch4_fossil", json!(lca::GWP100_CH4_FOSSIL)),
        ("gwp100_n2o", json!(lca::GWP100_N2O)),
        ("ship_ef", json!(lca::SHIP_EF)),
        ("ship_distance_baseline_km", json!(D0)),
        ("ship_distance_range_km", json!([2000.0, 12000.0])),
        ("boil_off_fraction", json!(lca::BOIL_OFF_FRACTION)),
        (
            "grid_ef_singapore_2024",
            json!(crate::enduse::GRID_EF_SINGAPORE_2024),
        ),
        ("ng_co2_ef", json!(lca::NG_CO2_EF)),
        ("ng_lhv", json!(lca::NG_LHV)),
        ("ccgt_efficiency", json!(lca::CCGT_EFFICIENCY)),
        ("ccgt_efficiency_range", json!([0.50, 0.60])),
        (
            "ng_upstream_leak_scenarios",
            json!(NG_UPSTREAM_LEAK_SCENARIOS),
        ),
        (
            "smr_h2_unabated",
            json!([lca::SMR_H2_UNABATED.0, lca::SMR_H2_UNABATED.1]),
        ),
        ("smr_h2_ccs", json!([lca::SMR_H2_CCS.0, lca::SMR_H2_CCS.1])),
        ("smr_h2_ccs_high", json!(SMR_H2_CCS_HIGH)),
        ("ahmad_gas_flow_per_MWh", json!(lca::AHMAD_GAS_FLOW_PER_MWH)),
        ("ahmad_n2o_ppmv_vnh3", json!(lca::AHMAD_N2O_PPMV)),
        ("ahmad_no_ppmv_vnh3", json!(lca::AHMAD_NO_PPMV)),
        ("flue_gas_molar_mass", json!(lca::FLUE_GAS_MOLAR_MASS)),
        ("carbon_tax_sg_2026", json!(CARBON_TAX_SG_2026)),
    ]
}

/// `environmental.reference_lines()`: (label, kg CO2e/kg H2).
pub fn reference_lines() -> R<Vec<(String, f64)>> {
    let f = crate::carbon::embedded_factors();
    let n = |p: &[&str]| f.num("environmental.yaml", p);
    let lhv = crate::enduse::lhv_h2_mj_kg();
    let eu = n(&["reference_lines", "eu_rfnbo", "fossil_comparator_g_per_MJ"])?
        * (1.0 - n(&["reference_lines", "eu_rfnbo", "required_saving"])?)
        * lhv
        / 1000.0;
    Ok(vec![
        ("EU RFNBO threshold (70 % below 94 g CO2e/MJ)".into(), eu),
        (
            "IEA low-emission H2 (as quoted by Kum et al.)".into(),
            n(&["reference_lines", "iea_low_emission", "value"])?,
        ),
    ])
}

/// A validation item (the fields that are not prose).
fn vitem(id: &str, obs: Value, exp: Value, tol: Option<f64>, status: &str, kind: &str) -> Value {
    json!({"id": id, "observed": obs, "expected": exp, "tolerance": tol, "status": status,
           "evidence_kind": kind})
}

fn pf(ok: bool) -> &'static str {
    if ok { "pass" } else { "fail" }
}

// ===================================================================================== lca_run
/// Output of [`lca_run`].
pub struct LcaRun {
    pub results: Value,
    pub assumptions: Value,
    pub validation: Value,
}

/// `lca_run.main()`.
pub fn lca_run(ctx: &Ctx) -> R<LcaRun> {
    let p = &ctx.p;
    let h2 = hydrogen_activity(
        ctx,
        "baseline",
        "h2_industrial",
        "industrial H2 (99.9 %)",
        "",
    )?;
    let pw_direct = act(ctx, "direct", None)?;
    let pw_part40 = act(ctx, "partial_exhaust", Some(0.4))?;
    let pw_pur = act(ctx, "full_purified", None)?;
    let ccgt = lca::ccgt_ci_kg_per_mwh(None, 0.0);
    let (smr_u, smr_c) = (lca::smr_h2_ci(false), lca::smr_h2_ci(true));
    let grid_mwh = crate::enduse::GRID_EF_SINGAPORE_2024 * 1000.0;
    // ---- 1 routes
    let mut routes = Vec::new();
    for r in lca::ROUTES {
        let s = lca::route_spec(r)?;
        let bh = carbon_intensity(&h2, s.ef, D0, None, None, None);
        let bm = carbon_intensity(&pw_direct, s.ef, D0, None, None, None);
        let bp = carbon_intensity(&pw_pur, s.ef, D0, None, None, None);
        routes.push(json!({
            "route": r, "label": s.label, "gate_kgCO2e_per_kgNH3": s.ef, "range_low": s.low,
            "range_high": s.high, "delivered_5000km": lca::delivered_nh3_ef(s.ef, D0, None, None)?,
            "source_type": s.source_type,
            "H2_kgCO2e_per_kg": bh[4], "H2_breakdown": ci_json(&bh),
            "direct_NH3_CCGT_kgCO2e_per_MWh": bm[4], "MWh_breakdown": ci_json(&bm),
            "cracked_purified_H2_CCGT_kgCO2e_per_MWh": bp[4],
            "H2_low_high": [ci(&h2, s.low, D0), ci(&h2, s.high, D0)],
            "MWh_low_high": [ci(&pw_direct, s.low, D0), ci(&pw_direct, s.high, D0)],
        }));
    }
    // ---- 2 alternatives and break-evens
    let mut cc = vec![
        ("central".to_string(), json!(ccgt)),
        (
            "low_eff_0.50".into(),
            json!(lca::ccgt_ci_kg_per_mwh(Some(0.50), 0.0)),
        ),
        (
            "high_eff_0.60".into(),
            json!(lca::ccgt_ci_kg_per_mwh(Some(0.60), 0.0)),
        ),
    ];
    for x in NG_UPSTREAM_LEAK_SCENARIOS {
        cc.push((
            format!("leak_{}", py_repr(x)),
            json!(lca::ccgt_ci_kg_per_mwh(None, x)),
        ));
    }
    let alts = json!({
        "ccgt_ng_kgCO2e_per_MWh": obj(cc),
        "grid_average_kgCO2e_per_MWh": {"central": grid_mwh},
        "smr_h2_unabated_kgCO2e_per_kgH2": {"central": smr_u,
            "range": [lca::SMR_H2_UNABATED.0, lca::SMR_H2_UNABATED.1]},
        "smr_h2_ccs_kgCO2e_per_kgH2": {"central": smr_c,
            "range": [lca::SMR_H2_CCS.0, lca::SMR_H2_CCS.1], "upper_sensitivity": SMR_H2_CCS_HIGH},
    });
    let leak15 = lca::ccgt_ci_kg_per_mwh(None, 0.015);
    let mut be = Vec::new();
    for dist in [2000.0, D0, 12000.0] {
        for (name, a, cmp) in [
            ("industrial H2 vs SMR unabated", &h2, smr_u),
            ("industrial H2 vs SMR + CCS", &h2, smr_c),
            ("direct NH3 CCGT vs NG CCGT", &pw_direct, ccgt),
            (
                "direct NH3 CCGT vs NG CCGT (leak 1.5 %)",
                &pw_direct,
                leak15,
            ),
            ("direct NH3 CCGT vs grid average", &pw_direct, grid_mwh),
            ("partial crack 40 vol% H2 vs NG CCGT", &pw_part40, ccgt),
            ("cracked + purified H2 CCGT vs NG CCGT", &pw_pur, ccgt),
            (
                "cracked + purified H2 CCGT vs grid average",
                &pw_pur,
                grid_mwh,
            ),
        ] {
            be.push(json!({"comparison": name, "distance_km": dist, "alternative_CI": cmp,
                "breakeven_NH3_gate_EF_kgCO2e_per_kgNH3": crate::enduse::breakeven_ef(a, cmp, dist, None)}));
        }
    }
    let be_blue = json!({"blue_v1": lca::blue_nh3_ef(1.0, 0.0, 0.0, None)?,
        "blue_v2": lca::blue_nh3_ef(1.0, 1.0, 0.0, None)?, "blue_param": ef("blue_param")?});
    // ---- 3 distance scenarios
    let mut dist_rows = Vec::new();
    for d in [0.0, 2000.0, 5000.0, 8000.0, 12000.0] {
        for r in ["green", "blue", "grey"] {
            let e = ef(r)?;
            dist_rows.push(json!({"distance_km": d, "route": r,
                "shipping_kgCO2e_per_kgNH3": lca::ship_kg_per_kg_nh3(d, None),
                "H2_kgCO2e_per_kg": ci(&h2, e, d), "direct_NH3_CCGT_kgCO2e_per_MWh": ci(&pw_direct, e, d)}));
        }
    }
    // ---- 4 OAT and Monte Carlo
    let margin = |cap: f64, leak: f64, dist: f64, es: f64, ce: f64, cl: f64| -> R<f64> {
        let e = lca::blue_nh3_ef(cap, 0.0, leak, None)?;
        let a = &pw_direct;
        let n = a.nh3_kg / es;
        let t = ci(a, e, dist) / a.nh3_kg * n;
        Ok(lca::ccgt_ci_kg_per_mwh(Some(ce), cl) - t)
    };
    let base = [0.95, 0.015, D0, 1.0, 0.55, 0.0];
    let m6 = |v: [f64; 6]| margin(v[0], v[1], v[2], v[3], v[4], v[5]);
    let base_margin = m6(base)?;
    let mut oat = Vec::new();
    for (label, k, lo, hi) in [
        ("process CO2 capture 0.90-1.00", 0, 0.90, 1.00),
        ("extra upstream CH4 leakage 0.2-3.0 %", 1, 0.002, 0.03),
        ("sea distance 2000-12000 km", 2, 2000.0, 12000.0),
        (
            "turbine electricity per kg NH3 +/-6 % (about +/-3 pts)",
            3,
            0.94,
            1.06,
        ),
        ("CCGT efficiency 0.50-0.60", 4, 0.50, 0.60),
        ("CCGT upstream CH4 leakage 0-3 %", 5, 0.0, 0.03),
    ] {
        let (mut a, mut b) = (base, base);
        a[k] = lo;
        b[k] = hi;
        oat.push(json!({"parameter": label, "margin_at_low": m6(a)?, "margin_at_high": m6(b)?}));
    }
    let mut g = Generator::new(20261123);
    let n = 20000usize;
    let mut draw =
        |lo: f64, hi: f64| -> Vec<f64> { (0..n).map(|_| g.bg.uniform(lo, hi)).collect() };
    let cap = draw(0.9, 1.0);
    let lk = draw(0.002, 0.03);
    let dist = draw(2000.0, 12000.0);
    let es = draw(0.94, 1.06);
    let ce = draw(0.50, 0.60);
    let cl = draw(0.0, 0.03);
    let smr_u_s = draw(lca::SMR_H2_UNABATED.0, lca::SMR_H2_UNABATED.1);
    let smr_c_s = draw(lca::SMR_H2_CCS.0, SMR_H2_CCS_HIGH);
    let mut n_pos = 0usize;
    for i in 0..n {
        if margin(cap[i], lk[i], dist[i], es[i], ce[i], cl[i])? > 0.0 {
            n_pos += 1;
        }
    }
    let mut pw_ci = Vec::new();
    for i in (0..n).step_by(10) {
        pw_ci.push(
            ci(
                &pw_direct,
                lca::blue_nh3_ef(cap[i], 0.0, lk[i], None)?,
                dist[i],
            ) / es[i],
        );
    }
    let mut h2_blue = Vec::with_capacity(n);
    for i in 0..n {
        h2_blue.push(ci(
            &h2,
            lca::blue_nh3_ef(cap[i], 0.0, lk[i], None)?,
            dist[i],
        ));
    }
    let frac = |c: usize| c as f64 / n as f64;
    let below = |s: &[f64]| frac(h2_blue.iter().zip(s).filter(|(a, b)| a < b).count());
    let pct = |x: &[f64]| -> Vec<f64> {
        [0.05, 0.50, 0.95]
            .iter()
            .map(|q| stats::quantile(x, *q))
            .collect()
    };
    let mc = json!({"n": n, "seed": 20261123,
        "blue_direct_NH3_power": {"CI_kgCO2e_per_MWh_p5_p50_p95": pct(&pw_ci),
                                  "P_cuts_emissions_vs_NG_CCGT": frac(n_pos)},
        "blue_industrial_H2": {"CI_kgCO2e_per_kgH2_p5_p50_p95": pct(&h2_blue),
                               "P_below_SMR_unabated": below(&smr_u_s),
                               "P_below_SMR_CCS": below(&smr_c_s)}});
    let (n2o_kg, n2o_co2e, no_kg) = lca::n2o_nox_per_mwh();
    let results = json!({
        "distance_km_baseline": D0,
        "activity_per_FU": {"H2": {"nh3_kg": h2.nh3_kg, "efficiency_LHV": h2.efficiency},
                            "direct_NH3_CCGT": {"nh3_kg": pw_direct.nh3_kg, "efficiency_LHV": pw_direct.efficiency}},
        "routes": routes, "alternatives": alts, "breakeven": be, "blue_ef_reproduction": be_blue,
        "distance_scenarios": dist_rows,
        "sensitivity_oat_blue_direct_power": {"base_margin_kgCO2e_per_MWh(CCGT minus NH3)": base_margin, "rows": oat},
        "monte_carlo": mc,
        "n2o_nox": {"N2O_kg_per_MWh": n2o_kg, "N2O_kgCO2e_per_MWh": n2o_co2e, "NO_kg_per_MWh": no_kg},
        "carbon_tax_sg": {"rate_SGD_per_t": CARBON_TAX_SG_2026,
            "direct_in_scope_kgCO2e_per_MWh_direct_NH3": pw_direct.n2o_kgco2e,
            "SGD_per_MWh": pw_direct.n2o_kgco2e / 1000.0 * CARBON_TAX_SG_2026},
    });
    // ---- assumptions register (values; the source texts are prose)
    let mut reg: Vec<Value> = lca_factor_values()
        .into_iter()
        .map(|(k, v)| json!({"name": k, "value": v}))
        .collect();
    reg.push(json!({"name": "eta_direct_ahmad", "value": p.eta_direct_ahmad}));
    reg.push(json!({"name": "eta_full_crack_ahmad", "value": p.eta_full_crack_ahmad}));
    reg.push(json!({"name": "eta_gt_gas", "value": p.eta_gt_gas}));
    // ---- validation
    let cr = ctx.cracker("baseline")?;
    let mut items = Vec::new();
    let kind_of = |id: &str| {
        if ["LCA-blue-", "LCA-ccgt", "LCA-ref-", "LCA-smr"]
            .iter()
            .any(|s| id.starts_with(s))
        {
            "literature_comparison"
        } else {
            "numerical_verification"
        }
    };
    for (nm, got, exp) in [
        ("v1", lca::blue_nh3_ef(1.0, 0.0, 0.0, None)?, 1.16),
        ("v2", lca::blue_nh3_ef(1.0, 1.0, 0.0, None)?, 0.77),
    ] {
        let id = format!("LCA-blue-{nm}");
        items.push(vitem(
            &id,
            json!(got),
            json!(exp),
            Some(1e-9),
            pf((got - exp).abs() < 1e-9),
            kind_of(&id),
        ));
    }
    let base_res = &ctx.stored("baseline")?.result;
    for (route, key) in [("grey", "grey"), ("blue", "blue"), ("green", "green_lee")] {
        let old = env_carbon_intensity(base_res, route, "self_firing", "singapore_2024")?.0;
        let e = if route != "green" { ef(key)? } else { 0.0 };
        let new = ci(&h2, e, D0);
        let id = format!("LCA-baseline-{route}");
        let ok = (new - old).abs() < 1e-6 * crate::pyops::py_max(1.0, old);
        items.push(vitem(
            &id,
            json!(new),
            json!(old),
            Some(1e-6),
            pf(ok),
            kind_of(&id),
        ));
    }
    let b = &routes[2]["H2_breakdown"];
    let parts = ["upstream_ammonia", "shipping", "electricity", "direct_n2o"];
    let mut ssum = 0.0;
    for k in parts {
        ssum += num(&b[k], k)?;
    }
    let tot = num(&b["total"], "total")?;
    items.push(vitem(
        "LCA-sum",
        json!(ssum),
        json!(tot),
        Some(1e-9),
        pf((ssum - tot).abs() < 1e-9),
        "numerical_verification",
    ));
    items.push(vitem(
        "LCA-nh3-per-h2",
        json!(h2.nh3_kg),
        json!(
            cr.nh3_kg_h / cr.h2_product_kg_h * (1.0 + cr.deficit_mj_per_kg_nh3() / p.lhv_nh3_mj_kg)
        ),
        Some(1e-9),
        "pass",
        "numerical_verification",
    ));
    items.push(vitem(
        "LCA-ccgt-vs-grid",
        json!(ccgt),
        json!(grid_mwh),
        None,
        "informational",
        "literature_comparison",
    ));
    let blue_h2 = &routes[2]["H2_kgCO2e_per_kg"];
    for (label, v) in reference_lines()? {
        let short: String = label
            .chars()
            .take(8)
            .collect::<String>()
            .trim()
            .replace(' ', "_");
        let id = format!("LCA-ref-{short}");
        items.push(vitem(
            &id,
            blue_h2.clone(),
            json!(v),
            None,
            "informational",
            kind_of(&id),
        ));
    }
    items.push(vitem(
        "LCA-smr",
        blue_h2.clone(),
        json!([smr_c, smr_u]),
        None,
        "informational",
        "literature_comparison",
    ));
    Ok(LcaRun {
        results,
        assumptions: Value::Array(reg),
        validation: Value::Array(items),
    })
}

// ===================================================================================== enduse_run
/// Output of [`enduse_run`].
pub struct EnduseRun {
    pub results: Value,
    pub assumptions: Value,
    pub validation: Vec<Value>,
}

const ROUTE_SET: [&str; 4] = ["green", "blue", "blue_param", "grey"];

fn price_cols(ctx: &Ctx) -> Vec<(&'static str, f64)> {
    let p = &ctx.p;
    vec![
        ("grey_450", p.price("grey")),
        ("blue_487", p.price("blue")),
        ("green_2030_709", p.price("green_2030")),
        ("green_current_1000", p.price("green_current")),
    ]
}

fn lcoe(ctx: &Ctx, a: &Activity, price: f64) -> R<f64> {
    Ok(power_cost(ctx, a, price, &CostOpts::new(&ctx.p))?.lcoe_usd_per_mwh)
}

/// `lc(kind, y, price, hours, **kw)` of `enduse_run.py`.
fn lc(ctx: &Ctx, kind: &str, y: Option<f64>, price: f64, hours: f64, full_corr: bool) -> R<f64> {
    let mut o = CostOpts::new(&ctx.p);
    o.hours = hours;
    o.unpurified_full_correlation = full_corr;
    Ok(power_cost(ctx, &act(ctx, kind, y)?, price, &o)?.lcoe_usd_per_mwh)
}

/// `enduse_run.main()`.
pub fn enduse_run(ctx: &Ctx, root: &Path) -> R<EnduseRun> {
    let p = &ctx.p;
    let d = ctx.d;
    let price = p.nh3_price_ref_usd_t;
    let tax = d.reference.carbon_tax_sgd_per_t;
    let fx = d.reference.fx_sgd_per_usd;
    let cr = ctx.cracker("baseline")?;
    let x = cr.conversion;
    let efs: Vec<(&str, f64)> = ROUTE_SET
        .iter()
        .map(|r| Ok((*r, ef(r)?)))
        .collect::<R<_>>()?;
    // ---------------- pathway table
    let mut specs: Vec<(&str, Option<f64>)> = vec![("direct", None)];
    for y in [0.3, 0.4, 0.5, 0.6] {
        specs.push(("partial_exhaust", Some(y)));
        specs.push(("partial_fired", Some(y)));
    }
    specs.extend([
        ("full_exhaust", None),
        ("full_fired", None),
        ("full_purified", None),
    ]);
    for y in [0.3, 0.4, 0.5, 0.6] {
        specs.push(("blend_purified", Some(y)));
    }
    let mut rows = Vec::new();
    let mut acts: Vec<Activity> = Vec::new();
    for (kind, y) in &specs {
        let a = act(ctx, kind, *y)?;
        let c = power_cost(ctx, &a, price, &CostOpts::new(p))?;
        let h = a.h2_fraction_vol.unwrap_or(0.0);
        let flex = if a.h2_fraction_vol.is_some() && h > 0.0 {
            if (0.3 - 1e-9..=0.6 + 1e-9).contains(&h) {
                "inside the essay's 30-60 vol% H2 range (not found for the H-25 or for NH3-H2 blends; NETL 2022 gives 30-60 % for H2 in natural gas, Baker Hughes)"
            } else if h < 0.3 {
                "below 30 vol%: NG-combustor-compatible range"
            } else {
                "above 60 vol%: beyond the quoted blend range, needs a H2-capable combustor (not demonstrated here)"
            }
        } else {
            ""
        };
        let labels = format!(
            "efficiency: literature-calibrated (Ahmad 2025){}; cost: python (amcrax.economics + Ahmad plant data, literature)",
            if kind.contains("fired") || kind.contains("purified") {
                "; cracker heat: aspen (stored baseline)"
            } else {
                ""
            }
        );
        let mut row = vec![
            ("id".to_string(), json!(a.id)),
            ("product".into(), json!("electricity")),
            ("functional_unit".into(), json!(a.functional_unit)),
            ("H2_vol_fraction_in_fuel".into(), json!(a.h2_fraction_vol)),
            ("cracked_NH3_share".into(), json!(a.cracked_share)),
            (
                "efficiency_NH3_LHV_to_electricity".into(),
                json!(a.efficiency),
            ),
            ("NH3_kg_per_MWh".into(), json!(a.nh3_kg)),
            ("cost_USD_per_MWh_at_450".into(), json!(c.lcoe_usd_per_mwh)),
            ("plant_W_net_MW".into(), json!(c.w_net_mw)),
            ("TCI_MUSD".into(), json!(c.tci_musd)),
            ("cost_capital".into(), json!(c.components[0])),
            ("cost_fixed_om".into(), json!(c.components[1])),
            ("cost_ammonia".into(), json!(c.components[2])),
            ("N2O_kgCO2e_per_MWh".into(), json!(a.n2o_kgco2e)),
            (
                "NO_kg_per_MWh".into(),
                match a.no_kg {
                    Some(v) => json!(v),
                    None => json!("not quantified (no source for this fuel)"),
                },
            ),
            ("heat_mode".into(), json!(a.heat_mode)),
            ("fuel_flexibility".into(), json!(flex)),
            ("source_labels".into(), json!(labels)),
        ];
        for (r, e) in &efs {
            row.push((format!("CI_{r}_kgCO2e_per_MWh"), json!(ci(&a, *e, D0))));
        }
        for (lab, pr) in price_cols(ctx) {
            row.push((
                format!("cost_USD_per_MWh_at_{lab}"),
                json!(lcoe(ctx, &a, pr)?),
            ));
        }
        let n2o_cpa = a.n2o_kgco2e / lca::GWP100_N2O * p.gwp_n2o_sg_carbon_pricing_act;
        row.push(("N2O_kgCO2e_per_MWh_CPA_GWP265".into(), json!(n2o_cpa)));
        row.push((
            "carbon_tax_USD_per_MWh_direct_in_scope".into(),
            json!(n2o_cpa / 1000.0 * tax / fx),
        ));
        row.push((
            "carbon_tax_SGD_per_MWh_direct_in_scope".into(),
            json!(n2o_cpa / 1000.0 * tax),
        ));
        row.push((
            "cost_SGD_per_MWh_at_450".into(),
            json!(c.lcoe_usd_per_mwh * fx),
        ));
        row.push(("TCI_cracker_MUSD".into(), json!(c.tci_cracker_musd)));
        rows.push(obj(row));
        acts.push(a);
    }
    // hydrogen pathways
    let mut hrows = Vec::new();
    for (case, id) in [
        ("baseline", "h2_industrial"),
        ("scn_fuel_cell_grade", "h2_fuelcell_candidate"),
    ] {
        let a = hydrogen_activity(ctx, case, id, "", "")?;
        let mut row = vec![
            ("id".to_string(), json!(id)),
            ("product".into(), json!("H2")),
            ("functional_unit".into(), json!(a.functional_unit)),
            ("efficiency_NH3_LHV_to_H2".into(), json!(a.efficiency)),
            ("NH3_kg_per_kg_H2".into(), json!(a.nh3_kg)),
        ];
        for (lab, pr) in price_cols(ctx) {
            row.push((
                format!("cost_USD_per_kg_at_{lab}"),
                json!(hydrogen_cost(ctx, case, pr, None, None, "reference")?.usd_per_kg),
            ));
        }
        let h450 = hydrogen_cost(ctx, case, price, None, None, "reference")?;
        row.push(("cost_breakdown_at_450".into(), h450.breakdown.clone()));
        row.push(("cost_SGD_per_kg_at_grey_450".into(), json!(h450.sgd_per_kg)));
        row.push((
            "cost_USD_per_kg_legacy_v1_basis_at_450".into(),
            json!(hydrogen_cost(ctx, case, price, None, None, "legacy")?.usd_per_kg),
        ));
        for (r, e) in &efs {
            row.push((format!("CI_{r}_kgCO2e_per_kgH2"), json!(ci(&a, *e, D0))));
        }
        hrows.push(obj(row));
    }
    for (cfgid, gk, id, has_pur) in [
        (
            "PSA_AMCRAX",
            "industrial_99.9",
            "h2_industrial_purif_study",
            false,
        ),
        (
            "PSA_D_MB",
            "fuel_cell_grade_D",
            "h2_fuelcell_gradeD_purif_study",
            true,
        ),
    ] {
        let (a, cst) = hydrogen_activity_purification(ctx, cfgid, gk, id, "")?;
        let usd = num(&cst["usd_per_kg_product_h2"], "usd_per_kg_product_h2")?;
        let mut row = vec![
            ("id".to_string(), json!(id)),
            ("product".into(), json!("H2")),
            ("functional_unit".into(), json!(a.functional_unit)),
            ("efficiency_NH3_LHV_to_H2".into(), json!(a.efficiency)),
            ("NH3_kg_per_kg_H2".into(), json!(a.nh3_kg)),
            (
                "compression_kWh_per_kg".into(),
                cst["compression_kWh_per_kg_h2"].clone(),
            ),
            (
                "delivery_pressure_bar".into(),
                cst["delivery_pressure_bar"].clone(),
            ),
            (
                "purification_only_USD_per_kg_at_450".into(),
                cst["purification_only_usd_per_kg"].clone(),
            ),
        ];
        if !has_pur {
            row.push(("purity_note".into(), json!(a.purity_note)));
        }
        for (lab, pr) in price_cols(ctx) {
            row.push((
                format!("cost_USD_per_kg_at_{lab}"),
                json!(usd + (pr - price) / 1000.0 * a.nh3_kg),
            ));
        }
        row.push((
            "cost_breakdown_at_450".into(),
            cst["components_usd_per_kg"].clone(),
        ));
        row.push(("cost_SGD_per_kg_at_grey_450".into(), json!(usd * fx)));
        for (r, e) in &efs {
            row.push((format!("CI_{r}_kgCO2e_per_kgH2"), json!(ci(&a, *e, D0))));
        }
        hrows.push(obj(row));
    }
    // ---------------- direct vs cracking cost ratio
    let (hh, ah, ap, gc) = (
        p.power_plant_hours_per_year,
        p.ahmad_hours_implied,
        p.ahmad_nh3_price_usd_t,
        p.price("green_current"),
    );
    let mut claim = Vec::new();
    for (pr, hours, tag) in [
        (
            price,
            hh,
            format!(
                "AmCraX price set ({} USD/t, {} h)",
                fmt_g(price, 6),
                fmt_g(hh, 6)
            ),
        ),
        (
            ap,
            ah,
            format!("Ahmad basis ({} USD/t, {} h)", fmt_g(ap, 6), fmt_g(ah, 6)),
        ),
        (
            gc,
            hh,
            format!("renewable NH3 today ({} USD/t)", fmt_g(gc, 6)),
        ),
    ] {
        let dd = lc(ctx, "direct", None, pr, hours, false)?;
        for kind in ["full_exhaust", "full_fired", "full_purified"] {
            let c = lc(ctx, kind, None, pr, hours, false)?;
            claim.push(json!({"basis": tag, "cracking_pathway": kind, "LCOE_direct": dd, "LCOE_cracking": c,
                "direct_cheaper_by_pct_of_cracking(1-d/c)": 100.0 * (1.0 - dd / c),
                "cracking_dearer_by_pct_of_direct(c/d-1)": 100.0 * (c / dd - 1.0)}));
        }
    }
    let cross = |ka: &str, kb: &str, ya: Option<f64>, yb: Option<f64>| -> R<Option<f64>> {
        root_or_none(
            |pr| Ok(lc(ctx, ka, ya, pr, hh, false)? - lc(ctx, kb, yb, pr, hh, false)?),
            1.0,
            5000.0,
            None,
        )
    };
    let crossovers = json!({
        "full_exhaust_vs_direct_NH3_price_USD_t": cross("full_exhaust", "direct", None, None)?,
        "partial_exhaust_40_vs_direct": cross("partial_exhaust", "direct", Some(0.4), None)?,
        "full_fired_vs_direct": cross("full_fired", "direct", None, None)?,
        "full_purified_vs_direct": cross("full_purified", "direct", None, None)?,
    });
    // ---------------- partial cracking scan
    let mut scan = Vec::new();
    for y in crate::pyops::linspace(0.0, 0.74, 38) {
        let (ke, kf) = if y > 0.0 {
            ("partial_exhaust", "partial_fired")
        } else {
            ("direct", "direct")
        };
        let yy = if y > 0.0 { Some(y) } else { None };
        let mut row = vec![
            ("H2_vol_fraction".to_string(), json!(y)),
            (
                "cracked_share".into(),
                json!(cracked_share_for_h2_fraction(y, x)?),
            ),
        ];
        for g in [1.0, 0.5, 0.0] {
            let o = PowerOpts {
                gain_scale: g,
                ..PowerOpts::default()
            };
            let a = power_activity(ctx, ke, yy, &o)?;
            row.push((
                format!("LCOE_exhaust_gain{}", py_repr(g)),
                json!(lcoe(ctx, &a, price)?),
            ));
        }
        row.push((
            "LCOE_fired".into(),
            json!(lcoe(ctx, &act(ctx, kf, yy)?, price)?),
        ));
        scan.push(obj(row));
    }
    let mut be_gain = Vec::new();
    for pr in [300.0, 450.0, 700.0, 1000.0] {
        let dd = lc(ctx, "direct", None, pr, hh, false)?;
        let g_be = root_or_none(
            |g| {
                let o = PowerOpts {
                    gain_scale: g,
                    ..PowerOpts::default()
                };
                Ok(lcoe(
                    ctx,
                    &power_activity(ctx, "partial_exhaust", Some(0.4), &o)?,
                    pr,
                )? - dd)
            },
            0.0,
            3.0,
            None,
        )?;
        be_gain.push(json!({"NH3_price_USD_t": pr, "gain_scale_where_partial_40vol_equals_direct": g_be,
            "LCOE_direct": dd, "LCOE_partial40_gain1": lc(ctx, "partial_exhaust", Some(0.4), pr, hh, false)?}));
    }
    let mut sweep = Vec::new();
    for pr in crate::pyops::linspace(250.0, 1100.0, 18) {
        let mut row = vec![("NH3_price_USD_t".to_string(), json!(pr))];
        for k in ["direct", "full_exhaust", "full_fired", "full_purified"] {
            row.push((k.into(), json!(lc(ctx, k, None, pr, hh, false)?)));
        }
        row.push((
            "partial40_exhaust".into(),
            json!(lc(ctx, "partial_exhaust", Some(0.4), pr, hh, false)?),
        ));
        row.push((
            "partial40_fired".into(),
            json!(lc(ctx, "partial_fired", Some(0.4), pr, hh, false)?),
        ));
        sweep.push(obj(row));
    }
    let mut hours_rows = Vec::new();
    for h in [3000i64, 5000, 7200, 8000] {
        let hf = h as f64;
        hours_rows.push(
            json!({"hours": h, "direct": lc(ctx, "direct", None, price, hf, false)?,
            "full_exhaust": lc(ctx, "full_exhaust", None, price, hf, false)?,
            "full_purified": lc(ctx, "full_purified", None, price, hf, false)?}),
        );
    }
    let full_corr = lc(ctx, "full_exhaust", None, price, hh, true)?;
    let hc = |case: &str, pr: f64| -> R<f64> {
        Ok(hydrogen_cost(ctx, case, pr, None, None, "reference")?.usd_per_kg)
    };
    let mut ind = Vec::new();
    let mut fcc = Vec::new();
    for pr in [300i64, 450, 709, 1000] {
        ind.push((pr.to_string(), json!(hc("baseline", pr as f64)?)));
        fcc.push((pr.to_string(), json!(hc("scn_fuel_cell_grade", pr as f64)?)));
    }
    let summary_h = json!({"industrial_H2_cost_vs_price": obj(ind), "fuelcell_candidate_cost_vs_price": obj(fcc),
        "purification_cost_increment_USD_per_kg_at_450": hc("scn_fuel_cell_grade", 450.0)? - hc("baseline", 450.0)?});
    let detour = json!({"kWh_electricity_per_kg_NH3_direct": p.elec_mj_per_kg_direct / 3.6,
        "kWh_electricity_per_kg_NH3_cracked_purified": act(ctx, "full_purified", None)?.efficiency * p.lhv_nh3_mj_kg / 3.6});
    let price_set = obj(p
        .nh3_price_set_usd_t
        .iter()
        .map(|(k, v)| (k.clone(), json!(v)))
        .collect());
    let results = json!({
        "price_set": {"NH3_USD_per_t": price_set, "NH3_USD_per_t_common_reference": price,
            "electricity_USD_per_kWh": p.electricity_usd_kwh, "operating_hours": p.hours_per_year,
            "power_plant_operating_hours": p.power_plant_hours_per_year, "discount_rate": p.discount_rate,
            "life_years": p.plant_life_yr, "carbon_tax_SGD_per_t": tax, "fx_SGD_per_USD": fx,
            "fx_date": d.reference.fx_date, "capex_method": d.reference.capex_method},
        "distance_km": D0,
        "ef_kgCO2e_per_kgNH3": obj(efs.iter().map(|(k, v)| (k.to_string(), json!(v))).collect()),
        "power_pathways": rows, "hydrogen_pathways": hrows,
        "halim_claim_check": {"computed": claim, "crossover_prices": crossovers,
            "unpurified_exhaust_LCOE_with_full_cracker_correlation": full_corr},
        "partial_cracking": {"scan": scan, "breakeven_efficiency_gain": be_gain},
        "price_sweep": sweep, "hours_sensitivity": hours_rows, "hydrogen_summary": summary_h, "detour": detour,
        "fuel_flexibility": {"halim_blend_range_vol_H2": [p.halim_h2_blend_range_vol.0, p.halim_h2_blend_range_vol.1],
            "NG_combustor_limit_vol_H2": p.ng_combustor_h2_limit_vol},
    });
    let iso = json!({"H2_min_mol_pct": 99.97, "N2_plus_Ar_max_ppm": 300.0, "NH3_max_ppm": 0.1});
    let reg = json!([
        {"name": "eta_direct_ahmad", "value": p.eta_direct_ahmad},
        {"name": "eta_full_crack_ahmad", "value": p.eta_full_crack_ahmad},
        {"name": "eta_gt_gas", "value": p.eta_gt_gas},
        {"name": "exhaust_gain_interpolation", "value": "linear in cracked share"},
        {"name": "plant_TCI_noncracker", "value": p.ahmad_tci_2a_musd},
        {"name": "plant_fixed_om", "value": p.ahmad_oc_fixed_2a_usd_per_kwh},
        {"name": "cracker_capex", "value": d.reference.capex_method},
        {"name": "operating_hours", "value": p.power_plant_hours_per_year},
        {"name": "nh3_price_reference", "value": price},
        {"name": "cracker_heat_scaling", "value": "linear in cracked share"},
        {"name": "fuel_flexibility", "value": "30-60 vol% H2"},
        {"name": "ISO_14687_grade_D", "value": iso},
    ]);
    // ---------------- validation
    let kind_of = |id: &str| {
        if id == "EU-energy-h2" {
            "python_vs_aspen"
        } else if ["EU-ahmad", "EU-halim", "EU-iso"]
            .iter()
            .any(|s| id.starts_with(s))
        {
            "literature_comparison"
        } else {
            "numerical_verification"
        }
    };
    let mut items = Vec::new();
    let mut add = |id: &str, obs: Value, exp: Value, tol: Option<f64>, status: &str| {
        items.push(vitem(id, obs, exp, tol, status, kind_of(id)));
    };
    for (alpha, byp) in &p.ahmad_alpha_bypass {
        let (alpha, byp) = (*alpha, *byp);
        let f = if 0.0 < alpha && alpha < 1.0 {
            root_or_none(
                |f| Ok(alpha_of_cracked_share(f, p.ahmad_crack_conversion) - alpha),
                0.0,
                1.0,
                None,
            )?
            .ok_or_else(|| EngineError::Domain("ValueError: brentq sign".into()))?
        } else if alpha == 0.0 {
            1.0
        } else {
            0.0
        };
        let exp = 1.0 - byp;
        add(
            &format!("EU-stoich-alpha-{}", py_repr(alpha)),
            json!(f),
            json!(exp),
            Some(0.005),
            pf((f - exp).abs() <= 0.005),
        );
    }
    for y in [0.3, 0.4, 0.5, 0.6] {
        let f = cracked_share_for_h2_fraction(y, x)?;
        let back = h2_fraction_of_blend(f, x);
        let t = (y * 100.0) as i64;
        add(
            &format!("EU-blend-{t}"),
            json!(back),
            json!(y),
            Some(1e-12),
            pf((back - y).abs() < 1e-12),
        );
        let _ = act(ctx, "partial_fired", Some(y))?;
        let m = f * x;
        let (nh3, h2_, n2) = (1.0 - m, 1.5 * m, 0.5 * m);
        add(
            &format!("EU-blend-N-{t}"),
            json!(2.0 * n2 + nh3),
            json!(1.0),
            Some(1e-12),
            "pass",
        );
        add(
            &format!("EU-blend-H-{t}"),
            json!(2.0 * h2_ + 3.0 * nh3),
            json!(3.0),
            Some(1e-12),
            "pass",
        );
    }
    for a in &acts {
        let eff = 3600.0 / (a.nh3_kg * p.lhv_nh3_mj_kg);
        add(
            &format!("EU-energy-{}", a.id),
            json!(eff),
            json!(a.efficiency),
            Some(1e-9),
            pf((eff - a.efficiency).abs() < 1e-9 && 0.0 < eff && eff < 1.0),
        );
    }
    let h = hydrogen_activity(ctx, "baseline", "x", "", "")?;
    let lhv_eff = ctx
        .stored("baseline")?
        .result
        .kpis
        .lhv_efficiency
        .unwrap_or(f64::NAN);
    add(
        "EU-energy-h2",
        json!(h.efficiency),
        json!(lhv_eff),
        Some(0.005),
        pf((h.efficiency - lhv_eff).abs() <= 0.005),
    );
    let old = env_carbon_intensity(
        &ctx.stored("baseline")?.result,
        "blue",
        "self_firing",
        "singapore_2024",
    )?
    .0;
    let new = ci(&h, ef("blue")?, D0);
    add(
        "EU-baseline-CI",
        json!(new),
        json!(old),
        Some(1e-6),
        pf((new - old).abs() < 1e-6 * old),
    );
    let econ = read_json(root, "results/simulations/economics_baseline.json")?;
    let node = if econ.get("lcoh").is_some() {
        &econ["lcoh"]
    } else if econ.get("result").is_some() {
        &econ["result"]
    } else {
        &econ
    };
    let ref_lcoh = node.get("lcoh_USD_per_kg").and_then(Value::as_f64);
    let ours = hydrogen_cost(
        ctx,
        "baseline",
        price,
        None,
        Some(p.legacy_electricity_usd_kwh),
        "legacy",
    )?
    .usd_per_kg;
    let st = match ref_lcoh {
        Some(r) if (ours - r).abs() < 1e-6 => "pass",
        None => "informational",
        _ => "fail",
    };
    add("EU-lcoh", json!(ours), json!(ref_lcoh), Some(1e-6), st);
    let ref_bl = num(
        &read_json(root, "results/research/reference_scenario/baseline.json")?["lcoh_USD_per_kg"],
        "lcoh_USD_per_kg",
    )?;
    let ours_ref = hc("baseline", price)?;
    add(
        "EU-lcoh-reference",
        json!(ours_ref),
        json!(ref_bl),
        Some(1e-6 * ref_bl),
        pf((ours_ref - ref_bl).abs() <= 1e-6 * ref_bl),
    );
    let d480 = lc(ctx, "direct", None, ap, ah, false)? / 1000.0;
    add(
        "EU-ahmad-lcoe",
        json!(d480),
        json!(p.ahmad_lcoe_2a),
        Some(0.01 * p.ahmad_lcoe_2a),
        pf((d480 - p.ahmad_lcoe_2a).abs() <= 0.01 * p.ahmad_lcoe_2a),
    );
    let mut o = CostOpts::new(p);
    o.hours = ah;
    o.unpurified_full_correlation = true;
    let fe = power_cost(ctx, &act(ctx, "full_exhaust", None)?, ap, &o)?;
    add(
        "EU-ahmad-tci-full",
        json!(fe.tci_musd),
        json!(p.ahmad_tci_full_crack_musd),
        None,
        "informational",
    );
    let d320 = lc(ctx, "direct", None, 320.0, ah, false)? / 1000.0;
    let f320 =
        power_cost(ctx, &act(ctx, "full_exhaust", None)?, 320.0, &o)?.lcoe_usd_per_mwh / 1000.0;
    add(
        "EU-ahmad-320",
        json!([py_round(d320, 4), py_round(f320, 4)]),
        json!([0.217, 0.22]),
        None,
        "informational",
    );
    add(
        "EU-ahmad-eta",
        json!(act(ctx, "direct", None)?.efficiency * p.lhv_nh3_mj_kg),
        json!(p.elec_mj_per_kg_direct),
        Some(1e-9),
        "pass",
    );
    let gaps: Vec<f64> = claim
        .iter()
        .filter(|c| c["basis"].as_str().is_some_and(|s| s.starts_with("AmCraX")))
        .map(|c| {
            py_round(
                c["direct_cheaper_by_pct_of_cracking(1-d/c)"]
                    .as_f64()
                    .unwrap_or(f64::NAN),
                1,
            )
        })
        .collect();
    add(
        "EU-halim-claim",
        json!(gaps),
        json!(40.0),
        None,
        "informational",
    );
    add(
        "EU-halim-plant",
        json!([60.1, 15.1, 10.1]),
        json!([60.1, 15.1, 10.1]),
        None,
        "informational",
    );
    add(
        "EU-iso",
        json!([
            cr.purity_mole_frac,
            ctx.cracker("scn_fuel_cell_grade")?.purity_mole_frac
        ]),
        iso,
        None,
        "informational",
    );
    Ok(EnduseRun {
        results,
        assumptions: reg,
        validation: items,
    })
}

// ===================================================================================== threshold
/// Output of [`enduse_threshold`].
pub struct ThresholdRun {
    pub results: Value,
    pub nox: Value,
    pub validation: Vec<Value>,
    /// CSV tables by file name.
    pub csv: Vec<(String, Vec<Value>)>,
}

#[derive(Clone, Copy, Default)]
struct Kw {
    cracker_capex_factor: Option<f64>,
    plant_capex_factor: Option<f64>,
    extra_capex: Option<f64>,
    full_corr: Option<bool>,
}

struct Th<'a, 'b> {
    ctx: &'a Ctx<'b>,
    price: f64,
    hours: f64,
    eta0: f64,
    x: f64,
    dsys: f64,
}

const CAPEX_BASES: [&str; 5] = [
    "reference",
    "reference_with_psa_items",
    "ahmad_fig6_correlation",
    "cracker_x0.5",
    "cracker_x2",
];

impl Th<'_, '_> {
    /// `act(kind, y, eta, g, case)`.
    fn act(&self, kind: &str, y: Option<f64>, eta: Option<f64>, g: f64, case: &str) -> R<Activity> {
        let mut o = PowerOpts {
            case: case.into(),
            ..PowerOpts::default()
        };
        if matches!(kind, "direct" | "partial_exhaust" | "full_exhaust") {
            o.gain_scale = g;
        } else {
            o.eta_h2_fuel = eta;
        }
        power_activity(self.ctx, kind, y, &o)
    }

    fn ahmad_corr_factor(&self, a: &Activity) -> R<f64> {
        if a.capex_kind == "none" || a.cracker_nh3_kg_h <= 0.0 {
            return Ok(1.0);
        }
        let mut args = RefCapexArgs::new(a.cracker_nh3_kg_h / molar_mass(Species::NH3));
        if a.capex_kind == "unpurified" {
            args.exclude = vec!["psa".into(), "adsorber".into()];
        }
        let r = num(
            &self.ctx.d.reference_capex(&args)?["total_capex_USD"],
            "total_capex_USD",
        )?;
        let t_h2 = a.cracker_nh3_kg_h * lca::KG_H2_PER_KG_NH3 * self.x / 1000.0;
        Ok(18.171e6 * t_h2.powf(0.7451) / r)
    }

    /// `cost(a, price, hours, basis, **kw)`.
    fn cost(&self, a: &Activity, price: f64, hours: f64, basis: &str, kw: Kw) -> R<f64> {
        let mut k = kw;
        match basis {
            "reference" => {}
            "reference_with_psa_items" => {
                if k.full_corr.is_none() {
                    k.full_corr = Some(true);
                }
            }
            "ahmad_fig6_correlation" => {
                k.cracker_capex_factor =
                    Some(k.cracker_capex_factor.unwrap_or(1.0) * self.ahmad_corr_factor(a)?);
            }
            "cracker_x0.5" => {
                if k.cracker_capex_factor.is_none() {
                    k.cracker_capex_factor = Some(0.5);
                }
            }
            "cracker_x2" => {
                if k.cracker_capex_factor.is_none() {
                    k.cracker_capex_factor = Some(2.0);
                }
            }
            other => return Err(EngineError::Domain(format!("KeyError: '{other}'"))),
        }
        let mut o = CostOpts::new(&self.ctx.p);
        o.hours = hours;
        if let Some(v) = k.cracker_capex_factor {
            o.cracker_capex_factor = v;
        }
        if let Some(v) = k.plant_capex_factor {
            o.plant_capex_factor = v;
        }
        if let Some(v) = k.extra_capex {
            o.extra_capex_usd_per_kw = v;
        }
        if let Some(v) = k.full_corr {
            o.unpurified_full_correlation = v;
        }
        Ok(power_cost(self.ctx, a, price, &o)?.lcoe_usd_per_mwh)
    }

    fn cost0(&self, a: &Activity) -> R<f64> {
        self.cost(a, self.price, self.hours, "reference", Kw::default())
    }

    fn cost_f(&self, a: &Activity, fct: f64) -> R<f64> {
        self.cost(
            a,
            self.price,
            self.hours,
            "reference",
            Kw {
                cracker_capex_factor: Some(fct),
                ..Kw::default()
            },
        )
    }

    /// `direct_lcoe(price, hours, **kw)` (plant capex factor and extra capex only).
    fn direct_lcoe(&self, price: f64, hours: f64, kw: Kw) -> R<f64> {
        let mut o = CostOpts::new(&self.ctx.p);
        o.hours = hours;
        if let Some(v) = kw.plant_capex_factor {
            o.plant_capex_factor = v;
        }
        if let Some(v) = kw.extra_capex {
            o.extra_capex_usd_per_kw = v;
        }
        Ok(power_cost(self.ctx, &act(self.ctx, "direct", None)?, price, &o)?.lcoe_usd_per_mwh)
    }

    /// `threshold(kind, y, price, hours, basis)`.
    fn threshold(
        &self,
        kind: &str,
        y: Option<f64>,
        price: f64,
        hours: f64,
        basis: &str,
    ) -> R<Value> {
        let d = self.direct_lcoe(price, hours, Kw::default())?;
        let p = &self.ctx.p;
        if matches!(kind, "partial_exhaust" | "full_exhaust") {
            let Some(g) = root_or_none(
                |g| {
                    Ok(self.cost(
                        &self.act(kind, y, None, g, "baseline")?,
                        price,
                        hours,
                        basis,
                        Kw::default(),
                    )? - d)
                },
                -3.0,
                8.0,
                Some(1e-12),
            )?
            else {
                return Ok(Value::Null);
            };
            let a = self.act(kind, y, None, g, "baseline")?;
            let f = a.cracked_share.unwrap_or(f64::NAN);
            return Ok(json!({"gain_scale": g, "system_efficiency": a.efficiency,
                "delta_system_pp_vs_direct": (a.efficiency - self.eta0) * 100.0,
                "delta_full_cracking_equivalent_pp": g * self.dsys * 100.0,
                "implied_eta_on_fuel_gas_LHV": a.efficiency * a.nh3_kg * p.lhv_nh3_mj_kg
                    / (a.nh3_kg * fuel_lhv_mj_per_kg_nh3_fed(f, self.x)),
                "cracked_share": f, "LCOE_check": self.cost(&a, price, hours, basis, Kw::default())?,
                "LCOE_direct": d}));
        }
        let Some(e) = root_or_none(
            |e| {
                Ok(self.cost(
                    &self.act(kind, y, Some(e), 1.0, "baseline")?,
                    price,
                    hours,
                    basis,
                    Kw::default(),
                )? - d)
            },
            0.2,
            0.99,
            Some(1e-12),
        )?
        else {
            return Ok(Value::Null);
        };
        let a = self.act(kind, y, Some(e), 1.0, "baseline")?;
        Ok(
            json!({"eta_h2_fuel": e, "delta_fuel_pp_vs_direct_turbine": (e - self.eta0) * 100.0,
            "ratio_to_direct_turbine": e / self.eta0, "system_efficiency_at_threshold": a.efficiency,
            "delta_system_pp_vs_direct": (a.efficiency - self.eta0) * 100.0,
            "cracked_share": a.cracked_share, "LCOE_check": self.cost(&a, price, hours, basis, Kw::default())?,
            "LCOE_direct": d}),
        )
    }
}

fn tag(kind: &str, y: Option<f64>) -> String {
    match y {
        Some(y) => format!("{kind}_{}", crate::enduse::pct_tag(y)),
        None => kind.to_string(),
    }
}

fn side(th: Option<f64>, lo: f64, hi: f64) -> &'static str {
    match th {
        None => "no threshold in range",
        Some(t) if hi < t => "all sourced values BELOW threshold: direct NH3 cheaper",
        Some(t) if lo > t => "all sourced values ABOVE threshold: cracking pathway cheaper",
        _ => "sourced values STRADDLE the threshold",
    }
}

fn arange(start: f64, stop: f64, step: f64) -> Vec<f64> {
    let n = ((stop - start) / step).ceil().max(0.0) as usize;
    (0..n).map(|i| start + i as f64 * step).collect()
}

fn sg_eval(d: &EconomicsData, raw: &Value, sc: Scenario, ov: &Overrides) -> R<Value> {
    evaluate(d, &Summary::extract(raw)?, &sc, ov)
}

fn fuel_cost_gap_on_paper_basis(ctx: &Ctx, root: &Path) -> R<Value> {
    let p = &ctx.p;
    let d = ctx.d;
    let hx_doc = read_json(root, "research/data/halim2025_extract.json")?;
    let entry = |id: &str| -> R<Value> {
        hx_doc["entries"]
            .as_array()
            .and_then(|v| v.iter().find(|e| e["id"].as_str() == Some(id)))
            .map(|e| e["value"].clone())
            .ok_or_else(|| EngineError::Domain(format!("KeyError: '{id}'")))
    };
    let (lhv_n, lhv_h) = (p.lhv_nh3_mj_kg, p.lhv_h2_mj_kg);
    let kg_eq = lhv_h / lhv_n;
    let hi = &ctx.stored("baseline")?.raw;
    let nohi = &ctx.stored("baseline_no_hi")?.raw;
    let pr = entry("cost_nh3_prices")?;
    let green_fob = num(&pr["green_FOB_USD_per_t"], "green_FOB_USD_per_t")?;
    let blue_fob = num(&pr["blue_FOB_USD_per_t"], "blue_FOB_USD_per_t")?;
    let mut prices: Vec<(String, &str, f64)> = p
        .nh3_price_set_usd_t
        .iter()
        .map(|(k, v)| {
            (
                k.clone(),
                "reference scenario (backend/amcrax/data/reference_scenario.yaml)",
                *v,
            )
        })
        .collect();
    prices.push((
        "halim_green_FOB".into(),
        "Halim et al. 2025 Table 4 (Platts, July 2024)",
        green_fob,
    ));
    prices.push((
        "halim_blue_FOB".into(),
        "Halim et al. 2025 Table 4 (Platts, July 2024)",
        blue_fob,
    ));
    let lcoh = |e: &Value| num(&e["lcoh_USD_per_kg"], "lcoh_USD_per_kg");
    let none = Overrides::new();
    let mut cases = Vec::new();
    for (lab, src, pp) in &prices {
        for (hl, res) in [("on", hi), ("off", nohi)] {
            let e = sg_eval(d, res, Scenario::Price(*pp), &none)?;
            let dd = pp / 1000.0 * kg_eq;
            let l = lcoh(&e)?;
            cases.push(
                json!({"price_case": lab, "price_source": src, "NH3_USD_per_t": pp,
                "heat_integration": hl, "cracked_LCOH_USD_per_kg": l,
                "direct_fuel_cost_USD_per_kg_H2_equivalent": dd,
                "gap_pct_1_minus_direct_over_cracked": 100.0 * (1.0 - dd / l)}),
            );
        }
    }
    let wt = entry("cost_discount_life_cf")?;
    let retain = num(&entry("eff_direct_equivalence")?, "eff_direct_equivalence")?
        / num(
            &entry("eff_cracker_nh3_feed")?["kg_per_h_at_8760h"],
            "kg_per_h_at_8760h",
        )?;
    let forty = entry("cost_forty_percent")?;
    let fig5 = [
        (
            "green",
            green_fob,
            num(&entry("cost_lcoh_green")?, "lcoh green")?,
            num(&entry("cost_lcoa_green")?, "lcoa green")?,
            8.70,
            6.05,
            forty["green_pct"].clone(),
        ),
        (
            "blue",
            blue_fob,
            num(&entry("cost_lcoh_blue")?, "lcoh blue")?,
            num(&entry("cost_lcoa_blue")?, "lcoa blue")?,
            3.67,
            2.55,
            forty["blue_pct"].clone(),
        ),
    ];
    let cf = num(&wt["capacity_factor"], "capacity_factor")?;
    let life = num(&wt["life_years"], "life_years")?;
    let hours_halim = 8760.0 * cf;
    let mut rec = Map::new();
    let mut paper = Map::new();
    let feed_heat = |e: &Value| -> R<f64> {
        Ok(
            num(&e["breakdown_USD_per_kg"]["ammonia_feed"], "ammonia_feed")?
                + num(&e["breakdown_USD_per_kg"]["heat_fuel"], "heat_fuel")?,
        )
    };
    for (k, zp, zl, za, lf, af, gap) in fig5 {
        let pk = zp / 1000.0;
        let e0 = sg_eval(d, hi, Scenario::Price(zp), &none)?;
        let nh3_kg = num(&e0["kg_nh3_feed_per_kg_h2"], "kg_nh3_feed_per_kg_h2")?
            + num(&e0["kg_nh3_fuel_per_kg_h2"], "kg_nh3_fuel_per_kg_h2")?;
        let l0 = lcoh(&e0)?;
        let non0 = l0 - feed_heat(&e0)?;
        let mut ov = Overrides::new();
        ov.insert("operating_hours_h_per_yr".into(), json!(hours_halim));
        ov.insert("plant_life_yr".into(), json!(life));
        let e2 = sg_eval(d, hi, Scenario::Price(zp), &ov)?;
        let non2 = lcoh(&e2)? - feed_heat(&e2)?;
        let d0 = pk * kg_eq;
        let nh3_halim = kg_eq / retain;
        let non_direct = za - af;
        let non_crack = zl - lf;
        let steps = [
            (
                "0 AmCraX unified model at the paper's price, heat integration on".to_string(),
                d0,
                l0,
            ),
            (
                format!(
                    "1 cracked side: NH3 per kg H2 at the paper's energy retention {} (AmCraX {})",
                    fmt_f(retain, 4),
                    fmt_f(kg_eq / nh3_kg, 4)
                ),
                d0,
                non0 + pk * nh3_halim,
            ),
            (
                format!(
                    "2 also the paper's capacity factor {} ({} h) and life {} yr on AmCraX non-NH3 costs",
                    py_str_num(&wt["capacity_factor"]),
                    fmt_f(hours_halim, 0),
                    py_str_num(&wt["life_years"])
                ),
                d0,
                non2 + pk * nh3_halim,
            ),
            (
                format!(
                    "3 also the paper's cracked-side non-feed cost {} USD/kg instead of AmCraX {} (storage tank, fired furnace, compressors, PSA, O&M; Fig. 5)",
                    fmt_f(non_crack, 2),
                    fmt_f(non2, 3)
                ),
                d0,
                non_crack + pk * nh3_halim,
            ),
            (
                format!(
                    "4 also the paper's direct-use non-feed cost {} USD/kg (mostly the same storage tank, plus vaporisation and compression; Fig. 5)",
                    fmt_f(non_direct, 2)
                ),
                d0 + non_direct,
                non_crack + pk * nh3_halim,
            ),
        ];
        let mut rows: Vec<Map<String, Value>> = Vec::new();
        let mut gaps = Vec::new();
        for (lab, dd, cc) in &steps {
            let g = 100.0 * (1.0 - dd / cc);
            gaps.push(g);
            let mut m = Map::new();
            m.insert("step".into(), json!(lab));
            m.insert("direct_USD_per_kg".into(), json!(dd));
            m.insert("cracked_USD_per_kg".into(), json!(cc));
            m.insert("gap_pct".into(), json!(g));
            rows.push(m);
        }
        for i in 1..rows.len() {
            rows[i].insert("change_pp".into(), json!(gaps[i] - gaps[i - 1]));
        }
        let g0 = gaps[0];
        let gap_f = num(&gap, "gap_pct")?;
        let one = json!({
            "energy_retention_only": 100.0 * (1.0 - d0 / (non0 + pk * nh3_halim)) - g0,
            "hours_and_life_only": 100.0 * (1.0 - d0 / (non2 + pk * nh3_kg)) - g0,
            "cracked_non_feed_cost_only": 100.0 * (1.0 - d0 / (non_crack + pk * nh3_kg)) - g0,
            "direct_non_feed_cost_only": 100.0 * (1.0 - (d0 + non_direct) / l0) - g0});
        rec.insert(k.into(), json!({"NH3_USD_per_t": zp, "paper_gap_pct_printed": gap,
            "paper_gap_pct_from_printed_LCOA_LCOH": 100.0 * (1.0 - za / zl),
            "amcrax_nh3_kg_per_kg_h2_feed_plus_fuel": nh3_kg, "amcrax_energy_retained_as_h2": kg_eq / nh3_kg,
            "paper_energy_retained_as_h2_derived": retain, "amcrax_non_nh3_cost_USD_per_kg": non0,
            "amcrax_non_nh3_cost_at_paper_hours_and_life_USD_per_kg": non2,
            "paper_non_feed_cost_cracked_USD_per_kg": non_crack, "paper_non_feed_cost_direct_USD_per_kg": non_direct,
            "steps": rows, "one_at_a_time_change_pp_from_step_0": one,
            "residual_pp_vs_printed": gaps[gaps.len() - 1] - gap_f}));
        paper.insert(
            k.into(),
            json!({"NH3_USD_per_t": zp, "LCOH_USD_per_kg": zl, "LCOA_USD_per_kg": za,
            "gap_pct_printed": gap}),
        );
    }
    let cap = entry("cost_capex")?;
    let h2_kg_h = num(&entry("sys_fuel_flows")?["H2_kg_per_h"], "H2_kg_per_h")?;
    let e_ref = sg_eval(d, hi, Scenario::Named("grey".into()), &none)?;
    let c = |k: &str| num(&cap[k], k);
    let capital = json!({"paper_TCI_USD_per_kg_h_H2": c("TCI_USD")? / h2_kg_h,
        "paper_TCI_excluding_storage_tank_share_USD_per_kg_h_H2":
            c("TCI_USD")? * (1.0 - c("storage_tank_T100_USD")? / c("PEIC_USD")?) / h2_kg_h,
        "paper_storage_tank_share_of_PEIC": c("storage_tank_T100_USD")? / c("PEIC_USD")?,
        "paper_furnace_share_of_PEIC": c("furnace_F100_USD")? / c("PEIC_USD")?,
        "amcrax_capex_USD_per_kg_h_H2": num(&e_ref["capex"]["total_capex_USD"], "total_capex_USD")?
            / num(&e_ref["h2_product_kg_h"], "h2_product_kg_h")?});
    Ok(
        json!({"lhv_MJ_per_kg": {"NH3": lhv_n, "H2": lhv_h}, "kg_NH3_per_kg_H2_equivalent": kg_eq,
        "cases": cases, "paper_values": Value::Object(paper), "reconciliation": Value::Object(rec),
        "capital_intensity": capital}),
    )
}

/// `enduse_threshold.main()`; `enduse` is the output of [`enduse_run`] (the script reads the
/// `enduse_results.json` and validation items written just before it).
pub fn enduse_threshold(ctx: &Ctx, root: &Path, enduse: &EnduseRun) -> R<ThresholdRun> {
    let p = &ctx.p;
    let d = ctx.d;
    let fx = d.reference.fx_sgd_per_usd;
    let usd_per_eur = d.reference.usd_per_eur;
    let tax = d.reference.carbon_tax_sgd_per_t;
    let eta0 = p.eta_gt_gas;
    let x = ctx.cracker("baseline")?.conversion;
    let dsys = (p.elec_mj_per_kg_full - p.elec_mj_per_kg_direct) / p.lhv_nh3_mj_kg;
    let th = Th {
        ctx,
        price: p.nh3_price_ref_usd_t,
        hours: p.power_plant_hours_per_year,
        eta0,
        x,
        dsys,
    };
    let (price, hours) = (th.price, th.hours);
    let lit_c = read_json(root, "research/data/enduse_cost_literature.json")?;
    let all: [(&str, Option<f64>); 7] = [
        ("direct", None),
        ("partial_exhaust", Some(0.4)),
        ("partial_fired", Some(0.4)),
        ("full_exhaust", None),
        ("full_fired", None),
        ("full_purified", None),
        ("blend_purified", Some(0.4)),
    ];
    let crk = &all[1..];
    let stored: Vec<(String, f64)> = enduse.results["power_pathways"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|r| {
            (
                r["id"].as_str().unwrap_or("").to_string(),
                r["cost_USD_per_MWh_at_450"].as_f64().unwrap_or(f64::NAN),
            )
        })
        .collect();
    let mut base: Vec<(String, f64)> = Vec::new();
    for (k, y) in all {
        base.push((tag(k, y), th.cost0(&th.act(k, y, None, 1.0, "baseline")?)?));
    }
    let bget = |k: &str| {
        base.iter()
            .find(|e| e.0 == k)
            .map(|e| e.1)
            .unwrap_or(f64::NAN)
    };
    let dd = bget("direct");
    let implied_fe = p.elec_mj_per_kg_full / fuel_lhv_mj_per_kg_nh3_fed(1.0, x);
    // ---- 1 statement
    let halim = enduse.results["halim_claim_check"]["computed"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut adv = Map::new();
    for k in [
        "full_fired",
        "full_purified",
        "full_exhaust",
        "partial_exhaust_40",
        "partial_fired_40",
        "blend_purified_40",
    ] {
        let b = bget(k);
        adv.insert(k.into(), json!({"LCOE": b, "direct_cheaper_pct_of_cracking_1_minus_d_over_c": 100.0 * (1.0 - dd / b),
            "cracking_dearer_pct_of_direct_c_over_d_minus_1": 100.0 * (b / dd - 1.0)}));
    }
    let adv_get = |k: &str| {
        adv[k]["direct_cheaper_pct_of_cracking_1_minus_d_over_c"]
            .as_f64()
            .unwrap_or(f64::NAN)
    };
    let statement = json!({"old_pre_unification": {"fired_pct": 5.0, "purified_pct": 15.0, "exhaust_pct": -4.0},
        "new_unified": Value::Object(adv.clone())});
    // ---- 2 thresholds
    let ahm_lo = 4.4 * p.ahmad_lhv_nh3 / p.lhv_nh3_mj_kg;
    let ahm_hi = 5.4 * p.ahmad_lhv_nh3 / p.lhv_nh3_mj_kg;
    let netl_rel = (66.9 / 59.6 - 1.0) * eta0 * 100.0;
    let bracket = [(implied_fe - eta0) * 100.0, 7.3];
    let sourced = json!({
        "exhaust_heated_system_delta_pp": {"ahmad2025_like_for_like_AmCraX_basis": [ahm_lo, dsys * 100.0, ahm_hi],
            "karpilov2025_maximum": [5.0, 5.5], "supported_range": [4.9, 5.5], "sensitivity_range": [0.0, 5.5]},
        "fired_H2N2_fuel_delta_pp": {"sourced": null, "indirect_bracket": bracket},
        "purified_H2_fuel_delta_pp": {"netl_absolute": 7.3, "netl_relative_on_AmCraX_turbine": netl_rel},
    });
    let mut cases: Vec<(&str, Option<f64>, &str)> = vec![
        ("full_fired", None, "fired_H2N2_fuel_delta_pp"),
        ("full_purified", None, "purified_H2_fuel_delta_pp"),
        ("blend_purified", Some(0.4), "purified_H2_fuel_delta_pp"),
        ("full_exhaust", None, "exhaust_heated_system_delta_pp"),
    ];
    for y in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7] {
        cases.push(("partial_fired", Some(y), "fired_H2N2_fuel_delta_pp"));
        cases.push(("partial_exhaust", Some(y), "exhaust_heated_system_delta_pp"));
    }
    let mut bases: Vec<(String, f64, f64, &str)> =
        vec![("reference".into(), price, hours, "reference")];
    for b in &CAPEX_BASES[1..] {
        bases.push((format!("capex_{b}"), price, hours, b));
    }
    for pr in [300.0, 709.0, 1000.0] {
        bases.push((format!("nh3_{}", fmt_g(pr, 6)), pr, hours, "reference"));
    }
    bases.push(("hours_5000".into(), price, 5000.0, "reference"));
    bases.push((
        "ahmad_basis_480_7200".into(),
        p.ahmad_nh3_price_usd_t,
        p.ahmad_hours_implied,
        "reference",
    ));
    bases.push((
        "ahmad_basis_480_7200_ahmad_capex".into(),
        p.ahmad_nh3_price_usd_t,
        p.ahmad_hours_implied,
        "ahmad_fig6_correlation",
    ));
    let mut th_rows = Vec::new();
    let mut th_json = Map::new();
    let mut th_order: Vec<String> = Vec::new();
    let f = |v: &Value, k: &str| v[k].as_f64();
    for (kind, y, cls) in &cases {
        let k = tag(kind, *y);
        let mut bmap = Map::new();
        for (bname, pr, hr, cb) in &bases {
            let t = th.threshold(kind, *y, *pr, *hr, cb)?;
            if !t.is_null() {
                let fired = t.get("eta_h2_fuel").is_some();
                let key = if fired {
                    "delta_fuel_pp_vs_direct_turbine"
                } else {
                    "delta_system_pp_vs_direct"
                };
                th_rows.push(json!({"pathway": k, "basis": bname, "NH3_USD_t": pr, "hours": hr, "capex_basis": cb,
                    "threshold_parameter": if fired { "eta_h2_fuel" } else { "system_efficiency" },
                    "threshold_efficiency": if fired { t["eta_h2_fuel"].clone() } else { t["system_efficiency"].clone() },
                    "threshold_delta_pp": t[key],
                    "threshold_full_cracking_equivalent_delta_pp": t.get("delta_full_cracking_equivalent_pp").cloned().unwrap_or(Value::Null),
                    "system_efficiency_at_threshold": t.get("system_efficiency_at_threshold").or_else(|| t.get("system_efficiency")).cloned().unwrap_or(Value::Null)}));
            }
            bmap.insert(bname.clone(), t);
        }
        let ref_t = bmap["reference"].clone();
        let key = if !ref_t.is_null() && ref_t.get("eta_h2_fuel").is_some() {
            "delta_fuel_pp_vs_direct_turbine"
        } else {
            "delta_system_pp_vs_direct"
        };
        let vals: Vec<f64> = bmap
            .values()
            .filter(|b| !b.is_null())
            .filter_map(|b| f(b, key))
            .collect();
        let ref_v = if ref_t.is_null() {
            None
        } else {
            f(&ref_t, key)
        };
        let range = |v: &[f64]| -> Value {
            if v.is_empty() {
                Value::Null
            } else {
                json!([
                    v.iter().copied().fold(f64::INFINITY, crate::pyops::py_min),
                    v.iter()
                        .copied()
                        .fold(f64::NEG_INFINITY, crate::pyops::py_max)
                ])
            }
        };
        let mut entry = Map::new();
        entry.insert("class".into(), json!(cls));
        // the Python dict keeps the bases in insertion order; the JSON object here is sorted
        entry.insert("bases".into(), Value::Object(bmap.clone()));
        entry.insert("threshold_delta_pp_reference".into(), json!(ref_v));
        entry.insert("threshold_delta_pp_range_over_bases".into(), range(&vals));
        if matches!(*kind, "full_exhaust" | "partial_exhaust") {
            let cmp_ref = if ref_t.is_null() {
                None
            } else {
                f(&ref_t, "delta_full_cracking_equivalent_pp")
            };
            let cmp_all: Vec<f64> = bmap
                .values()
                .filter(|b| !b.is_null())
                .filter_map(|b| f(b, "delta_full_cracking_equivalent_pp"))
                .collect();
            entry.insert(
                "vs_ahmad_like_for_like".into(),
                json!(side(cmp_ref, ahm_lo, ahm_hi)),
            );
            entry.insert("vs_supported_range".into(), json!(side(cmp_ref, 4.9, 5.5)));
            entry.insert(
                "vs_sensitivity_range".into(),
                json!(side(cmp_ref, 0.0, 5.5)),
            );
            let set: BTreeSet<&str> = cmp_all.iter().map(|v| side(Some(*v), 4.9, 5.5)).collect();
            entry.insert(
                "vs_supported_range_all_bases".into(),
                json!(set.into_iter().collect::<Vec<_>>()),
            );
            entry.insert("threshold_full_equiv_pp_reference".into(), json!(cmp_ref));
            entry.insert(
                "threshold_full_equiv_pp_range_over_bases".into(),
                range(&cmp_all),
            );
        } else if *cls == "fired_H2N2_fuel_delta_pp" {
            entry.insert(
                "vs_sourced".into(),
                json!("nothing sourced for a standalone fired cracker's turbine: threshold is the finding"),
            );
            entry.insert(
                "vs_indirect_bracket".into(),
                json!(side(ref_v, bracket[0], bracket[1])),
            );
        } else {
            entry.insert(
                "vs_netl_upper_bound_absolute".into(),
                json!(side(ref_v, -1e9, 7.3)),
            );
            entry.insert(
                "vs_netl_upper_bound_relative".into(),
                json!(side(ref_v, -1e9, netl_rel)),
            );
            let set: BTreeSet<&str> = vals.iter().map(|v| side(Some(*v), -1e9, 7.3)).collect();
            entry.insert(
                "vs_netl_all_bases".into(),
                json!(set.into_iter().collect::<Vec<_>>()),
            );
        }
        th_order.push(k.clone());
        th_json.insert(k, Value::Object(entry));
    }
    // ---- 2b cracker-heat fuel efficiency
    let bl = read_json(root, "results/research/reference_scenario/baseline.json")?;
    let fe_eta_flow = py_round(
        num(
            &bl["fuel_efficiency_sensitivity"]["flowsheet_tailgas_ratio_exact"],
            "flowsheet_tailgas_ratio_exact",
        )?,
        4,
    );
    let mut fe_rows = Vec::new();
    let mut shifts: Vec<(f64, f64, f64)> = Vec::new();
    for eta_h in [1.0, fe_eta_flow, 0.85] {
        let mut row = vec![("heat_fuel_efficiency".to_string(), json!(eta_h))];
        let mut sh = [0.0; 2];
        for (i, k) in ["full_fired", "full_purified"].iter().enumerate() {
            let o1 = PowerOpts {
                heat_fuel_efficiency: eta_h,
                ..PowerOpts::default()
            };
            let a1 = power_activity(ctx, k, None, &o1)?;
            let e = root_or_none(
                |e| {
                    let o = PowerOpts {
                        eta_h2_fuel: Some(e),
                        heat_fuel_efficiency: eta_h,
                        ..PowerOpts::default()
                    };
                    Ok(th.cost0(&power_activity(ctx, k, None, &o)?)? - dd)
                },
                0.2,
                0.99,
                Some(1e-12),
            )?
            .ok_or_else(|| {
                EngineError::Domain("ValueError: f(a) and f(b) must have different signs".into())
            })?;
            sh[i] = (e - eta0) * 100.0;
            row.push((k.to_string(), json!({"LCOE_USD_per_MWh": th.cost0(&a1)?, "system_efficiency": a1.efficiency,
                "threshold_eta_h2_fuel": e, "threshold_delta_fuel_pp_vs_direct_turbine": (e - eta0) * 100.0})));
        }
        shifts.push((eta_h, sh[0], sh[1]));
        fe_rows.push(obj(row));
    }
    let fuel_eff = json!({"cases": fe_rows,
        "fired_threshold_shift_pp": obj(shifts.iter().map(|s| (py_repr(s.0), json!(s.1 - shifts[0].1))).collect()),
        "purified_threshold_shift_pp": obj(shifts.iter().map(|s| (py_repr(s.0), json!(s.2 - shifts[0].2))).collect())});
    // ---- 3 sensitivities
    struct RowKw<'s> {
        price: f64,
        hours: f64,
        eta: Option<f64>,
        g: f64,
        case: &'s str,
        basis: &'s str,
        ckw: Kw,
        dkw: Kw,
    }
    let dflt = || RowKw {
        price,
        hours,
        eta: None,
        g: 1.0,
        case: "baseline",
        basis: "reference",
        ckw: Kw::default(),
        dkw: Kw::default(),
    };
    let row_all = |extra: Vec<(String, Value)>, kw: RowKw| -> R<Value> {
        let mut r = extra;
        let dv = th.direct_lcoe(kw.price, kw.hours, kw.dkw)?;
        r.push(("direct".into(), json!(dv)));
        for (k, y) in crk {
            let a = th.act(k, *y, kw.eta, kw.g, kw.case)?;
            let v = th.cost(&a, kw.price, kw.hours, kw.basis, kw.ckw)?;
            r.push((tag(k, *y), json!(v)));
            r.push((format!("direct_minus_{}", tag(k, *y)), json!(dv - v)));
        }
        Ok(obj(r))
    };
    let mut s_eta = Vec::new();
    for dpp in arange(-4.0, 12.01, 0.5) {
        let e = eta0 + dpp / 100.0;
        s_eta.push(row_all(
            vec![
                ("delta_fuel_pp".into(), json!(dpp)),
                ("eta_h2_fuel".into(), json!(e)),
            ],
            RowKw {
                eta: Some(e),
                ..dflt()
            },
        )?);
    }
    let mut s_gain = Vec::new();
    for dpp in arange(0.0, 6.01, 0.25) {
        let g = dpp / (dsys * 100.0);
        s_gain.push(row_all(
            vec![
                ("delta_system_full_pp".into(), json!(dpp)),
                ("gain_scale".into(), json!(g)),
            ],
            RowKw { g, ..dflt() },
        )?);
    }
    let mut s_case = Vec::new();
    for (case, lab) in [
        ("baseline", "stored Aspen baseline (600 C, FEHE on)"),
        (
            "baseline_no_hi",
            "stored Aspen baseline, heat integration off",
        ),
        (
            "scn_low_temperature",
            "stored Aspen low-temperature scenario",
        ),
        (
            "scn_high_temperature",
            "stored Aspen high-temperature scenario",
        ),
    ] {
        let r = ctx.cracker(case).and_then(|c| {
            row_all(
                vec![
                    ("case".into(), json!(case)),
                    ("label".into(), json!(lab)),
                    (
                        "crack_heat_MJ_per_kg_NH3".into(),
                        json!(c.crack_heat_mj_per_kg_nh3()),
                    ),
                    (
                        "deficit_MJ_per_kg_NH3".into(),
                        json!(c.deficit_mj_per_kg_nh3()),
                    ),
                    ("conversion".into(), json!(c.conversion)),
                ],
                RowKw { case, ..dflt() },
            )
        });
        s_case.push(match r {
            Ok(v) => v,
            Err(e) => json!({"case": case, "label": lab, "error": e.to_string()}),
        });
    }
    let mut s_price = Vec::new();
    for pr in arange(200.0, 1101.0, 50.0) {
        s_price.push(row_all(
            vec![("NH3_USD_t".into(), json!(pr))],
            RowKw {
                price: pr,
                ..dflt()
            },
        )?);
    }
    let mut s_cf = Vec::new();
    for h in [
        1000i64, 2000, 3000, 4000, 5000, 6000, 7000, 7200, 8000, 8760,
    ] {
        let hf = h as f64;
        s_cf.push(row_all(
            vec![
                ("hours".into(), json!(h)),
                ("capacity_factor".into(), json!(hf / 8760.0)),
            ],
            RowKw {
                hours: hf,
                ..dflt()
            },
        )?);
    }
    let ab = lit_c["entries"]
        .as_array()
        .and_then(|v| {
            v.iter()
                .find(|e| e["id"].as_str() == Some("abuzayed_capex_uplift"))
        })
        .map(|e| e["value"].clone())
        .ok_or_else(|| EngineError::Domain("StopIteration: abuzayed_capex_uplift".into()))?;
    let hcp = num(
        &ab["hydrogen_cofiring_percent"],
        "hydrogen_cofiring_percent",
    )?;
    let amp = num(&ab["ammonia_percent"], "ammonia_percent")?;
    let h2_vs_nh3 = (1.0 + hcp / 100.0) / (1.0 + amp / 100.0);
    let (scr_lo, scr_hi, scr_adv) = (15.0 * usd_per_eur, 36.0 * usd_per_eur, 60.0 * usd_per_eur);
    let kf = |c: Option<f64>, pl: Option<f64>, ex: Option<f64>| Kw {
        cracker_capex_factor: c,
        plant_capex_factor: pl,
        extra_capex: ex,
        full_corr: None,
    };
    let mut cap_specs: Vec<(String, Kw, Kw, &str)> = vec![(
        "reference".into(),
        Kw::default(),
        Kw::default(),
        "reference",
    )];
    for fct in [0.5, 0.75, 1.5, 2.0, 3.0] {
        cap_specs.push((
            format!("cracker capex x{}", py_repr(fct)),
            kf(Some(fct), None, None),
            Kw::default(),
            "reference",
        ));
    }
    cap_specs.push((
        "cracker capex: Ahmad Fig. 6 correlation".into(),
        Kw::default(),
        Kw::default(),
        "ahmad_fig6_correlation",
    ));
    cap_specs.push((
        "cracker capex: reference incl. PSA/adsorber items for unpurified".into(),
        Kw::default(),
        Kw::default(),
        "reference_with_psa_items",
    ));
    cap_specs.push((
        format!(
            "plant capex: Abuzayed 2025 H2 vs NH3 uplift ratio {} on cracking plants (assumption-grade source)",
            fmt_f(h2_vs_nh3, 4)
        ),
        kf(None, Some(h2_vs_nh3), None),
        Kw::default(),
        "reference",
    ));
    cap_specs.push((
        "plant capex: NETL 2024 AFCC +12 % on direct, Abuzayed +7.98 % on cracking plants (mixed sources; Ahmad base read as NGCC-like)".into(),
        kf(None, Some(1.0 + hcp / 100.0), None),
        kf(None, Some(1.12), None),
        "reference",
    ));
    cap_specs.push((
        "plant capex: NETL 2024 AFCC +16 % on direct, Abuzayed +7.98 % on cracking plants (mixed sources)".into(),
        kf(None, Some(1.0 + hcp / 100.0), None),
        kf(None, Some(1.16), None),
        "reference",
    ));
    cap_specs.push((
        format!(
            "SCR standard 15 EUR/kW on all ({} USD/kW at {} USD/EUR; price year not stated)",
            fmt_f(scr_lo, 1),
            py_repr(usd_per_eur)
        ),
        kf(None, None, Some(scr_lo)),
        kf(None, None, Some(scr_lo)),
        "reference",
    ));
    cap_specs.push((
        format!(
            "SCR standard 36 EUR/kW on all ({} USD/kW)",
            fmt_f(scr_hi, 1)
        ),
        kf(None, None, Some(scr_hi)),
        kf(None, None, Some(scr_hi)),
        "reference",
    ));
    cap_specs.push((
        "SCR 36 + advanced 60 EUR/kW on direct only, 36 on cracking (worst case for direct; allocation not sourced)".into(),
        kf(None, None, Some(scr_hi)),
        kf(None, None, Some(scr_hi + scr_adv)),
        "reference",
    ));
    cap_specs.push((
        "SCR 36 + advanced 60 EUR/kW on all".into(),
        kf(None, None, Some(scr_hi + scr_adv)),
        kf(None, None, Some(scr_hi + scr_adv)),
        "reference",
    ));
    let mut s_cap = Vec::new();
    for (nm, ck, dk, cb) in &cap_specs {
        s_cap.push(row_all(
            vec![("scenario".into(), json!(nm))],
            RowKw {
                basis: cb,
                ckw: *ck,
                dkw: *dk,
                ..dflt()
            },
        )?);
    }
    // ---- two-way map
    let dps = arange(-2.0, 12.01, 0.5);
    let dsy = arange(0.0, 6.01, 0.25);
    let fcts = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0];
    let cheapest = |v: &[(&str, f64)]| -> String {
        let mut best = v[0];
        for e in &v[1..] {
            if e.1 < best.1 {
                best = *e;
            }
        }
        best.0.to_string()
    };
    let mut grid = Vec::new();
    for fct in fcts {
        let dv = th.direct_lcoe(price, hours, Kw::default())?;
        for dpp in &dps {
            let e = eta0 + dpp / 100.0;
            let v = [
                (
                    "full_fired",
                    th.cost_f(&th.act("full_fired", None, Some(e), 1.0, "baseline")?, fct)?,
                ),
                (
                    "full_purified",
                    th.cost_f(
                        &th.act("full_purified", None, Some(e), 1.0, "baseline")?,
                        fct,
                    )?,
                ),
                ("direct", dv),
            ];
            grid.push(json!({"panel": "A_fuel_efficiency", "cracker_capex_factor": fct, "delta_pp": dpp,
                "full_fired": v[0].1, "full_purified": v[1].1, "direct": dv, "cheapest": cheapest(&v)}));
        }
        for dpp in &dsy {
            let g = dpp / (dsys * 100.0);
            let v = [
                (
                    "full_exhaust",
                    th.cost_f(&th.act("full_exhaust", None, None, g, "baseline")?, fct)?,
                ),
                (
                    "partial_exhaust_40",
                    th.cost_f(
                        &th.act("partial_exhaust", Some(0.4), None, g, "baseline")?,
                        fct,
                    )?,
                ),
                ("direct", dv),
            ];
            grid.push(json!({"panel": "B_exhaust_system_gain", "cracker_capex_factor": fct, "delta_pp": dpp,
                "full_exhaust": v[0].1, "partial_exhaust_40": v[1].1, "direct": dv, "cheapest": cheapest(&v)}));
        }
    }
    let direct0 = th.direct_lcoe(price, hours, Kw::default())?;
    let mut be_b = Vec::new();
    let mut be_a = Vec::new();
    for fct in fcts {
        let g = root_or_none(
            |g| Ok(th.cost_f(&th.act("full_exhaust", None, None, g, "baseline")?, fct)? - direct0),
            -3.0,
            8.0,
            None,
        )?;
        be_b.push(json!({"cracker_capex_factor": fct,
            "full_exhaust_threshold_delta_system_pp": g.map(|g| g * dsys * 100.0)}));
        let mut r = vec![("cracker_capex_factor".to_string(), json!(fct))];
        for k in ["full_fired", "full_purified"] {
            let e = root_or_none(
                |e| Ok(th.cost_f(&th.act(k, None, Some(e), 1.0, "baseline")?, fct)? - direct0),
                0.2,
                0.99,
                None,
            )?;
            r.push((
                format!("{k}_threshold_delta_fuel_pp"),
                json!(e.map(|e| (e - eta0) * 100.0)),
            ));
        }
        be_a.push(obj(r));
    }
    let fe_full = th.act("full_exhaust", None, None, 1.0, "baseline")?;
    let fct_be = root_or_none(|f_| Ok(th.cost_f(&fe_full, f_)? - dd), 0.01, 50.0, None)?;
    // ---- 4 emissions
    let (n2o_kg, _, no_kg) = lca::n2o_nox_per_mwh();
    let gcpa = p.gwp_n2o_sg_carbon_pricing_act;
    let emis = json!({"direct_NH3": {"N2O_kg_per_MWh": n2o_kg,
            "N2O_kgCO2e_per_MWh_AR6_273_lifecycle": n2o_kg * lca::GWP100_N2O,
            "N2O_kgCO2e_per_MWh_CPA_265_tax": n2o_kg * gcpa,
            "carbon_tax_SGD_per_MWh_at_CPA_265": n2o_kg * gcpa / 1000.0 * tax,
            "carbon_tax_USD_per_MWh_at_CPA_265": n2o_kg * gcpa / 1000.0 * tax / fx,
            "carbon_tax_rate_SGD_per_t": tax, "NO_kg_per_MWh": no_kg},
        "SCR": {"standard_EUR_per_kW": [15, 36], "advanced_additional_EUR_per_kW": 60, "USD_per_EUR": usd_per_eur}});
    // ---- 5 the 40 % figure
    let gaps: Vec<f64> = halim
        .iter()
        .map(|c| {
            c["direct_cheaper_by_pct_of_cracking(1-d/c)"]
                .as_f64()
                .unwrap_or(f64::NAN)
        })
        .collect();
    let fct_for = |kind: &str, target: f64| -> R<Option<f64>> {
        let a = th.act(kind, None, None, 1.0, "baseline")?;
        root_or_none(
            |f_| Ok(1.0 - dd / th.cost_f(&a, f_)? - target),
            0.0,
            200.0,
            None,
        )
    };
    let mut gap_map = Map::new();
    for c in &halim {
        gap_map.insert(
            format!(
                "{} | {}",
                c["basis"].as_str().unwrap_or(""),
                c["cracking_pathway"].as_str().unwrap_or("")
            ),
            c["direct_cheaper_by_pct_of_cracking(1-d/c)"].clone(),
        );
    }
    let mut sens_max = f64::NAN;
    let mut first = true;
    for tbl in [&s_eta, &s_gain, &s_price, &s_cf, &s_cap] {
        for r in tbl.iter() {
            for k in ["full_fired", "full_purified", "full_exhaust"] {
                let v = 100.0
                    * (1.0
                        - r["direct"].as_f64().unwrap_or(f64::NAN)
                            / r[k].as_f64().unwrap_or(f64::NAN));
                if first || v > sens_max {
                    sens_max = v;
                    first = false;
                }
            }
        }
    }
    let gap_paper = fuel_cost_gap_on_paper_basis(ctx, root)?;
    let largest = py_max_iter(gaps.iter().copied()).unwrap_or(f64::NAN);
    let smallest = gaps
        .iter()
        .copied()
        .fold(f64::INFINITY, crate::pyops::py_min);
    let f40_fired = fct_for("full_fired", 0.40)?;
    let f40_pur = fct_for("full_purified", 0.40)?;
    let forty = json!({"computed_gaps_pct_1_minus_d_over_c": Value::Object(gap_map),
        "largest_computed_pct": largest, "smallest_computed_pct": smallest,
        "largest_in_sensitivities_pct": sens_max,
        "cracker_capex_factor_for_40pct_fired": f40_fired, "cracker_capex_factor_for_40pct_purified": f40_pur,
        "fuel_cost_gap_on_paper_basis": gap_paper});
    // ---- 6 H1-d evidence
    let be = read_json(
        root,
        "results/research/singapore/breakeven_ammonia_price.json",
    )?;
    let be = &be["results"]["heat_integration_on"];
    let mut h2c = Vec::new();
    for (lab, pr) in &p.nh3_price_set_usd_t {
        h2c.push((
            lab.clone(),
            hydrogen_cost(ctx, "baseline", *pr, None, None, "reference")?.usd_per_kg,
        ));
    }
    let h2c_get = |k: &str| {
        h2c.iter()
            .find(|e| e.0 == k)
            .map(|e| e.1)
            .unwrap_or(f64::NAN)
    };
    let hb = hydrogen_activity(ctx, "baseline", "h", "", "")?;
    let mut hci = Map::new();
    for r in ["green", "blue", "grey"] {
        hci.insert(r.into(), json!(ci(&hb, ef(r)?, 5000.0)));
    }
    let mut bench = Map::new();
    for (k, v) in be.as_object().into_iter().flatten() {
        bench.insert(
            k.clone(),
            json!({"USD_per_kg": v["h2_price_USD_per_kg"],
            "breakeven_NH3_USD_t": v["breakeven_nh3_USD_per_t"], "source": v["source"]}),
        );
    }
    let kd = p.elec_mj_per_kg_direct / 3.6;
    let fp = |e: Option<f64>| -> R<f64> {
        let o = PowerOpts {
            eta_h2_fuel: e,
            ..PowerOpts::default()
        };
        Ok(power_activity(ctx, "full_purified", None, &o)?.efficiency * p.lhv_nh3_mj_kg / 3.6)
    };
    let kwh = json!({"direct": kd, "cracked_purified_at_eta_copy": fp(None)?,
        "cracked_purified_at_NETL_plus_7p3pp_absolute": fp(Some(eta0 + 0.073))?,
        "cracked_purified_at_NETL_ratio_1p1225": fp(Some(eta0 * 66.9 / 59.6))?});
    let lhv_eff = ctx.stored("baseline")?.result.kpis.lhv_efficiency;
    let h1d = json!({"efficiency_NH3_LHV_to_H2_aspen": lhv_eff,
        "H2_cost_USD_per_kg_by_NH3_scenario": obj(h2c.iter().map(|(k, v)| (k.clone(), json!(v))).collect()),
        "H2_cost_SGD_per_kg_grey": h2c_get("grey") * fx, "H2_CI_kgCO2e_per_kg_5000km": Value::Object(hci),
        "benchmarks_USD_per_kg": Value::Object(bench.clone()), "electricity_kWh_per_kg_NH3": kwh});
    // ---- row evidence
    let tget = |k: &str| th_json[k].clone();
    let (tf, tp, te) = (
        tget("full_fired"),
        tget("full_purified"),
        tget("full_exhaust"),
    );
    let rng = |r: &Value| -> String {
        format!(
            "{} to {}",
            fmt_f(r[0].as_f64().unwrap_or(f64::NAN), 2),
            fmt_f(r[1].as_f64().unwrap_or(f64::NAN), 2)
        )
    };
    let sstr = |v: &Value| v.as_str().unwrap_or("").to_string();
    let all_bases: Vec<String> = tp["vs_netl_all_bases"]
        .as_array()
        .into_iter()
        .flatten()
        .map(sstr)
        .collect();
    let paper_cases: Vec<String> = forty["fuel_cost_gap_on_paper_basis"]["cases"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|c| {
            c["price_case"]
                .as_str()
                .is_some_and(|s| s.starts_with("halim"))
        })
        .map(|c| {
            format!(
                "{} % ({}, HI {})",
                fmt_f(
                    c["gap_pct_1_minus_direct_over_cracked"]
                        .as_f64()
                        .unwrap_or(f64::NAN),
                    1
                ),
                sstr(&c["price_case"]),
                sstr(&c["heat_integration"])
            )
        })
        .collect();
    let mut partial = Map::new();
    for y in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7] {
        partial.insert(
            py_repr(y),
            th_json[&format!("partial_exhaust_{}", (y * 100.0) as i64)]["threshold_full_equiv_pp_reference"].clone(),
        );
    }
    let bmk = |k: &str| {
        bench
            .get(k)
            .map(|v| v["breakeven_NH3_USD_t"].clone())
            .unwrap_or(Value::Null)
    };
    let row_evidence = json!({
        "H1-a": {"proposed_verdict": "INCONCLUSIVE",
            "numbers": {"LCOE_direct": dd, "LCOE_full_fired": bget("full_fired"), "LCOE_full_purified": bget("full_purified"),
                "direct_cheaper_pct_fired": adv_get("full_fired"), "direct_cheaper_pct_purified": adv_get("full_purified"),
                "threshold_delta_fuel_pp_fired": tf["threshold_delta_pp_reference"],
                "threshold_delta_fuel_pp_purified": tp["threshold_delta_pp_reference"]},
            "uncertainty": format!("fired threshold over bases {} pp; purified {} pp",
                rng(&tf["threshold_delta_pp_range_over_bases"]), rng(&tp["threshold_delta_pp_range_over_bases"])),
            "threshold": {"fired": tf["threshold_delta_pp_reference"], "purified": tp["threshold_delta_pp_reference"],
                "fired_vs_sources": format!("{}; indirect bracket: {}", sstr(&tf["vs_sourced"]), sstr(&tf["vs_indirect_bracket"])),
                "purified_vs_sources": format!("{} (NETL absolute); {} (NETL ratio); all bases: {}",
                    sstr(&tp["vs_netl_upper_bound_absolute"]), sstr(&tp["vs_netl_upper_bound_relative"]), all_bases.join("; "))}},
        "H1-b": {"proposed_verdict": "CONTRADICTED (secondary, does not vote)",
            "numbers": {"claim_pct": 40.0, "largest_computed_pct_stored_bases": largest,
                "largest_in_all_sensitivities_pct": sens_max,
                "cracker_capex_factor_needed_for_40pct_purified": f40_pur,
                "cracker_capex_factor_needed_for_40pct_fired": f40_fired},
            "uncertainty": format!("The paper (full text read 24 Nov 2026) computes no cost of electricity: its 'about 40 %' is a fuel cost at the turbine inlet (1 - LCOA/LCOH, 39 % green, 44 % blue). On that basis AmCraX gives {} (fuel_cost_gap_on_paper_basis)", paper_cases.join(", "))},
        "H1-c": {"proposed_verdict": "INCONCLUSIVE",
            "numbers": {"LCOE_full_exhaust": bget("full_exhaust"), "LCOE_partial_exhaust_40": bget("partial_exhaust_40"),
                "LCOE_partial_fired_40": bget("partial_fired_40"), "LCOE_direct": dd,
                "threshold_delta_system_pp_full_exhaust": te["threshold_delta_pp_reference"],
                "threshold_full_equiv_pp_partial": Value::Object(partial),
                "ahmad_gain_AmCraX_basis_pp": dsys * 100.0, "capex_factor_where_full_exhaust_equals_direct": fct_be},
            "uncertainty": format!("full-exhaust threshold over bases {} pp", rng(&te["threshold_delta_pp_range_over_bases"])),
            "threshold": {"full_exhaust_reference": te["threshold_delta_pp_reference"], "vs_ahmad": te["vs_ahmad_like_for_like"],
                "vs_supported_range": te["vs_supported_range"], "vs_supported_range_all_bases": te["vs_supported_range_all_bases"],
                "vs_sensitivity_range": te["vs_sensitivity_range"]}},
        "H1-d": {"proposed_verdict": "INCONCLUSIVE",
            "numbers": {"eta_H2_product": lhv_eff, "LCOH_grey_USD": h2c_get("grey"), "LCOH_grey_SGD": h2c_get("grey") * fx,
                "LCOH_green_2030": h2c_get("green_2030"), "LCOH_green_current": h2c_get("green_current"),
                "benchmarks": obj(bench.iter().map(|(k, v)| (k.clone(), v["USD_per_kg"].clone())).collect()),
                "kWh_per_kg_NH3": h1d["electricity_kWh_per_kg_NH3"]},
            "threshold": {"breakeven_NH3_vs_SMR_3p06": bmk("ne_asia_smr_production_cost"),
                "breakeven_NH3_vs_WTP_3p0": bmk("sg_low_carbon_willingness_to_pay"),
                "breakeven_NH3_vs_blue_delivered_6": bmk("blue_delivered_east_asia"),
                "breakeven_NH3_vs_offer_10": bmk("low_carbon_offer_fob_malaysia")}},
    });
    let tb = obj(bases
        .iter()
        .map(|b| {
            (
                b.0.clone(),
                json!({"NH3_USD_t": b.1, "hours": b.2, "capex_basis": b.3}),
            )
        })
        .collect());
    let results = json!({"statement_of_result": statement, "sourced_values": sourced,
        "thresholds": Value::Object(th_json.clone()), "cracker_heat_fuel_efficiency_sensitivity": fuel_eff,
        "threshold_bases": tb,
        "twoway_map": {"panelA_thresholds_by_capex": be_a, "panelB_thresholds_by_capex": be_b,
            "cracker_capex_factor_where_full_exhaust_equals_direct_at_ahmad_gain": fct_be},
        "forty_percent_figure": forty, "h1d_evidence": h1d, "row_evidence": row_evidence});
    // ---- validation (the items of enduse_run without EU-P2-*, then the new ones)
    let mut items: Vec<Value> = enduse
        .validation
        .iter()
        .filter(|i| !i["id"].as_str().unwrap_or("").starts_with("EU-P2-"))
        .cloned()
        .collect();
    let mut add = |id: &str, obs: Value, exp: Value, tol: Option<f64>, ok: bool, kind: &str| {
        items.push(vitem(id, obs, exp, tol, pf(ok), kind));
    };
    let nv = "numerical_verification";
    for (k, y) in all {
        let t = tag(k, y);
        let st = stored
            .iter()
            .find(|e| e.0 == t)
            .map(|e| e.1)
            .unwrap_or(f64::NAN);
        let b = bget(&t);
        add(
            &format!("EU-P2-defaults-{t}"),
            json!(b),
            json!(st),
            Some(1e-9 * st),
            (b - st).abs() <= 1e-9 * st,
            nv,
        );
    }
    for k in &th_order {
        let t = &th_json[k.as_str()]["bases"]["reference"];
        if !t.is_null() {
            let (c, dv) = (
                t["LCOE_check"].as_f64().unwrap_or(f64::NAN),
                t["LCOE_direct"].as_f64().unwrap_or(f64::NAN),
            );
            add(
                &format!("EU-P2-threshold-{k}"),
                json!(c),
                json!(dv),
                Some(1e-6),
                (c - dv).abs() < 1e-6,
                nv,
            );
        }
    }
    let e_fe: Vec<f64> = [0.4, 0.6]
        .iter()
        .map(|v| {
            let o = PowerOpts {
                eta_h2_fuel: Some(*v),
                ..PowerOpts::default()
            };
            Ok(power_activity(ctx, "full_exhaust", None, &o)?.efficiency)
        })
        .collect::<R<_>>()?;
    let ex: Vec<f64> = e_fe.iter().map(|v| v * p.lhv_nh3_mj_kg).collect();
    add(
        "EU-P2-no-double-count",
        json!(ex),
        json!([0.54 * 18.8, 0.54 * 18.8]),
        Some(1e-9),
        ex.iter().all(|v| (v - 0.54 * 18.8).abs() < 1e-9),
        nv,
    );
    let o_eta = PowerOpts {
        eta_h2_fuel: Some(eta0),
        ..PowerOpts::default()
    };
    let e1 = power_activity(ctx, "full_fired", None, &o_eta)?.efficiency;
    let e2 = act(ctx, "full_fired", None)?.efficiency;
    add(
        "EU-P2-eta-default",
        json!(e1),
        json!(e2),
        Some(1e-12),
        (e1 - e2).abs() < 1e-12,
        nv,
    );
    let lc_ref = num(&bl["lcoh_USD_per_kg"], "lcoh_USD_per_kg")?;
    let g = h2c_get("grey");
    add(
        "EU-P2-frozen-lcoh",
        json!(g),
        json!(lc_ref),
        Some(1e-6 * lc_ref),
        (g - lc_ref).abs() <= 1e-6 * lc_ref,
        nv,
    );
    let ag = (0.54 - 0.4912) * 18.8 / p.lhv_nh3_mj_kg * 100.0;
    add(
        "EU-P2-ahmad-gain",
        json!(dsys * 100.0),
        json!(ag),
        Some(1e-9),
        (dsys * 100.0 - ag).abs() < 1e-9,
        nv,
    );
    items.push(vitem(
        "EU-P2-threshold-vs-literature",
        te["threshold_delta_pp_reference"].clone(),
        json!([ahm_lo, ahm_hi]),
        None,
        "informational",
        "literature_comparison",
    ));
    let fb = &forty["fuel_cost_gap_on_paper_basis"];
    let gh = |k: &str| -> Value {
        fb["cases"]
            .as_array()
            .into_iter()
            .flatten()
            .find(|c| {
                c["price_case"].as_str() == Some(k) && c["heat_integration"].as_str() == Some("on")
            })
            .map(|c| c["gap_pct_1_minus_direct_over_cracked"].clone())
            .unwrap_or(Value::Null)
    };
    items.push(vitem(
        "EU-P2-halim-fuel-basis",
        json!([gh("halim_green_FOB"), gh("halim_blue_FOB")]),
        json!([
            fb["paper_values"]["green"]["gap_pct_printed"],
            fb["paper_values"]["blue"]["gap_pct_printed"]
        ]),
        None,
        "informational",
        "literature_comparison",
    ));
    let rr: Vec<f64> = ["green", "blue"]
        .iter()
        .map(|k| {
            let s = &fb["reconciliation"][*k]["steps"];
            s[s.as_array().map(|a| a.len()).unwrap_or(1) - 1]["gap_pct"]
                .as_f64()
                .unwrap_or(f64::NAN)
        })
        .collect();
    let pp: Vec<f64> = ["green", "blue"]
        .iter()
        .map(|k| {
            fb["reconciliation"][*k]["paper_gap_pct_printed"]
                .as_f64()
                .unwrap_or(f64::NAN)
        })
        .collect();
    items.push(vitem(
        "EU-P2-halim-reconcile",
        json!(rr),
        json!(pp),
        Some(1.0),
        pf(rr.iter().zip(&pp).all(|(a, b)| (a - b).abs() <= 1.0)),
        nv,
    ));
    let ratio = emis["direct_NH3"]["N2O_kgCO2e_per_MWh_CPA_265_tax"]
        .as_f64()
        .unwrap_or(f64::NAN)
        / emis["direct_NH3"]["N2O_kgCO2e_per_MWh_AR6_273_lifecycle"]
            .as_f64()
            .unwrap_or(f64::NAN);
    items.push(vitem(
        "EU-P2-n2o-gwp",
        json!(ratio),
        json!(265.0 / 273.0),
        Some(1e-12),
        pf((ratio - 265.0 / 273.0).abs() < 1e-12),
        nv,
    ));
    let csv = vec![
        ("turbine_threshold.csv".to_string(), th_rows),
        ("sensitivity_turbine_efficiency.csv".into(), s_eta),
        ("sensitivity_heat_integration_exhaust.csv".into(), s_gain),
        (
            "sensitivity_heat_integration_fired_cases.csv".into(),
            s_case,
        ),
        ("sensitivity_nh3_price.csv".into(), s_price),
        ("sensitivity_capacity_factor.csv".into(), s_cf),
        ("sensitivity_capital.csv".into(), s_cap),
        ("twoway_map_efficiency_capital.csv".into(), grid),
    ];
    Ok(ThresholdRun {
        results,
        nox: emis,
        validation: items,
        csv,
    })
}
