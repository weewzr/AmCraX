//! Heat integration coupled to catalyst performance (port of Python
//! `research/catalyst_comparison.py`): catalyst mass for a target conversion from the PFR, the
//! flowsheet at the kinetic conversion ([`Cracker::FixedConversion`] replaces the `mock.patch`
//! of `solve_equilibrium`), temperature-level heat accounting, fired duty, economics
//! (`singapore.evaluate`), carbon intensity, design points, LCOH(T) curves and their optimum.

use crate::economics::reference::EconomicsData;
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate};
use crate::enduse::{Activity, carbon_intensity};
use crate::error::EngineError;
use crate::heat::{analyse, pinch::problem_table, streams::extract_streams};
use crate::kinetics::KineticsRegistry;
use crate::process::result::{
    CaseInputs, LHV_KJ_PER_MOL, SimulationResult, get_or, jf, jo, molar_mass,
};
use crate::process::{Cracker, run_case};
use crate::props::FluidProps;
use crate::pyops::py_max;
use crate::reactor::{PfrInput, SolverOptions, Target, catalyst_mass_for_conversion};
use crate::species::Species;
use crate::thermo::equilibrium::ideal_conversion;
use serde_json::{Map, Value, json};
use std::collections::BTreeMap;

pub const FEED_TOTAL_KMOL_H: f64 = 100.0;
pub const FEED_H2O: f64 = 0.002;
pub const FEED_NH3_KMOL_H: f64 = FEED_TOTAL_KMOL_H * (1.0 - FEED_H2O);
pub const LCA_DISTANCE_KM: f64 = 5000.0;
pub const LCA_ROUTES: [&str; 3] = ["grey", "blue", "green"];
/// ASSUMPTION: fraction of supplementary-fuel LHV delivered to the process.
pub const FURNACE_EFFICIENCY: f64 = 0.85;
/// ASSUMPTION: wall/radiation loss, fraction of reactor + trim-heater duty.
pub const THERMAL_LOSS_FRACTION: f64 = 0.02;
pub const CATALYST_LIFETIME_YR: f64 = 2.0;
pub const REFERENCE_NI: &str = "ni_takahashi_microkinetic";

/// `research/data/catalyst_prices.json` (embedded).
pub const PRICE_JSON: &str = include_str!("../../../../research/data/catalyst_prices.json");

/// One catalyst of `CATALYSTS`.
#[derive(Debug, Clone, PartialEq)]
pub struct CatalystSpec {
    pub id: &'static str,
    pub label: &'static str,
    pub family: &'static str,
    pub short: &'static str,
    pub eps_b: f64,
    pub rho_particle: f64,
    pub price_key: &'static str,
    /// Derived central price, USD/kg (`derived_price(price_key)`).
    pub price: f64,
}

/// `derived_price(price_key, scenario)`.
pub fn derived_price(price_key: &str, scenario: &str) -> Result<f64, EngineError> {
    let v: Value = serde_json::from_str(PRICE_JSON)
        .map_err(|e| EngineError::data("catalyst_prices.json", e.to_string()))?;
    v["scenarios_usd_per_kg_finished_catalyst"][price_key][scenario]["usd_per_kg"]
        .as_f64()
        .ok_or_else(|| {
            EngineError::data(
                "catalyst_prices.json",
                format!("no price {price_key}/{scenario}"),
            )
        })
}

/// `CATALYSTS` in the Python dict order.
pub fn catalysts() -> Result<Vec<CatalystSpec>, EngineError> {
    let raw: [(&str, &str, &str, &str, f64, &str); 5] = [
        (
            "ru_kum_temkin_pyzhev",
            "Ru/Al2O3 (Kum)",
            "Ru",
            "Ru/Al2O3",
            980.0,
            "Ru/Al2O3",
        ),
        (
            "ru_takahashi_microkinetic",
            "Ru/MgO (Takahashi)",
            "Ru",
            "Ru/MgO",
            980.0,
            "Ru/MgO",
        ),
        (
            "nire_ceo2_5ni1ru_lucentini_lhhw",
            "5Ni1Ru/CeO2 (Lucentini)",
            "NiRu",
            "5Ni1Ru/CeO2",
            1651.8,
            "5Ni1Ru/CeO2",
        ),
        (
            "nire_ceo2_2p5ni0p5ru_lucentini_lhhw",
            "2.5Ni0.5Ru/CeO2 (Lucentini)",
            "NiRu",
            "2.5Ni0.5Ru/CeO2",
            1651.8,
            "2.5Ni0.5Ru/CeO2",
        ),
        (
            "ni_takahashi_microkinetic",
            "Ni/MgO (Takahashi)",
            "Ni",
            "Ni/MgO",
            980.0,
            "Ni/MgO",
        ),
    ];
    raw.iter()
        .map(|&(id, label, family, short, rho, pk)| {
            Ok(CatalystSpec {
                id,
                label,
                family,
                short,
                eps_b: 0.36,
                rho_particle: rho,
                price_key: pk,
                price: derived_price(pk, "central")?,
            })
        })
        .collect()
}

