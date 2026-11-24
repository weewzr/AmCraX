//! 1-D pseudo-homogeneous packed-bed plug-flow reactor (Python `reactor/pfr.py`).
//!
//! Independent variable: catalyst mass W (kg). State `u = (X, T, P, tau)`:
//!
//! ```text
//! dX/dW   = r(T, p_i) / F_NH3,0
//! dT/dW   = [ -dH_r(T) r + U (4 / D_t) (T_wall - T) / rho_bed ] / sum_i F_i cp_i(T)
//!           (isothermal: 0; adiabatic: U = 0; external: wall temperature + overall U)
//! dP/dW   = (dP/dz)_Ergun / (rho_bed A_total)
//! dtau/dW = eps_b / (rho_bed Q_actual)
//! ```
//!
//! The equations, constants, clipping (`X` in `[0, 1 - 1e-15]` inside the right-hand side, the
//! `1e-300` H2 floor of the Temkin-Pyzhev law), the H2 seed, the terminal event at 5 % of the inlet
//! pressure (state at the stop appended to the profile), the `linspace` output grid and the
//! post-processing (local equilibrium conversion, approach, Q/K, outlet, heat input, GHSV) are those
//! of the Python code. The integrator differs on purpose: Python uses SciPy LSODA (rtol 1e-8, atol
//! 1e-12); here the Dormand-Prince 5(4) of `amcrax-numerics` with [`SolverOptions`] (default rtol
//! 1e-10), so that the Rust global error is well below LSODA's and the comparison gates (outlet
//! conversion 1e-7, T 1e-4 K, P 1e-6 bar) measure the reference's own integration error.
//!
//! Input validation beyond Python (typed errors instead of NaN results or Python exceptions such as
//! "not enough values to unpack"): `W_kg > 0`, `n_points >= 2`, positive and finite bed data and
//! pressures, non-negative feed flows, a known feed species, NH3 in the feed.

use crate::error::EngineError;
use crate::kinetics::{Form, KeqBasis, KineticsRegistry, RateOpts, rate_mol_per_kgcat_s};
use crate::pyops::{fmt_g, linspace, py_max, py_min, py_sum};
use crate::species::Species;
use crate::thermo::equilibrium::{equilibrium_constant, ideal_conversion, mixture_enthalpy_kw};
use crate::thermo::nasa7::{R_J_MOL_K, species_cp_j_mol_k};
use crate::thermo::{Alpha, Eos, Kij, reaction_enthalpy_kj_mol};
use crate::transport::{NV, Transport};
use amcrax_numerics::ode::{Event, OdeError, OdeOptions, OdeStatus, dopri5};
use amcrax_numerics::roots::{BrentError, BrentOptions, brentq_try};
use serde::{Deserialize, Serialize};
use std::cell::RefCell;
use std::collections::BTreeMap;

/// kmol/h to mol/s.
pub const KMOLH_TO_MOLS: f64 = 1000.0 / 3600.0;
/// GHSV normal basis temperature (0 degC).
pub const NORMAL_T_K: f64 = 273.15;
/// GHSV normal basis pressure (1 atm).
pub const NORMAL_P_PA: f64 = 101325.0;
/// Monatomic ideal-gas cp of Ar, J/(mol K) (Python `_cp_species`).
pub const CP_AR_J_MOL_K: f64 = 20.786;
/// Bed source text of the Python module (`DEFAULT_BED_SOURCE`).
pub const DEFAULT_BED_SOURCE: &str = "kum2026heatintegrated p. 5 Table 1 (eps_b, rho_cat, dp, Din); rho_bed = (1-eps_b)*rho_cat as in Kum Table 2";
/// Default bed void fraction (kum2026heatintegrated Table 1).
pub const DEFAULT_EPS_B: f64 = 0.36;
/// Default particle density, kg/m3.
pub const DEFAULT_RHO_PARTICLE: f64 = 980.0;
/// Default particle diameter, m.
pub const DEFAULT_DP_M: f64 = 0.0006;
/// Default tube inner diameter, m.
pub const DEFAULT_TUBE_D_M: f64 = 0.126;

/// Gases of the reactor model (Python `MOLAR_MASS_kg_mol` keys).
pub const GASES: [&str; 5] = ["NH3", "H2", "N2", "H2O", "Ar"];
/// Molar masses, kg/mol (Python `MOLAR_MASS_kg_mol`).
pub const MOLAR_MASS_KG_MOL: [f64; 5] = [0.017031, 0.002016, 0.028014, 0.018015, 0.039948];
const I_NH3: usize = 0;
const I_H2: usize = 1;
const I_N2: usize = 2;
const I_H2O: usize = 3;
const I_AR: usize = 4;

