//! Independent mirror of the AmCraX Aspen Plus flowsheet (port of Python
//! `process_model/flowsheet.py`, `run_python_case`).
//!
//! `FEED -> PUMP -S1-> VAPORIZR -S2-> FEHE(cold) -S3-> HEATER -S4-> CRACKER -S5-> FEHE(hot) -S6->
//! COOLER -S7-> PSA -> H2PROD / TAILGAS -> BURNER (+AIR) -FLUE-> FLUEHX -> STACK`; without heat
//! integration S2 -> HEATER and S5 -> COOLER. The block models, the property bases (including
//! the FEHE cold side on NASA-7 + reference-EOS NH3 residual and the hot side on NASA-7 + PR in
//! both eos modes, and the Raoult dew point + 10 K superheat of the vaporiser) are those of the
//! Python reference, statement by statement; the known Python-versus-Aspen FEHE duty offset
//! (vaporiser outlet state and residual-enthalpy basis, `results/research/heat_exchanger/
//! fehe_duty_diagnosis.json`) is therefore reproduced as Python has it.

use super::kpis::{compute_balances, compute_kpis};
use super::properties::{FeedPhase, Props, gas_enthalpy_kw, solve_t_for_enthalpy};
use super::result::{
    BlockResult, CaseInputs, Detail, RunStatus, SCHEMA_VERSION, SimulationResult, StreamResult,
    molar_mass,
};
use crate::error::EngineError;
use crate::props::FluidProps;
use crate::pyops::{linspace, py_max, py_min, py_repr, py_sum};
use crate::species::{Comp, Species};
use crate::thermo::equilibrium::{Eos, solve_equilibrium};
use crate::thermo::peng_robinson::{Alpha, Kij};
use amcrax_numerics::interp::Pchip;
use serde_json::Value;
use std::sync::OnceLock;

pub const FEED_PRESSURE_BAR: f64 = 1.013;
pub const VAPORIZER_SUPERHEAT_K: f64 = 10.0;
/// ASSUMPTION (typical centrifugal pump; identical to the Aspen input).
pub const PUMP_EFFICIENCY: f64 = 0.75;
pub const AIR_T_C: f64 = 25.0;
pub const AIR_O2: f64 = 0.21;
pub const AIR_N2: f64 = 0.79;
pub const MIN_FLOWSHEET_PRESSURE_BAR: f64 = 3.0;
pub const FEHE_PROFILE_POINTS: usize = 41;
pub const HOT_SIDE_GRID_POINTS: usize = 61;
pub const K0: f64 = 273.15;

/// `config/flowsheet.json` (embedded; read by Python at run time).
pub const FLOWSHEET_JSON: &str = include_str!("../../../../../config/flowsheet.json");

type Profile = Vec<(String, (bool, f64))>;

/// `pressure_profile()`: key -> (absolute?, value in bar).
pub fn pressure_profile() -> Result<&'static Profile, EngineError> {
    static P: OnceLock<Result<Profile, EngineError>> = OnceLock::new();
    P.get_or_init(|| {
        let cfg: Value = serde_json::from_str(FLOWSHEET_JSON)
            .map_err(|e| EngineError::data("config/flowsheet.json", e.to_string()))?;
        let m = cfg["pressure_profile_bar_relative_to_reactor"]
            .as_object()
            .ok_or_else(|| {
                EngineError::data("config/flowsheet.json", "pressure profile missing")
            })?;
        let mut out = Vec::new();
        for (k, v) in m {
            if k == "comment" {
                continue;
            }
            let s = match v {
                Value::String(s) => s.trim().to_string(),
                other => other.to_string(),
            };
            let parse = |t: &str| {
                t.parse::<f64>().map_err(|_| {
                    EngineError::data("config/flowsheet.json", format!("bad pressure {t}"))
                })
            };
            if s.contains("absolute") {
                let first = s.split_whitespace().next().unwrap_or("");
                out.push((k.clone(), (true, parse(first)?)));
            } else {
                out.push((k.clone(), (false, parse(&s)?)));
            }
        }
        Ok(out)
    })
    .as_ref()
    .map_err(Clone::clone)
}