/// One catalyst by id.
pub fn catalyst(cid: &str) -> Result<CatalystSpec, EngineError> {
    catalysts()?
        .into_iter()
        .find(|c| c.id == cid)
        .ok_or_else(|| EngineError::Domain(format!("KeyError: '{cid}'")))
}

/// `bed_density(cid)`.
pub fn bed_density(c: &CatalystSpec) -> f64 {
    (1.0 - c.eps_b) * c.rho_particle
}

fn nh3_feed() -> [f64; 5] {
    [FEED_NH3_KMOL_H, 0.0, 0.0, 0.0, 0.0]
}

/// `eq_conversion(T_C, P_bar)`: ideal-gas equilibrium conversion of the NH3 feed.
pub fn eq_conversion(t_c: f64, p_bar: f64) -> Result<f64, EngineError> {
    ideal_conversion(t_c + 273.15, p_bar, &nh3_feed())
}

/// The engine context of the study (kinetics registry, PFR solver options, economics data,
/// fluid-property back end).
pub struct Ctx<'a> {
    pub reg: &'a KineticsRegistry,
    pub sopt: SolverOptions,
    pub econ: &'a EconomicsData,
    pub props: &'a dyn FluidProps,
}

/// `required_mass_kg(cid, T_C, P_bar, X)`: catalyst mass for conversion X (NaN if not reachable).
pub fn required_mass_kg(
    ctx: &Ctx,
    cid: &str,
    t_c: f64,
    p_bar: f64,
    x: f64,
) -> Result<f64, EngineError> {
    let c = catalyst(cid)?;
    if eq_conversion(t_c, p_bar)? <= x + 1e-4 {
        return Ok(f64::NAN);
    }
    let mut base = PfrInput::new(cid, 1.0);
    base.t_in_c = t_c;
    base.p_in_bar = p_bar;
    base.feed_kmol_h = Some(BTreeMap::from([("NH3".to_string(), FEED_NH3_KMOL_H)]));
    base.mode = "isothermal".into();
    base.pressure_drop = false;
    base.eps_b = c.eps_b;
    base.rho_particle_kg_m3 = c.rho_particle;
    let r = catalyst_mass_for_conversion(ctx.reg, &base, Target::Conversion(x), 1e5, &ctx.sopt)?;
    Ok(r.w_kg)
}

/// `kinetic_flowsheet(T_C, P_bar, X, heat_integration, psa_recovery)`.
pub fn kinetic_flowsheet(
    ctx: &Ctx,
    t_c: f64,
    p_bar: f64,
    x: f64,
    heat_integration: bool,
    psa_recovery: f64,
) -> Result<SimulationResult, EngineError> {
    let ci = CaseInputs {
        case_id: "hcat".into(),
        feed_total_kmol_h: FEED_TOTAL_KMOL_H,
        feed_h2o_mole_frac: FEED_H2O,
        reactor_temperature_c: t_c,
        reactor_pressure_bar: p_bar,
        heat_integration,
        psa_h2_recovery: psa_recovery,
        ..CaseInputs::default()
    };
    ci.validate()?;
    let mut r = run_case(
        &ci,
        crate::thermo::equilibrium::Eos::Ideal,
        ctx.props,
        Cracker::FixedConversion(x),
    )?;
    r.notes.push(format!(
        "workstream H: cracker conversion fixed at the kinetic value X = {x:.4} (not equilibrium)"
    ));
    Ok(r)
}

fn num(v: &Value, k: &str) -> f64 {
    v[k].as_f64().unwrap_or(f64::NAN)
}