fn d600() -> f64 {
    600.0
}
fn d20() -> f64 {
    20.0
}
fn d_mode() -> String {
    "isothermal".into()
}
fn d_eps() -> f64 {
    DEFAULT_EPS_B
}
fn d_rho() -> f64 {
    DEFAULT_RHO_PARTICLE
}
fn d_dp() -> f64 {
    DEFAULT_DP_M
}
fn d_tube() -> f64 {
    DEFAULT_TUBE_D_M
}
fn d_one() -> u32 {
    1
}
fn d_true() -> bool {
    true
}
fn d_keq() -> String {
    "amcrax_thermo".into()
}
fn d_seed() -> f64 {
    1e-6
}
fn d_points() -> usize {
    201
}

/// Inputs of [`simulate_pfr`] (Python keyword arguments of `simulate_pfr`, same names and defaults).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PfrInput {
    pub catalyst_id: String,
    /// Total catalyst over all tubes, kg.
    #[serde(rename = "W_kg")]
    pub w_kg: f64,
    #[serde(rename = "T_in_C", default = "d600")]
    pub t_in_c: f64,
    #[serde(rename = "P_in_bar", default = "d20")]
    pub p_in_bar: f64,
    /// Feed, kmol/h (default `{"NH3": 99.8, "H2O": 0.2}`).
    #[serde(default)]
    pub feed_kmol_h: Option<BTreeMap<String, f64>>,
    /// `isothermal` | `adiabatic` | `external`.
    #[serde(default = "d_mode")]
    pub mode: String,
    #[serde(rename = "T_wall_C", default)]
    pub t_wall_c: Option<f64>,
    #[serde(rename = "U_W_m2K", default)]
    pub u_w_m2k: Option<f64>,
    #[serde(default = "d_eps")]
    pub eps_b: f64,
    #[serde(default = "d_rho")]
    pub rho_particle_kg_m3: f64,
    #[serde(default = "d_dp")]
    pub dp_m: f64,
    #[serde(default = "d_tube")]
    pub tube_inner_diameter_m: f64,
    #[serde(default = "d_one")]
    pub n_tubes: u32,
    #[serde(default = "d_true")]
    pub pressure_drop: bool,
    #[serde(default)]
    pub approach_factor: Option<bool>,
    /// `amcrax_thermo` (default) or `published` (Kum law only).
    #[serde(default = "d_keq")]
    pub keq_basis: String,
    #[serde(default = "d_seed")]
    pub x_seed: f64,
    #[serde(default = "d_points")]
    pub n_points: usize,
}

impl PfrInput {
    /// The Python defaults for `catalyst_id` and `w_kg`.
    pub fn new(catalyst_id: &str, w_kg: f64) -> PfrInput {
        PfrInput {
            catalyst_id: catalyst_id.to_string(),
            w_kg,
            t_in_c: 600.0,
            p_in_bar: 20.0,
            feed_kmol_h: None,
            mode: d_mode(),
            t_wall_c: None,
            u_w_m2k: None,
            eps_b: DEFAULT_EPS_B,
            rho_particle_kg_m3: DEFAULT_RHO_PARTICLE,
            dp_m: DEFAULT_DP_M,
            tube_inner_diameter_m: DEFAULT_TUBE_D_M,
            n_tubes: 1,
            pressure_drop: true,
            approach_factor: None,
            keq_basis: d_keq(),
            x_seed: 1e-6,
            n_points: 201,
        }
    }
}

/// Settings of the DOPRI5 integration (not part of the Python inputs).
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct SolverOptions {
    pub rtol: f64,
    /// Absolute tolerances of X, T (K), P (bar), tau (s).
    pub atol: [f64; 4],
    /// Step-attempt guard of the integrator.
    pub max_attempts: usize,
    /// Accepted steps above which the case is reported as stiff for DOPRI5.
    pub stiff_steps: usize,
}

impl Default for SolverOptions {
    fn default() -> Self {
        SolverOptions {
            rtol: 1e-10,
            atol: [1e-13, 1e-9, 1e-11, 1e-12],
            max_attempts: 2_000_000,
            stiff_steps: 5_000,
        }
    }
}

/// Integration statistics.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct SolverStats {
    pub method: &'static str,
    pub rtol: f64,
    pub nfev: usize,
    pub n_steps: usize,
    pub n_rejected: usize,
    /// `n_steps > SolverOptions::stiff_steps`.
    pub stiff: bool,
}

/// Outlet block (Python `PFRResult.outlet`).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Outlet {
    pub conversion: f64,
    #[serde(rename = "T_C")]
    pub t_c: f64,
    #[serde(rename = "P_bar")]
    pub p_bar: f64,
    pub pressure_drop_bar: f64,
    #[serde(rename = "X_eq_outlet")]
    pub x_eq_outlet: f64,
    pub approach_to_equilibrium: f64,
    pub y: BTreeMap<String, f64>,
    pub flows_kmol_h: BTreeMap<String, f64>,
    #[serde(rename = "H2_kmol_h")]
    pub h2_kmol_h: f64,
    #[serde(rename = "heat_input_kW")]
    pub heat_input_kw: f64,
    pub residence_time_s: f64,
    #[serde(rename = "W_reached_kg")]
    pub w_reached_kg: f64,
    #[serde(rename = "W_requested_kg")]
    pub w_requested_kg: f64,
    pub hydraulic_limit: bool,
}

