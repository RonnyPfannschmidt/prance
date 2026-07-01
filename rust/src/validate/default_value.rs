use pyo3::prelude::*;
use serde_json::Value as JsonValue;

use crate::convert::OpaquePool;
use crate::error::PranceError;
use crate::validate::{SpecVersion, value_to_json};
use crate::value::Value;

pub fn validate_schema_default(
    py: Python<'_>,
    version: SpecVersion,
    schema: &Value,
    pool: &OpaquePool,
) -> Result<(), PranceError> {
    let Some(default_val) = super::schema_view::object_get(schema, "default") else {
        return Ok(());
    };
    let nullable = super::schema_view::object_get(schema, "nullable")
        .and_then(|v| match v {
            Value::Bool(b) => Some(*b),
            _ => None,
        })
        .unwrap_or(false);
    if nullable && matches!(default_val, Value::Null) {
        return Ok(());
    }
    let schema_json = value_to_json(py, schema, pool).map_err(PranceError::from)?;
    let default_json = value_to_json(py, default_val, pool).map_err(PranceError::from)?;
    validate_instance(version, &schema_json, &default_json)
}

pub fn validate_parameter_default(
    py: Python<'_>,
    version: SpecVersion,
    parameter: &Value,
    pool: &OpaquePool,
) -> Result<(), PranceError> {
    let Some(default_val) = super::schema_view::object_get(parameter, "default") else {
        return Ok(());
    };
    if matches!(default_val, Value::Null) {
        return Ok(());
    }
    let schema_json = value_to_json(py, parameter, pool).map_err(PranceError::from)?;
    let default_json = value_to_json(py, default_val, pool).map_err(PranceError::from)?;
    validate_instance(version, &schema_json, &default_json)
}

fn validate_instance(
    version: SpecVersion,
    schema: &JsonValue,
    instance: &JsonValue,
) -> Result<(), PranceError> {
    let result = match version {
        SpecVersion::V31 => jsonschema::draft202012::validate(schema, instance),
        _ => jsonschema::draft4::validate(schema, instance),
    };
    result.map_err(|e| PranceError::Validation(e.to_string()))?;
    if let Some(format) = schema.get("format").and_then(JsonValue::as_str) {
        super::oas_format::check_oas_format(version, format, instance)?;
    }
    Ok(())
}
