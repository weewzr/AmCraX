//! Process flowsheet (stage 4): port of Python `process_model/properties.py`,
//! `process_model/flowsheet.py` (`run_python_case`) and `kpis.py`, on a [crate::props]
//! fluid-property back end.

pub mod flowsheet;
pub mod kpis;
pub mod properties;
pub mod result;

pub use flowsheet::{Cracker, eos_from_name, eos_name, run_case, run_python_case};
pub use result::{CaseInputs, SimulationResult};