/// Result of [`simulate_pfr`] (Python `PFRResult`; NaN serialises as JSON null).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct PfrResult {
    pub catalyst_id: String,
    pub mode: String,
    #[serde(rename = "W_kg")]
    pub w_kg: Vec<f64>,
    pub conversion: Vec<f64>,
    #[serde(rename = "T_K")]
    pub t_k: Vec<f64>,
    #[serde(rename = "P_bar")]
    pub p_bar: Vec<f64>,
    pub y: BTreeMap<String, Vec<f64>>,
    pub rate_mol_per_kgcat_s: Vec<f64>,
    #[serde(rename = "X_eq_local")]
    pub x_eq_local: Vec<f64>,
    pub approach_to_equilibrium: Vec<f64>,
    #[serde(rename = "Q_over_K")]
    pub q_over_k: Vec<f64>,
    pub residence_time_s: Vec<f64>,
    pub outlet: Outlet,
    #[serde(rename = "W_over_F_kg_s_per_mol_NH3")]
    pub w_over_f_kg_s_per_mol_nh3: f64,
    #[serde(rename = "GHSV_h_inv")]
    pub ghsv_h_inv: f64,
    pub bed_volume_m3: f64,
    pub inputs: PfrInput,
    pub assumptions: Vec<String>,
    pub source: String,
    pub solver: SolverStats,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Mode {
    Isothermal,
    Adiabatic,
    External { t_w_k: f64, u: f64 },
}

/// Prepared case (validated inputs and derived constants).
struct Case<'a> {
    reg: &'a KineticsRegistry,
    inp: &'a PfrInput,
    form: Form,
    present: [bool; 5],
    f_feed: [f64; 5],
    f0: f64,
    feed_kmol_h: [f64; 5],
    mode: Mode,
    rho_bed: f64,
    a_tot: f64,
    g_flux: f64,
    keq: KeqBasis,
}

fn domain(msg: impl Into<String>) -> EngineError {
    EngineError::Domain(msg.into())
}

fn finite_pos(v: f64, name: &str) -> Result<(), EngineError> {
    if v.is_finite() && v > 0.0 {
        Ok(())
    } else {
        Err(domain(format!("{name} must be finite and > 0 (got {v})")))
    }
}

fn species_of(i: usize) -> Species {
    match i {
        I_NH3 => Species::NH3,
        I_H2 => Species::H2,
        I_N2 => Species::N2,
        I_H2O => Species::H2O,
        _ => Species::O2,
    }
}

