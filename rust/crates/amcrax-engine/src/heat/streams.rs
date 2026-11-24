//! H-T streams of a `SimulationResult` (port of Python `heat_integration/streams.py`): the
//! ammonia feed S1 -> S4 (CoolProp liquid, saturation and vapour up to the switch temperature,
//! then NASA-7 + PR departure), the isothermal reaction heat, the cracked gas S5 -> S7 and the
//! flue gas FLUE -> STACK (NASA-7 + PR departure).

use super::pinch::{Curve, make_curve};
use crate::error::EngineError;
use crate::process::result::{SimulationResult, StreamResult};
use crate::props::Phase;
use crate::props::{Fluid, FluidProps, Imposed, Output, Query};
use crate::pyops::{fmt_f, linspace, py_max, py_min, py_sum};
use crate::species::Species;
use crate::thermo::equilibrium::{Eos, isothermal_reactor_duty_kw};
use crate::thermo::nasa7::species_enthalpy_kj_mol;
use crate::thermo::peng_robinson::{Alpha, Kij, enthalpy_departure_j_mol};

/// Discretisation points per curve segment.
pub const N_POINTS: usize = 40;

/// `ASSUMPTIONS`.
pub const ASSUMPTIONS: [&str; 5] = [
    "Feed water (0.2 mol%) contributes ideal-gas sensible heat only; its latent heat (<0.4 % of feed duty) is neglected.",
    "Gas-phase enthalpies: NASA-7 ideal gas (GRI-Mech 3.0 via amcrax.thermodynamics) + Peng-Robinson departure (kij = 0).",
    "Liquid/two-phase NH3: CoolProp reference EOS for pure ammonia at the vaporiser outlet pressure (pressure drop along the train neglected for the H-T curve).",
    "Isothermal duties (pure NH3 boiling, isothermal cracker) are represented as linear segments of 0.01 K width (numerical device).",
    "Each stream is taken at a single representative pressure (its inlet pressure); pressure drops in the exchangers are neglected for enthalpy.",
];

/// Species flows of a component map (names that are not model species are an error).
pub fn species_flows(m: &[(String, f64)]) -> Result<Vec<(Species, f64)>, EngineError> {
    m.iter()
        .map(|(k, v)| {
            Species::from_name(k)
                .map(|s| (s, *v))
                .ok_or_else(|| EngineError::Domain(format!("unknown species {k}")))
        })
        .collect()
}

/// `_T_K(stream)`.
pub fn t_k(s: Option<&StreamResult>) -> Option<f64> {
    s.and_then(|s| s.temperature_c).map(|t| t + 273.15)
}

/// `_flows(stream)`: positive component flows (or total flow x mole fractions).
pub fn flows(s: &StreamResult) -> Result<Vec<(Species, f64)>, EngineError> {
    let mut f: Vec<(String, f64)> = s
        .component_mole_flow_kmol_h
        .iter()
        .filter(|(_, v)| *v != 0.0 && *v > 0.0)
        .cloned()
        .collect();
    if f.is_empty()
        && let Some(tot) = s.mole_flow_kmol_h.filter(|x| *x != 0.0)
        && !s.mole_frac.is_empty()
    {
        f = s
            .mole_frac
            .iter()
            .filter(|(_, y)| *y > 0.0)
            .map(|(k, y)| (k.clone(), tot * y))
            .collect();
    }
    if f.is_empty() {
        return Err(EngineError::Domain(format!(
            "stream {}: no component flows",
            s.id
        )));
    }
    species_flows(&f)
}

