//! Chemical species in the fixed order of the Python `COMPONENTS` tuple
//! (`backend/amcrax/schemas.py`: NH3, H2, N2, H2O, O2).

use serde::{Deserialize, Serialize};

/// Number of species.
pub const N_SPECIES: usize = 5;

/// A composition or a per-species quantity, indexed by [`Species`] (molar flows in kmol/h,
/// mole fractions, partial pressures in bar, ...; the unit is in the variable name).
pub type Comp = [f64; N_SPECIES];

/// Species of the AmCraX models.
#[allow(clippy::upper_case_acronyms)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[repr(u8)]
pub enum Species {
    NH3 = 0,
    H2 = 1,
    N2 = 2,
    H2O = 3,
    O2 = 4,
}

impl Species {
    /// All species in `COMPONENTS` order.
    pub const ALL: [Species; N_SPECIES] = [
        Species::NH3,
        Species::H2,
        Species::N2,
        Species::H2O,
        Species::O2,
    ];

    /// Index into a [`Comp`].
    #[inline]
    pub fn index(self) -> usize {
        self as usize
    }

    /// The Python name (`"NH3"`, `"H2"`, ...).
    pub fn name(self) -> &'static str {
        match self {
            Species::NH3 => "NH3",
            Species::H2 => "H2",
            Species::N2 => "N2",
            Species::H2O => "H2O",
            Species::O2 => "O2",
        }
    }

    /// Parse a Python name.
    pub fn from_name(name: &str) -> Option<Species> {
        Species::ALL.into_iter().find(|s| s.name() == name)
    }
}

/// Sum of a composition.
pub fn total(c: &Comp) -> f64 {
    c.iter().sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn order_and_names() {
        for (i, s) in Species::ALL.iter().enumerate() {
            assert_eq!(s.index(), i);
            assert_eq!(Species::from_name(s.name()), Some(*s));
        }
        assert_eq!(Species::from_name("Ar"), None);
        assert_eq!(serde_json::to_string(&Species::H2O).unwrap(), "\"H2O\"");
    }
}
