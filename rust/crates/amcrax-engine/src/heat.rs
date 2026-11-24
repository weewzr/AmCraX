//! Heat integration (stage 4): port of Python `heat_integration/` - problem table and composite
//! curves (`pinch.py`), H-T stream extraction (`streams.py`), the pinch analysis of one
//! `SimulationResult` (`analysis.py`) and the shell-and-tube exchanger sizing, costing and
//! break-even solves (`exchanger.py`).

pub mod analysis;
pub mod exchanger;
pub mod pinch;
pub mod streams;

pub use analysis::analyse;