impl<'a> Case<'a> {
    fn new(reg: &'a KineticsRegistry, inp: &'a PfrInput) -> Result<Case<'a>, EngineError> {
        let mode = match inp.mode.as_str() {
            "isothermal" => Mode::Isothermal,
            "adiabatic" => Mode::Adiabatic,
            "external" => match (inp.t_wall_c, inp.u_w_m2k) {
                (Some(tw), Some(u)) => Mode::External {
                    t_w_k: tw + 273.15,
                    u,
                },
                _ => return Err(domain("external mode requires T_wall_C and U_W_m2K")),
            },
            _ => return Err(domain("mode must be isothermal | adiabatic | external")),
        };
        let cat = reg.get(&inp.catalyst_id)?;
        finite_pos(inp.w_kg, "W_kg")?;
        if inp.n_points < 2 {
            return Err(domain("n_points must be >= 2"));
        }
        if !inp.p_in_bar.is_finite() || inp.p_in_bar <= 0.0 {
            return Err(domain(format!(
                "total pressure must be > 0 (P_in_bar = {})",
                inp.p_in_bar
            )));
        }
        if !inp.t_in_c.is_finite() {
            return Err(domain("T_in_C must be finite"));
        }
        if !(inp.eps_b > 0.0 && inp.eps_b < 1.0) {
            return Err(domain(format!(
                "eps_b must lie in (0, 1) (got {})",
                inp.eps_b
            )));
        }
        finite_pos(inp.rho_particle_kg_m3, "rho_particle_kg_m3")?;
        finite_pos(inp.dp_m, "dp_m")?;
        finite_pos(inp.tube_inner_diameter_m, "tube_inner_diameter_m")?;
        if inp.n_tubes == 0 {
            return Err(domain("n_tubes must be >= 1"));
        }
        let keq = KeqBasis::from_python(&inp.keq_basis)?;
        let mut feed_kmol_h = [0.0; 5];
        match &inp.feed_kmol_h {
            None => {
                feed_kmol_h[I_NH3] = 99.8;
                feed_kmol_h[I_H2O] = 0.2;
            }
            Some(m) => {
                for (k, v) in m {
                    let i = GASES.iter().position(|g| g == k).ok_or_else(|| {
                        domain(format!(
                            "feed species {k:?} is not modelled by the reactor (known: {GASES:?})"
                        ))
                    })?;
                    if !v.is_finite() || *v < 0.0 {
                        return Err(domain(format!("feed flow of {k} must be finite and >= 0")));
                    }
                    feed_kmol_h[i] = *v;
                }
            }
        }
        let mut present = [false; 5];
        let mut f_feed = [0.0; 5];
        for i in 0..5 {
            if feed_kmol_h[i] > 0.0 {
                present[i] = true;
                f_feed[i] = feed_kmol_h[i] * KMOLH_TO_MOLS;
            }
        }
        if !present[I_NH3] {
            return Err(domain("the feed must contain NH3"));
        }
        present[I_N2] = true;
        present[I_H2] = true;
        let f0 = f_feed[I_NH3];
        let m_dot = py_sum(
            (0..5)
                .filter(|&i| present[i])
                .map(|i| f_feed[i] * MOLAR_MASS_KG_MOL[i]),
        );
        let rho_bed = (1.0 - inp.eps_b) * inp.rho_particle_kg_m3;
        let a_tot =
            f64::from(inp.n_tubes) * std::f64::consts::PI * inp.tube_inner_diameter_m.powf(2.0)
                / 4.0;
        Ok(Case {
            reg,
            inp,
            form: cat.form,
            present,
            f_feed,
            f0,
            feed_kmol_h,
            mode,
            rho_bed,
            a_tot,
            g_flux: m_dot / a_tot,
            keq,
        })
    }

    /// Molar flows (mol/s) at conversion `x` (Python `_flows`).
    fn flows(&self, x: f64) -> [f64; 5] {
        let mut f = self.f_feed;
        f[I_NH3] = self.f0 * (1.0 - x);
        f[I_N2] = self.f_feed[I_N2] + 0.5 * self.f0 * x;
        f[I_H2] = self.f_feed[I_H2] + 1.5 * self.f0 * x;
        f
    }

    fn total(&self, v: &[f64; 5]) -> f64 {
        py_sum((0..5).filter(|&i| self.present[i]).map(|i| v[i]))
    }

    /// `(F, F_total, y)`.
    fn state(&self, x: f64) -> ([f64; 5], f64, [f64; 5]) {
        let f = self.flows(x);
        let ft = self.total(&f);
        let mut y = [0.0; 5];
        for i in 0..5 {
            if self.present[i] {
                y[i] = f[i] / ft;
            }
        }
        (f, ft, y)
    }

    fn pressures(&self, y: &[f64; 5], p: f64) -> Vec<(&'static str, f64)> {
        (0..5)
            .filter(|&i| self.present[i])
            .map(|i| (GASES[i], y[i] * p))
            .collect()
    }

    fn rate(&self, t: f64, pp: &[(&str, f64)]) -> Result<f64, EngineError> {
        rate_mol_per_kgcat_s(
            self.reg,
            &self.inp.catalyst_id,
            t,
            pp,
            RateOpts {
                approach_factor: self.inp.approach_factor,
                keq_basis: self.keq,
                param_overrides: None,
            },
        )
    }

    fn cp(&self, i: usize, t: f64) -> Result<f64, EngineError> {
        if i == I_AR {
            return Ok(CP_AR_J_MOL_K);
        }
        species_cp_j_mol_k(species_of(i), t)
    }

    /// Ideal-gas equilibrium conversion of the feed (Python `_eq_conversion`: Ar passed as O2).
    fn eq_conversion(&self, t_k: f64, p_bar: f64) -> Result<f64, EngineError> {
        let fe = &self.feed_kmol_h;
        let comp = [fe[I_NH3], fe[I_H2], fe[I_N2], fe[I_H2O], fe[I_AR]];
        ideal_conversion(t_k, p_bar, &comp)
    }

    /// Enthalpy flow, kW, of flows in kmol/h (Python `_enthalpy_kW`).
    fn enthalpy_kw(&self, n: &[f64; 5], t_k: f64) -> Result<f64, EngineError> {
        let list: Vec<(Species, f64)> = (0..5)
            .filter(|&i| self.present[i] && i != I_AR)
            .map(|i| (species_of(i), n[i]))
            .collect();
        let h = mixture_enthalpy_kw(&list, t_k, None, Eos::Ideal, &Kij::zero(), Alpha::Standard)?;
        Ok(h + n[I_AR] * 20.786e-3 * (t_k - 298.15) / 3.6)
    }

    /// Right-hand side `du/dW` (Python `rhs`).
    fn rhs(&self, u: &[f64; 4]) -> Result<[f64; 4], EngineError> {
        let inp = self.inp;
        let (t, p) = (u[1], u[2]);
        let xv = py_min(py_max(u[0], 0.0), 1.0 - 1e-15);
        let (f, ft, y) = self.state(xv);
        let mut pp = self.pressures(&y, p);
        if self.form == Form::TemkinPyzhev
            && let Some(h) = pp.iter_mut().find(|q| q.0 == "H2")
            && h.1 <= 0.0
        {
            h.1 = 1e-300;
        }
        let r = self.rate(t, &pp)?;
        let dx = r / self.f0;
        let dt = match self.mode {
            Mode::Isothermal => 0.0,
            _ => {
                let mut terms = Vec::with_capacity(5);
                for i in (0..5).filter(|&i| self.present[i]) {
                    terms.push(f[i] * self.cp(i, t)?);
                }
                let fcp = py_sum(terms);
                let mut q = -reaction_enthalpy_kj_mol(t)? * 1e3 * r;
                if let Mode::External { t_w_k, u } = self.mode {
                    q += u * (4.0 / inp.tube_inner_diameter_m) * (t_w_k - t) / self.rho_bed;
                }
                q / fcp
            }
        };
        let eps = inp.eps_b;
        let dp = if inp.pressure_drop {
            let m = py_sum(
                (0..5)
                    .filter(|&i| self.present[i])
                    .map(|i| y[i] * MOLAR_MASS_KG_MOL[i]),
            );
            let rho_g = p * 1e5 * m / (R_J_MOL_K * t);
            let mu = gas_viscosity_pa_s(t, &y)?;
            let g = self.g_flux;
            let dpdz = -(g / (rho_g * inp.dp_m))
                * ((1.0 - eps) / eps.powf(3.0))
                * (150.0 * (1.0 - eps) * mu / inp.dp_m + 1.75 * g);
            dpdz / (self.rho_bed * self.a_tot) / 1e5
        } else {
            0.0
        };
        let q = ft * R_J_MOL_K * t / (p * 1e5);
        let dtau = eps / (self.rho_bed * q);
        Ok([dx, dt, dp, dtau])
    }
}

