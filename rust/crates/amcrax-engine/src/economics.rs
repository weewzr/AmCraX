//! Techno-economics (Python `backend/amcrax/economics/`; data `economics.yaml`, `singapore.yaml`,
//! `reference_scenario.yaml`). Stage 3.
//!
//! * [`reference`]: the unified reference scenario and the CAPEX method `cho2026_itemised_v1`
//!   (Python `reference.py`).
//! * [`lcoh`]: `EconomicAssumptions` and the legacy plant-level correlation (Python `models.py`,
//!   `lcoh.py`), kept because it is the version 1 basis of the core stored results.
//! * [`singapore`]: `evaluate` (LCOH, REC, NPV, IRR, payback, every `capex_mode`), the break-even
//!   ammonia price and the equipment CAPEX (Python `singapore.py`).
//!
//! Every formula keeps the Python operation order (left-to-right products and quotients, the
//! builtin `sum()` as [`crate::pyops::py_sum`], `x ** y` as `powf`, `round()` half to even), so
//! the results agree with Python to the last bits except where the platform `pow` differs by an
//! ulp. Gate: 1e-12 relative on every output (`amcrax verify economics`).
//!
//! Where Python raises (`KeyError` for an unknown override, `ValueError` for a bad option or a
//! failed pydantic validation, `ZeroDivisionError` for a float division by zero) the port returns
//! [`EngineError::Domain`]; it never returns infinities that Python would not produce.

pub mod lcoh;
pub mod reference;
pub mod singapore;

use crate::error::EngineError;
use serde_json::Value;

/// Python float division: `ZeroDivisionError` (here [`EngineError::Domain`]) for a zero divisor.
#[inline]
pub(crate) fn pydiv(a: f64, b: f64, what: &str) -> Result<f64, EngineError> {
    if b == 0.0 {
        Err(EngineError::Domain(format!(
            "ZeroDivisionError: float division by zero ({what})"
        )))
    } else {
        Ok(a / b)
    }
}

/// Python `x ** y` for floats (C `pow`).
#[inline]
pub(crate) fn pypow(x: f64, y: f64) -> f64 {
    x.powf(y)
}

/// A float as JSON (`"nan"`, `"inf"`, `"-inf"` for non-finite values, as the golden tables).
pub fn jf(x: f64) -> Value {
    if x.is_finite() {
        serde_json::Number::from_f64(x)
            .map(Value::Number)
            .unwrap_or(Value::Null)
    } else if x.is_nan() {
        Value::String("nan".into())
    } else if x > 0.0 {
        Value::String("inf".into())
    } else {
        Value::String("-inf".into())
    }
}

/// An optional float as JSON (`None` is `null`).
pub fn jo(x: Option<f64>) -> Value {
    x.map(jf).unwrap_or(Value::Null)
}

/// A float from a JSON override value (integers accepted, as pydantic's float fields).
pub(crate) fn json_f64(key: &str, v: &Value) -> Result<f64, EngineError> {
    match v {
        Value::Number(n) => n
            .as_f64()
            .ok_or_else(|| EngineError::Domain(format!("{key}: number expected"))),
        Value::String(s) if s == "nan" => Ok(f64::NAN),
        Value::String(s) if s == "inf" => Ok(f64::INFINITY),
        Value::String(s) if s == "-inf" => Ok(f64::NEG_INFINITY),
        _ => Err(EngineError::Domain(format!(
            "ValueError: {key}: number expected, got {v}"
        ))),
    }
}

/// An optional float (`null` is `None`).
pub(crate) fn json_opt_f64(key: &str, v: &Value) -> Result<Option<f64>, EngineError> {
    if v.is_null() {
        Ok(None)
    } else {
        json_f64(key, v).map(Some)
    }
}

/// A boolean override value.
pub(crate) fn json_bool(key: &str, v: &Value) -> Result<bool, EngineError> {
    v.as_bool()
        .ok_or_else(|| EngineError::Domain(format!("ValueError: {key}: boolean expected, got {v}")))
}

/// A string override value.
pub(crate) fn json_string(key: &str, v: &Value) -> Result<String, EngineError> {
    v.as_str()
        .map(str::to_string)
        .ok_or_else(|| EngineError::Domain(format!("ValueError: {key}: string expected, got {v}")))
}

/// Python `round(x)` for a float (half to even) as an integer.
#[inline]
pub(crate) fn py_round(x: f64) -> i64 {
    x.round_ties_even() as i64
}