/// `heat_accounting(res, dT_min_K)` as the Python dict.
pub fn heat_accounting(
    ctx: &Ctx,
    res: &SimulationResult,
    dt_min_k: f64,
) -> Result<Value, EngineError> {
    let hi = res.inputs.heat_integration;
    let a = analyse(ctx.props, res, dt_min_k)?;
    let row = |id: &str| -> Result<&Value, EngineError> {
        a["configurations"]
            .as_array()
            .and_then(|v| v.iter().find(|r| r["id"].as_str() == Some(id)))
            .ok_or_else(|| EngineError::Domain(format!("KeyError: '{id}'")))
    };
    let k = &res.kpis;
    let (imp, tg_used, recovered) = if hi {
        (
            num(row("c")?, "external_heating_kW"),
            num(row("c")?, "tailgas_heat_used_kW"),
            num(row("b")?, "process_heat_recovered_kW"),
        )
    } else {
        let x = extract_streams(ctx.props, res)?;
        let flue = x
            .flue
            .as_ref()
            .ok_or_else(|| EngineError::Domain("no flue-gas curve (TypeError in Python)".into()))?;
        let r = problem_table(&[&x.feed, &x.reaction, flue], dt_min_k)?;
        let imp = r.hot_utility_kw;
        (imp, x.feed.duty_kw() + x.reaction.duty_kw() - imp, 0.0)
    };
    let fe = &a["fehe"];
    let ua = match fe["ua_segmented_kW_K"].as_f64().filter(|v| *v != 0.0) {
        Some(v) => Value::from(v),
        None => fe["ua_lmtd_kW_K"].clone(),
    };
    let tg = if tg_used.is_nan() || tg_used != 0.0 {
        tg_used
    } else {
        0.0
    };
    let or0 = |x: Option<f64>| match x {
        Some(v) if v != 0.0 => v,
        _ => 0.0,
    };
    Ok(json!({
        "heat_integration": hi, "dT_min_K": jf(dt_min_k),
        "external_heat_import_kW": jf(imp), "tailgas_heat_used_kW": jf(tg), "recovered_heat_kW": jf(recovered),
        "pinch_min_hot_utility_process_only_kW": a["targets_process"]["hot_utility_kW"],
        "pinch_min_hot_utility_with_flue_kW": if a["targets_with_flue"].is_null() { Value::Null } else { a["targets_with_flue"]["hot_utility_kW"].clone() },
        "pinch_temperature_C": a["targets_process"]["pinch_shifted_C"],
        "pinch_energy_balance_residual_kW": a["targets_process"]["energy_balance_residual_kW"],
        "fehe_duty_kW": if hi { fe["duty_kW"].clone() } else { jf(0.0) },
        "fehe_UA_kW_K": if hi { ua } else { jf(0.0) },
        "fehe_area_m2_at_U50": if hi { fe["area_m2"].clone() } else { jf(0.0) },
        "fehe_area_range_m2": if hi { fe["area_range_m2"].clone() } else { json!([]) },
        "kpi_total_external_heating_kW": jo(k.total_external_heating_kw), "kpi_recovered_heat_kW": jo(k.recovered_heat_kw),
        "kpi_tailgas_combustion_heat_kW": jo(k.tailgas_combustion_heat_kw),
        "kpi_net_fuel_heat_deficit_kW_first_law": jo(k.net_fuel_heat_deficit_kw),
        "reactor_duty_kW": jo(k.reactor_duty_kw), "preheat_duty_kW": jo(k.preheat_duty_kw),
        "vaporiser_duty_kW": jo(k.vaporiser_duty_kw),
        "cooling_duty_kW": jf(k.cooling_duty_kw.unwrap_or(f64::NAN).abs()), "pump_power_kW": jf(or0(k.pump_power_kw)),
        "warnings": a["warnings"].clone(),
    }))
}

/// `fired_duty(h, furnace_efficiency, loss_fraction)`.
pub fn fired_duty(h: &Value, furnace_efficiency: f64, loss_fraction: f64) -> Value {
    let pre = match h["preheat_duty_kW"].as_f64() {
        Some(v) if v != 0.0 => v,
        _ => 0.0,
    };
    let loss = loss_fraction * (num(h, "reactor_duty_kW") + pre);
    let q = num(h, "external_heat_import_kW") + loss;
    let fuel_kmol_h = q / (LHV_KJ_PER_MOL[1].1 * furnace_efficiency) * 3600.0 / 1000.0;
    json!({"thermal_loss_kW": jf(loss), "fired_process_duty_kW": jf(q), "furnace_efficiency": jf(furnace_efficiency),
           "furnace_fuel_LHV_kW": jf(q / furnace_efficiency),
           "supplementary_nh3_kg_h": jf(fuel_kmol_h * molar_mass(Species::NH3)),
           "supplementary_fuel_needed": q > 1e-6})
}