/// Mixture viscosity of the reactor gas (Python `gas_viscosity_Pa_s`: Ar mapped to Cantera's AR).
pub fn gas_viscosity_pa_s(t_k: f64, y: &[f64; 5]) -> Result<f64, EngineError> {
    let mut x = [0.0; NV];
    x[0] = py_max(y[I_NH3], 0.0);
    x[1] = py_max(y[I_H2], 0.0);
    x[2] = py_max(y[I_N2], 0.0);
    x[3] = py_max(y[I_H2O], 0.0);
    if y[I_AR] > 0.0 {
        x[5] = y[I_AR];
    }
    Transport::embedded().mixture_viscosity(t_k, &x)
}

/// Integrate the packed-bed PFR from W = 0 to `inp.w_kg` (Python `simulate_pfr`).
pub fn simulate_pfr(
    reg: &KineticsRegistry,
    inp: &PfrInput,
    sopt: &SolverOptions,
) -> Result<PfrResult, EngineError> {
    let cs = Case::new(reg, inp)?;
    let t_in = inp.t_in_c + 273.15;
    let mut assumptions = Vec::new();
    let mut x0 = 0.0;
    if cs.form == Form::TemkinPyzhev && cs.f_feed[I_H2] <= 0.0 {
        x0 = inp.x_seed;
        assumptions.push(format!(
            "numerical: H2 seed, integration starts at X0={} (rate singular at p_H2=0)",
            fmt_g(inp.x_seed, 6)
        ));
    }
    let on = inp.approach_factor.unwrap_or(true);
    match cs.form {
        Form::TakahashiMicrokinetic => assumptions.push(format!(
            "AmCraX extension: equilibrium approach factor (1-Q/K) {}",
            if on { "ON" } else { "OFF" }
        )),
        Form::LhhwLucentini => assumptions.push(format!(
            "AmCraX extension: equilibrium approach factor (1-Q/K) {} (Lucentini LHHW)",
            if on { "ON" } else { "OFF" }
        )),
        Form::TemkinPyzhev => assumptions.push(format!("Kum Keq basis: {}", inp.keq_basis)),
    }
    let defaults = (inp.eps_b, inp.rho_particle_kg_m3, inp.dp_m)
        == (DEFAULT_EPS_B, DEFAULT_RHO_PARTICLE, DEFAULT_DP_M);
    assumptions.push(format!(
        "bed: {DEFAULT_BED_SOURCE}{}",
        if defaults {
            " (defaults used)"
        } else {
            " (user values)"
        }
    ));
    assumptions.push(
        "effectiveness factor = 1; no radial gradients; no axial dispersion (see module docstring)"
            .into(),
    );

    let rhs_error: RefCell<Option<EngineError>> = RefCell::new(None);
    let mut rhs = |_w: f64, u: &[f64; 4], du: &mut [f64; 4]| -> Result<(), String> {
        match cs.rhs(u) {
            Ok(v) => {
                *du = v;
                Ok(())
            }
            Err(e) => {
                let msg = e.to_string();
                *rhs_error.borrow_mut() = Some(e);
                Err(msg)
            }
        }
    };
    let p_stop = 0.05 * inp.p_in_bar;
    let mut events = [Event::new(
        move |_w: f64, u: &[f64; 4]| u[2] - p_stop,
        true,
        0.0,
    )];
    let w_eval = linspace(0.0, inp.w_kg, inp.n_points);
    let opts = OdeOptions {
        rtol: sopt.rtol,
        atol: sopt.atol,
        first_step: None,
        max_step: f64::INFINITY,
        max_attempts: sopt.max_attempts,
    };
    let sol = dopri5(
        &mut rhs,
        (0.0, inp.w_kg),
        [x0, t_in, inp.p_in_bar, 0.0],
        Some(&w_eval),
        &mut events,
        &opts,
    );
    let sol = match sol {
        Ok(s) => s,
        Err(e) => {
            if let Some(inner) = rhs_error.borrow_mut().take() {
                return Err(inner);
            }
            return Err(match e {
                OdeError::TooManySteps { t, attempts } => EngineError::Integration(format!(
                    "PFR integration failed: more than {attempts} DOPRI5 step attempts at W = {t} kg \
                     (stiff for the explicit method)"
                )),
                other => EngineError::Integration(format!("PFR integration failed: {other}")),
            });
        }
    };
    let mut ws = sol.t.clone();
    let mut ys = sol.y.clone();
    let hydraulic = sol.status == OdeStatus::TerminalEvent
        && sol.t_events.first().is_some_and(|v| !v.is_empty());
    if hydraulic {
        let w_stop = sol.t_events[0][0];
        let y_stop = sol.y_events[0][0];
        if ws.is_empty() || w_stop > ws[ws.len() - 1] {
            ws.push(w_stop);
            ys.push(y_stop);
        }
        assumptions.push(format!(
            "integration stopped (hydraulic limit): pressure fell to 5 % of inlet at W = {} kg of the \
             requested {} kg (bed too long/narrow); outlet = state at the stop",
            fmt_g(w_stop, 6),
            fmt_g(inp.w_kg, 6)
        ));
    }
    if ws.is_empty() {
        return Err(EngineError::Integration(
            "PFR integration produced no output point".into(),
        ));
    }
    let mut yprof: BTreeMap<String, Vec<f64>> = BTreeMap::new();
    let (mut rates, mut xeq, mut appr, mut qk) = (Vec::new(), Vec::new(), Vec::new(), Vec::new());
    for u in &ys {
        let (xv, t, p) = (py_min(py_max(u[0], 0.0), 1.0), u[1], u[2]);
        let (_, _, y) = cs.state(xv);
        for i in (0..5).filter(|&i| cs.present[i]) {
            yprof.entry(GASES[i].to_string()).or_default().push(y[i]);
        }
        let pp = cs.pressures(&y, p);
        rates.push(if cs.form == Form::TemkinPyzhev && y[I_H2] <= 0.0 {
            f64::NAN
        } else {
            cs.rate(t, &pp)?
        });
        let eq = cs.eq_conversion(t, p)?;
        xeq.push(eq);
        appr.push(if eq > 0.0 { xv / eq } else { f64::NAN });
        let (pn2, ph2, pnh3) = (y[I_N2] * p, y[I_H2] * p, y[I_NH3] * p);
        let qv = if pnh3 > 0.0 {
            pn2.powf(0.5) * ph2.powf(1.5) / pnh3
        } else {
            f64::INFINITY
        };
        qk.push(qv / equilibrium_constant(t)?);
    }
    let last = ys[ys.len() - 1];
    let (x_out, t_out, p_out, tau_out) = (last[0], last[1], last[2], last[3]);
    let v_bed = inp.w_kg / cs.rho_bed;
    let fn_tot = cs.total(&cs.f_feed);
    let q_normal = fn_tot * R_J_MOL_K * NORMAL_T_K / NORMAL_P_PA;
    let f_out = cs.flows(x_out);
    let mut fout_kmol = [0.0; 5];
    let mut fin_kmol = [0.0; 5];
    let mut flows_map = BTreeMap::new();
    for i in (0..5).filter(|&i| cs.present[i]) {
        fout_kmol[i] = f_out[i] / KMOLH_TO_MOLS;
        fin_kmol[i] = cs.f_feed[i] / KMOLH_TO_MOLS;
        flows_map.insert(GASES[i].to_string(), fout_kmol[i]);
    }
    let heat = cs.enthalpy_kw(&fout_kmol, t_out)? - cs.enthalpy_kw(&fin_kmol, t_in)?;
    let outlet = Outlet {
        conversion: x_out,
        t_c: t_out - 273.15,
        p_bar: p_out,
        pressure_drop_bar: inp.p_in_bar - p_out,
        x_eq_outlet: xeq[xeq.len() - 1],
        approach_to_equilibrium: appr[appr.len() - 1],
        y: yprof
            .iter()
            .map(|(k, v)| (k.clone(), v[v.len() - 1]))
            .collect(),
        flows_kmol_h: flows_map,
        h2_kmol_h: f_out[I_H2] / KMOLH_TO_MOLS,
        heat_input_kw: heat,
        residence_time_s: tau_out,
        w_reached_kg: ws[ws.len() - 1],
        w_requested_kg: inp.w_kg,
        hydraulic_limit: hydraulic,
    };
    Ok(PfrResult {
        catalyst_id: inp.catalyst_id.clone(),
        mode: inp.mode.clone(),
        conversion: ys.iter().map(|u| u[0]).collect(),
        t_k: ys.iter().map(|u| u[1]).collect(),
        p_bar: ys.iter().map(|u| u[2]).collect(),
        residence_time_s: ys.iter().map(|u| u[3]).collect(),
        w_kg: ws,
        y: yprof,
        rate_mol_per_kgcat_s: rates,
        x_eq_local: xeq,
        approach_to_equilibrium: appr,
        q_over_k: qk,
        outlet,
        w_over_f_kg_s_per_mol_nh3: inp.w_kg / cs.f0,
        ghsv_h_inv: if v_bed > 0.0 {
            q_normal * 3600.0 / v_bed
        } else {
            f64::INFINITY
        },
        bed_volume_m3: v_bed,
        inputs: inp.clone(),
        assumptions,
        source: "rust_model".into(),
        solver: SolverStats {
            method: "DOPRI5 (amcrax-numerics)",
            rtol: sopt.rtol,
            nfev: sol.nfev,
            n_steps: sol.n_steps,
            n_rejected: sol.n_rejected,
            stiff: sol.n_steps > sopt.stiff_steps,
        },
    })
}

