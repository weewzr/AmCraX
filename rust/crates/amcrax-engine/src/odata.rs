//! An ordered data tree for the YAML reference data.
//!
//! `serde_json::Value` (without the `preserve_order` feature) sorts the keys of a mapping, but the
//! Python reference iterates some YAML mappings in document order and sums the results with the
//! order-dependent builtin `sum()` (for example `singapore.yaml`
//! `capex_equipment.equipment_shares_pct`). [`OValue`] keeps the document order of every mapping
//! (as PyYAML's `dict`) and records whether a number was written as an integer.

use crate::error::EngineError;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::Value;
use std::fmt;

/// A parsed YAML (or JSON) value with mappings in document order.
#[derive(Debug, Clone, PartialEq, Default)]
pub enum OValue {
    #[default]
    Null,
    Bool(bool),
    /// An integer literal.
    Int(i64),
    /// A float literal.
    Float(f64),
    Str(String),
    Seq(Vec<OValue>),
    /// Entries in document order.
    Map(Vec<(String, OValue)>),
}

static NULL: OValue = OValue::Null;

impl OValue {
    /// The value under `key` of a mapping ([`OValue::Null`] when absent or not a mapping).
    pub fn get(&self, key: &str) -> &OValue {
        match self {
            OValue::Map(m) => m
                .iter()
                .find(|(k, _)| k == key)
                .map(|e| &e.1)
                .unwrap_or(&NULL),
            _ => &NULL,
        }
    }

    /// The value at a path of mapping keys.
    pub fn at(&self, path: &[&str]) -> &OValue {
        path.iter().fold(self, |v, k| v.get(k))
    }

    /// `entry["value"]` of a sourced YAML entry.
    pub fn val(&self, path: &[&str]) -> &OValue {
        self.at(path).get("value")
    }

    /// The number (integers converted), or `None`.
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            OValue::Int(i) => Some(*i as f64),
            OValue::Float(f) => Some(*f),
            _ => None,
        }
    }

    /// The string, or `None`.
    pub fn as_str(&self) -> Option<&str> {
        match self {
            OValue::Str(s) => Some(s),
            _ => None,
        }
    }

    /// The boolean, or `None`.
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            OValue::Bool(b) => Some(*b),
            _ => None,
        }
    }

    /// The entries of a mapping in document order (empty otherwise).
    pub fn entries(&self) -> &[(String, OValue)] {
        match self {
            OValue::Map(m) => m,
            _ => &[],
        }
    }

    /// The items of a sequence (empty otherwise).
    pub fn items(&self) -> &[OValue] {
        match self {
            OValue::Seq(s) => s,
            _ => &[],
        }
    }

    /// True for [`OValue::Null`].
    pub fn is_null(&self) -> bool {
        matches!(self, OValue::Null)
    }

    /// A required number at `path` (`file` names the data file in the error).
    pub fn num(&self, file: &str, path: &[&str]) -> Result<f64, EngineError> {
        self.at(path)
            .as_f64()
            .ok_or_else(|| EngineError::data(file, format!("{}: number expected", path.join("."))))
    }

    /// A required number at `path` + `value`.
    pub fn num_v(&self, file: &str, path: &[&str]) -> Result<f64, EngineError> {
        self.val(path).as_f64().ok_or_else(|| {
            EngineError::data(file, format!("{}.value: number expected", path.join(".")))
        })
    }

    /// A required string at `path`.
    pub fn string(&self, file: &str, path: &[&str]) -> Result<String, EngineError> {
        self.at(path)
            .as_str()
            .map(str::to_string)
            .ok_or_else(|| EngineError::data(file, format!("{}: string expected", path.join("."))))
    }

    /// A mapping of numbers in document order.
    pub fn num_map(&self, file: &str, path: &[&str]) -> Result<Vec<(String, f64)>, EngineError> {
        let v = self.at(path);
        if !matches!(v, OValue::Map(_)) {
            return Err(EngineError::data(
                file,
                format!("{}: mapping expected", path.join(".")),
            ));
        }
        v.entries()
            .iter()
            .map(|(k, x)| {
                x.as_f64().map(|f| (k.clone(), f)).ok_or_else(|| {
                    EngineError::data(file, format!("{}.{k}: number expected", path.join(".")))
                })
            })
            .collect()
    }

    /// A sequence of numbers.
    pub fn num_seq(&self, file: &str, path: &[&str]) -> Result<Vec<f64>, EngineError> {
        let v = self.at(path);
        if !matches!(v, OValue::Seq(_)) {
            return Err(EngineError::data(
                file,
                format!("{}: sequence expected", path.join(".")),
            ));
        }
        v.items()
            .iter()
            .map(|x| {
                x.as_f64().ok_or_else(|| {
                    EngineError::data(file, format!("{}: numbers expected", path.join(".")))
                })
            })
            .collect()
    }

    /// Conversion to `serde_json::Value` (keys sorted; integers stay integers).
    pub fn to_json(&self) -> Value {
        match self {
            OValue::Null => Value::Null,
            OValue::Bool(b) => Value::Bool(*b),
            OValue::Int(i) => Value::from(*i),
            OValue::Float(f) => serde_json::Number::from_f64(*f)
                .map(Value::Number)
                .unwrap_or(Value::Null),
            OValue::Str(s) => Value::String(s.clone()),
            OValue::Seq(v) => Value::Array(v.iter().map(OValue::to_json).collect()),
            OValue::Map(m) => {
                Value::Object(m.iter().map(|(k, v)| (k.clone(), v.to_json())).collect())
            }
        }
    }

    /// Parse YAML text (YAML 1.2, see the stage 1 data-parity report for the PyYAML differences).
    #[cfg(feature = "yaml")]
    pub fn from_yaml(file: &str, text: &str) -> Result<OValue, EngineError> {
        serde_saphyr::from_str(text).map_err(|e| EngineError::data(file, e.to_string()))
    }
}

