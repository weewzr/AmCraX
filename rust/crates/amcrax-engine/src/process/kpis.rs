//! KPI and balance definitions shared by every result source (port of Python `amcrax/kpis.py`).

use super::result::{
    Balances, BlockResult, Kpis, LHV_KJ_PER_MOL, StreamResult, get_opt, get_or, molar_mass,
};
use crate::pyops::{py_max, py_sum};
use crate::species::Species;

const KJ_PER_MOL_KMOL_H_TO_KW: f64 = 1000.0 / 3600.0;
/// N atoms per molecule (dict order of Python `N_ATOMS`).
const N_ATOMS: [(&str, f64); 2] = [("NH3", 1.0), ("N2", 2.0)];
/// H atoms per molecule (dict order of Python `H_ATOMS`).
const H_ATOMS: [(&str, f64); 3] = [("NH3", 3.0), ("H2", 2.0), ("H2O", 2.0)];
const FEED_STREAMS: [&str; 2] = ["FEED", "AIR"];
const PRODUCT_STREAMS: [&str; 2] = ["H2PROD", "STACK"];

fn stream<'a>(streams: &'a [(String, StreamResult)], id: &str) -> Option<&'a StreamResult> {
    streams.iter().find(|x| x.0 == id).map(|x| &x.1)
}

fn block<'a>(blocks: &'a [(String, BlockResult)], id: &str) -> Option<&'a BlockResult> {
    blocks.iter().find(|x| x.0 == id).map(|x| &x.1)
}

fn n_of(streams: &[(String, StreamResult)], sid: &str, comp: &str) -> Option<f64> {
    stream(streams, sid).map(|s| get_or(&s.component_mole_flow_kmol_h, comp, 0.0))
}

fn duty(blocks: &[(String, BlockResult)], bid: &str) -> Option<f64> {
    block(blocks, bid).and_then(|b| b.duty_kw)
}

/// Python truthiness of an optional float (`None` and `0.0` are false; NaN is true).
fn truthy(x: Option<f64>) -> bool {
    matches!(x, Some(v) if v != 0.0)
}

/// `lhv_kW(stream)`: lower heating value flow (H2 and NH3), kW.
pub fn lhv_kw(s: &StreamResult) -> f64 {
    py_sum(LHV_KJ_PER_MOL.iter().map(|(c, lhv)| {
        get_or(&s.component_mole_flow_kmol_h, c.name(), 0.0) * lhv * KJ_PER_MOL_KMOL_H_TO_KW
    }))
}

/// `compute_kpis(streams, blocks)`.
pub fn compute_kpis(streams: &[(String, StreamResult)], blocks: &[(String, BlockResult)]) -> Kpis {
    let mut k = Kpis::default();
    let (nh3_in, nh3_out) = (n_of(streams, "S4", "NH3"), n_of(streams, "S5", "NH3"));
    if truthy(nh3_in)
        && let (Some(a), Some(b)) = (nh3_in, nh3_out)
    {
        k.nh3_conversion = Some(1.0 - b / a);
    }
    k.h2_in_cracked_gas_kmol_h = n_of(streams, "S5", "H2");
    let prod = stream(streams, "H2PROD");
    if let Some(p) = prod {
        let h2p = get_or(&p.component_mole_flow_kmol_h, "H2", 0.0);
        k.h2_product_kmol_h = Some(h2p);
        k.h2_product_kg_h = Some(h2p * molar_mass(Species::H2));
        k.h2_purity_mole_frac = get_opt(&p.mole_frac, "H2");
        let nh3_feed = n_of(streams, "FEED", "NH3");
        if let Some(f) = nh3_feed.filter(|v| *v != 0.0) {
            k.h2_yield_overall = Some(h2p / (1.5 * f));
        }
    }
    k.reactor_duty_kw = duty(blocks, "CRACKER");
    k.preheat_duty_kw = duty(blocks, "HEATER");
    k.vaporiser_duty_kw = duty(blocks, "VAPORIZR");
    k.recovered_heat_kw = if block(blocks, "FEHE").is_some() {
        duty(blocks, "FEHE")
    } else {
        Some(0.0)
    };
    if let (Some(a), Some(b), Some(c)) = (k.reactor_duty_kw, k.preheat_duty_kw, k.vaporiser_duty_kw)
    {
        k.total_external_heating_kw = Some(py_sum([a, b, c]));
    }
    if let Some(q) = duty(blocks, "COOLER") {
        k.cooling_duty_kw = Some(q.abs());
    }
    if let Some(p) = block(blocks, "PUMP") {
        k.pump_power_kw = p.power_kw;
    }
    if let Some(qf) = duty(blocks, "FLUEHX") {
        k.tailgas_combustion_heat_kw = Some(py_max(-qf, 0.0));
        if qf > 0.0
            && let Some(t) = k.total_external_heating_kw
        {
            k.total_external_heating_kw = Some(t + qf);
        }
    }
    if let Some(t) = stream(streams, "TAILGAS") {
        k.tailgas_lhv_kw = Some(lhv_kw(t));
    }
    if let Some(t) = k.total_external_heating_kw
        && truthy(k.h2_product_kg_h)
    {
        k.specific_heat_demand_kwh_per_kgh2 = Some(t / k.h2_product_kg_h.unwrap_or(f64::NAN));
    }
    if let (Some(t), Some(c)) = (k.total_external_heating_kw, k.tailgas_combustion_heat_kw) {
        k.net_fuel_heat_deficit_kw = Some(t - c);
    }
    if let (Some(feed), Some(p), Some(def)) =
        (stream(streams, "FEED"), prod, k.net_fuel_heat_deficit_kw)
    {
        let lhv_in = lhv_kw(feed);
        let pump = match k.pump_power_kw {
            Some(v) if v != 0.0 => v,
            _ => 0.0,
        };
        let denom = lhv_in + py_max(def, 0.0) + pump;
        if denom > 0.0 {
            k.lhv_efficiency = Some(lhv_kw(p) / denom);
        }
    }
    k
}

