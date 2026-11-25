//! Catalyst economics for hypothesis H3 (port of Python `research/catalyst_economics.py`):
//! derived catalyst prices, catalyst cost per kg H2, the catalyst-independent design states
//! (kinetic flowsheet, heat accounting, fired duty, FEHE geometry and cost for the three U cases),
//! `singapore.evaluate` on a design with the optional CAPEX responses of the three economic modes
//! (`reference`, `exchanger`, `exchanger_reactor_mass`), designs, cost-optimal temperatures (5 K
//! grid refined on 1 K), the comparison of a low-temperature design with the Ni reference (LCOH
//! decomposition, fixed-design break-even price and lifetime) and the investment view (incremental
//! investment, operating saving, NPV with discrete catalyst replacements, payback).
//!
//! Designs are JSON objects with the keys of the Python dicts. The states, catalyst masses and
//! equilibrium conversions are cached as `functools.lru_cache` does in Python.

use crate::catalyst::{
    CATALYST_LIFETIME_YR, Ctx, FURNACE_EFFICIENCY, PRICE_JSON, REFERENCE_NI, THERMAL_LOSS_FRACTION,
    catalyst, eq_conversion, fired_duty, heat_accounting, kinetic_flowsheet, required_mass_kg,
    summary_for_economics,
};
use crate::economics::jf;
use crate::economics::reference::RefCapexArgs;
use crate::economics::singapore::{Overrides, Scenario, Summary, evaluate};
use crate::error::EngineError;
use crate::heat::analysis::analyse;
use crate::heat::exchanger::{SizeOptions, UCase, size_and_cost};
use crate::process::result::SimulationResult;
use crate::pyops::{py_max, py_sum};
use serde_json::{Map, Value, json};
use std::cell::RefCell;
use std::collections::HashMap;
use std::path::Path;
use std::rc::Rc;

pub const P_BAR: f64 = 20.0;
pub const X_TARGET: f64 = 0.95;
pub const MODES: [&str; 3] = ["reference", "exchanger", "exchanger_reactor_mass"];
pub const UNMODELLED: [&str; 3] = ["Ni/CeO2", "Ru/CeO2", "Ru-K/CaO"];
pub const LIFETIMES_YR: [f64; 4] = [1.0, 2.0, 4.0, 5.0];
pub const PRICE_SCENARIOS: [&str; 3] = ["low", "central", "high"];
/// `CHO_PRICE` (USD/kg): Ni 33.4, Ru 542.
pub const CHO_PRICE_NI: f64 = 33.4;
pub const CHO_PRICE_RU: f64 = 542.0;

type R<T> = Result<T, EngineError>;

/// `T_GRID` (470 to 760 degC, step 5 K).
pub fn t_grid() -> Vec<f64> {
    (0..59).map(|i| 470.0 + 5.0 * i as f64).collect()
}

fn n(v: &Value, k: &str) -> R<f64> {
    v[k].as_f64()
        .ok_or_else(|| EngineError::Domain(format!("KeyError/TypeError: '{k}'")))
}

/// The `U_case` argument (a key of `U_CASES` or a value in W/m2K).
#[derive(Debug, Clone, PartialEq)]
pub enum U {
    Key(String),
    Value(f64),
}

impl U {
    pub fn central() -> U {
        U::Key("central".into())
    }
    fn json(&self) -> Value {
        match self {
            U::Key(s) => json!(s),
            U::Value(v) => json!(v),
        }
    }
    fn ucase(&self) -> UCase {
        match self {
            U::Key(s) => UCase::Key(s.clone()),
            U::Value(v) => UCase::Value(*v),
        }
    }
    /// From a JSON value.
    pub fn from_json(v: &Value) -> U {
        match v {
            Value::String(s) => U::Key(s.clone()),
            Value::Number(x) => U::Value(x.as_f64().unwrap_or(f64::NAN)),
            _ => U::central(),
        }
    }
}

/// A design state (`state()` / `state_from_result()`).
#[derive(Debug, Clone)]
pub struct State {
    pub v: Value,
    pub summary: Summary,
}

/// Keyword arguments of `design` / `optimise` (Python defaults by [`DesignKw::default`]).
#[derive(Debug, Clone)]
pub struct DesignKw {
    pub w_kg: Option<f64>,
    pub kinetic_factor: f64,
    pub hi: bool,
    pub mode: String,
    pub u: U,
    pub scenario: Value,
    pub econ_overrides: Option<Overrides>,
}

impl Default for DesignKw {
    fn default() -> Self {
        DesignKw {
            w_kg: None,
            kinetic_factor: 1.0,
            hi: true,
            mode: "exchanger".into(),
            u: U::central(),
            scenario: json!("grey"),
            econ_overrides: None,
        }
    }
}

