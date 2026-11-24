//! Fluid-property back ends of the process model.
//!
//! The Python reference calls CoolProp 8.0.0 (reference equations of state: ammonia Gao et al.
//! 2020, water IAPWS-95 Wagner and Pruss 2002) in `process_model/properties.py` and
//! `heat_integration/streams.py`, always with CoolProp's default reference state (it never calls
//! `set_reference_state`; the NH3 enthalpy scale is anchored to NASA-7 by the model itself). The
//! complete set of calls is:
//!
//! | Fluid | Output | Inputs | Phase | Python call |
//! |---|---|---|---|---|
//! | Ammonia | `Hmolar`, `Dmolar` | T, P | imposed liquid | `AbstractState("HEOS")`, `specify_phase(iphase_liquid)`, `update(PT_INPUTS)` |
//! | Ammonia | `Hmolar`, `Hmolar_residual` | T, P | imposed gas | idem with `iphase_gas` |
//! | Ammonia | `Hmolar` | T, P | CoolProp's phase determination | `PropsSI("Hmolar", "T", T, "P", P, ...)` |
//! | Ammonia | `P` | T, Q = 0 | saturation | `PropsSI("P", "T", T, "Q", 0, ...)` |
//! | Ammonia | `T`, `Hmolar` | P, Q = 0 or 1 | saturation | `PropsSI("T"/"Hmolar", "P", P, "Q", q, ...)` |
//! | Ammonia, Water | `Tcrit` | - | - | `PropsSI("Tcrit", fluid)` |
//! | Water | `P` | T, Q = 0 | saturation | `PropsSI("P", "T", T, "Q", 0, "Water")` |
//! | Water | `Hmolar`, `Cpmolar` | T, Q | saturation | `PropsSI(..., "T", T, "Q", q, "Water")` |
//! | Water | `T` | P, Q = 1 | saturation | `PropsSI("T", "P", p, "Q", 1, "Water")` |
//!
//! Two interchangeable back ends implement [`FluidProps`]:
//!
//! * `coolprop` (crate `amcrax-coolprop`, feature `coolprop` of the CLI): CoolProp 8.0.0 built
//!   from its C++ sources in CI and called through a thin FFI, making exactly the calls above;
//! * `tables` ([`TablesBackend`]): **tabulated CoolProp values, exact only at stored states**.
//!   The golden table `rust/golden/stage4/coolprop_states.json` holds every CoolProp call the
//!   Python reference made while running the stored flowsheet and heat-integration cases, with
//!   the derivative of the output with respect to the input that root searches vary. A query
//!   returns the stored value when its inputs are identical, the first-order Taylor value when
//!   the varying input lies within [`TAYLOR_WINDOW_REL`] (relative) of a stored state (the root
//!   searches of the Rust port can step through states that differ from Python's in the last
//!   digits), and an error otherwise.

use crate::error::EngineError;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Phase selector of a Peng-Robinson call (root / branch).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    /// Vapour (gas) root / branch.
    Vapour,
    /// Liquid root / branch.
    Liquid,
}

/// Fluids of the CoolProp calls.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Fluid {
    Ammonia,
    Water,
}

impl Fluid {
    /// CoolProp fluid name.
    pub fn name(self) -> &'static str {
        match self {
            Fluid::Ammonia => "Ammonia",
            Fluid::Water => "Water",
        }
    }
    /// From the CoolProp fluid name.
    pub fn from_name(s: &str) -> Option<Fluid> {
        match s {
            "Ammonia" => Some(Fluid::Ammonia),
            "Water" => Some(Fluid::Water),
            _ => None,
        }
    }
}

/// CoolProp output parameters used by the model (SI units: J/mol, mol/m3, J/(mol K), Pa, K).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Output {
    Hmolar,
    HmolarResidual,
    Dmolar,
    Cpmolar,
    P,
    T,
    Tcrit,
}

impl Output {
    /// CoolProp parameter name.
    pub fn name(self) -> &'static str {
        match self {
            Output::Hmolar => "Hmolar",
            Output::HmolarResidual => "Hmolar_residual",
            Output::Dmolar => "Dmolar",
            Output::Cpmolar => "Cpmolar",
            Output::P => "P",
            Output::T => "T",
            Output::Tcrit => "Tcrit",
        }
    }
    /// From the CoolProp parameter name.
    pub fn from_name(s: &str) -> Option<Output> {
        Some(match s {
            "Hmolar" => Output::Hmolar,
            "Hmolar_residual" => Output::HmolarResidual,
            "Dmolar" => Output::Dmolar,
            "Cpmolar" => Output::Cpmolar,
            "P" => Output::P,
            "T" => Output::T,
            "Tcrit" => Output::Tcrit,
            _ => return None,
        })
    }
}

