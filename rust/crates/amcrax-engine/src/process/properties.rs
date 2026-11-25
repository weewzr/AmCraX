//! Property basis of the process model (port of Python `process_model/properties.py`).
//!
//! Enthalpy reference: elements in their standard state at 298.15 K are zero (NASA-7 with the
//! enthalpy of formation). Liquid and vaporising NH3 come from CoolProp (reference EOS of Gao et
//! al. 2020) anchored to the NASA scale at 298.15 K, 1 Pa:
//! `h_NH3(T, P) = h_CP(T, P) - h_CP(T0, 1 Pa) + h_NASA(T0)`. The 0.2 mol% water is an ideal-gas
//! NASA species in the vapour and a linearly extrapolated liquid (`dh_vap`, `cp_L` of pure water
//! at T0 from CoolProp) in the liquid. Feed-section VLE: Raoult's law with CoolProp vapour
//! pressures. All CoolProp calls go through a [`FluidProps`] back end.

use crate::error::EngineError;
use crate::props::{Fluid, FluidProps, Imposed, Output, Query};
use crate::pyops::py_min;
use crate::species::Species;
use crate::thermo::equilibrium::{Eos, mixture_enthalpy_kw};
use crate::thermo::nasa7::species_enthalpy_kj_mol;
use crate::thermo::peng_robinson::{Alpha, Kij};
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use std::sync::OnceLock;

/// Anchor temperature, K.
pub const T0_K: f64 = 298.15;
/// Anchor pressure, Pa.
pub const P_LOW_PA: f64 = 1.0;

/// Phase of a feed-section stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FeedPhase {
    Liquid,
    Gas,
}

/// Map a brentq failure to the Python exception class (`ValueError` for a bad bracket or a NaN,
/// `RuntimeError` for no convergence); errors of the function itself pass through.
pub fn brent_err(e: BrentError<EngineError>) -> EngineError {
    match e {
        BrentError::Function(e) => e,
        BrentError::SignError { fa, fb } => EngineError::Domain(format!(
            "f(a) and f(b) must have different signs (f(a) = {fa:e}, f(b) = {fb:e})"
        )),
        BrentError::NanValue { x, .. } => {
            EngineError::Domain(format!("the function value at x={x} is NaN"))
        }
        BrentError::InvalidTolerance { xtol, rtol } => {
            EngineError::Domain(format!("invalid tolerance xtol={xtol} rtol={rtol}"))
        }
        BrentError::NotConverged(r) => EngineError::Numerical(format!(
            "failed to converge after {} iterations, value is {}",
            r.iterations, r.x
        )),
    }
}

/// The property functions of `properties.py` on one back end (the two `lru_cache` constants are
/// cached here as well).
pub struct Props<'a> {
    b: &'a dyn FluidProps,
    anchor: OnceLock<Result<f64, EngineError>>,
    water: OnceLock<Result<(f64, f64), EngineError>>,
}

impl<'a> Props<'a> {
    /// Property functions on back end `b`.
    pub fn new(b: &'a dyn FluidProps) -> Props<'a> {
        Props {
            b,
            anchor: OnceLock::new(),
            water: OnceLock::new(),
        }
    }

    /// The back end.
    pub fn backend(&self) -> &'a dyn FluidProps {
        self.b
    }

    fn q(&self, q: Query) -> Result<f64, EngineError> {
        self.b.value(&q)
    }

    /// `nh3_anchor_offset_kJ_mol`.
    pub fn nh3_anchor_offset_kj_mol(&self) -> Result<f64, EngineError> {
        self.anchor
            .get_or_init(|| {
                let h_cp = self.q(Query::tp(
                    Fluid::Ammonia,
                    Output::Hmolar,
                    T0_K,
                    P_LOW_PA,
                    Imposed::None,
                ))? / 1000.0;
                Ok(species_enthalpy_kj_mol(Species::NH3, T0_K)? - h_cp)
            })
            .clone()
    }

    fn nh3_tp(&self, out: Output, t_k: f64, p_bar: f64, ph: Imposed) -> Result<f64, EngineError> {
        self.q(Query::tp(Fluid::Ammonia, out, t_k, p_bar * 1e5, ph))
    }