/// state() cache: (T, P, X bits, heat integration) to the state.
type StateCache = HashMap<(u64, u64, u64, bool), Rc<State>>;

/// The study context with the Python caches.
pub struct Econ<'a, 'b> {
    pub ctx: &'a Ctx<'b>,
    prices: Value,
    validity: Value,
    states: RefCell<StateCache>,
    masses: RefCell<HashMap<(String, u64), f64>>,
    eqc: RefCell<HashMap<u64, f64>>,
}

impl<'a, 'b> Econ<'a, 'b> {
    /// Read the price file (embedded) and the kinetic validity classification (repository).
    pub fn new(ctx: &'a Ctx<'b>, root: &Path) -> R<Econ<'a, 'b>> {
        let rel = "results/research/kinetics/validity_classification.json";
        let t = std::fs::read_to_string(root.join(rel))
            .map_err(|e| EngineError::data(rel, e.to_string()))?;
        Ok(Econ {
            ctx,
            prices: serde_json::from_str(PRICE_JSON)
                .map_err(|e| EngineError::data("catalyst_prices.json", e.to_string()))?,
            validity: serde_json::from_str(&t)
                .map_err(|e| EngineError::data(rel, e.to_string()))?,
            states: RefCell::new(HashMap::new()),
            masses: RefCell::new(HashMap::new()),
            eqc: RefCell::new(HashMap::new()),
        })
    }

    fn fx(&self) -> f64 {
        self.ctx.econ.reference.fx_sgd_per_usd
    }

    fn scen(&self, name: &str) -> R<&Value> {
        let s = &self.prices["scenarios_usd_per_kg_finished_catalyst"][name];
        if s.is_null() {
            return Err(EngineError::Domain(format!("KeyError: '{name}'")));
        }
        Ok(s)
    }

    // ---------------------------------------------------------------------------------- prices
    /// `price_from_components(name, P_Ni, P_Ru, N)`.
    pub fn price_from_components(&self, name: &str, p_ni: f64, p_ru: f64, nn: f64) -> R<f64> {
        let w = &self.scen(name)?["loading_wt_pct"];
        Ok(n(w, "Ni")? / 100.0 * p_ni + n(w, "Ru")? / 100.0 * p_ru + nn)
    }

    /// `price(name, scenario)`: derived price recomputed from its components.
    pub fn price(&self, name: &str, scenario: &str) -> R<f64> {
        let e = &self.scen(name)?[scenario];
        self.price_from_components(
            name,
            n(e, "P_Ni_usd_per_kg")?,
            n(e, "P_Ru_usd_per_kg")?,
            n(e, "N_usd_per_kg")?,
        )
    }

    /// `ru_metal_floor(wt_pct_ru, P_Ru)` at the low (USGS 2025 average) Ru price.
    pub fn ru_metal_floor(&self, wt_pct_ru: f64, p_ru: Option<f64>) -> R<f64> {
        let p = match p_ru {
            Some(v) => v,
            None => n(&self.scen("Ru/MgO")?["low"], "P_Ru_usd_per_kg")?,
        };
        Ok(wt_pct_ru / 100.0 * p)
    }

    /// `PUBLISHED_TEA_PRICE[cid]`.
    pub fn published_tea_price(cid: &str) -> R<f64> {
        Ok(if catalyst(cid)?.family == "Ni" {
            CHO_PRICE_NI
        } else {
            CHO_PRICE_RU
        })
    }