/// Target of [`catalyst_mass_for_conversion`].
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Target {
    /// Absolute conversion.
    Conversion(f64),
    /// Fraction of the inlet equilibrium conversion.
    FractionOfEquilibrium(f64),
}

/// Result of [`catalyst_mass_for_conversion`] (Python `return_details=True`).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct MassResult {
    /// NaN when not reachable.
    #[serde(rename = "W_kg")]
    pub w_kg: f64,
    pub reachable: bool,
    pub reason: Option<String>,
    pub target_conversion: f64,
    pub hydraulic_limit: bool,
    #[serde(rename = "W_reached_kg")]
    pub w_reached_kg: Option<f64>,
    #[serde(rename = "X_reached")]
    pub x_reached: Option<f64>,
    /// PFR solves done.
    pub n_pfr: usize,
}

fn brent_engine(e: BrentError<EngineError>) -> EngineError {
    match e {
        BrentError::Function(e) => e,
        BrentError::NotConverged(r) => EngineError::Numerical(format!(
            "brentq failed to converge after {} iterations",
            r.iterations
        )),
        BrentError::SignError { fa, fb } => {
            EngineError::Bracket(format!("f(a) = {fa:e}, f(b) = {fb:e}"))
        }
        other => EngineError::Domain(other.to_string()),
    }
}

