//! Ideal-gas species thermochemistry from NASA 7-coefficient polynomials (Python
//! `thermodynamics/nasa7.py`), data `backend/amcrax/data/nasa7.json` (GRI-Mech 3.0).
//!
//! The expressions are written in the operation order of the Python source; `T**k` is
//! `powf(k)` (C `pow`, as Python's float `**`).

use crate::error::EngineError;
use crate::provenance::sha256_hex;
use crate::species::{N_SPECIES, Species};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::sync::OnceLock;

/// Gas constant, J/(mol K) (CODATA 2018 exact; Python `R_J_molK`).
pub const R_J_MOL_K: f64 = 8.314462618;
/// Standard-state pressure of all public s, g, K values, bar.
pub const P_STD_BAR: f64 = 1.0;
/// Pressure the GRI-Mech entropies were fitted at, bar (see the Python module docstring).
pub const POLY_PREF_BAR: f64 = 1.0;
/// Repository path of the data file.
pub const DATA_FILE: &str = "backend/amcrax/data/nasa7.json";
/// The data file, embedded at compile time (the verification checks its SHA-256 against the
/// file on disk).
pub const EMBEDDED_JSON: &str = include_str!("../../../../../backend/amcrax/data/nasa7.json");

/// Elements counted in element balances.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Element {
    N,
    H,
    O,
}

/// NASA-7 data of one species.
#[derive(Debug, Clone, PartialEq)]
pub struct Nasa7Species {
    pub t_min: f64,
    pub t_mid: f64,
    pub t_max: f64,
    pub low: [f64; 7],
    pub high: [f64; 7],
    /// Correction from the polynomial reference pressure to the 1 bar standard state, units of R.
    pub ds_r: f64,
    /// Atoms of N, H, O.
    pub composition: [f64; 3],
}

/// NASA-7 data of the five species.
#[derive(Debug, Clone, PartialEq)]
pub struct Nasa7 {
    species: Vec<Nasa7Species>,
    /// SHA-256 of the JSON text the data were parsed from.
    pub sha256: String,
}

#[derive(Deserialize)]
struct RawFile {
    species: BTreeMap<String, RawSpecies>,
}

#[derive(Deserialize)]
struct RawSpecies {
    composition: BTreeMap<String, f64>,
    #[serde(rename = "T_ranges_K")]
    t_ranges_k: [f64; 3],
    coeffs_low: [f64; 7],
    coeffs_high: [f64; 7],
}

impl Nasa7 {
    /// Parse `nasa7.json`.
    pub fn from_json(text: &str) -> Result<Self, EngineError> {
        let raw: RawFile =
            serde_json::from_str(text).map_err(|e| EngineError::data(DATA_FILE, e.to_string()))?;
        let mut species = Vec::with_capacity(N_SPECIES);
        for s in Species::ALL {
            let r = raw.species.get(s.name()).ok_or_else(|| {
                EngineError::data(DATA_FILE, format!("species {} missing", s.name()))
            })?;
            let p = POLY_PREF_BAR * 1e5;
            let el = |k: &str| r.composition.get(k).copied().unwrap_or(0.0);
            species.push(Nasa7Species {
                t_min: r.t_ranges_k[0],
                t_mid: r.t_ranges_k[1],
                t_max: r.t_ranges_k[2],
                low: r.coeffs_low,
                high: r.coeffs_high,
                ds_r: (p / (P_STD_BAR * 1e5)).ln(),
                composition: [el("N"), el("H"), el("O")],
            });
        }
        Ok(Nasa7 {
            species,
            sha256: sha256_hex(text.as_bytes()),
        })
    }

