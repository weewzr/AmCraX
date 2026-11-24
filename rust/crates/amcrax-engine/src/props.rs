//! Property backends (Python `process_model/properties.py`): CoolProp for NH3 and water on
//! native builds (feature `coolprop`, later), an exported table for the browser. Stage 3.

use serde::{Deserialize, Serialize};

/// Phase selector of a property call.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    /// Vapour (gas) root / branch.
    Vapour,
    /// Liquid root / branch.
    Liquid,
}