/// `summary_for_economics(res, fd, h)`.
pub fn summary_for_economics(
    res: &SimulationResult,
    fd: &Value,
    h: &Value,
) -> Result<Summary, EngineError> {
    let k = &res.kpis;
    let feed = res
        .stream("FEED")
        .ok_or_else(|| EngineError::Domain("KeyError: 'FEED'".into()))?;
    let nh3 = feed
        .component_mole_flow_kmol_h
        .iter()
        .find(|x| x.0 == "NH3")
        .map(|x| x.1)
        .ok_or_else(|| EngineError::Domain("KeyError: 'NH3'".into()))?;
    Ok(Summary {
        case_id: Some(res.case_id.clone()),
        source: Some(res.source.clone()),
        heat_integration: Value::Bool(res.inputs.heat_integration),
        h2_kg_h: k.h2_product_kg_h.unwrap_or(f64::NAN),
        nh3_feed_kmol_h: nh3,
        heat_deficit_kw: num(fd, "fired_process_duty_kW"),
        cooling_kw: num(h, "cooling_duty_kW"),
        pump_kw: num(h, "pump_power_kW"),
        h2_cracked_kmol_h: k.h2_in_cracked_gas_kmol_h,
        psa_recovery: Some(res.inputs.psa_h2_recovery),
        tailgas_lhv_kw: k.tailgas_lhv_kw,
        tailgas_heat_kw: k.tailgas_combustion_heat_kw,
    })
}

/// `econ(summary, W_kg, price, scenario, lifetime, furnace_efficiency, overrides)`.
#[allow(clippy::too_many_arguments)]
pub fn econ(
    ctx: &Ctx,
    s: &Summary,
    w_kg: f64,
    price: f64,
    scenario: &Value,
    lifetime: f64,
    furnace_efficiency: f64,
    overrides: Option<&Overrides>,
) -> Result<Value, EngineError> {
    let mut o = Map::new();
    o.insert("catalyst_mass_kg".into(), jf(py_max(w_kg, 0.0)));
    o.insert("catalyst_price_USD_per_kg".into(), jf(price));
    o.insert("catalyst_lifetime_yr".into(), jf(lifetime));
    o.insert("fuel_efficiency".into(), jf(furnace_efficiency));
    o.insert("heat_fuel".into(), Value::String("ammonia".into()));
    if let Some(ov) = overrides {
        for (k, v) in ov {
            o.insert(k.clone(), v.clone());
        }
    }
    evaluate(ctx.econ, s, &Scenario::from_json(scenario)?, &o)
}

/// `carbon(summary, fuel_nh3_kg_h, routes)`.
pub fn carbon(s: &Summary, fuel_nh3_kg_h: f64) -> Result<Value, EngineError> {
    let h2 = s.h2_kg_h;
    let nh3 = (s.nh3_feed_kmol_h * molar_mass(Species::NH3) + fuel_nh3_kg_h) / h2;
    let a = Activity::new(
        "cat",
        "catalyst design",
        "H2",
        "1 kg H2",
        nh3,
        s.pump_kw / h2,
        0.0,
    );
    let mut out = Map::new();
    out.insert("kg_nh3_total_per_kg_h2".into(), jf(nh3));
    out.insert("distance_km".into(), jf(LCA_DISTANCE_KM));
    out.insert("n2o".into(), Value::String("not quantified (0)".into()));
    for r in LCA_ROUTES {
        let ef = crate::lca::route_spec(r)?.ef;
        out.insert(
            format!("{r}_kgCO2e_per_kgH2"),
            jf(carbon_intensity(&a, ef, LCA_DISTANCE_KM, None, None, None)[4]),
        );
    }
    Ok(Value::Object(out))
}

/// Options of [`design_point`] (Python keyword arguments).
#[derive(Debug, Clone)]
pub struct DesignOpts {
    pub heat_integration: bool,
    pub w_kg: Option<f64>,
    pub dt_min_k: f64,
    pub scenario: Value,
    pub price: Option<f64>,
    pub lifetime: f64,
    pub furnace_efficiency: f64,
    pub psa_recovery: f64,
    pub econ_overrides: Option<Overrides>,
}