fn p_of(key: &str, p_reactor: f64) -> Result<f64, EngineError> {
    let (abs, v) = pressure_profile()?
        .iter()
        .find(|x| x.0 == key)
        .map(|x| x.1)
        .ok_or_else(|| EngineError::data("config/flowsheet.json", format!("no pressure {key}")))?;
    Ok(if abs { v } else { p_reactor + v })
}

/// `_clean(n)`: all components in `COMPONENTS` order, negative flows set to 0.
fn clean(n: &[(Species, f64)]) -> Comp {
    let mut c = [0.0; 5];
    for s in Species::ALL {
        let v = n.iter().find(|x| x.0 == s).map(|x| x.1).unwrap_or(0.0);
        c[s.index()] = py_max(v, 0.0);
    }
    c
}

fn comp_list(c: &Comp) -> Vec<(Species, f64)> {
    Species::ALL.iter().map(|s| (*s, c[s.index()])).collect()
}

#[allow(clippy::too_many_arguments)]
fn mk_stream(
    sid: &str,
    name: &str,
    src: Option<&str>,
    dst: Option<&str>,
    n: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    h_kw: f64,
    phase: &str,
    vf: f64,
) -> (String, StreamResult) {
    let n = clean(n);
    let tot = py_sum(n);
    let mass: Vec<f64> = Species::ALL
        .iter()
        .map(|s| n[s.index()] * molar_mass(*s))
        .collect();
    let mtot = py_sum(mass.iter().copied());
    let names = Species::ALL.map(|s| s.name().to_string());
    (
        sid.to_string(),
        StreamResult {
            id: sid.into(),
            name: name.into(),
            source_block: src.map(str::to_string),
            dest_block: dst.map(str::to_string),
            phase: Some(phase.into()),
            temperature_c: Some(t_k - K0),
            pressure_bar: Some(p_bar),
            vapor_fraction: Some(vf),
            mole_flow_kmol_h: Some(tot),
            mass_flow_kg_h: Some(mtot),
            enthalpy_flow_kw: Some(h_kw),
            mole_frac: names
                .iter()
                .zip(n.iter())
                .map(|(k, v)| (k.clone(), if tot > 0.0 { v / tot } else { 0.0 }))
                .collect(),
            mass_frac: names
                .iter()
                .zip(mass.iter())
                .map(|(k, v)| (k.clone(), if mtot > 0.0 { v / mtot } else { 0.0 }))
                .collect(),
            component_mole_flow_kmol_h: names.iter().cloned().zip(n.iter().copied()).collect(),
        },
    )
}

fn num(k: &str, v: f64) -> (String, Detail) {
    (k.to_string(), Detail::Num(v))
}

fn txt(k: &str, v: &str) -> (String, Detail) {
    (k.to_string(), Detail::Str(v.to_string()))
}

#[allow(clippy::too_many_arguments)]
fn mk_block(
    id: &str,
    name: &str,
    block_type: &str,
    duty: f64,
    power: Option<f64>,
    t_out_c: f64,
    p_out: f64,
    details: Vec<(String, Detail)>,
) -> (String, BlockResult) {
    (
        id.to_string(),
        BlockResult {
            id: id.into(),
            name: name.into(),
            block_type: block_type.into(),
            duty_kw: Some(duty),
            power_kw: power,
            outlet_temperature_c: Some(t_out_c),
            outlet_pressure_bar: Some(p_out),
            details,
        },
    )
}

/// `validate_inputs`.
pub fn validate_inputs(inputs: &CaseInputs) -> Result<(), EngineError> {
    if inputs.reactor_pressure_bar < MIN_FLOWSHEET_PRESSURE_BAR {
        return Err(EngineError::Spec(format!(
            "reactor_pressure_bar={} below {} bar: the fixed pressure profile (H2 product at P-1.0 bar, tail gas at 1.3 bar) is not physical",
            py_repr(inputs.reactor_pressure_bar),
            py_repr(MIN_FLOWSHEET_PRESSURE_BAR)
        )));
    }
    if inputs.stack_temperature_c <= -100.0 {
        return Err(EngineError::Spec("stack temperature unphysical".into()));
    }
    Ok(())
}

/// Python name of an eos.
pub fn eos_name(eos: Eos) -> &'static str {
    match eos {
        Eos::Ideal => "ideal",
        Eos::Pr => "pr",
    }
}