    /// `price_table()` (numbers, flags and the labels that are computed).
    pub fn price_table(&self) -> R<Vec<Value>> {
        let cats = crate::catalyst::catalysts()?;
        let mut names: Vec<(String, Option<&str>)> = cats
            .iter()
            .map(|c| (c.price_key.to_string(), Some(c.id)))
            .collect();
        names.extend(UNMODELLED.iter().map(|s| (s.to_string(), None)));
        let fx = self.fx();
        let mut rows = Vec::new();
        for (name, cid) in names {
            let s = self.scen(&name)?;
            let mut r = Map::new();
            r.insert("catalyst".into(), json!(name));
            r.insert("catalyst_id".into(), json!(cid));
            r.insert("modelled".into(), json!(cid.is_some()));
            r.insert("loading_wt_pct".into(), s["loading_wt_pct"].clone());
            r.insert("loading_basis".into(), s["loading_basis"].clone());
            r.insert("formula".into(), s["formula"].clone());
            r.insert("grade".into(), s["grade"].clone());
            for sc in PRICE_SCENARIOS {
                let e = &s[sc];
                let usd = self.price(&name, sc)?;
                r.insert(sc.into(), json!({"USD_per_kg": usd, "SGD_per_kg": usd * fx,
                    "P_Ni_USD_per_kg": e["P_Ni_usd_per_kg"], "P_Ru_USD_per_kg": e["P_Ru_usd_per_kg"],
                    "N_USD_per_kg": e["N_usd_per_kg"], "price_file_USD_per_kg": e["usd_per_kg"],
                    "price_file_SGD_per_kg_superseded_fx": e["sgd_per_kg"]}));
            }
            if let Some(c) = cid {
                let tea = Self::published_tea_price(c)?;
                r.insert("published_TEA_case_USD_per_kg".into(), json!(tea));
                r.insert("published_TEA_case_SGD_per_kg".into(), json!(tea * fx));
                let floor = self.ru_metal_floor(n(&s["loading_wt_pct"], "Ru")?, None)?;
                r.insert(
                    "published_TEA_case_below_Ru_metal_floor".into(),
                    json!(tea < floor),
                );
            }
            rows.push(Value::Object(r));
        }
        Ok(rows)
    }

    /// `published_tea_prices()`.
    pub fn published_tea_prices(&self) -> R<Vec<Value>> {
        let fx = self.fx();
        let ue = self.ctx.econ.reference.usd_per_eur;
        let mut out = Vec::new();
        for e in self.prices["entries"].as_array().into_iter().flatten() {
            if e["kind"].as_str() != Some("tea_price") {
                continue;
            }
            let cur = e["currency"].as_str().unwrap_or("");
            let pv = e["price_value"].as_f64();
            let usd = match (cur, pv) {
                ("USD", Some(v)) => Some(v),
                ("EUR", Some(v)) => Some(v * ue),
                _ => None,
            };
            let wru = e["loading_wt_pct"]["Ru"].as_f64();
            let floor = match wru {
                Some(w) if w != 0.0 => Some(self.ru_metal_floor(w, None)?),
                _ => None,
            };
            let below = match (usd, floor) {
                (Some(u), Some(f)) if f != 0.0 => json!(u < f),
                _ => Value::Null,
            };
            out.push(
                json!({"id": e["id"], "material": e["material"], "price_value": e["price_value"],
                "currency": cur, "unit": e["unit"], "price_date": e["price_date"],
                "publication": e["supplier_or_publication"], "url": e["url"], "grade": e["grade"],
                "USD_per_kg": usd, "SGD_per_kg": usd.map(|u| u * fx), "Ru_wt_pct": wru,
                "Ru_metal_floor_USD_per_kg_USGS2025": floor, "below_Ru_metal_floor": below,
                "label": "published TEA price: shown as a separate case, NOT a current price"}),
            );
        }
        Ok(out)
    }

    // ---------------------------------------------------------------------------------- costs
    /// `catalyst_cost(W_kg, price, lifetime, annual_h2_kg)`.
    pub fn catalyst_cost(&self, w: f64, p: f64, l: f64, h: f64) -> Value {
        let fx = self.fx();
        let yr = w * p / l;
        json!({"W_kg": w, "price_USD_per_kg": p, "lifetime_yr": l, "charge_USD": w * p,
               "charge_SGD": w * p * fx, "annual_USD_per_yr": yr, "annual_SGD_per_yr": yr * fx,
               "USD_per_kg_H2": yr / h, "SGD_per_kg_H2": yr / h * fx})
    }

    // ---------------------------------------------------------------------------------- states
    /// `fehe_geometry(res)`.
    pub fn fehe_geometry(&self, res: &SimulationResult) -> R<Value> {
        if !res.inputs.heat_integration {
            return Ok(Value::Null);
        }
        let Some(b) = res.block("FEHE") else {
            return Ok(Value::Null);
        };
        let duty = b.duty_kw.unwrap_or(0.0).abs();
        if duty <= 0.0 {
            return Ok(Value::Null);
        }
        let t = |id: &str| -> R<f64> {
            res.stream(id)
                .and_then(|s| s.temperature_c)
                .ok_or_else(|| EngineError::Domain(format!("KeyError: '{id}'")))
        };
        let a = analyse(self.ctx.props, res, 20.0)?;
        Ok(
            json!({"duty_kW": duty, "T_hot_in": t("S5")?, "T_hot_out": t("S6")?, "T_cold_in": t("S2")?,
                  "T_cold_out": t("S3")?, "ua_seg_kW_K": a["fehe"]["ua_segmented_kW_K"]}),
        )
    }

