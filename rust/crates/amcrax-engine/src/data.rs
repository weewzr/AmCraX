//! Reference data: located in the repository, read as raw bytes (hashed for provenance) and
//! parsed into typed structures. The YAML files stay in `backend/amcrax/data/` and the JSON
//! files in `research/data/`, `backend/amcrax/data/` and `config/`; they are not copied.
//!
//! The typed loaders (kinetics, economics, Singapore, reference scenario, environmental,
//! separation, NASA-7, critical properties, transport, flowsheet) arrive in stage 1 and later.

use crate::error::EngineError;
use crate::provenance::sha256_hex;
use serde::de::DeserializeOwned;
use std::path::{Path, PathBuf};

/// Environment variable with the repository root (set by `scripts/env.ps1`).
pub const ROOT_ENV: &str = "AMCRAX_ROOT";

/// Repository-relative paths of the reference data files.
pub mod files {
    pub const KINETICS_YAML: &str = "backend/amcrax/data/kinetics.yaml";
    pub const ECONOMICS_YAML: &str = "backend/amcrax/data/economics.yaml";
    pub const SINGAPORE_YAML: &str = "backend/amcrax/data/singapore.yaml";
    pub const REFERENCE_SCENARIO_YAML: &str = "backend/amcrax/data/reference_scenario.yaml";
    pub const ENVIRONMENTAL_YAML: &str = "backend/amcrax/data/environmental.yaml";
    pub const SEPARATION_YAML: &str = "backend/amcrax/data/separation.yaml";
    pub const NASA7_JSON: &str = "backend/amcrax/data/nasa7.json";
    pub const CRITICAL_PROPERTIES_JSON: &str = "backend/amcrax/data/critical_properties.json";
    pub const FLOWSHEET_JSON: &str = "config/flowsheet.json";

    /// All YAML data files.
    pub const YAML: [&str; 6] = [
        KINETICS_YAML,
        ECONOMICS_YAML,
        SINGAPORE_YAML,
        REFERENCE_SCENARIO_YAML,
        ENVIRONMENTAL_YAML,
        SEPARATION_YAML,
    ];
}

/// The repository root that data paths are resolved against.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DataRoot {
    root: PathBuf,
}

/// A data file read as raw bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawFile {
    /// Repository-relative path (forward slashes).
    pub rel_path: String,
    /// The bytes as stored (checked out with fixed line endings, see `.gitattributes`).
    pub bytes: Vec<u8>,
    /// SHA-256 of `bytes`.
    pub sha256: String,
}

impl DataRoot {
    /// Use `root` as the repository root.
    pub fn new(root: impl Into<PathBuf>) -> Self {
        DataRoot { root: root.into() }
    }

    /// The root from the `AMCRAX_ROOT` environment variable.
    pub fn from_env() -> Result<Self, EngineError> {
        std::env::var_os(ROOT_ENV)
            .map(|v| DataRoot::new(PathBuf::from(v)))
            .ok_or_else(|| EngineError::data(ROOT_ENV, "environment variable not set"))
    }

    /// The root directory.
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Absolute path of a repository-relative path.
    pub fn path(&self, rel_path: &str) -> PathBuf {
        rel_path
            .split('/')
            .fold(self.root.clone(), |p, part| p.join(part))
    }

    /// Read a file and hash it.
    pub fn read(&self, rel_path: &str) -> Result<RawFile, EngineError> {
        let bytes = std::fs::read(self.path(rel_path))
            .map_err(|e| EngineError::data(rel_path, e.to_string()))?;
        let sha256 = sha256_hex(&bytes);
        Ok(RawFile {
            rel_path: rel_path.to_string(),
            bytes,
            sha256,
        })
    }
}

impl RawFile {
    /// The contents as UTF-8 text.
    pub fn text(&self) -> Result<&str, EngineError> {
        std::str::from_utf8(&self.bytes)
            .map_err(|e| EngineError::data(&self.rel_path, e.to_string()))
    }

    /// Parse JSON into `T`.
    pub fn parse_json<T: DeserializeOwned>(&self) -> Result<T, EngineError> {
        serde_json::from_slice(&self.bytes)
            .map_err(|e| EngineError::data(&self.rel_path, e.to_string()))
    }

    /// Parse YAML (1.2) into `T`.
    #[cfg(feature = "yaml")]
    pub fn parse_yaml<T: DeserializeOwned>(&self) -> Result<T, EngineError> {
        serde_saphyr::from_str(self.text()?)
            .map_err(|e| EngineError::data(&self.rel_path, e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repo_root() -> DataRoot {
        DataRoot::new(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../.."))
    }

    #[test]
    fn reads_and_hashes_json_data() {
        let f = repo_root().read(files::NASA7_JSON).unwrap();
        assert_eq!(f.sha256.len(), 64);
        let v: serde_json::Value = f.parse_json().unwrap();
        assert!(v.is_object());
        let missing = repo_root().read("backend/amcrax/data/does_not_exist.json");
        assert!(matches!(missing, Err(EngineError::Data { .. })));
    }

    #[cfg(feature = "yaml")]
    #[test]
    fn parses_every_yaml_data_file() {
        for rel in files::YAML {
            let f = repo_root().read(rel).unwrap();
            let v: serde_json::Value = f.parse_yaml().unwrap_or_else(|e| panic!("{rel}: {e}"));
            assert!(v.is_object(), "{rel}: top level is not a mapping");
        }
    }

    #[cfg(feature = "yaml")]
    #[test]
    fn yaml_into_typed_struct() {
        #[derive(serde::Deserialize, Debug, PartialEq)]
        #[serde(deny_unknown_fields)]
        struct Block {
            name: String,
            ea_j_mol: f64,
            orders: Vec<f64>,
        }
        let f = RawFile {
            rel_path: "inline".into(),
            bytes: b"name: test\nea_j_mol: 1.2e5\norders: [1, 0.5]\n".to_vec(),
            sha256: String::new(),
        };
        let b: Block = f.parse_yaml().unwrap();
        assert_eq!(
            b,
            Block {
                name: "test".into(),
                ea_j_mol: 1.2e5,
                orders: vec![1.0, 0.5]
            }
        );
        let bad = RawFile {
            rel_path: "inline".into(),
            bytes: b"name: test\nea_j_mol: 1\norders: []\nextra: 1\n".to_vec(),
            sha256: String::new(),
        };
        assert!(bad.parse_yaml::<Block>().is_err());
    }
}