/// `gas_enthalpy_kW(n, T, P)` of the heat-integration module: NASA-7 + PR departure (for P > 1.5 bar).
pub fn gas_enthalpy_kw(
    n: &[(Species, f64)],
    t_k: f64,
    p_bar: Option<f64>,
) -> Result<f64, EngineError> {
    let mut terms = Vec::with_capacity(n.len());
    for &(s, v) in n {
        terms.push(v * species_enthalpy_kj_mol(s, t_k)?);
    }
    let mut h = py_sum(terms) / 3.6;
    if let Some(p) = p_bar
        && p > 1.5
    {
        let tot = py_sum(n.iter().map(|x| x.1));
        let y: Vec<(Species, f64)> = n.iter().map(|(s, v)| (*s, v / tot)).collect();
        h += tot
            * enthalpy_departure_j_mol(&y, t_k, p, &Kij::zero(), Alpha::Standard, Phase::Vapour)?
            / 3600.0;
    }
    Ok(h)
}

/// `gas_curve(id, kind, n, T_a, T_b, P, name)`.
pub fn gas_curve(
    id: &str,
    kind: &str,
    n: &[(Species, f64)],
    t_a: f64,
    t_b: f64,
    p_bar: Option<f64>,
    name: &str,
) -> Result<Curve, EngineError> {
    let (lo, hi) = if t_b < t_a { (t_b, t_a) } else { (t_a, t_b) };
    let t = linspace(lo, hi, N_POINTS);
    let mut h = Vec::with_capacity(t.len());
    for &x in &t {
        h.push(gas_enthalpy_kw(n, x, p_bar)?);
    }
    let h0 = h[0];
    let hr: Vec<f64> = h.iter().map(|x| x - h0).collect();
    make_curve(id, kind, &t, &hr, name)
}

/// `feed_meta`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FeedMeta {
    pub t_sat_k: f64,
    pub t_switch_k: f64,
    pub latent_heat_kw: f64,
}

/// `feed_curve(n, T_in, T_out, P, T_switch)`.
pub fn feed_curve(
    props: &dyn FluidProps,
    n: &[(Species, f64)],
    t_in_k: f64,
    t_out_k: f64,
    p_bar: f64,
    t_switch_k: Option<f64>,
    name: &str,
) -> Result<(Curve, FeedMeta), EngineError> {
    let n_nh3 = n
        .iter()
        .find(|x| x.0 == Species::NH3)
        .map(|x| x.1)
        .unwrap_or(0.0);
    let others: Vec<(Species, f64)> = n.iter().copied().filter(|x| x.0 != Species::NH3).collect();
    let p_pa = p_bar * 1e5;
    let am = Fluid::Ammonia;
    let tsat = props.value(&Query::pq(am, Output::T, p_pa, 0.0))?;
    let mut t_sw = match t_switch_k {
        Some(t) if t > tsat => t,
        _ => tsat + 10.0,
    };
    t_sw = py_min(t_sw, t_out_k);
    let h_tp = |t: f64| props.value(&Query::tp(am, Output::Hmolar, t, p_pa, Imposed::None));
    let h_other = |t: f64| -> Result<f64, EngineError> {
        let mut v = Vec::with_capacity(others.len());
        for &(s, x) in &others {
            v.push(x * species_enthalpy_kj_mol(s, t)?);
        }
        Ok(py_sum(v) / 3.6)
    };
    let mut pts_t: Vec<f64> = Vec::new();
    let mut pts_h: Vec<f64> = Vec::new();
    if t_in_k < tsat && tsat < t_sw {
        let mut tl = linspace(t_in_k, tsat - 1e-3, N_POINTS / 2);
        let mut hl = Vec::with_capacity(tl.len());
        for &t in &tl[..tl.len() - 1] {
            hl.push(h_tp(t)?);
        }
        hl.push(props.value(&Query::pq(am, Output::Hmolar, p_pa, 0.0))?);
        let mut tv = linspace(tsat + 1e-3, t_sw, N_POINTS / 2);
        let mut hv = vec![props.value(&Query::pq(am, Output::Hmolar, p_pa, 1.0))?];
        for &t in &tv[1..] {
            hv.push(h_tp(t)?);
        }
        let nl = tl.len();
        tl[nl - 1] = tsat;
        tv[0] = tsat;
        for (t, h) in tl.iter().zip(hl.iter()).chain(tv.iter().zip(hv.iter())) {
            pts_t.push(*t);
            pts_h.push(n_nh3 * h / 3600.0 + h_other(*t)?);
        }
    } else {
        for t in linspace(t_in_k, t_sw, N_POINTS) {
            pts_t.push(t);
            pts_h.push(n_nh3 * h_tp(t)? / 3600.0 + h_other(t)?);
        }
    }
    if t_out_k > t_sw {
        let h_sw = pts_h[pts_h.len() - 1];
        let g0 = gas_enthalpy_kw(n, t_sw, Some(p_bar))?;
        for &t in &linspace(t_sw, t_out_k, N_POINTS)[1..] {
            pts_t.push(t);
            pts_h.push(h_sw + gas_enthalpy_kw(n, t, Some(p_bar))? - g0);
        }
    }
    let h0 = pts_h[0];
    let hr: Vec<f64> = pts_h.iter().map(|x| x - h0).collect();
    let c = make_curve("FEED", "cold", &pts_t, &hr, name)?;
    let latent = n_nh3
        * (props.value(&Query::pq(am, Output::Hmolar, p_pa, 1.0))?
            - props.value(&Query::pq(am, Output::Hmolar, p_pa, 0.0))?)
        / 3600.0;
    Ok((
        c,
        FeedMeta {
            t_sat_k: tsat,
            t_switch_k: t_sw,
            latent_heat_kw: latent,
        },
    ))
}