    /// `fehe_cost(geo, U_case)`.
    pub fn fehe_cost(&self, geo: &Value, u: &U) -> R<Value> {
        if geo.is_null() {
            return Ok(json!({"area_m2": 0.0, "tci_equivalent_USD": 0.0, "U_case": u.json()}));
        }
        let o = SizeOptions {
            ua_kw_k: geo["ua_seg_kW_K"].as_f64(),
            ..SizeOptions::default()
        };
        let r = size_and_cost(
            self.ctx.econ,
            n(geo, "duty_kW")?,
            n(geo, "T_hot_in")?,
            n(geo, "T_hot_out")?,
            n(geo, "T_cold_in")?,
            n(geo, "T_cold_out")?,
            &u.ucase(),
            &o,
        )?;
        Ok(
            json!({"area_m2": r["area_m2"], "n_shells": r["n_shells"], "U_W_m2K": r["U_W_m2K"],
                  "U_case": u.json(), "tci_equivalent_USD": r["tci_equivalent_USD"],
                  "tci_equivalent_SGD": r["tci_equivalent_SGD"], "installed_USD": r["installed_USD"]}),
        )
    }

    /// `state_from_result(res, dT, feff)`.
    pub fn state_from_result(&self, res: &SimulationResult, dt: f64, feff: f64) -> R<State> {
        let h = heat_accounting(self.ctx, res, dt)?;
        let fd = fired_duty(&h, feff, THERMAL_LOSS_FRACTION);
        let s = summary_for_economics(res, &fd, &h)?;
        let geo = self.fehe_geometry(res)?;
        let mut fe = Map::new();
        for u in ["low", "central", "high"] {
            fe.insert(u.into(), self.fehe_cost(&geo, &U::Key(u.into()))?);
        }
        Ok(State {
            v: json!({"T_C": res.inputs.reactor_temperature_c, "heat": h, "fired": fd, "summary": s.to_json(),
                      "fehe_geometry": geo, "fehe": Value::Object(fe), "source": res.source}),
            summary: s,
        })
    }

    /// `state(T_C, P_bar, X, hi)` (psa 0.85, furnace efficiency 0.85, dT 20 K), cached.
    pub fn state(&self, t_c: f64, p_bar: f64, x: f64, hi: bool) -> R<Rc<State>> {
        let key = (t_c.to_bits(), p_bar.to_bits(), x.to_bits(), hi);
        if let Some(s) = self.states.borrow().get(&key) {
            return Ok(s.clone());
        }
        let res = kinetic_flowsheet(self.ctx, t_c, p_bar, x, hi, 0.85)?;
        let s = Rc::new(self.state_from_result(&res, 20.0, FURNACE_EFFICIENCY)?);
        self.states.borrow_mut().insert(key, s.clone());
        Ok(s)
    }

    /// `hx_size_ratio(fehe_tci_USD, nh3_feed_kmol_h)`.
    pub fn hx_size_ratio(&self, fehe_tci: f64, nh3_feed_kmol_h: f64) -> R<f64> {
        let cap = self
            .ctx
            .econ
            .reference_capex(&RefCapexArgs::new(nh3_feed_kmol_h))?;
        let ne = n(&cap, "scaling_exponent")?;
        Ok(n(&cap["size_ratio"], "heat_exchangers")?
            * (1.0 + fehe_tci / n(&cap["tci_by_item_USD"], "heat_exchangers")?).powf(1.0 / ne))
    }

