//! OpenAPI / Swagger specification validation (Rust fast path).
//!
//! Pass 1: structural validation against the official OpenAPI meta-schemas.
//! Pass 2: semantic keyword walk (see `semantic` submodule) — incremental port.

mod default_value;
mod oas_format;
mod schema_view;
mod semantic;

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;
use serde_json::Value as JsonValue;

use jsonschema::Validator;

use crate::convert::OpaquePool;
use crate::error::PranceError;
use crate::fetch;
use crate::parse;
use crate::url::{ParsedUrl, absurl};
use crate::value::{Key, Value};

static OPENAPI_VERSION_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^(?P<major>\d+)\.(?P<minor>\d+)").unwrap());

static SCHEMA_V2: Lazy<JsonValue> = Lazy::new(|| {
    serde_json::from_str(include_str!("../../resources/schemas/v2.0/schema.json"))
        .expect("v2.0 meta-schema JSON must be valid")
});

static SCHEMA_V30: Lazy<JsonValue> = Lazy::new(|| {
    serde_json::from_str(include_str!("../../resources/schemas/v3.0/schema.json"))
        .expect("v3.0 meta-schema JSON must be valid")
});

static SCHEMA_V31: Lazy<JsonValue> = Lazy::new(|| {
    serde_json::from_str(include_str!("../../resources/schemas/v3.1/schema.json"))
        .expect("v3.1 meta-schema JSON must be valid")
});

static VALIDATOR_V2: Lazy<Validator> = Lazy::new(|| {
    jsonschema::validator_for(&SCHEMA_V2).expect("v2.0 meta-schema must compile")
});

static VALIDATOR_V30: Lazy<Validator> = Lazy::new(|| {
    jsonschema::validator_for(&SCHEMA_V30).expect("v3.0 meta-schema must compile")
});

static VALIDATOR_V31: Lazy<Validator> = Lazy::new(|| {
    jsonschema::validator_for(&SCHEMA_V31).expect("v3.1 meta-schema must compile")
});

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SpecVersion {
    V2_0,
    V30,
    V31,
}

pub fn detect_version(spec: &Value) -> Result<SpecVersion, PranceError> {
    let Value::Object(entries) = spec else {
        return Err(PranceError::Validation(
            "OpenAPI specification must be a mapping".into(),
        ));
    };

    for (key, value) in entries {
        let Some(keyword) = key.as_str() else {
            continue;
        };
        let Value::Str(version_str) = value else {
            continue;
        };
        let Some(caps) = OPENAPI_VERSION_RE.captures(version_str) else {
            continue;
        };
        let major: u32 = caps
            .name("major")
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);
        let minor: u32 = caps
            .name("minor")
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);

        match keyword {
            "swagger" if major == 2 && minor == 0 => return Ok(SpecVersion::V2_0),
            "openapi" if major == 3 && minor == 0 => return Ok(SpecVersion::V30),
            "openapi" if major == 3 && minor == 1 => return Ok(SpecVersion::V31),
            _ => {}
        }
    }

    Err(PranceError::Validation(
        "Could not determine OpenAPI specification version".into(),
    ))
}

fn validate_structural(version: SpecVersion, instance: &JsonValue) -> Result<(), PranceError> {
    let validator = match version {
        SpecVersion::V2_0 => &*VALIDATOR_V2,
        SpecVersion::V30 => &*VALIDATOR_V30,
        SpecVersion::V31 => &*VALIDATOR_V31,
    };
    validator
        .validate(instance)
        .map_err(|e| PranceError::Validation(e.to_string()))
}

fn ensure_string_keys(py: Python<'_>, value: &Value, pool: &OpaquePool) -> Result<(), PranceError> {
    match value {
        Value::Object(entries) => {
            for (key, item) in entries {
                if !matches!(key, Key::Str(_)) {
                    let repr = key_to_string(py, key, pool).unwrap_or_else(|_| "?".into());
                    return Err(PranceError::Validation(format!(
                        "Object property names must be strings (got {repr})"
                    )));
                }
                ensure_string_keys(py, item, pool)?;
            }
        }
        Value::Array(items) => {
            for item in items {
                ensure_string_keys(py, item, pool)?;
            }
        }
        _ => {}
    }
    Ok(())
}

