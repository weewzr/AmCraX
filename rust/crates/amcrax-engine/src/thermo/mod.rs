//! Thermodynamics (Python `thermodynamics/`): NASA-7 heat capacity, enthalpy, entropy and Gibbs
//! energy; the equilibrium constant; ideal-gas and Peng-Robinson equilibrium; Peng-Robinson
//! fugacity, compressibility, enthalpy departure and dew points. Stage 1. Gates (against
//! `rust/golden/stage1`): 1e-12 relative for the NASA-7 functions and Kp, 1e-10 relative for
//! Peng-Robinson, 1e-10 absolute for equilibrium conversions, 1e-8 relative for dew points.

pub mod equilibrium;
pub mod nasa7;
pub mod peng_robinson;

pub use equilibrium::{
    Eos, EquilibriumResult, equilibrium_constant, mixture_enthalpy_kw, reaction_enthalpy_kj_mol,
    reaction_entropy_j_mol_k, reaction_gibbs_kj_mol, solve_equilibrium,
};
pub use nasa7::{
    Nasa7, R_J_MOL_K, species_cp_j_mol_k, species_enthalpy_kj_mol, species_entropy_j_mol_k,
    species_gibbs_kj_mol,
};
pub use peng_robinson::{Alpha, Kij};