    /// `evaluate_design(st, W_kg, price, lifetime, mode, U_case, scenario, econ_overrides)`.
    #[allow(clippy::too_many_arguments)]
    pub fn evaluate_design(
        &self,
        st: &State,
        w: f64,
        price: f64,
        lifetime: f64,
        mode: &str,
        u: &U,
        scenario: &Value,
        econ_overrides: Option<&Overrides>,
    ) -> R<Value> {
        if !MODES.contains(&mode) {
            return Err(EngineError::Domain(format!(
                "ValueError: mode must be one of {MODES:?}"
            )));
        }
        let mut o = Overrides::new();
        o.insert("catalyst_mass_kg".into(), jf(py_max(w, 0.0)));
        o.insert("catalyst_price_USD_per_kg".into(), jf(price));
        o.insert("catalyst_lifetime_yr".into(), jf(lifetime));
        o.insert(
            "fuel_efficiency".into(),
            st.v["fired"]["furnace_efficiency"].clone(),
        );
        o.insert("heat_fuel".into(), json!("ammonia"));
        let fe = match u {
            U::Key(k) if st.v["fehe"].get(k).is_some() => st.v["fehe"][k.as_str()].clone(),
            _ => self.fehe_cost(&st.v["fehe_geometry"], u)?,
        };
        if mode != "reference" {
            let r =
                self.hx_size_ratio(n(&fe, "tci_equivalent_USD")?, st.summary.nh3_feed_kmol_h)?;
            o.insert("item_size_ratio".into(), json!({"heat_exchangers": r}));
        }
        if mode == "exchanger_reactor_mass" {
            o.insert("reactor_size_driver".into(), json!("catalyst_mass"));
        }
        if let Some(ov) = econ_overrides {
            for (k, v) in ov {
                o.insert(k.clone(), v.clone());
            }
        }
        let e = evaluate(
            self.ctx.econ,
            &st.summary,
            &Scenario::from_json(scenario)?,
            &o,
        )?;
        let a = &e["assumptions"]["economic"];
        let fac = n(&e, "crf")?
            + (n(a, "maintenance_frac_capex_per_yr")?
                * (1.0 + n(a, "plant_overhead_frac_labour_maint")?)
                + n(a, "insurance_frac_capex_per_yr")?)
                * (1.0 + n(a, "g_and_a_frac_fixed_opex")?);
        let items = e["capex"]["tci_by_item_USD"].clone();
        let h = n(&e, "annual_h2_kg")?;
        let mut ia = Map::new();
        for (k, v) in items.as_object().into_iter().flatten() {
            ia.insert(k.clone(), json!(v.as_f64().unwrap_or(f64::NAN) * fac / h));
        }
        Ok(
            json!({"lcoh_USD_per_kg": e["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"],
            "rec_USD_per_kg": e["rec_USD_per_kg"], "breakdown_USD_per_kg": e["breakdown_USD_per_kg"],
            "annual_USD_per_yr": e["annual_USD_per_yr"], "annual_h2_kg": e["annual_h2_kg"], "crf": e["crf"],
            "capex_total_USD": e["capex"]["total_capex_USD"], "tci_by_item_USD": items,
            "item_annual_charge_factor": fac, "item_annualised_USD_per_kg": Value::Object(ia),
            "fehe": fe, "mode": mode, "U_case": u.json(), "discount_rate": a["discount_rate"],
            "plant_life_yr": a["plant_life_yr"], "nh3_price_USD_per_t": e["nh3_price_USD_per_t"],
            "npv_USD_evaluate": e["npv_USD"]}),
        )
    }

    fn eqc(&self, t: f64) -> R<f64> {
        if let Some(v) = self.eqc.borrow().get(&t.to_bits()) {
            return Ok(*v);
        }
        let v = eq_conversion(t, P_BAR)?;
        self.eqc.borrow_mut().insert(t.to_bits(), v);
        Ok(v)
    }

    fn mass(&self, cid: &str, t: f64) -> R<f64> {
        let key = (cid.to_string(), t.to_bits());
        if let Some(v) = self.masses.borrow().get(&key) {
            return Ok(*v);
        }
        let v = required_mass_kg(self.ctx, cid, t, P_BAR, X_TARGET)?;
        self.masses.borrow_mut().insert(key, v);
        Ok(v)
    }

    /// `kinetic_validity(cid, P_bar, T_C)`.
    pub fn kinetic_validity(&self, cid: &str, p_bar: f64, t_c: Option<f64>) -> R<Value> {
        let law = self.validity["laws"]
            .as_array()
            .and_then(|v| v.iter().find(|x| x["catalyst_id"].as_str() == Some(cid)))
            .ok_or_else(|| EngineError::Domain(format!("StopIteration: {cid}")))?;
        let fr = &law["fitted_range"];
        let p0 = fr["P_bar"][0].as_f64().unwrap_or(f64::NAN);
        let p1 = fr["P_bar"][1].as_f64().unwrap_or(f64::NAN);
        let p_out = !(p0 - 1e-9 <= p_bar && p_bar <= p1 + 1e-9);
        let t_out = t_c.map(|t| {
            let t0 = fr["T_C"][0].as_f64().unwrap_or(f64::NAN);
            let t1 = fr["T_C"][1].as_f64().unwrap_or(f64::NAN);
            !(t0 <= t && t <= t1)
        });
        let cls = law["class"].as_str().unwrap_or("");
        let label = if cls == "extrapolated" {
            "extrapolation".to_string()
        } else if p_out {
            "pressure extrapolation of a law validated against literature".to_string()
        } else {
            cls.to_string()
        };
        Ok(
            json!({"kinetic_validity_class": cls, "kinetic_result_label": label,
            "kinetic_pressure_extrapolated": p_out, "kinetic_T_outside_fitted_range": t_out,
            "kinetic_fitted_P_bar": fr["P_bar"], "kinetic_fitted_T_C": fr["T_C"],
            "kinetic_validity_source": "results/research/kinetics/validity_classification.json"}),
        )
    }