/// Catalyst mass at which the conversion first reaches the target (Python
/// `catalyst_mass_for_conversion`: trial masses from 1e-3 kg growing x4, last clamped to
/// `w_max_kg`; a hydraulic stop is evaluated at the stop; brentq with `xtol = 1e-6 W`,
/// `rtol = 1e-6` on the outlet conversion of 2-point runs).
pub fn catalyst_mass_for_conversion(
    reg: &KineticsRegistry,
    base: &PfrInput,
    target: Target,
    w_max_kg: f64,
    sopt: &SolverOptions,
) -> Result<MassResult, EngineError> {
    let target_conversion = match target {
        Target::Conversion(x) => x,
        Target::FractionOfEquilibrium(fr) => {
            let probe = PfrInput {
                w_kg: 1.0,
                ..base.clone()
            };
            let cs = Case::new(reg, &probe)?;
            fr * cs.eq_conversion(base.t_in_c + 273.15, base.p_in_bar)?
        }
    };
    let n_pfr = RefCell::new(0usize);
    let outlet = |w: f64| -> Result<Outlet, EngineError> {
        *n_pfr.borrow_mut() += 1;
        let inp = PfrInput {
            w_kg: w,
            n_points: 2,
            ..base.clone()
        };
        Ok(simulate_pfr(reg, &inp, sopt)?.outlet)
    };
    let done = |w: f64,
                reason: Option<String>,
                hyd: bool,
                w_r: Option<f64>,
                x_r: Option<f64>|
     -> MassResult {
        MassResult {
            w_kg: w,
            reachable: reason.is_none(),
            reason,
            target_conversion,
            hydraulic_limit: hyd,
            w_reached_kg: w_r,
            x_reached: x_r,
            n_pfr: *n_pfr.borrow(),
        }
    };
    let mut w = py_min(1e-3, w_max_kg);
    let mut lo = 0.0;
    loop {
        let o = outlet(w)?;
        if o.hydraulic_limit {
            let (w_r, x_r) = (o.w_reached_kg, o.conversion);
            if x_r < target_conversion {
                return Ok(done(
                    f64::NAN,
                    Some(format!(
                        "target X = {} not reached before the hydraulic limit (pressure < 5 % of inlet \
                         at W = {} kg, X = {} there)",
                        fmt_g(target_conversion, 6),
                        fmt_g(w_r, 6),
                        fmt_g(x_r, 6)
                    )),
                    true,
                    Some(w_r),
                    Some(x_r),
                ));
            }
            w = w_r;
            break;
        }
        if o.conversion >= target_conversion {
            break;
        }
        lo = w;
        if w >= w_max_kg {
            return Ok(done(
                f64::NAN,
                Some(format!(
                    "target X = {} not reached within W_max_kg = {} kg (X = {} there)",
                    fmt_g(target_conversion, 6),
                    fmt_g(w_max_kg, 6),
                    fmt_g(o.conversion, 6)
                )),
                false,
                Some(o.w_reached_kg),
                Some(o.conversion),
            ));
        }
        w = py_min(4.0 * w, w_max_kg);
    }
    let f =
        |ww: f64| -> Result<f64, EngineError> { Ok(outlet(ww)?.conversion - target_conversion) };
    if lo == 0.0 {
        lo = 1e-9;
        if f(lo)? >= 0.0 {
            return Ok(done(lo, None, false, None, None));
        }
    }
    let f_hi = f(w)?;
    if f_hi < 0.0 {
        return Ok(done(w, None, false, None, None));
    }
    let opts = BrentOptions {
        xtol: 1e-6 * w,
        rtol: 1e-6,
        maxiter: 100,
    };
    let r = brentq_try(f, lo, w, opts).map_err(brent_engine)?;
    Ok(done(r.x, None, false, None, None))
}

