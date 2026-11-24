//! WebAssembly facade of the AmCraX engine (target `wasm32-unknown-unknown`, wasm-bindgen).
//!
//! Stage 0 exports a version string and two numerics entry points that the browser can already
//! use (NumPy-compatible uniform draws and SciPy-compatible PCHIP). The `Engine` object of the
//! architecture document (model loaded once from `model.json`, `simulate_pfr`,
//! `simulate_process`, `evaluate_economics`, ...) is added when the engine modules are ported.
//!
//! Every export is a thin wrapper over a plain Rust function of this crate, so the logic is
//! tested natively; the wrappers only convert errors to `JsError`.

use amcrax_numerics::interp::Pchip;
use amcrax_numerics::random::Pcg64;

/// Engine version (same as the CLI's `amcrax --version`).
pub fn version() -> String {
    amcrax_engine::ENGINE_VERSION.to_string()
}

/// `numpy.random.default_rng(seed).random(n)`.
pub fn uniform_draws(seed: u32, n: usize) -> Vec<f64> {
    Pcg64::from_seed(u128::from(seed)).random_vec(n)
}

/// `scipy.interpolate.PchipInterpolator(x, y)(at)`.
pub fn pchip(x: &[f64], y: &[f64], at: &[f64]) -> Result<Vec<f64>, String> {
    Pchip::new(x, y)
        .map(|p| p.eval_many(at))
        .map_err(|e| e.to_string())
}

/// The wasm-bindgen exports (the macro generates the JavaScript glue, which uses `unsafe`).
pub mod bindings {
    #![allow(unsafe_code)]

    use wasm_bindgen::prelude::*;

    /// Engine version.
    #[wasm_bindgen(js_name = engineVersion)]
    pub fn engine_version() -> String {
        super::version()
    }

    /// NumPy-compatible uniform draws in [0, 1).
    #[wasm_bindgen(js_name = uniformDraws)]
    pub fn uniform_draws(seed: u32, n: usize) -> Vec<f64> {
        super::uniform_draws(seed, n)
    }

    /// SciPy-compatible PCHIP interpolation.
    #[wasm_bindgen(js_name = pchip)]
    pub fn pchip(x: &[f64], y: &[f64], at: &[f64]) -> Result<Vec<f64>, JsError> {
        super::pchip(x, y, at).map_err(|e| JsError::new(&e))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wrappers_work_natively() {
        assert_eq!(version(), amcrax_engine::ENGINE_VERSION);
        let u = uniform_draws(20261123, 5);
        assert_eq!(u.len(), 5);
        assert!(u.iter().all(|v| (0.0..1.0).contains(v)));
        assert_eq!(pchip(&[0.0, 1.0], &[0.0, 2.0], &[0.5]).unwrap(), [1.0]);
        assert!(pchip(&[0.0], &[0.0], &[0.5]).is_err());
    }
}