    /// `design(cid, T_C, price, lifetime, ...)`; `None` where the target conversion is not
    /// reachable.
    pub fn design(
        &self,
        cid: &str,
        t_c: f64,
        price: f64,
        lifetime: f64,
        kw: &DesignKw,
        st: Option<&State>,
    ) -> R<Option<Value>> {
        let w = match kw.w_kg {
            Some(w) => w,
            None => {
                if self.eqc(t_c)? <= X_TARGET + 1e-4 {
                    return Ok(None);
                }
                let w = self.mass(cid, t_c)?;
                if !w.is_finite() {
                    return Ok(None);
                }
                w / kw.kinetic_factor
            }
        };
        let owned;
        let st = match st {
            Some(s) => s,
            None => {
                owned = self.state(t_c, P_BAR, X_TARGET, kw.hi)?;
                &owned
            }
        };
        let ev = self.evaluate_design(
            st,
            w,
            price,
            lifetime,
            &kw.mode,
            &kw.u,
            &kw.scenario,
            kw.econ_overrides.as_ref(),
        )?;
        let c = catalyst(cid)?;
        let mut d = Map::new();
        d.insert("catalyst_id".into(), json!(cid));
        d.insert("catalyst".into(), json!(c.short));
        d.insert("T_C".into(), json!(t_c));
        d.insert("W_kg".into(), json!(w));
        d.insert("heat_integration".into(), json!(kw.hi));
        d.insert(
            "fired_process_duty_kW".into(),
            st.v["fired"]["fired_process_duty_kW"].clone(),
        );
        d.insert(
            "supplementary_nh3_kg_h".into(),
            st.v["fired"]["supplementary_nh3_kg_h"].clone(),
        );
        d.insert(
            "first_law_deficit_kW".into(),
            st.v["heat"]["kpi_net_fuel_heat_deficit_kW_first_law"].clone(),
        );
        d.insert(
            "total_external_heating_kW".into(),
            st.v["heat"]["kpi_total_external_heating_kW"].clone(),
        );
        d.insert("h2_product_kg_h".into(), st.v["summary"]["h2_kg_h"].clone());
        d.insert("flowsheet_source".into(), st.v["source"].clone());
        for (k, v) in ev.as_object().into_iter().flatten() {
            d.insert(k.clone(), v.clone());
        }
        let h = n(&ev, "annual_h2_kg")?;
        d.insert(
            "catalyst_cost".into(),
            self.catalyst_cost(w, price, lifetime, h),
        );
        for (k, v) in self
            .kinetic_validity(cid, P_BAR, Some(t_c))?
            .as_object()
            .into_iter()
            .flatten()
        {
            d.insert(k.clone(), v.clone());
        }
        Ok(Some(Value::Object(d)))
    }

    /// `optimise(cid, price, lifetime, refine, grid, **kw)`: minimum LCOH on the 5 K grid,
    /// refined on 1 K around it.
    pub fn optimise(
        &self,
        cid: &str,
        price: f64,
        lifetime: f64,
        refine: bool,
        grid: Option<&[f64]>,
        kw: &DesignKw,
    ) -> R<Option<Value>> {
        let g0 = t_grid();
        let grid = grid.unwrap_or(&g0);
        let mut rows = Vec::new();
        for t in grid {
            if let Some(d) = self.design(cid, *t, price, lifetime, kw, None)? {
                rows.push(d);
            }
        }
        if rows.is_empty() {
            return Ok(None);
        }
        let lc = |d: &Value| d["lcoh_USD_per_kg"].as_f64().unwrap_or(f64::NAN);
        let argmin = |v: &[Value]| -> usize {
            let mut b = 0;
            for (i, d) in v.iter().enumerate() {
                if lc(d) < lc(&v[b]) {
                    b = i;
                }
            }
            b
        };
        let mut best = rows[argmin(&rows)].clone();
        if refine {
            let bt = best["T_C"].as_f64().unwrap_or(f64::NAN);
            let mut loc = Vec::new();
            for k in -4..5 {
                if let Some(d) = self.design(cid, bt + k as f64, price, lifetime, kw, None)? {
                    loc.push(d);
                }
            }
            loc.push(best);
            best = loc[argmin(&loc)].clone();
        }
        let bt = best["T_C"].as_f64().unwrap_or(f64::NAN);
        let gmax = grid.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let rmin = rows
            .iter()
            .map(|r| r["T_C"].as_f64().unwrap_or(f64::NAN))
            .fold(f64::INFINITY, f64::min);
        best["at_grid_bound"] = json!(bt >= gmax || bt <= rmin);
        Ok(Some(best))
    }
}

