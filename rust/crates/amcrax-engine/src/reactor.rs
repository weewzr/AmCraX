//! Plug-flow reactor (Python `reactor/pfr.py`): DOPRI5 from `amcrax-numerics` with the
//! terminal event at 5 % of the inlet pressure, Ergun pressure drop, viscosity from the exported
//! Cantera fits. Stage 2. Gate: conversion 1e-7 absolute against the stored Python results.

use serde::{Deserialize, Serialize};

/// Thermal mode of the reactor (Python `mode`).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThermalMode {
    /// Constant temperature.
    Isothermal,
    /// No heat exchange.
    Adiabatic,
    /// Heat exchange with a wall at `t_wall_c` through `u_w_m2k`.
    External { t_wall_c: f64, u_w_m2k: f64 },
}

/// Packed-bed geometry.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Bed {
    /// Bed void fraction, -.
    pub eps_b: f64,
    /// Catalyst particle density, kg/m3.
    pub rho_particle_kg_m3: f64,
    /// Particle diameter, m.
    pub dp_m: f64,
    /// Tube inner diameter, m.
    pub tube_inner_diameter_m: f64,
    /// Number of tubes.
    pub n_tubes: u32,
}