/// Parse a Python eos name (case-insensitive).
pub fn eos_from_name(s: &str) -> Result<Eos, EngineError> {
    match s.to_lowercase().as_str() {
        "ideal" => Ok(Eos::Ideal),
        "pr" => Ok(Eos::Pr),
        _ => Err(EngineError::Domain("eos must be 'ideal' or 'pr'".into())),
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn start_clock() -> Option<std::time::Instant> {
    Some(std::time::Instant::now())
}

#[cfg(target_arch = "wasm32")]
fn start_clock() -> Option<()> {
    None
}

#[cfg(not(target_arch = "wasm32"))]
fn elapsed_s(t: Option<std::time::Instant>) -> Option<f64> {
    t.map(|t| t.elapsed().as_secs_f64())
}

#[cfg(target_arch = "wasm32")]
fn elapsed_s(_t: Option<()>) -> Option<f64> {
    None
}

/// `run_python_case(inputs, eos)` on the property back end `backend` (result source
/// `python_model`, exactly as the Python reference labels it; the engine is the Rust port).
pub fn run_python_case(
    inputs: &CaseInputs,
    eos: Eos,
    backend: &dyn FluidProps,
) -> Result<SimulationResult, EngineError> {
    run_case(inputs, eos, backend, Cracker::Equilibrium)
}

/// Cracker outlet specification.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Cracker {
    /// Isothermal equilibrium (`run_python_case`).
    Equilibrium,
    /// Outlet conversion fixed at X (never above equilibrium): the replacement `solve` of Python
    /// `research/catalyst_comparison.kinetic_flowsheet` (which patches `solve_equilibrium`).
    FixedConversion(f64),
}

/// `run_python_case` with an explicit cracker specification.
pub fn run_case(
    inputs: &CaseInputs,
    eos: Eos,
    backend: &dyn FluidProps,
    cracker: Cracker,
) -> Result<SimulationResult, EngineError> {
    let t_start = start_clock();
    validate_inputs(inputs)?;
    let pp = Props::new(backend);
    let p = inputs.reactor_pressure_bar;
    let t_r = inputs.reactor_temperature_c + K0;
    let hi = inputs.heat_integration;
    let mut msgs: Vec<String> = Vec::new();
    let mut warn = false;
    let mut streams: Vec<(String, StreamResult)> = Vec::new();
    let mut blocks: Vec<(String, BlockResult)> = Vec::new();
    let gas_h = |n: &[(Species, f64)], t: f64, pb: f64| gas_enthalpy_kw(n, t, pb, eos);

    // ------------------------------------------------------------ FEED
    let x_w = inputs.feed_h2o_mole_frac;
    let f_tot = inputs.feed_total_kmol_h;
    let n_feed = [
        (Species::NH3, f_tot * (1.0 - x_w)),
        (Species::H2O, f_tot * x_w),
    ];
    let t_feed = pp.bubble_point_k(FEED_PRESSURE_BAR, 1.0 - x_w)?;
    let h_feed =
        pp.feed_section_enthalpy_kw(&n_feed, t_feed, FEED_PRESSURE_BAR, FeedPhase::Liquid)?;
    streams.push(mk_stream(
        "FEED",
        "Liquid ammonia feed",
        None,
        Some("PUMP"),
        &n_feed,
        t_feed,
        FEED_PRESSURE_BAR,
        h_feed,
        "liquid",
        0.0,
    ));

    // ------------------------------------------------------------ PUMP
    let p1 = p_of("PUMP_discharge", p)?;
    let v_l = pp.nh3_liquid_molar_volume_m3_mol(t_feed, FEED_PRESSURE_BAR)?;
    let n_tot_mol_s = f_tot * 1000.0 / 3600.0;
    let fluid_power_kw = n_tot_mol_s * v_l * (p1 - FEED_PRESSURE_BAR) * 1e5 / 1000.0;
    let w_pump = fluid_power_kw / PUMP_EFFICIENCY;
    let h1 = h_feed + w_pump;
    let t1 = solve_t_for_enthalpy(
        |t| pp.feed_section_enthalpy_kw(&n_feed, t, p1, FeedPhase::Liquid),
        h1,
        t_feed - 5.0,
        t_feed + 20.0,
    )?;
    streams.push(mk_stream(
        "S1",
        "Pressurised liquid ammonia",
        Some("PUMP"),
        Some("VAPORIZR"),
        &n_feed,
        t1,
        p1,
        h1,
        "liquid",
        0.0,
    ));
    blocks.push(mk_block(
        "PUMP",
        "Ammonia feed pump",
        "Pump",
        0.0,
        Some(w_pump),
        t1 - K0,
        p1,
        vec![
            num("efficiency", PUMP_EFFICIENCY),
            num("fluid_power_kW", fluid_power_kw),
            txt("efficiency_source", "assumption"),
        ],
    ));

    // ------------------------------------------------------------ VAPORIZR
    let p2 = p_of("VAPORIZR_out", p)?;
    let (y_n, y_w) = (n_feed[0].1 / f_tot, n_feed[1].1 / f_tot);
    let t_dew = pp.dew_point_k(p2, y_n, y_w)?;
    let t2 = t_dew + VAPORIZER_SUPERHEAT_K;
    let h2 = pp.feed_section_enthalpy_kw(&n_feed, t2, p2, FeedPhase::Gas)?;
    let q_vap = h2 - h1;
    streams.push(mk_stream(
        "S2",
        "Ammonia vapour",
        Some("VAPORIZR"),
        Some(if hi { "FEHE" } else { "HEATER" }),
        &n_feed,
        t2,
        p2,
        h2,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "VAPORIZR",
        "Ammonia vaporiser",
        "Heater",
        q_vap,
        None,
        t2 - K0,
        p2,
        vec![
            num("dew_point_C", t_dew - K0),
            num("superheat_K", VAPORIZER_SUPERHEAT_K),
            txt("vle_model", "Raoult (ideal liquid), CoolProp Psat"),
        ],
    ));

    // ------------------------------------------------------------ HEATER / CRACKER
    let p4 = p_of("HEATER_out", p)?;
    let h4 = gas_h(&n_feed, t_r, p4)?;
    let mut eq = solve_equilibrium(t_r, p, &clean(&n_feed), eos, &Kij::zero(), Alpha::Standard)?;
    if let Cracker::FixedConversion(x) = cracker {
        if x > eq.conversion + 1e-9 {
            return Err(EngineError::Domain(format!(
                "X = {} above equilibrium {:.5} at {:.1} degC, {} bar",
                py_repr(x),
                eq.conversion,
                t_r - K0,
                py_repr(p)
            )));
        }
        // out = dict(n): NH3, H2O, then N2 and H2 appended (the solver's dict n is n_feed)
        let n0 = n_feed[0].1;
        let ext = x * n0 / 2.0;
        eq.n_out = vec![
            (Species::NH3, n0 * (1.0 - x)),
            (Species::H2O, n_feed[1].1),
            (Species::N2, 0.0 + ext),
            (Species::H2, 0.0 + 3.0 * ext),
        ];
        eq.conversion = x;
        eq.extent = ext;
    }
    let n5c = clean(&eq.n_out);
    let n5 = comp_list(&n5c);
    let h5 = gas_h(&n5, t_r, p)?;
    let q_crk = h5 - h4;

    // ------------------------------------------------------------ FEHE
    let (h_heater_in, h6) = if hi {
        let p3 = p_of("FEHE_cold_out", p)?;
        let p6v = p_of("FEHE_hot_out", p)?;
        let t3 = t_r - inputs.fehe_hot_end_approach_k;
        if t3 <= t2 {
            return Err(EngineError::Spec(format!(
                "FEHE infeasible: cold outlet {:.1} degC not above cold inlet {:.1} degC; reduce fehe_hot_end_approach_K or raise reactor_temperature_C",
                t3 - K0,
                t2 - K0
            )));
        }
        let cold_h = |t: f64| pp.feed_gas_enthalpy_kw(&n_feed, t, p3);
        let hot_h_at = |t: f64, pb: f64| gas_enthalpy_kw(&n5, t, pb, Eos::Pr);
        let h3 = cold_h(t3)?;
        let q = h3 - h2;
        let h6v = h5 - q;
        let h6r = hot_h_at(t_r, p)? - q;
        let t6v = solve_t_for_enthalpy(|t| hot_h_at(t, p6v), h6r, 250.0, t_r + 1.0)?;
        let s6_offset = h6v - gas_h(&n5, t6v, p6v)?;
        let delta_c = h2 - cold_h(t2)?;
        let tg = linspace(t6v, t_r + 2.0, HOT_SIDE_GRID_POINTS);
        let mut hg = Vec::with_capacity(tg.len());
        for &t in &tg {
            hg.push(hot_h_at(t, p6v)?);
        }
        let th_of_h = Pchip::new(&hg, &tg).map_err(|e| EngineError::Domain(e.to_string()))?;
        let (hg0, hg1) = (hg[0], hg[hg.len() - 1]);
        let mut dt_min = f64::INFINITY;
        let np = FEHE_PROFILE_POINTS;
        for i in 0..np {
            let f = i as f64 / (np - 1) as f64;
            let hc = h2 + f * q;
            let hh = h6r + f * q;
            let tc = if i == 0 {
                t2
            } else if i == np - 1 {
                t3
            } else {
                solve_t_for_enthalpy(
                    |t| Ok(cold_h(t)? + (1.0 - f) * delta_c),
                    hc,
                    t2 - 5.0,
                    t3 + 5.0,
                )?
            };
            let th = if i == 0 {
                t6v
            } else if i == np - 1 {
                t_r
            } else {
                let v = if (hg0..=hg1).contains(&hh) {
                    th_of_h.eval(hh)
                } else {
                    f64::NAN
                };
                if v.is_finite() {
                    v
                } else {
                    solve_t_for_enthalpy(|t| hot_h_at(t, p6v), hh, t6v - 5.0, t_r + 5.0)?
                }
            };
            dt_min = py_min(dt_min, th - tc);
        }
        if dt_min <= 0.0 {
            return Err(EngineError::Spec(format!(
                "FEHE temperature cross (minimum hot-cold difference {:.2} K) with approach {} K: specification infeasible",
                dt_min,
                py_repr(inputs.fehe_hot_end_approach_k)
            )));
        }
        streams.push(mk_stream(
            "S3",
            "Preheated ammonia",
            Some("FEHE"),
            Some("HEATER"),
            &n_feed,
            t3,
            p3,
            h3,
            "vapor",
            1.0,
        ));
        streams.push(mk_stream(
            "S6",
            "Partly cooled cracked gas",
            Some("FEHE"),
            Some("COOLER"),
            &n5,
            t6v,
            p6v,
            h6v,
            "vapor",
            1.0,
        ));
        blocks.push(mk_block(
            "FEHE",
            "Feed/effluent heat exchanger",
            "HeatX",
            q,
            None,
            t3 - K0,
            p3,
            vec![
                num("cold_outlet_C", t3 - K0),
                num("hot_outlet_C", t6v - K0),
                num("hot_end_approach_K", inputs.fehe_hot_end_approach_k),
                num("cold_end_approach_K", t6v - t2),
                num("min_internal_dT_K", dt_min),
                txt(
                    "cold_side_basis",
                    "NASA-7 ideal gas + reference-EOS NH3 residual enthalpy (both eos modes)",
                ),
                txt(
                    "hot_side_basis",
                    "NASA-7 ideal gas + PR residual (both eos modes)",
                ),
                num("s6_enthalpy_minus_eos_basis_at_T6_kW", s6_offset),
            ],
        ));
        (h3, h6v)
    } else {
        // Python: Q_fehe = 0, H_heater_in = H2, (T6, H6, P6) = (T_R, H5, P)
        (h2, h5)
    };

    let q_heat = h4 - h_heater_in;
    let s4_offset = h4 - pp.feed_gas_enthalpy_kw(&n_feed, t_r, p4)?;
    streams.push(mk_stream(
        "S4",
        "Reactor feed",
        Some("HEATER"),
        Some("CRACKER"),
        &n_feed,
        t_r,
        p4,
        h4,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "HEATER",
        "Fired trim preheater",
        "Heater",
        q_heat,
        None,
        t_r - K0,
        p4,
        vec![
            num("s4_basis_minus_reference_real_gas_kW", s4_offset),
            txt(
                "basis_note",
                &format!(
                    "inlet on the real-gas reference basis, outlet on the eos={} gas basis; the duty includes the basis difference at S4 (s4_basis_minus_reference_real_gas_kW)",
                    eos_name(eos)
                ),
            ),
        ],
    ));
    streams.push(mk_stream(
        "S5",
        "Hot cracked gas",
        Some("CRACKER"),
        Some(if hi { "FEHE" } else { "COOLER" }),
        &n5,
        t_r,
        p,
        h5,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "CRACKER",
        "Ammonia cracking reactor",
        "RGibbs",
        q_crk,
        None,
        t_r - K0,
        p,
        vec![
            num("conversion", eq.conversion),
            num("K_eq", eq.k_eq),
            txt("eos", eos_name(eos)),
            num("extent_kmol_h", eq.extent),
        ],
    ));

    // ------------------------------------------------------------ COOLER
    let p7 = p_of("COOLER_out", p)?;
    let t7 = inputs.psa_feed_temperature_c + K0;
    let h7 = gas_h(&n5, t7, p7)?;
    let q_cool = h7 - h6;
    let tot5 = py_sum(n5c);
    let y5: Vec<(Species, f64)> = n5.iter().map(|(s, v)| (*s, v / tot5)).collect();
    let dew_sum = pp.raoult_dew_sum(t7, p7, &y5)?;
    if dew_sum >= 1.0 {
        warn = true;
        msgs.push(format!(
            "COOLER outlet below the (Raoult) dew point of NH3/H2O (sum={dew_sum:.3}); condensation is not modelled - stream treated as vapour"
        ));
    }
    streams.push(mk_stream(
        "S7",
        "PSA feed",
        Some("COOLER"),
        Some("PSA"),
        &n5,
        t7,
        p7,
        h7,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "COOLER",
        "Cracked-gas cooler",
        "Heater",
        q_cool,
        None,
        t7 - K0,
        p7,
        vec![num("raoult_dew_sum", dew_sum)],
    ));

    // ------------------------------------------------------------ PSA
    let frac = [0.0, inputs.psa_h2_recovery, inputs.psa_n2_slip, 0.0, 0.0];
    let n_prod: Vec<(Species, f64)> = Species::ALL
        .iter()
        .map(|s| (*s, n5c[s.index()] * frac[s.index()]))
        .collect();
    let n_tail: Vec<(Species, f64)> = Species::ALL
        .iter()
        .map(|s| (*s, n5c[s.index()] - n_prod[s.index()].1))
        .collect();
    let p_prod = p_of("H2PROD", p)?;
    let p_tail = p_of("TAILGAS", p)?;
    let h_prod = gas_h(&n_prod, t7, p_prod)?;
    let h_tail = gas_h(&n_tail, t7, p_tail)?;
    let q_psa = h_prod + h_tail - h7;
    streams.push(mk_stream(
        "H2PROD",
        "Hydrogen product",
        Some("PSA"),
        None,
        &n_prod,
        t7,
        p_prod,
        h_prod,
        "vapor",
        1.0,
    ));
    streams.push(mk_stream(
        "TAILGAS",
        "PSA tail gas (N2-rich off-gas)",
        Some("PSA"),
        Some("BURNER"),
        &n_tail,
        t7,
        p_tail,
        h_tail,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "PSA",
        "Hydrogen purification (reduced-order PSA)",
        "Sep",
        q_psa,
        None,
        t7 - K0,
        p_prod,
        vec![
            num("h2_recovery", inputs.psa_h2_recovery),
            num("n2_slip", inputs.psa_n2_slip),
        ],
    ));

    // ------------------------------------------------------------ BURNER
    let tail = |s: Species| n_tail[s.index()].1;
    let lam = 1.0 + inputs.burner_excess_air;
    let o2_stoich = 0.5 * tail(Species::H2) + 0.75 * tail(Species::NH3);
    let n_air_tot = o2_stoich * lam / AIR_O2;
    let n_air = [
        (Species::N2, n_air_tot * AIR_N2),
        (Species::O2, n_air_tot * AIR_O2),
    ];
    let t_air = AIR_T_C + K0;
    let p_air = p_of("AIR", p)?;
    let h_air = gas_h(&n_air, t_air, p_air)?;
    streams.push(mk_stream(
        "AIR",
        "Combustion air",
        None,
        Some("BURNER"),
        &n_air,
        t_air,
        p_air,
        h_air,
        "vapor",
        1.0,
    ));
    let n_flue = [
        (Species::NH3, 0.0),
        (Species::H2, 0.0),
        (
            Species::N2,
            tail(Species::N2) + n_air[0].1 + 0.5 * tail(Species::NH3),
        ),
        (
            Species::H2O,
            tail(Species::H2O) + tail(Species::H2) + 1.5 * tail(Species::NH3),
        ),
        (Species::O2, tail(Species::O2) + n_air[1].1 - o2_stoich),
    ];
    let p_b = p_of("BURNER", p)?;
    let h_flue = h_tail + h_air;
    let t_ad = solve_t_for_enthalpy(|t| gas_h(&n_flue, t, p_b), h_flue, 250.0, 3500.0)?;
    streams.push(mk_stream(
        "FLUE",
        "Hot flue gas",
        Some("BURNER"),
        Some("FLUEHX"),
        &n_flue,
        t_ad,
        p_b,
        h_flue,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "BURNER",
        "Tail-gas burner",
        "RStoic",
        0.0,
        None,
        t_ad - K0,
        p_b,
        vec![
            num("adiabatic_flame_temperature_C", t_ad - K0),
            num("air_kmol_h", n_air_tot),
            num("excess_air", inputs.burner_excess_air),
        ],
    ));

    // ------------------------------------------------------------ FLUEHX
    let p_s = p_of("FLUEHX_out", p)?;
    let t_s = inputs.stack_temperature_c + K0;
    let h_stack = gas_h(&n_flue, t_s, p_s)?;
    let q_flue = h_stack - h_flue;
    let flue_heated = t_ad <= t_s;
    if flue_heated {
        warn = true;
        msgs.push(
            "adiabatic flame temperature below the stack temperature: FLUEHX heats the flue gas (no combustion credit; the positive FLUEHX duty counts as external heating, amcrax.kpis)"
                .into(),
        );
    }
    streams.push(mk_stream(
        "STACK",
        "Stack gas",
        Some("FLUEHX"),
        None,
        &n_flue,
        t_s,
        p_s,
        h_stack,
        "vapor",
        1.0,
    ));
    blocks.push(mk_block(
        "FLUEHX",
        "Flue-gas heat recovery",
        "Heater",
        q_flue,
        None,
        t_s - K0,
        p_s,
        vec![
            txt(
                "flame_below_stack_temperature",
                if flue_heated { "yes" } else { "no" },
            ),
            num("signed_heat_released_kW", -q_flue),
        ],
    ));

    // ------------------------------------------------------------ KPIs and balances
    // stream order of the Python dict: FEED, S1, S2, (S3, S6), S4, S5, S7, H2PROD, TAILGAS, AIR, FLUE, STACK
    let kpis = compute_kpis(&streams, &blocks);
    let balances = compute_balances(&streams, &blocks);
    let notes = vec![
        "Independent AmCraX Python process model (amcrax.process_model); NOT an Aspen Plus result.".to_string(),
        format!(
            "Cracker equilibrium eos={}; gas enthalpies NASA-7 ideal gas{} (formation-enthalpy reference, 298.15 K).",
            eos_name(eos),
            if eos == Eos::Pr { " + Peng-Robinson residual" } else { "" }
        ),
        "Liquid/vaporising NH3 from CoolProp (Gao et al. JPCRD 2020 EOS) anchored to NASA ideal gas at 298.15 K, 1 Pa."
            .to_string(),
        "Feed-section VLE by Raoult's law (ideal NH3-H2O liquid): ASSUMPTION; Aspen PENG-ROB dew point may differ."
            .to_string(),
        format!(
            "Pump efficiency {} (ASSUMPTION). PSA is a reduced-order component splitter.",
            py_repr(PUMP_EFFICIENCY)
        ),
    ];
    Ok(SimulationResult {
        schema_version: SCHEMA_VERSION.into(),
        case_id: inputs.case_id.clone(),
        source: "python_model".into(),
        model_file: Some("amcrax.process_model".into()),
        inputs: inputs.clone(),
        status: RunStatus {
            converged: true,
            has_errors: false,
            has_warnings: warn,
            messages: msgs,
            engine_time_s: elapsed_s(t_start),
        },
        streams,
        blocks,
        kpis,
        balances,
        notes,
    })
}