/// Result of [`temperature_for_conversion`].
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct TemperatureResult {
    /// The target lies between the bracket ends.
    pub ok: bool,
    /// NaN when not bracketed.
    #[serde(rename = "T_required_C")]
    pub t_required_c: f64,
    pub iterations: u32,
}

/// Inlet temperature (degC) of an isothermal PFR at which the outlet conversion equals
/// `x_target` (`scripts/research/kinetics_studies.py`, study 5: bracket `[t_lo, t_hi]` degC checked
/// as `g(lo) < 0 < g(hi)` (an error at either end counts as not bracketed), then brentq with
/// `xtol` K on 2-point runs of `base` with `T_in_C` replaced).
pub fn temperature_for_conversion(
    reg: &KineticsRegistry,
    base: &PfrInput,
    x_target: f64,
    t_lo: f64,
    t_hi: f64,
    xtol: f64,
    sopt: &SolverOptions,
) -> Result<TemperatureResult, EngineError> {
    let g = |t: f64| -> Result<f64, EngineError> {
        let inp = PfrInput {
            t_in_c: t,
            n_points: 2,
            ..base.clone()
        };
        Ok(simulate_pfr(reg, &inp, sopt)?.outlet.conversion - x_target)
    };
    let ok = match (g(t_lo), g(t_hi)) {
        (Ok(a), Ok(b)) => a < 0.0 && 0.0 < b,
        _ => false,
    };
    if !ok {
        return Ok(TemperatureResult {
            ok: false,
            t_required_c: f64::NAN,
            iterations: 0,
        });
    }
    let r = brentq_try(g, t_lo, t_hi, BrentOptions::with_xtol(xtol)).map_err(brent_engine)?;
    Ok(TemperatureResult {
        ok: true,
        t_required_c: r.x,
        iterations: r.iterations,
    })
}

#[cfg(all(test, feature = "yaml"))]
mod tests {
    use super::*;

    #[test]
    fn validation_errors_are_typed() {
        let reg = KineticsRegistry::embedded();
        let s = SolverOptions::default();
        let mut i = PfrInput::new("ru_takahashi_microkinetic", 10.0);
        i.p_in_bar = -1.0;
        assert!(matches!(
            simulate_pfr(reg, &i, &s),
            Err(EngineError::Domain(_))
        ));
        let mut i = PfrInput::new("ru_takahashi_microkinetic", 0.0);
        i.n_points = 3;
        assert!(matches!(
            simulate_pfr(reg, &i, &s),
            Err(EngineError::Domain(_))
        ));
        let mut i = PfrInput::new("ru_takahashi_microkinetic", 10.0);
        i.t_in_c = 6000.0;
        i.pressure_drop = false;
        assert!(matches!(
            simulate_pfr(reg, &i, &s),
            Err(EngineError::Domain(_))
        ));
        let i = PfrInput::new("no_such", 10.0);
        assert!(matches!(
            simulate_pfr(reg, &i, &s),
            Err(EngineError::Domain(_))
        ));
    }
}