/// Imposed phase of a (T, P) call: none (CoolProp's own phase determination, as `PropsSI`) or
/// liquid / gas (`AbstractState.specify_phase`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Imposed {
    None,
    Liquid,
    Gas,
}

impl Imposed {
    /// Name used in the golden tables.
    pub fn name(self) -> &'static str {
        match self {
            Imposed::None => "none",
            Imposed::Liquid => "liquid",
            Imposed::Gas => "gas",
        }
    }
    /// From the golden-table name.
    pub fn from_name(s: &str) -> Option<Imposed> {
        match s {
            "none" => Some(Imposed::None),
            "liquid" => Some(Imposed::Liquid),
            "gas" => Some(Imposed::Gas),
            _ => None,
        }
    }
}

/// Input pair of a call.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Inputs {
    /// Temperature (K) and pressure (Pa).
    Tp { t_k: f64, p_pa: f64, phase: Imposed },
    /// Temperature (K) and vapour quality.
    Tq { t_k: f64, q: f64 },
    /// Pressure (Pa) and vapour quality.
    Pq { p_pa: f64, q: f64 },
    /// No state (fluid constants such as `Tcrit`).
    Constant,
}

/// One CoolProp call.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Query {
    pub fluid: Fluid,
    pub out: Output,
    pub inputs: Inputs,
}

impl Query {
    /// `(T, P)` call.
    pub fn tp(fluid: Fluid, out: Output, t_k: f64, p_pa: f64, phase: Imposed) -> Query {
        Query {
            fluid,
            out,
            inputs: Inputs::Tp { t_k, p_pa, phase },
        }
    }
    /// `(T, Q)` call.
    pub fn tq(fluid: Fluid, out: Output, t_k: f64, q: f64) -> Query {
        Query {
            fluid,
            out,
            inputs: Inputs::Tq { t_k, q },
        }
    }
    /// `(P, Q)` call.
    pub fn pq(fluid: Fluid, out: Output, p_pa: f64, q: f64) -> Query {
        Query {
            fluid,
            out,
            inputs: Inputs::Pq { p_pa, q },
        }
    }
    /// Fluid constant.
    pub fn constant(fluid: Fluid, out: Output) -> Query {
        Query {
            fluid,
            out,
            inputs: Inputs::Constant,
        }
    }
    /// Golden-table pair name (`TP`, `TQ`, `PQ`, `none`).
    pub fn pair(&self) -> &'static str {
        match self.inputs {
            Inputs::Tp { .. } => "TP",
            Inputs::Tq { .. } => "TQ",
            Inputs::Pq { .. } => "PQ",
            Inputs::Constant => "none",
        }
    }
    /// Imposed phase (`None` except for imposed-phase `(T, P)` calls).
    pub fn phase(&self) -> Imposed {
        match self.inputs {
            Inputs::Tp { phase, .. } => phase,
            _ => Imposed::None,
        }
    }
    /// The golden-table inputs `(a, b)`: TP `(T, P)`, TQ `(T, Q)`, PQ `(P, Q)`, constant `(0, 0)`.
    /// `a` is the input that root searches vary.
    pub fn ab(&self) -> (f64, f64) {
        match self.inputs {
            Inputs::Tp { t_k, p_pa, .. } => (t_k, p_pa),
            Inputs::Tq { t_k, q } => (t_k, q),
            Inputs::Pq { p_pa, q } => (p_pa, q),
            Inputs::Constant => (0.0, 0.0),
        }
    }
    /// Build from the golden-table columns.
    pub fn from_parts(
        fluid: &str,
        out: &str,
        pair: &str,
        phase: &str,
        a: f64,
        b: f64,
    ) -> Result<Query, EngineError> {
        let bad = || {
            EngineError::data(
                "coolprop table",
                format!("bad query {fluid} {out} {pair} {phase}"),
            )
        };
        let fluid = Fluid::from_name(fluid).ok_or_else(bad)?;
        let out = Output::from_name(out).ok_or_else(bad)?;
        let phase = Imposed::from_name(phase).ok_or_else(bad)?;
        Ok(match pair {
            "TP" => Query::tp(fluid, out, a, b, phase),
            "TQ" => Query::tq(fluid, out, a, b),
            "PQ" => Query::pq(fluid, out, a, b),
            "none" => Query::constant(fluid, out),
            _ => return Err(bad()),
        })
    }
    /// Short description for error messages.
    pub fn describe(&self) -> String {
        let (a, b) = self.ab();
        format!(
            "{} {} {} phase={} a={a:e} b={b:e}",
            self.fluid.name(),
            self.out.name(),
            self.pair(),
            self.phase().name()
        )
    }
}

