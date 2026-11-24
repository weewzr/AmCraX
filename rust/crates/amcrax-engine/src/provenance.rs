//! Provenance written into every Rust result file: a superset of the keys the Python drivers
//! write, so the downstream builders can read Rust outputs unchanged.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

/// SHA-256 of raw bytes as lower-case hex (identical to Python `hashlib.sha256(b).hexdigest()`).
pub fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

/// A hashed input file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileStamp {
    /// Repository-relative path with forward slashes.
    pub file: String,
    /// SHA-256 of the raw bytes.
    pub sha256: String,
}

/// Provenance block of a result.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Provenance {
    /// UTC time stamp, ISO 8601.
    pub generated_utc: String,
    /// The command that produced the result.
    pub command: String,
    /// Implementation that produced the result (`"rust"`).
    pub implementation: String,
    /// Engine crate version.
    pub engine_version: String,
    /// Git revision of the sources, when known.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub engine_git: Option<String>,
    /// The reference scenario file and its hash.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference_scenario: Option<FileStamp>,
    /// SHA-256 of every input file, by repository-relative path.
    pub input_sha256: BTreeMap<String, String>,
    /// Random seed, when the result is stochastic.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub seed: Option<u64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_of_known_input() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }
}
