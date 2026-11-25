//! Engine errors (one enum for the whole engine; Python exception names in the comments).

/// Every fallible engine function returns this error.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum EngineError {
    /// The specification cannot be met (Python `FlowsheetSpecError`).
    #[error("specification infeasible: {0}")]
    Spec(String),
    /// A root-finding bracket does not contain a sign change.
    #[error("root not bracketed: {0}")]
    Bracket(String),
    /// ODE integration failed.
    #[error("integration failed: {0}")]
    Integration(String),
    /// Input outside the model's domain (for example the NASA-7 range, or p_H2 = 0 in Temkin).
    #[error("outside model domain: {0}")]
    Domain(String),
    /// A data file is missing, unreadable or malformed.
    #[error("data error in {file}: {msg}")]
    Data { file: String, msg: String },
    /// The property backend (CoolProp or a table) failed.
    #[error("property backend: {0}")]
    Property(String),
    /// A numerical method failed where Python raises `RuntimeError` (no physical cubic root,
    /// successive substitution not converged or trivial, brentq not converged, failed balance).
    #[error("numerical failure: {0}")]
    Numerical(String),
}

impl EngineError {
    /// A [`EngineError::Data`] error for `file`.
    pub fn data(file: impl Into<String>, msg: impl Into<String>) -> Self {
        EngineError::Data {
            file: file.into(),
            msg: msg.into(),
        }
    }
}
