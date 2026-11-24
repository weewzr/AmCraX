//! Rate laws (Python `kinetics/rate_laws.py`; data `kinetics.yaml`): Takahashi
//! micro-kinetic, Temkin-Pyzhev and Lucentini LHHW forms with the approach factor `1 - Q/K`.
//! Stage 2. Gate: 1e-12 relative (closed forms; Takahashi coverages by brentq).

use serde::{Deserialize, Serialize};

/// Basis of the equilibrium constant inside a rate law (Python `keq_basis`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum KeqBasis {
    /// The correlation published with the rate law.
    #[default]
    Published,
    /// The AmCraX NASA-7 thermodynamics.
    AmcraxThermo,
}

/// Options of a rate evaluation (Python `rate_mol_per_kgcat_s` keyword arguments).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct RateOpts {
    /// Apply the approach factor `1 - Q/K` (`None`: the catalyst's registry default).
    pub approach_factor: Option<bool>,
    /// Equilibrium-constant basis.
    pub keq_basis: KeqBasis,
}