// ===================================================================================== comparison
fn item(d: &Value, k: &str) -> f64 {
    d["item_annualised_USD_per_kg"][k].as_f64().unwrap_or(0.0)
}

fn rep_pv(charge: f64, l: f64, i: f64, nn: i64) -> f64 {
    let mut pv = 0.0;
    let mut k = 1.0;
    while k * l < nn as f64 - 1e-9 {
        pv += charge * (1.0 + i).powf(-(k * l));
        k += 1.0;
    }
    pv
}

/// `investment(low, ref)`.
pub fn investment(low: &Value, rf: &Value, fx: f64) -> R<Value> {
    let (al, ar) = (&low["annual_USD_per_yr"], &rf["annual_USD_per_yr"]);
    let ops = [
        "heat_fuel",
        "electricity",
        "cooling_water",
        "fixed_opex",
        "carbon_tax",
        "ammonia_feed",
    ];
    let mut terms = Vec::new();
    for k in ops {
        terms.push(n(al, k)? - n(ar, k)?);
    }
    let s = -py_sum(terms);
    let dtci = n(low, "capex_total_USD")? - n(rf, "capex_total_USD")?;
    let (ch_l, ch_r) = (
        n(&low["catalyst_cost"], "charge_USD")?,
        n(&rf["catalyst_cost"], "charge_USD")?,
    );
    let (l_l, l_r) = (
        n(&low["catalyst_cost"], "lifetime_yr")?,
        n(&rf["catalyst_cost"], "lifetime_yr")?,
    );
    let i0 = dtci + ch_l - ch_r;
    let i = n(low, "discount_rate")?;
    let nn = n(low, "plant_life_yr")?.round_ties_even() as i64;
    let a = if i > 0.0 {
        (1.0 - (1.0 + i).powf(-(nn as f64))) / i
    } else {
        nn as f64
    };
    let repl = rep_pv(ch_l, l_l, i, nn) - rep_pv(ch_r, l_r, i, nn);
    let npv = -i0 + s * a - repl;
    let s_net = s - (ch_l / l_l - ch_r / l_r);
    let payback = if s_net > 0.0 {
        Some(py_max(i0, 0.0) / s_net)
    } else {
        None
    };
    let npv_s = -(n(low, "lcoh_USD_per_kg")? - n(rf, "lcoh_USD_per_kg")?) * n(low, "annual_h2_kg")?
        / n(low, "crf")?;
    Ok(
        json!({"incremental_TCI_USD": dtci, "incremental_first_charge_USD": ch_l - ch_r,
        "incremental_investment_USD": i0, "incremental_investment_SGD": i0 * fx,
        "annual_operating_saving_USD_per_yr": s, "annual_saving_net_of_smoothed_replacement_USD_per_yr": s_net,
        "simple_payback_yr": payback, "npv_choose_low_USD": npv, "npv_choose_low_SGD": npv * fx,
        "npv_choose_low_smoothed_USD": npv_s, "npv_discount_rate": i, "npv_life_yr": nn}),
    )
}

