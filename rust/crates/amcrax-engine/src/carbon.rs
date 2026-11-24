//! Carbon intensity of hydrogen and carbon pricing (Python `environmental/__init__.py`,
//! `economics/carbon_pricing.py`; data `environmental.yaml`, `research/data/carbon_policy_sg.json`).
//! Stage 4. Gate: 1e-12 relative; crossover prices found by brentq 1e-9 relative.

use serde::{Deserialize, Serialize};

/// Heat supply of the cracker (Python `heating` option).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Heating {
    /// Natural-gas fired heater.
    NaturalGas,
    /// Burning a fraction of the product (PSA tail gas and NH3).
    SelfFiring,
    /// Electric heating.
    Electric,
}
