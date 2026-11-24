//! AmCraX science engine.
//!
//! Stage 0 of the Rust migration provides the module layout, the shared data types and the unit
//! conventions; the science is ported module by module in later stages, each gated against the
//! Python reference (see `rust/README.md`).
//!
//! Conventions:
//!
//! * Quantities are plain `f64` with the unit in the identifier, using the Python names
//!   (`t_k`, `p_bar`, `n_kmol_h`, `w_kg`, `rate_mol_per_kgcat_s`, `lcoh_usd_per_kg`), so the
//!   port can be reviewed line by line against the Python source. Conversions are in [`units`].
//! * Compositions are [`Comp`] arrays indexed by [`Species`] in the Python `COMPONENTS` order.
//! * Fallible functions return `Result<_, EngineError>`; the library does not panic on user input.
//! * Reference data are read from the repository (`AMCRAX_ROOT`), never copied; every file read
//!   carries its SHA-256 for provenance.

pub mod carbon;
pub mod data;
pub mod economics;
pub mod enduse;
pub mod error;
pub mod heat;
pub mod kinetics;
pub mod lca;
pub mod odata;
pub mod optim;
pub mod process;
pub mod props;
pub mod provenance;
pub mod pyops;
pub mod reactor;
pub mod schema;
pub mod separation;
pub mod species;
pub mod studies;
pub mod thermo;
pub mod transport;
pub mod units;
pub mod uq;
pub mod verify;

pub use error::EngineError;
pub use species::{Comp, N_SPECIES, Species};

/// Version of the engine crate (written into result provenance).
pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");

/// The numerical methods used by the engine.
pub use amcrax_numerics as numerics;