/// `water_dew_point_K(n, P)` (None below the triple-point pressure).
pub fn water_dew_point_k(
    props: &dyn FluidProps,
    n: &[(Species, f64)],
    p_bar: f64,
) -> Result<Option<f64>, EngineError> {
    let tot = py_sum(n.iter().map(|x| x.1));
    let h2o = n
        .iter()
        .find(|x| x.0 == Species::H2O)
        .map(|x| x.1)
        .unwrap_or(0.0);
    let p_w = if tot > 0.0 {
        h2o / tot * p_bar * 1e5
    } else {
        0.0
    };
    if p_w < 612.0 {
        return Ok(None);
    }
    Ok(Some(props.value(&Query::pq(
        Fluid::Water,
        Output::T,
        p_w,
        1.0,
    ))?))
}

/// `reaction_duty_kW(res)`: (duty, source label).
pub fn reaction_duty_kw(res: &SimulationResult) -> Result<(f64, String), EngineError> {
    if let Some(d) = res.block("CRACKER").and_then(|b| b.duty_kw) {
        return Ok((d, "CRACKER block duty (simulation result)".into()));
    }
    if let Some(d) = res.kpis.reactor_duty_kw {
        return Ok((d, "KPI reactor_duty_kW (simulation result)".into()));
    }
    let (s4, s5) = (
        res.stream("S4")
            .ok_or_else(|| EngineError::Domain("S4".into()))?,
        res.stream("S5")
            .ok_or_else(|| EngineError::Domain("S5".into()))?,
    );
    let q = isothermal_reactor_duty_kw(
        &flows(s4)?,
        t_k(Some(s4)).unwrap_or(f64::NAN),
        &flows(s5)?,
        t_k(Some(s5)).unwrap_or(f64::NAN),
        s4.pressure_bar,
        s5.pressure_bar,
        Eos::Pr,
    )?;
    Ok((
        q,
        "independent calculation (amcrax.thermodynamics, PR)".into(),
    ))
}

/// Output of [`extract_streams`].
#[derive(Debug, Clone)]
pub struct Extracted {
    pub feed: Curve,
    pub feed_meta: FeedMeta,
    pub reaction: Curve,
    pub reaction_source: String,
    pub cracked: Curve,
    pub flue: Option<Curve>,
    pub t_reactor_k: f64,
    pub warnings: Vec<String>,
    pub p_vap_bar: f64,
}

/// Python truthiness of an optional float.
fn truthy(x: Option<f64>) -> Option<f64> {
    x.filter(|v| *v != 0.0)
}