    /// The data embedded in the engine (parsed once).
    pub fn embedded() -> &'static Nasa7 {
        static CELL: OnceLock<Nasa7> = OnceLock::new();
        CELL.get_or_init(|| {
            Nasa7::from_json(EMBEDDED_JSON).expect("embedded nasa7.json is valid (checked in CI)")
        })
    }

    /// Data of one species.
    pub fn species(&self, s: Species) -> &Nasa7Species {
        &self.species[s.index()]
    }

    /// Atoms of `el` in species `s` (Python `composition(s).get(el, 0)`).
    pub fn atoms(&self, s: Species, el: Element) -> f64 {
        let c = &self.species[s.index()].composition;
        match el {
            Element::N => c[0],
            Element::H => c[1],
            Element::O => c[2],
        }
    }

    fn coeffs(&self, s: Species, t_k: f64) -> Result<&[f64; 7], EngineError> {
        let sp = &self.species[s.index()];
        // GRI-Mech gives N2 from 300 K only; extrapolation down to Tmin - 100 K is allowed (Python).
        if !(sp.t_min - 100.0 <= t_k && t_k <= sp.t_max) {
            return Err(EngineError::Domain(format!(
                "T = {t_k} K outside NASA7 validity [{}, {}] K for {}",
                sp.t_min,
                sp.t_max,
                s.name()
            )));
        }
        Ok(if t_k <= sp.t_mid { &sp.low } else { &sp.high })
    }

    /// cp / R.
    pub fn cp_r(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        let a = self.coeffs(s, t_k)?;
        let t = t_k;
        Ok(a[0] + a[1] * t + a[2] * t.powf(2.0) + a[3] * t.powf(3.0) + a[4] * t.powf(4.0))
    }

    /// h / (R T), including the formation enthalpy.
    pub fn h_rt(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        let a = self.coeffs(s, t_k)?;
        let t = t_k;
        Ok(a[0]
            + a[1] * t / 2.0
            + a[2] * t.powf(2.0) / 3.0
            + a[3] * t.powf(3.0) / 4.0
            + a[4] * t.powf(4.0) / 5.0
            + a[5] / t)
    }

    /// Standard entropy / R at 1 bar.
    pub fn s_r(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        let a = self.coeffs(s, t_k)?;
        let t = t_k;
        let v = a[0] * t.ln()
            + a[1] * t
            + a[2] * t.powf(2.0) / 2.0
            + a[3] * t.powf(3.0) / 3.0
            + a[4] * t.powf(4.0) / 4.0
            + a[6];
        Ok(v + self.species[s.index()].ds_r)
    }

    /// Sums of the absolute values of the polynomial terms of `(cp, h, s)` in J/(mol K), kJ/mol,
    /// J/(mol K): the scale against which rounding errors of the sums are measured (verification).
    pub fn term_scales(&self, s: Species, t_k: f64) -> Result<(f64, f64, f64), EngineError> {
        let a = self.coeffs(s, t_k)?;
        let t = t_k;
        let cp = a[0].abs()
            + (a[1] * t).abs()
            + (a[2] * t * t).abs()
            + (a[3] * t * t * t).abs()
            + (a[4] * t * t * t * t).abs();
        let h = a[0].abs()
            + (a[1] * t / 2.0).abs()
            + (a[2] * t * t / 3.0).abs()
            + (a[3] * t * t * t / 4.0).abs()
            + (a[4] * t * t * t * t / 5.0).abs()
            + (a[5] / t).abs();
        let sr = (a[0] * t.ln()).abs()
            + (a[1] * t).abs()
            + (a[2] * t * t / 2.0).abs()
            + (a[3] * t * t * t / 3.0).abs()
            + (a[4] * t * t * t * t / 4.0).abs()
            + a[6].abs();
        Ok((R_J_MOL_K * cp, R_J_MOL_K * t * h / 1000.0, R_J_MOL_K * sr))
    }

    /// Ideal-gas heat capacity, J/(mol K).
    pub fn cp_j_mol_k(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        Ok(R_J_MOL_K * self.cp_r(s, t_k)?)
    }

    /// Ideal-gas molar enthalpy including the formation enthalpy, kJ/mol.
    pub fn enthalpy_kj_mol(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        Ok(R_J_MOL_K * t_k * self.h_rt(s, t_k)? / 1000.0)
    }

    /// Standard (1 bar) molar entropy, J/(mol K).
    pub fn entropy_j_mol_k(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        Ok(R_J_MOL_K * self.s_r(s, t_k)?)
    }

    /// Standard (1 bar) molar Gibbs energy `h - T s`, kJ/mol.
    pub fn gibbs_kj_mol(&self, s: Species, t_k: f64) -> Result<f64, EngineError> {
        Ok(self.enthalpy_kj_mol(s, t_k)? - t_k * self.entropy_j_mol_k(s, t_k)? / 1000.0)
    }
}

/// [`Nasa7::cp_j_mol_k`] with the embedded data (Python `species_cp_J_molK`).
pub fn species_cp_j_mol_k(s: Species, t_k: f64) -> Result<f64, EngineError> {
    Nasa7::embedded().cp_j_mol_k(s, t_k)
}

/// [`Nasa7::enthalpy_kj_mol`] with the embedded data (Python `species_enthalpy_kJ_mol`).
pub fn species_enthalpy_kj_mol(s: Species, t_k: f64) -> Result<f64, EngineError> {
    Nasa7::embedded().enthalpy_kj_mol(s, t_k)
}

/// [`Nasa7::entropy_j_mol_k`] with the embedded data (Python `species_entropy_J_molK`).
pub fn species_entropy_j_mol_k(s: Species, t_k: f64) -> Result<f64, EngineError> {
    Nasa7::embedded().entropy_j_mol_k(s, t_k)
}

/// [`Nasa7::gibbs_kj_mol`] with the embedded data (Python `species_gibbs_kJ_mol`).
pub fn species_gibbs_kj_mol(s: Species, t_k: f64) -> Result<f64, EngineError> {
    Nasa7::embedded().gibbs_kj_mol(s, t_k)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_data_parse_and_reference_values() {
        let d = Nasa7::embedded();
        // elements in their reference state have h(298.15 K) ~ 0
        assert!(d.enthalpy_kj_mol(Species::H2, 298.15).unwrap().abs() < 1e-2);
        // NH3 formation enthalpy -45.9 kJ/mol
        assert!((d.enthalpy_kj_mol(Species::NH3, 298.15).unwrap() + 45.9).abs() < 0.2);
        assert!(matches!(
            d.cp_r(Species::NH3, 50.0),
            Err(EngineError::Domain(_))
        ));
        assert!(d.cp_r(Species::NH3, f64::NAN).is_err());
        assert_eq!(d.atoms(Species::NH3, Element::H), 3.0);
    }
}