fn atoms(s: &StreamResult, table: &[(&str, f64)]) -> f64 {
    py_sum(
        table
            .iter()
            .map(|(c, n)| get_or(&s.component_mole_flow_kmol_h, c, 0.0) * n),
    )
}

/// `(x or 0.0)` of an optional float.
fn or0(x: Option<f64>) -> f64 {
    match x {
        Some(v) if v != 0.0 => v,
        _ => 0.0,
    }
}

/// `compute_balances(streams, blocks)`: boundary {FEED, AIR} -> {H2PROD, STACK}.
pub fn compute_balances(
    streams: &[(String, StreamResult)],
    blocks: &[(String, BlockResult)],
) -> Balances {
    let mut b = Balances::default();
    let feeds: Vec<&StreamResult> = FEED_STREAMS
        .iter()
        .filter_map(|s| stream(streams, s))
        .collect();
    let prods: Vec<&StreamResult> = PRODUCT_STREAMS
        .iter()
        .filter_map(|s| stream(streams, s))
        .collect();
    if feeds.is_empty() || prods.is_empty() {
        return b;
    }
    let all: Vec<&StreamResult> = feeds.iter().chain(prods.iter()).copied().collect();
    if all.iter().all(|s| s.mass_flow_kg_h.is_some()) {
        let mi = py_sum(feeds.iter().map(|s| s.mass_flow_kg_h.unwrap_or(0.0)));
        let mo = py_sum(prods.iter().map(|s| s.mass_flow_kg_h.unwrap_or(0.0)));
        b.mass_in_kg_h = Some(mi);
        b.mass_out_kg_h = Some(mo);
        if mi != 0.0 {
            b.mass_closure_rel = Some((mi - mo) / mi);
        }
    }
    b.n_atoms_in_kmol_h = Some(py_sum(feeds.iter().map(|s| atoms(s, &N_ATOMS))));
    b.n_atoms_out_kmol_h = Some(py_sum(prods.iter().map(|s| atoms(s, &N_ATOMS))));
    b.h_atoms_in_kmol_h = Some(py_sum(feeds.iter().map(|s| atoms(s, &H_ATOMS))));
    b.h_atoms_out_kmol_h = Some(py_sum(prods.iter().map(|s| atoms(s, &H_ATOMS))));
    if all.iter().all(|s| s.enthalpy_flow_kw.is_some()) {
        let h_in = py_sum(feeds.iter().map(|s| s.enthalpy_flow_kw.unwrap_or(0.0)));
        let h_out = py_sum(prods.iter().map(|s| s.enthalpy_flow_kw.unwrap_or(0.0)));
        let q_net = py_sum(
            blocks
                .iter()
                .filter(|(id, _)| id != "FEHE")
                .map(|(_, blk)| or0(blk.duty_kw)),
        );
        let w_net = py_sum(blocks.iter().map(|(_, blk)| or0(blk.power_kw)));
        let e_in = h_in + q_net + w_net;
        b.energy_in_kw = Some(e_in);
        b.energy_out_kw = Some(h_out);
        let sc = py_sum(
            blocks
                .iter()
                .filter(|(id, _)| id != "FEHE")
                .map(|(_, blk)| or0(blk.duty_kw).abs()),
        );
        let scale = if sc != 0.0 { sc } else { 1.0 };
        b.energy_closure_rel = Some((e_in - h_out) / scale);
    }
    b
}