/// A fluid-property back end.
pub trait FluidProps: Send + Sync {
    /// Back-end name (`coolprop`, `tables`).
    fn backend(&self) -> &'static str;
    /// The value of one call (SI units), or the error CoolProp raised.
    fn value(&self, q: &Query) -> Result<f64, EngineError>;
    /// Lookup statistics (exact hits, Taylor hits, misses) of a tabulated back end.
    fn lookup_stats(&self) -> Option<(usize, usize, usize)> {
        None
    }
}

/// Relative window of the first-order Taylor lookup of [`TablesBackend`].
pub const TAYLOR_WINDOW_REL: f64 = 1e-7;

#[derive(Debug, Clone)]
struct Rec {
    x: f64,
    v: Result<f64, String>,
    d: Option<f64>,
}

type Key = (Fluid, Output, &'static str, Imposed, u64);

/// Tabulated CoolProp values (see the module documentation): exact only at stored states.
#[derive(Debug, Default)]
pub struct TablesBackend {
    map: HashMap<Key, Vec<Rec>>,
    n_states: usize,
    exact_hits: AtomicUsize,
    taylor_hits: AtomicUsize,
    misses: AtomicUsize,
}

fn key_of(q: &Query) -> Key {
    let (_, b) = q.ab();
    (q.fluid, q.out, q.pair(), q.phase(), b.to_bits())
}

impl TablesBackend {
    /// Build from the `states` list of `coolprop_states.json`.
    pub fn from_states(states: &Value) -> Result<TablesBackend, EngineError> {
        let list = states
            .as_array()
            .ok_or_else(|| EngineError::data("coolprop_states", "states list expected"))?;
        let mut map: HashMap<Key, Vec<Rec>> = HashMap::new();
        for s in list {
            let txt = |k: &str| s.get(k).and_then(Value::as_str).unwrap_or("");
            let f = |k: &str| crate::verify::num(&s[k]);
            let q = Query::from_parts(
                txt("fluid"),
                txt("out"),
                txt("in"),
                txt("phase"),
                f("a"),
                f("b"),
            )?;
            let v = match s.get("error").and_then(Value::as_str) {
                Some(e) => Err(e.to_string()),
                None => Ok(f("v")),
            };
            let d = s.get("d").filter(|x| !x.is_null()).map(crate::verify::num);
            map.entry(key_of(&q))
                .or_default()
                .push(Rec { x: q.ab().0, v, d });
        }
        let mut n = 0;
        for v in map.values_mut() {
            v.sort_by(|a, b| a.x.total_cmp(&b.x));
            n += v.len();
        }
        Ok(TablesBackend {
            map,
            n_states: n,
            ..TablesBackend::default()
        })
    }

    /// Number of stored states.
    pub fn len(&self) -> usize {
        self.n_states
    }

    /// True when no state is stored.
    pub fn is_empty(&self) -> bool {
        self.n_states == 0
    }

    /// (exact hits, Taylor hits, misses) since construction.
    pub fn stats(&self) -> (usize, usize, usize) {
        (
            self.exact_hits.load(Ordering::Relaxed),
            self.taylor_hits.load(Ordering::Relaxed),
            self.misses.load(Ordering::Relaxed),
        )
    }

    fn miss(&self, q: &Query, why: &str) -> EngineError {
        self.misses.fetch_add(1, Ordering::Relaxed);
        EngineError::Property(format!(
            "tables back end: {} ({why}; tabulated CoolProp values are exact only at stored states)",
            q.describe()
        ))
    }
}

impl FluidProps for TablesBackend {
    fn backend(&self) -> &'static str {
        "tables"
    }

    fn lookup_stats(&self) -> Option<(usize, usize, usize)> {
        Some(self.stats())
    }

    fn value(&self, q: &Query) -> Result<f64, EngineError> {
        let Some(recs) = self.map.get(&key_of(q)) else {
            return Err(self.miss(q, "no stored state with this fixed input"));
        };
        let x = q.ab().0;
        let i = recs.partition_point(|r| r.x < x);
        let mut best: Option<&Rec> = None;
        for j in [i.wrapping_sub(1), i] {
            if let Some(r) = recs.get(j)
                && best.is_none_or(|b| (r.x - x).abs() < (b.x - x).abs())
            {
                best = Some(r);
            }
        }
        let Some(r) = best else {
            return Err(self.miss(q, "empty table"));
        };
        if r.x.to_bits() == x.to_bits() {
            self.exact_hits.fetch_add(1, Ordering::Relaxed);
            return r.v.clone().map_err(EngineError::Property);
        }
        match (&r.v, r.d) {
            (Ok(v), Some(d)) if (x - r.x).abs() <= TAYLOR_WINDOW_REL * r.x.abs() => {
                self.taylor_hits.fetch_add(1, Ordering::Relaxed);
                Ok(v + d * (x - r.x))
            }
            _ => Err(self.miss(
                q,
                &format!("nearest stored input {:e} differs by {:e}", r.x, x - r.x),
            )),
        }
    }
}