/// `compare(low, ref)`: decomposition of LCOH(low) - LCOH(ref) and the investment view.
pub fn compare(low: &Value, rf: &Value, fx: f64) -> R<Value> {
    let (bl, br) = (&low["breakdown_USD_per_kg"], &rf["breakdown_USD_per_kg"]);
    let mut d = Map::new();
    for (k, v) in bl.as_object().into_iter().flatten() {
        d.insert(k.clone(), json!(v.as_f64().unwrap_or(f64::NAN) - n(br, k)?));
    }
    let dv = Value::Object(d);
    let g = |k: &str| n(&dv, k);
    let hx = item(low, "heat_exchangers") - item(rf, "heat_exchangers");
    let rx = item(low, "reactor") - item(rf, "reactor");
    let cap_fixed = g("capex")? + g("fixed_opex")?;
    let dec = [
        ("energy_heat_fuel", g("heat_fuel")?),
        (
            "utilities_cooling_electricity",
            g("cooling_water")? + g("electricity")?,
        ),
        ("exchanger_capital_and_fixed", hx),
        ("reactor_capital_and_fixed", rx),
        ("other_capital_and_fixed", cap_fixed - hx - rx),
        ("catalyst", g("catalyst")?),
        ("carbon_tax", g("carbon_tax")?),
        ("ammonia_feed", g("ammonia_feed")?),
    ];
    let net = n(low, "lcoh_USD_per_kg")? - n(rf, "lcoh_USD_per_kg")?;
    let h = n(low, "annual_h2_kg")?;
    let a_low = n(low, "lcoh_USD_per_kg")? - n(bl, "catalyst")?;
    let margin = n(rf, "lcoh_USD_per_kg")? - a_low;
    let w = n(low, "W_kg")?;
    let p = n(&low["catalyst_cost"], "price_USD_per_kg")?;
    let l = n(&low["catalyst_cost"], "lifetime_yr")?;
    let p_be: Option<f64> = if margin > 0.0 && w > 0.0 {
        Some(margin * l * h / w)
    } else if w > 0.0 {
        None
    } else {
        Some(f64::INFINITY)
    };
    let l_be = if margin > 0.0 {
        Some(w * p / (margin * h))
    } else {
        None
    };
    let mut out = Map::new();
    let mut put = |k: &str, v: Value| {
        out.insert(k.to_string(), v);
    };
    put("low", low["catalyst"].clone());
    put("ref", rf["catalyst"].clone());
    put("low_T_C", low["T_C"].clone());
    put("ref_T_C", rf["T_C"].clone());
    put("low_W_kg", json!(w));
    put("ref_W_kg", rf["W_kg"].clone());
    put("net_lcoh_delta_USD_per_kg", json!(net));
    put("net_lcoh_delta_SGD_per_kg", json!(net * fx));
    put("low_cheaper", json!(net < 0.0));
    put(
        "decomposition_USD_per_kg",
        Value::Object(dec.iter().map(|(k, v)| (k.to_string(), json!(v))).collect()),
    );
    put(
        "decomposition_sum_check_USD_per_kg",
        json!(py_sum(dec.iter().map(|e| e.1)) - net),
    );
    put("energy_saving_USD_per_kg", json!(-g("heat_fuel")?));
    put(
        "energy_saving_fired_duty_kW",
        json!(n(rf, "fired_process_duty_kW")? - n(low, "fired_process_duty_kW")?),
    );
    put(
        "ref_fired_process_duty_kW",
        rf["fired_process_duty_kW"].clone(),
    );
    put(
        "energy_saving_supplementary_nh3_kg_h",
        json!(n(rf, "supplementary_nh3_kg_h")? - n(low, "supplementary_nh3_kg_h")?),
    );
    put(
        "energy_saving_first_law_deficit_kW",
        json!(n(rf, "first_law_deficit_kW")? - n(low, "first_law_deficit_kW")?),
    );
    put("catalyst_cost_increase_USD_per_kg", json!(g("catalyst")?));
    put("savings_minus_catalyst_increase_USD_per_kg", json!(-net));
    put(
        "breakeven_price_fixed_design_USD_per_kg",
        match p_be {
            Some(v) => jf(v),
            None => Value::Null,
        },
    );
    put(
        "breakeven_price_fixed_design_SGD_per_kg",
        match p_be {
            Some(v) if v.is_finite() => json!(v * fx),
            _ => Value::Null,
        },
    );
    put("breakeven_lifetime_fixed_design_yr", json!(l_be));
    put("margin_for_low_T_catalyst_USD_per_kg", json!(margin));
    for (k, v) in investment(low, rf, fx)?.as_object().into_iter().flatten() {
        out.insert(k.clone(), v.clone());
    }
    Ok(Value::Object(out))
}

/// `kinetics_label(*cids)`.
pub fn kinetics_label(e: &Econ, cids: &[&str]) -> R<Value> {
    let mut laws = Map::new();
    let mut ext = Vec::new();
    for c in cids {
        let v = e.kinetic_validity(c, P_BAR, None)?;
        let cls = v["kinetic_validity_class"]
            .as_str()
            .unwrap_or("")
            .to_string();
        let short = catalyst(c)?.short;
        if cls == "extrapolated" {
            ext.push(short.to_string());
        }
        laws.insert(short.into(), json!(cls));
    }
    Ok(
        json!({"laws": Value::Object(laws), "rests_on_extrapolated_law": !ext.is_empty(),
        "result_label": if ext.is_empty() { "pressure extrapolation (laws validated against literature at <= 10 bar only)" } else { "extrapolation" },
        "extrapolated_laws": ext}),
    )
}

/// `LOW_T`: the catalysts other than the Ni reference, in `CATALYSTS` order.
pub fn low_t() -> R<Vec<&'static str>> {
    Ok(crate::catalyst::catalysts()?
        .into_iter()
        .map(|c| c.id)
        .filter(|c| *c != REFERENCE_NI)
        .collect())
}

/// `CATALYST_LIFETIME_YR` (base lifetime).
pub const BASE_LIFETIME: f64 = CATALYST_LIFETIME_YR;