impl Default for DesignOpts {
    fn default() -> Self {
        DesignOpts {
            heat_integration: true,
            w_kg: None,
            dt_min_k: 20.0,
            scenario: Value::String("grey".into()),
            price: None,
            lifetime: CATALYST_LIFETIME_YR,
            furnace_efficiency: FURNACE_EFFICIENCY,
            psa_recovery: 0.85,
            econ_overrides: None,
        }
    }
}

/// `design_point(cid, T_C, P_bar, X, ...)`; `result` = an existing (e.g. Aspen) flowsheet.
pub fn design_point(
    ctx: &Ctx,
    cid: &str,
    t_c: f64,
    p_bar: f64,
    x: f64,
    o: &DesignOpts,
    result: Option<&SimulationResult>,
) -> Result<Value, EngineError> {
    let c = catalyst(cid)?;
    let w = match o.w_kg {
        Some(w) => w,
        None => required_mass_kg(ctx, cid, t_c, p_bar, x)?,
    };
    let owned;
    let res = match result {
        Some(r) => r,
        None => {
            owned = kinetic_flowsheet(ctx, t_c, p_bar, x, o.heat_integration, o.psa_recovery)?;
            &owned
        }
    };
    let h = heat_accounting(ctx, res, o.dt_min_k)?;
    let fd = fired_duty(&h, o.furnace_efficiency, THERMAL_LOSS_FRACTION);
    let s = summary_for_economics(res, &fd, &h)?;
    let p = o.price.unwrap_or(c.price);
    let e = econ(
        ctx,
        &s,
        w,
        p,
        &o.scenario,
        o.lifetime,
        o.furnace_efficiency,
        o.econ_overrides.as_ref(),
    )?;
    let rho = bed_density(&c);
    let mut out = Map::new();
    let put = |m: &mut Map<String, Value>, k: &str, v: Value| {
        m.insert(k.to_string(), v);
    };
    put(&mut out, "catalyst_id", json!(cid));
    put(&mut out, "catalyst", json!(c.label));
    put(&mut out, "family", json!(c.family));
    put(&mut out, "T_C", jf(t_c));
    put(&mut out, "P_bar", jf(p_bar));
    put(&mut out, "X_target", jf(x));
    put(&mut out, "X_flowsheet", jo(res.kpis.nh3_conversion));
    put(&mut out, "X_eq", jf(eq_conversion(t_c, p_bar)?));
    put(
        &mut out,
        "heat_integration",
        json!(res.inputs.heat_integration),
    );
    put(&mut out, "flowsheet_source", json!(res.source));
    put(&mut out, "W_kg", jf(w));
    put(&mut out, "bed_volume_m3", jf(w / rho));
    put(&mut out, "bed_density_kg_m3", jf(rho));
    put(
        &mut out,
        "GHSV_NH3_STP_h-1",
        if w > 0.0 {
            jf(FEED_NH3_KMOL_H * 22.414 / (w / rho))
        } else {
            Value::Null
        },
    );
    put(&mut out, "h2_product_kg_h", jf(s.h2_kg_h));
    if let Some(m) = h.as_object() {
        for (k, v) in m {
            out.insert(format!("heat_{k}"), v.clone());
        }
    }
    if let Some(m) = fd.as_object() {
        for (k, v) in m {
            out.insert(k.clone(), v.clone());
        }
    }
    put(&mut out, "catalyst_price_USD_per_kg", jf(p));
    put(&mut out, "catalyst_lifetime_yr", jf(o.lifetime));
    for k in [
        "lcoh_USD_per_kg",
        "rec_USD_per_kg",
        "lcoh_SGD_per_kg",
        "rec_SGD_per_kg",
        "fx_SGD_per_USD",
        "breakdown_USD_per_kg",
        "kg_nh3_fuel_per_kg_h2",
        "annual_h2_kg",
        "nh3_price_USD_per_t",
    ] {
        out.insert(k.to_string(), e[k].clone());
    }
    put(
        &mut out,
        "carbon",
        carbon(&s, num(&fd, "supplementary_nh3_kg_h"))?,
    );
    Ok(Value::Object(out))
}

/// Options of [`lcoh_curve`].
#[derive(Debug, Clone)]
pub struct CurveOpts {
    pub p_bar: f64,
    pub x: f64,
    pub hi: bool,
    pub dt: f64,
    pub psa: f64,
    pub feff: f64,
    pub scenario: Value,
    pub price: Option<f64>,
    pub lifetime: f64,
    pub kinetic_factor: f64,
    pub capex_volume_scaling: bool,
    pub econ_overrides: Option<Overrides>,
}

