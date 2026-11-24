//! Unit conventions and the conversion constants used by the Python code (same values, same
//! names). Quantities are plain `f64` with the unit in the identifier (`t_k`, `p_bar`,
//! `n_kmol_h`, `q_kw`, ...).
//!
//! The gas constant is not a single value in Python: `thermodynamics/nasa7.py` uses the exact
//! CODATA 2018 value ([`R_J_MOL_K_NASA7`]); the kinetics registry uses the value stored in
//! `backend/amcrax/data/kinetics.yaml`, which the engine will read from that file (stage 2), not
//! retype.

/// 0 degC in kelvin (`process_model/flowsheet.py: K0`).
pub const K0: f64 = 273.15;
/// Thermochemical reference temperature in kelvin (`process_model/properties.py: T0_K`).
pub const T0_K: f64 = 298.15;
/// Standard pressure in bar (reference state of the equilibrium constant).
pub const P_STD_BAR: f64 = 1.0;
/// bar to pascal.
pub const BAR_TO_PA: f64 = 1e5;
/// kmol/h to mol/s (`reactor/pfr.py: KMOLH_TO_MOLS = 1000.0 / 3600.0`).
pub const KMOLH_TO_MOLS: f64 = 1000.0 / 3600.0;
/// kW to W.
pub const KW_TO_W: f64 = 1e3;
/// Gas constant of the NASA-7 thermodynamics, J/(mol K) (`thermodynamics/nasa7.py: R_J_molK`).
pub const R_J_MOL_K_NASA7: f64 = 8.314462618;

/// degC to K.
#[inline]
pub fn c_to_k(t_c: f64) -> f64 {
    t_c + K0
}

/// K to degC.
#[inline]
pub fn k_to_c(t_k: f64) -> f64 {
    t_k - K0
}

/// bar to Pa.
#[inline]
pub fn bar_to_pa(p_bar: f64) -> f64 {
    p_bar * BAR_TO_PA
}

/// kmol/h to mol/s.
#[inline]
pub fn kmol_h_to_mol_s(n_kmol_h: f64) -> f64 {
    n_kmol_h * KMOLH_TO_MOLS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn conversions() {
        assert_eq!(c_to_k(0.0), 273.15);
        assert!((k_to_c(c_to_k(550.0)) - 550.0).abs() < 1e-12);
        assert_eq!(bar_to_pa(1.0), 1e5);
        assert!((kmol_h_to_mol_s(3.6) - 1.0).abs() < 1e-15);
    }
}