    /// `nh3_enthalpy_kJ_mol(T, P, phase)`.
    pub fn nh3_enthalpy_kj_mol(
        &self,
        t_k: f64,
        p_bar: f64,
        phase: FeedPhase,
    ) -> Result<f64, EngineError> {
        let ph = match phase {
            FeedPhase::Liquid => Imposed::Liquid,
            FeedPhase::Gas => Imposed::Gas,
        };
        Ok(self.nh3_tp(Output::Hmolar, t_k, p_bar, ph)? / 1000.0
            + self.nh3_anchor_offset_kj_mol()?)
    }

    /// `nh3_liquid_molar_volume_m3_mol(T, P)`.
    pub fn nh3_liquid_molar_volume_m3_mol(&self, t_k: f64, p_bar: f64) -> Result<f64, EngineError> {
        Ok(1.0 / self.nh3_tp(Output::Dmolar, t_k, p_bar, Imposed::Liquid)?)
    }

    fn water_liquid_params(&self) -> Result<(f64, f64), EngineError> {
        self.water
            .get_or_init(|| {
                let hv = self.q(Query::tq(Fluid::Water, Output::Hmolar, T0_K, 1.0))?;
                let hl = self.q(Query::tq(Fluid::Water, Output::Hmolar, T0_K, 0.0))?;
                let cpl = self.q(Query::tq(Fluid::Water, Output::Cpmolar, T0_K, 0.0))?;
                Ok(((hv - hl) / 1000.0, cpl / 1000.0))
            })
            .clone()
    }

    /// `water_liquid_enthalpy_kJ_mol(T)`.
    pub fn water_liquid_enthalpy_kj_mol(&self, t_k: f64) -> Result<f64, EngineError> {
        let (dh_vap, cp_l) = self.water_liquid_params()?;
        Ok(species_enthalpy_kj_mol(Species::H2O, T0_K)? - dh_vap + cp_l * (t_k - T0_K))
    }

    /// `psat_nh3_bar(T)`.
    pub fn psat_nh3_bar(&self, t_k: f64) -> Result<f64, EngineError> {
        Ok(self.q(Query::tq(Fluid::Ammonia, Output::P, t_k, 0.0))? / 1e5)
    }

    /// `psat_water_bar(T)`.
    pub fn psat_water_bar(&self, t_k: f64) -> Result<f64, EngineError> {
        Ok(self.q(Query::tq(Fluid::Water, Output::P, t_k, 0.0))? / 1e5)
    }

    /// `bubble_point_K(P, x_NH3)` (water vapour pressure neglected).
    pub fn bubble_point_k(&self, p_bar: f64, x_nh3: f64) -> Result<f64, EngineError> {
        self.q(Query::pq(
            Fluid::Ammonia,
            Output::T,
            p_bar * 1e5 / x_nh3,
            0.0,
        ))
    }

    /// `dew_point_K(P, y)` (Raoult: `sum_i y_i P / Psat_i(T) = 1`); `y = (y_NH3, y_H2O)`.
    pub fn dew_point_k(&self, p_bar: f64, y_n: f64, y_w: f64) -> Result<f64, EngineError> {
        let t_sat_n = self.q(Query::pq(Fluid::Ammonia, Output::T, p_bar * 1e5, 1.0))?;
        if y_w <= 0.0 {
            return Ok(t_sat_n);
        }
        let t_crit_n = self.q(Query::constant(Fluid::Ammonia, Output::Tcrit))?;
        let f = |t: f64| -> Result<f64, EngineError> {
            let mut s = y_w * p_bar / self.psat_water_bar(t)?;
            if y_n > 0.0 {
                s += y_n * p_bar / self.psat_nh3_bar(py_min(t, t_crit_n - 1e-6))?;
            }
            Ok(s - 1.0)
        };
        let r = brentq_try(f, t_sat_n - 1e-9, 640.0, BrentOptions::with_xtol(1e-10))
            .map_err(brent_err)?;
        Ok(r.x)
    }

    /// `raoult_dew_sum(T, P, y)` over the condensables (y as `(species, fraction)` in dict order).
    pub fn raoult_dew_sum(
        &self,
        t_k: f64,
        p_bar: f64,
        y: &[(Species, f64)],
    ) -> Result<f64, EngineError> {
        let g = |s: Species| y.iter().find(|x| x.0 == s).map(|x| x.1).unwrap_or(0.0);
        let mut s = 0.0;
        if g(Species::H2O) > 0.0 && t_k < 647.0 {
            s += g(Species::H2O) * p_bar / self.psat_water_bar(t_k)?;
        }
        if g(Species::NH3) > 0.0 && t_k < 405.0 {
            s += g(Species::NH3) * p_bar / self.psat_nh3_bar(t_k)?;
        }
        Ok(s)
    }