fn key_to_string(py: Python<'_>, key: &Key, pool: &OpaquePool) -> PyResult<String> {
    match key {
        Key::Str(s) => Ok(s.clone()),
        Key::Int(i) => Ok(i.to_string()),
        Key::Opaque(id) => {
            let obj = pool.get(*id).ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Opaque pool missing key id {id}"
                ))
            })?;
            Ok(obj.bind(py).repr()?.to_string())
        }
    }
}

fn opaque_to_string(py: Python<'_>, id: u32, pool: &OpaquePool) -> PyResult<String> {
    let obj = pool.get(id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
            "Opaque pool missing value id {id}"
        ))
    })?;
    if let Ok(s) = obj.bind(py).downcast::<pyo3::types::PyString>() {
        return Ok(s.to_string_lossy().into());
    }
    Ok(obj.bind(py).str()?.to_string_lossy().into())
}

pub fn value_to_json(py: Python<'_>, value: &Value, pool: &OpaquePool) -> PyResult<JsonValue> {
    match value {
        Value::Null => Ok(JsonValue::Null),
        Value::Bool(b) => Ok(JsonValue::Bool(*b)),
        Value::Int(i) => Ok(JsonValue::Number((*i).into())),
        Value::Float(f) => serde_json::Number::from_f64(*f)
            .map(JsonValue::Number)
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid float for JSON")
            }),
        Value::Str(s) => Ok(JsonValue::String(s.clone())),
        Value::Array(items) => {
            let mut out = Vec::with_capacity(items.len());
            for item in items {
                out.push(value_to_json(py, item, pool)?);
            }
            Ok(JsonValue::Array(out))
        }
        Value::Object(entries) => {
            let mut map = serde_json::Map::new();
            for (key, item) in entries {
                let key_str = key_to_string(py, key, pool)?;
                map.insert(key_str, value_to_json(py, item, pool)?);
            }
            Ok(JsonValue::Object(map))
        }
        Value::Opaque(id) => Ok(JsonValue::String(opaque_to_string(py, *id, pool)?)),
    }
}

pub fn validate_openapi(
    py: Python<'_>,
    spec: &Value,
    pool: &OpaquePool,
    strict: bool,
    base_url: Option<&str>,
) -> Result<(), PranceError> {
    if strict {
        ensure_string_keys(py, spec, pool)?;
    }

    let version = detect_version(spec)?;
    let instance = value_to_json(py, spec, pool).map_err(PranceError::from)?;

    validate_structural(version, &instance)?;

    semantic::validate_semantic(py, spec, pool, version, base_url)?;

    Ok(())
}

fn resolve_input_url(url: &str) -> Result<ParsedUrl, PranceError> {
    match absurl(url, None) {
        Ok(parsed) => Ok(parsed),
        Err(PranceError::Resolution(_)) => {
            let cwd = std::env::current_dir().map_err(|e| {
                PranceError::Validation(format!("Cannot resolve spec URL: {e}"))
            })?;
            let cwd_str = cwd.to_string_lossy();
            absurl(url, Some(cwd_str.as_ref()))
        }
        Err(e) => Err(e),
    }
}

pub fn load_openapi_spec(
    py: Python<'_>,
    spec_string: Option<&str>,
    url: Option<&str>,
    content_type: Option<&str>,
    strict: bool,
) -> Result<(Value, Option<String>), PranceError> {
    if let Some(text) = spec_string {
        let filename = url.unwrap_or("");
        let parsed = parse::parse_spec_text(text, filename, content_type, strict)?;
        Ok((parsed, url.map(str::to_string)))
    } else if let Some(u) = url {
        let parsed_url = resolve_input_url(u)?;
        let text = fetch::fetch_url_text(py, &parsed_url, None)?;
        let parsed = parse::parse_spec_text(&text, &parsed_url.path, content_type, strict)?;
        Ok((parsed, Some(parsed_url.geturl())))
    } else {
        Err(PranceError::Validation(
            "Either spec_string or url must be provided".into(),
        ))
    }
}

pub fn parse_and_validate(
    py: Python<'_>,
    spec_string: Option<&str>,
    url: Option<&str>,
    content_type: Option<&str>,
    strict: bool,
) -> Result<Value, PranceError> {
    let (value, base_url) = load_openapi_spec(py, spec_string, url, content_type, strict)?;
    let pool = OpaquePool::new();
    validate_openapi(py, &value, &pool, strict, base_url.as_deref())?;
    Ok(value)
}
