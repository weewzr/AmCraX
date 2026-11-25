//! Gas viscosity for the Ergun pressure drop: an exact port of Cantera's mixture-averaged
//! viscosity (`GasTransport::updateSpeciesViscosities`, `GasTransport::updateViscosity_T`,
//! `MixTransport::viscosity`) with GRI-Mech 3.0 transport data, the only Cantera call of the
//! Python reactor (`reactor/pfr.py: gas_viscosity_Pa_s`).
//!
//! Data: `rust/data/transport_gri30.json`, exported from Cantera by
//! `rust/golden/generate_stage2_golden.py` (`gas.get_viscosity_polynomial(k)` and the molar
//! masses of NH3, H2, N2, H2O, O2, AR). Pure species: `sqrt(mu_k) = T^(1/4) sum_n c_n (ln T)^n`.
//! Mixture (Wilke): `mu = sum_k x_k mu_k / sum_j phi_kj x_j`,
//! `phi_kj = (1 + sqrt(mu_k / mu_j) (M_j / M_k)^(1/4))^2 / sqrt(8 (1 + M_k / M_j))`.
//! Cantera adds 1e-20 to every mole fraction of its 53 species; those terms change the result by
//! less than 1e-18 relative and are not reproduced. Gate against Cantera: 1e-10 relative
//! (`rust/golden/stage2/viscosity.json`).

use crate::error::EngineError;
use crate::provenance::sha256_hex;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::sync::OnceLock;

/// Repository path of the transport data.
pub const DATA_FILE: &str = "rust/data/transport_gri30.json";
/// The transport data, embedded at compile time.
pub const EMBEDDED_JSON: &str = include_str!("../../../data/transport_gri30.json");
/// Species of the viscosity model, in this order: NH3, H2, N2, H2O, O2, AR.
pub const SPECIES: [&str; 6] = ["NH3", "H2", "N2", "H2O", "O2", "AR"];
/// Number of species of the viscosity model.
pub const NV: usize = 6;

#[derive(Deserialize)]
struct RawSpecies {
    molecular_weight_kg_kmol: f64,
    viscosity_polynomial: [f64; 5],
}

#[derive(Deserialize)]
struct RawFile {
    species: BTreeMap<String, RawSpecies>,
}

/// Viscosity data of the six species.
#[derive(Debug, Clone, PartialEq)]
pub struct Transport {
    mw: [f64; NV],
    poly: [[f64; 5]; NV],
    /// SHA-256 of the JSON text.
    pub sha256: String,
}

impl Transport {
    /// Parse `transport_gri30.json`.
    pub fn from_json(text: &str) -> Result<Transport, EngineError> {
        let raw: RawFile =
            serde_json::from_str(text).map_err(|e| EngineError::data(DATA_FILE, e.to_string()))?;
        let mut mw = [0.0; NV];
        let mut poly = [[0.0; 5]; NV];
        for (k, s) in SPECIES.iter().enumerate() {
            let r = raw
                .species
                .get(*s)
                .ok_or_else(|| EngineError::data(DATA_FILE, format!("species {s} missing")))?;
            mw[k] = r.molecular_weight_kg_kmol;
            poly[k] = r.viscosity_polynomial;
        }
        Ok(Transport {
            mw,
            poly,
            sha256: sha256_hex(text.as_bytes()),
        })
    }

    /// The embedded data (parsed once).
    pub fn embedded() -> &'static Transport {
        static CELL: OnceLock<Transport> = OnceLock::new();
        CELL.get_or_init(|| {
            Transport::from_json(EMBEDDED_JSON).expect("embedded transport_gri30.json is valid")
        })
    }

    /// Molar masses, kg/kmol (Cantera's).
    pub fn molecular_weights(&self) -> &[f64; NV] {
        &self.mw
    }

    /// Pure-species viscosities `mu_k` (Pa s) and `sqrt(mu_k)` at `t_k`.
    pub fn species_viscosities(&self, t_k: f64) -> ([f64; NV], [f64; NV]) {
        let logt = t_k.ln();
        let t14 = t_k.sqrt().sqrt();
        let mut pv = [1.0, logt, 0.0, 0.0, 0.0];
        pv[2] = logt * logt;
        pv[3] = pv[2] * logt;
        pv[4] = pv[3] * logt;
        let mut visc = [0.0; NV];
        let mut sq = [0.0; NV];
        for k in 0..NV {
            let c = &self.poly[k];
            let dot5 = pv[0] * c[0] + pv[1] * c[1] + pv[2] * c[2] + pv[3] * c[3] + pv[4] * c[4];
            sq[k] = t14 * dot5;
            visc[k] = sq[k] * sq[k];
        }
        (visc, sq)
    }

    /// Mixture viscosity, Pa s, of mole fractions `x` (in [`SPECIES`] order; normalised here as
    /// Cantera does; negative entries are an error).
    pub fn mixture_viscosity(&self, t_k: f64, x: &[f64; NV]) -> Result<f64, EngineError> {
        if x.iter().any(|v| *v < 0.0 || !v.is_finite()) || t_k.is_nan() || t_k <= 0.0 {
            return Err(EngineError::Domain(format!(
                "viscosity: invalid state T = {t_k} K, x = {x:?}"
            )));
        }
        let tot: f64 = x.iter().sum();
        if tot <= 0.0 {
            return Err(EngineError::Domain(
                "viscosity: all mole fractions are zero".into(),
            ));
        }
        let xs: Vec<f64> = x.iter().map(|v| v / tot).collect();
        let (visc, sq) = self.species_viscosities(t_k);
        let mut vismix = 0.0;
        for k in 0..NV {
            if xs[k] == 0.0 {
                continue;
            }
            let mut den = 0.0;
            for j in 0..NV {
                if xs[j] == 0.0 {
                    continue;
                }
                let factor = 1.0 + (sq[k] / sq[j]) * (self.mw[j] / self.mw[k]).sqrt().sqrt();
                let phi = factor * factor / (8.0 * (1.0 + self.mw[k] / self.mw[j])).sqrt();
                den += phi * xs[j];
            }
            vismix += xs[k] * visc[k] / den;
        }
        Ok(vismix)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nitrogen_viscosity_magnitude() {
        let t = Transport::embedded();
        let mu = t
            .mixture_viscosity(873.15, &[0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
            .unwrap();
        // N2 at 600 degC: about 3.6e-5 Pa s
        assert!(mu > 3.0e-5 && mu < 4.2e-5);
        assert!(t.mixture_viscosity(873.15, &[0.0; 6]).is_err());
    }
}