impl Default for CurveOpts {
    fn default() -> Self {
        CurveOpts {
            p_bar: 20.0,
            x: 0.95,
            hi: true,
            dt: 20.0,
            psa: 0.85,
            feff: FURNACE_EFFICIENCY,
            scenario: Value::String("grey".into()),
            price: None,
            lifetime: CATALYST_LIFETIME_YR,
            kinetic_factor: 1.0,
            capex_volume_scaling: false,
            econ_overrides: None,
        }
    }
}

/// `lcoh_curve(cid, T_grid, ...)`: LCOH(T) for one catalyst (rows as the Python dicts).
pub fn lcoh_curve(
    ctx: &Ctx,
    cid: &str,
    t_grid: &[f64],
    o: &CurveOpts,
) -> Result<Vec<Value>, EngineError> {
    let c = catalyst(cid)?;
    let p = o.price.unwrap_or(c.price);
    let rho = bed_density(&c);
    let mut out = Vec::new();
    for &t in t_grid {
        if eq_conversion(t, o.p_bar)? <= o.x + 1e-4 {
            continue;
        }
        let w0 = required_mass_kg(ctx, cid, t, o.p_bar, o.x)?;
        if !w0.is_finite() {
            continue;
        }
        let w = w0 / o.kinetic_factor;
        let res = kinetic_flowsheet(ctx, t, o.p_bar, o.x, o.hi, o.psa)?;
        let h = heat_accounting(ctx, &res, o.dt)?;
        let fd = fired_duty(&h, o.feff, THERMAL_LOSS_FRACTION);
        let s = summary_for_economics(&res, &fd, &h)?;
        let e0 = econ(
            ctx,
            &s,
            0.0,
            p,
            &o.scenario,
            o.lifetime,
            o.feff,
            o.econ_overrides.as_ref(),
        )?;
        let annual = num(&e0, "annual_h2_kg");
        let cat = w * p / o.lifetime / annual;
        let mut cap_extra = 0.0;
        if o.capex_volume_scaling {
            let tci_cr = e0["capex"]["tci_by_equipment_USD"]["cracker"]
                .as_f64()
                .unwrap_or(f64::NAN);
            let v_ref = 248.0 / rho;
            cap_extra = tci_cr * ((w / rho / v_ref).powf(0.8) - 1.0) * num(&e0, "crf") / annual;
        }
        let l0 = num(&e0, "lcoh_USD_per_kg");
        out.push(json!({
            "T_C": jf(t), "W_kg": jf(w), "bed_volume_m3": jf(w / rho), "lcoh_USD_per_kg": jf(l0 + cat + cap_extra),
            "rec_USD_per_kg": jf(num(&e0, "rec_USD_per_kg") + cat + cap_extra), "catalyst_USD_per_kg": jf(cat),
            "lcoh_SGD_per_kg": jf((l0 + cat + cap_extra) * num(&e0, "fx_SGD_per_USD")),
            "capex_volume_extra_USD_per_kg": jf(cap_extra),
            "heat_fuel_USD_per_kg": e0["breakdown_USD_per_kg"]["heat_fuel"],
            "external_heat_import_kW": h["external_heat_import_kW"],
            "fired_process_duty_kW": fd["fired_process_duty_kW"],
            "supplementary_nh3_kg_h": fd["supplementary_nh3_kg_h"],
            "h2_product_kg_h": jf(s.h2_kg_h),
        }));
    }
    Ok(out)
}

/// `optimum(curve)`: the row of minimum LCOH (first on ties, as `numpy.argmin`) with
/// `at_grid_bound` and `grid_index`.
pub fn optimum(curve: &[Value]) -> Option<Value> {
    if curve.is_empty() {
        return None;
    }
    let mut i = 0;
    for (j, r) in curve.iter().enumerate() {
        let (a, b) = (num(r, "lcoh_USD_per_kg"), num(&curve[i], "lcoh_USD_per_kg"));
        if a < b || (a.is_nan() && !b.is_nan()) {
            i = j;
        }
    }
    let mut best = curve[i].clone();
    best["at_grid_bound"] = Value::Bool(i == 0 || i == curve.len() - 1);
    best["grid_index"] = Value::from(i as u64);
    Some(best)
}

/// The FEED NH3 of a result (kmol/h).
pub fn feed_nh3(res: &SimulationResult) -> f64 {
    res.stream("FEED")
        .map(|s| get_or(&s.component_mole_flow_kmol_h, "NH3", f64::NAN))
        .unwrap_or(f64::NAN)
}
