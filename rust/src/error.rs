use pyo3::exceptions::{PyLookupError, PyValueError};
use pyo3::prelude::*;

#[derive(Debug)]
pub enum PranceError {
    Resolution(String),
    Parse(String),
    Value(String),
    Io(String),
}

impl std::fmt::Display for PranceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PranceError::Resolution(s) => write!(f, "{s}"),
            PranceError::Parse(s) => write!(f, "{s}"),
            PranceError::Value(s) => write!(f, "{s}"),
            PranceError::Io(s) => write!(f, "{s}"),
        }
    }
}

impl std::error::Error for PranceError {}

impl From<PyErr> for PranceError {
    fn from(err: PyErr) -> Self {
        Python::with_gil(|py| {
            let is_resolution = py
                .import("prance.util.url")
                .and_then(|m| m.getattr("ResolutionError"))
                .map(|cls| err.is_instance(py, &cls))
                .unwrap_or(false);
            if is_resolution || err.is_instance_of::<PyLookupError>(py) {
                let msg = err
                    .value(py)
                    .str()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_else(|_| err.to_string());
                PranceError::Resolution(msg)
            } else if err.is_instance_of::<PyValueError>(py) {
                let msg = err
                    .value(py)
                    .str()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_else(|_| err.to_string());
                PranceError::Parse(msg)
            } else {
                PranceError::Value(err.to_string())
            }
        })
    }
}

pub fn into_py_err(err: PranceError) -> PyErr {
    match err {
        PranceError::Resolution(msg) => Python::with_gil(|py| {
            let cls = match py.import("prance.util.url").and_then(|m| m.getattr("ResolutionError")) {
                Ok(cls) => cls,
                Err(e) => return e,
            };
            match cls.call1((msg,)) {
                Ok(exc) => PyErr::from_value(exc),
                Err(e) => e,
            }
        }),
        PranceError::Parse(msg) => PyErr::new::<PyValueError, _>(msg),
        PranceError::Value(msg) => PyErr::new::<PyValueError, _>(msg),
        PranceError::Io(msg) => PyErr::new::<pyo3::exceptions::PyOSError, _>(msg),
    }
}