struct OVisitor;

impl<'de> Visitor<'de> for OVisitor {
    type Value = OValue;

    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.write_str("a YAML value")
    }
    fn visit_bool<E: de::Error>(self, v: bool) -> Result<OValue, E> {
        Ok(OValue::Bool(v))
    }
    fn visit_i64<E: de::Error>(self, v: i64) -> Result<OValue, E> {
        Ok(OValue::Int(v))
    }
    fn visit_u64<E: de::Error>(self, v: u64) -> Result<OValue, E> {
        Ok(i64::try_from(v)
            .map(OValue::Int)
            .unwrap_or(OValue::Float(v as f64)))
    }
    fn visit_f64<E: de::Error>(self, v: f64) -> Result<OValue, E> {
        Ok(OValue::Float(v))
    }
    fn visit_str<E: de::Error>(self, v: &str) -> Result<OValue, E> {
        Ok(OValue::Str(v.to_string()))
    }
    fn visit_string<E: de::Error>(self, v: String) -> Result<OValue, E> {
        Ok(OValue::Str(v))
    }
    fn visit_none<E: de::Error>(self) -> Result<OValue, E> {
        Ok(OValue::Null)
    }
    fn visit_unit<E: de::Error>(self) -> Result<OValue, E> {
        Ok(OValue::Null)
    }
    fn visit_some<D: Deserializer<'de>>(self, d: D) -> Result<OValue, D::Error> {
        OValue::deserialize(d)
    }
    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<OValue, A::Error> {
        let mut v = Vec::new();
        while let Some(x) = seq.next_element::<OValue>()? {
            v.push(x);
        }
        Ok(OValue::Seq(v))
    }
    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<OValue, A::Error> {
        let mut m: Vec<(String, OValue)> = Vec::new();
        while let Some((k, v)) = map.next_entry::<KeyString, OValue>()? {
            // a repeated key replaces the earlier value in place (PyYAML dict semantics)
            let pos = m.iter().position(|e| e.0 == k.0);
            match pos {
                Some(i) => m[i].1 = v,
                None => m.push((k.0, v)),
            }
        }
        Ok(OValue::Map(m))
    }
}

impl<'de> Deserialize<'de> for OValue {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<OValue, D::Error> {
        d.deserialize_any(OVisitor)
    }
}

/// A mapping key: strings as they are, numbers and booleans in their Python `str()` form.
struct KeyString(String);

struct KeyVisitor;

impl Visitor<'_> for KeyVisitor {
    type Value = KeyString;
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.write_str("a mapping key")
    }
    fn visit_str<E: de::Error>(self, v: &str) -> Result<KeyString, E> {
        Ok(KeyString(v.to_string()))
    }
    fn visit_string<E: de::Error>(self, v: String) -> Result<KeyString, E> {
        Ok(KeyString(v))
    }
    fn visit_i64<E: de::Error>(self, v: i64) -> Result<KeyString, E> {
        Ok(KeyString(v.to_string()))
    }
    fn visit_u64<E: de::Error>(self, v: u64) -> Result<KeyString, E> {
        Ok(KeyString(v.to_string()))
    }
    fn visit_f64<E: de::Error>(self, v: f64) -> Result<KeyString, E> {
        Ok(KeyString(format!("{v:?}")))
    }
    fn visit_bool<E: de::Error>(self, v: bool) -> Result<KeyString, E> {
        Ok(KeyString(if v { "True" } else { "False" }.to_string()))
    }
}

impl<'de> Deserialize<'de> for KeyString {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<KeyString, D::Error> {
        d.deserialize_any(KeyVisitor)
    }
}

#[cfg(all(test, feature = "yaml"))]
mod tests {
    use super::*;

    #[test]
    fn keeps_document_order_and_integer_kind() {
        let v =
            OValue::from_yaml("inline", "b: 1\na: 2.5\nc: {z: 1, w: [1, 2]}\nm: null\n").unwrap();
        let keys: Vec<&str> = v.entries().iter().map(|e| e.0.as_str()).collect();
        // (keys `y`, `n` would be YAML 1.1 booleans for the non-strict parser)
        assert_eq!(keys, ["b", "a", "c", "m"], "{v:?}");
        assert_eq!(v.get("b"), &OValue::Int(1));
        assert_eq!(v.get("a").as_f64(), Some(2.5));
        assert_eq!(v.at(&["c", "z"]).as_f64(), Some(1.0));
        assert_eq!(v.at(&["c", "w"]).items().len(), 2);
        assert!(v.get("m").is_null());
        assert!(v.get("missing").is_null());
        assert_eq!(v.to_json()["c"]["z"], serde_json::json!(1));
    }
}