/// `extract_streams(res)`.
pub fn extract_streams(
    props: &dyn FluidProps,
    res: &SimulationResult,
) -> Result<Extracted, EngineError> {
    for sid in ["S1", "S4", "S5", "S7"] {
        if t_k(res.stream(sid)).is_none() {
            return Err(EngineError::Domain(format!(
                "SimulationResult lacks stream {sid} temperature"
            )));
        }
    }
    let mut warnings = Vec::new();
    let (s1, s4, s5, s7) = (
        res.stream("S1")
            .ok_or_else(|| EngineError::Domain("S1".into()))?,
        res.stream("S4")
            .ok_or_else(|| EngineError::Domain("S4".into()))?,
        res.stream("S5")
            .ok_or_else(|| EngineError::Domain("S5".into()))?,
        res.stream("S7")
            .ok_or_else(|| EngineError::Domain("S7".into()))?,
    );
    let s2 = res.stream("S2");
    let p_vap = truthy(s2.and_then(|s| s.pressure_bar))
        .or(truthy(s1.pressure_bar))
        .unwrap_or(res.inputs.reactor_pressure_bar + 0.8);
    let feed_n = flows(s1)?;
    let (mut feed, meta) = feed_curve(
        props,
        &feed_n,
        t_k(Some(s1)).unwrap_or(f64::NAN),
        t_k(Some(s4)).unwrap_or(f64::NAN),
        p_vap,
        t_k(s2),
        "Ammonia feed S1->S4",
    )?;
    feed.t_switch_k = Some(meta.t_switch_k);
    let t_r = t_k(Some(s5)).unwrap_or(f64::NAN);
    let (q_rxn, q_src) = reaction_duty_kw(res)?;
    let rxn = make_curve(
        "REACTION",
        "cold",
        &[t_r, t_r],
        &[0.0, py_max(q_rxn, 0.0)],
        &format!(
            "Cracking reaction heat (isothermal, {} degC)",
            fmt_f(t_r - 273.15, 0)
        ),
    )?;
    let cg_n = flows(s5)?;
    let p_cg = truthy(s5.pressure_bar).unwrap_or(res.inputs.reactor_pressure_bar);
    let t7 = t_k(Some(s7)).unwrap_or(f64::NAN);
    let cracked = gas_curve(
        "CRACKED",
        "hot",
        &cg_n,
        t_r,
        t7,
        Some(p_cg),
        "Cracked gas S5->S7",
    )?;
    let dp = water_dew_point_k(props, &cg_n, truthy(s7.pressure_bar).unwrap_or(p_cg))?;
    if let Some(d) = dp
        && d > t7
    {
        warnings.push(format!(
            "Cracked gas water dew point {} degC above PSA feed T: condensation neglected.",
            fmt_f(d - 273.15, 1)
        ));
    }
    let mut flue = None;
    match res.stream("FLUE") {
        Some(fl) if fl.temperature_c.is_some() => {
            let t_stack =
                truthy(t_k(res.stream("STACK"))).unwrap_or(res.inputs.stack_temperature_c + 273.15);
            let fnw = flows(fl)?;
            let t_fl = t_k(Some(fl)).unwrap_or(f64::NAN);
            if t_fl > t_stack {
                flue = Some(gas_curve(
                    "FLUE",
                    "hot",
                    &fnw,
                    t_fl,
                    t_stack,
                    fl.pressure_bar,
                    "Tail-gas flue gas FLUE->STACK",
                )?);
            }
            let dpf = water_dew_point_k(props, &fnw, truthy(fl.pressure_bar).unwrap_or(1.1))?;
            if let Some(d) = dpf
                && d > t_stack
            {
                warnings.push(format!(
                    "Flue-gas water dew point {} degC above stack T: condensation neglected.",
                    fmt_f(d - 273.15, 1)
                ));
            }
        }
        _ => warnings.push("No FLUE stream in result: tail-gas firing not analysed.".into()),
    }
    Ok(Extracted {
        feed,
        feed_meta: meta,
        reaction: rxn,
        reaction_source: q_src,
        cracked,
        flue,
        t_reactor_k: t_r,
        warnings,
        p_vap_bar: p_vap,
    })
}