    /// `feed_section_enthalpy_kW(n, T, P, phase)`; `n` in dict order, NH3 and H2O only.
    pub fn feed_section_enthalpy_kw(
        &self,
        n: &[(Species, f64)],
        t_k: f64,
        p_bar: f64,
        phase: FeedPhase,
    ) -> Result<f64, EngineError> {
        let mut h = 0.0;
        for &(s, v) in n {
            if v == 0.0 {
                continue;
            }
            match s {
                Species::NH3 => h += v * self.nh3_enthalpy_kj_mol(t_k, p_bar, phase)?,
                Species::H2O => {
                    h += v * match phase {
                        FeedPhase::Liquid => self.water_liquid_enthalpy_kj_mol(t_k)?,
                        FeedPhase::Gas => species_enthalpy_kj_mol(Species::H2O, t_k)?,
                    }
                }
                other => {
                    return Err(EngineError::Domain(format!(
                        "feed-section property basis supports NH3/H2O only, got {}",
                        other.name()
                    )));
                }
            }
        }
        Ok(h * 1000.0 / 3600.0)
    }

    /// `nh3_residual_enthalpy_kJ_mol(T, P)` (reference EOS, imposed gas phase).
    pub fn nh3_residual_enthalpy_kj_mol(&self, t_k: f64, p_bar: f64) -> Result<f64, EngineError> {
        Ok(self.nh3_tp(Output::HmolarResidual, t_k, p_bar, Imposed::Gas)? / 1000.0)
    }

    /// `feed_gas_enthalpy_kW(n, T, P)`: NASA-7 + reference-EOS NH3 residual; water ideal gas.
    pub fn feed_gas_enthalpy_kw(
        &self,
        n: &[(Species, f64)],
        t_k: f64,
        p_bar: f64,
    ) -> Result<f64, EngineError> {
        let mut h = 0.0;
        for &(s, v) in n {
            if v == 0.0 {
                continue;
            }
            match s {
                Species::NH3 => {
                    h += v
                        * (species_enthalpy_kj_mol(Species::NH3, t_k)?
                            + self.nh3_residual_enthalpy_kj_mol(t_k, p_bar)?)
                }
                Species::H2O => h += v * species_enthalpy_kj_mol(Species::H2O, t_k)?,
                other => {
                    return Err(EngineError::Domain(format!(
                        "feed-gas property basis supports NH3/H2O only, got {}",
                        other.name()
                    )));
                }
            }
        }
        Ok(h * 1000.0 / 3600.0)
    }
}

/// `gas_enthalpy_kW(n, T, P, eos)`: NASA ideal gas (+ PR residual for `eos = pr`); species with
/// a non-positive flow are dropped first.
pub fn gas_enthalpy_kw(
    n: &[(Species, f64)],
    t_k: f64,
    p_bar: f64,
    eos: Eos,
) -> Result<f64, EngineError> {
    let nn: Vec<(Species, f64)> = n.iter().copied().filter(|x| x.1 > 0.0).collect();
    if nn.is_empty() {
        return Ok(0.0);
    }
    mixture_enthalpy_kw(&nn, t_k, Some(p_bar), eos, &Kij::zero(), Alpha::Standard)
}

/// `solve_T_for_enthalpy(h_fun, H_target, T_lo, T_hi)`: brentq with `xtol = 1e-10`,
/// `rtol = 1e-14`, `maxiter = 200`.
pub fn solve_t_for_enthalpy<F>(
    mut h_fun: F,
    h_target_kw: f64,
    t_lo: f64,
    t_hi: f64,
) -> Result<f64, EngineError>
where
    F: FnMut(f64) -> Result<f64, EngineError>,
{
    let opts = BrentOptions {
        xtol: 1e-10,
        rtol: 1e-14,
        maxiter: 200,
    };
    let r = brentq_try(|t| Ok(h_fun(t)? - h_target_kw), t_lo, t_hi, opts).map_err(brent_err)?;
    Ok(r.x)
}
