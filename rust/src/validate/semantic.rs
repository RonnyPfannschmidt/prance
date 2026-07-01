use std::collections::HashSet;

use pyo3::prelude::*;

use crate::convert::OpaquePool;
use crate::error::PranceError;
use crate::validate::SpecVersion;
use crate::value::Value;

use crate::validate::default_value::{validate_parameter_default, validate_schema_default};
use crate::validate::schema_view::{
    SemanticContext, array_items, is_operation, key_to_str, object_entries, object_get,
    object_get_str, parse_base_url, path_template_params,
};

pub fn validate_semantic(
    py: Python<'_>,
    spec: &Value,
    pool: &OpaquePool,
    version: SpecVersion,
    base_url: Option<&str>,
) -> Result<(), PranceError> {
    let parsed_base = parse_base_url(base_url)?;
    let mut ctx = SemanticContext::new(spec, parsed_base, version, true);
    validate_root(py, &mut ctx, pool)
}

fn validate_root(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
) -> Result<(), PranceError> {
    if let Some(paths) = object_get(ctx.root, "paths") {
        validate_paths(py, ctx, pool, paths)?;
    }
    if let Some(components) = object_get(ctx.root, "components") {
        if let Some(schemas) = object_get(components, "schemas") {
            validate_schemas_map(py, ctx, pool, schemas)?;
        }
    }
    if ctx.version == SpecVersion::V2_0 {
        if let Some(definitions) = object_get(ctx.root, "definitions") {
            validate_schemas_map(py, ctx, pool, definitions)?;
        }
    }
    Ok(())
}

fn validate_paths(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    paths: &Value,
) -> Result<(), PranceError> {
    let Some(entries) = object_entries(paths) else {
        return Ok(());
    };
    for (key, path_item) in entries {
        let Some(url) = key_to_str(key) else {
            continue;
        };
        validate_path_item(py, ctx, pool, url, path_item)?;
    }
    Ok(())
}

fn validate_path_item(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    url: &str,
    path_item: &Value,
) -> Result<(), PranceError> {
    let path_parameters = object_get(path_item, "parameters");
    if let Some(parameters) = path_parameters {
        validate_parameters(py, ctx, pool, parameters)?;
    }

    let Some(entries) = object_entries(path_item) else {
        return Ok(());
    };
    for (key, operation) in entries {
        let Some(name) = key_to_str(key) else {
            continue;
        };
        if !is_operation(name) {
            continue;
        }
        validate_operation(py, ctx, pool, url, name, operation, path_parameters)?;
    }
    Ok(())
}

fn validate_operation(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    url: &str,
    method: &str,
    operation: &Value,
    path_parameters: Option<&Value>,
) -> Result<(), PranceError> {
    if let Some(operation_id) = object_get_str(operation, "operationId") {
        if ctx.operation_ids.iter().any(|id| id == operation_id) {
            return Err(PranceError::Validation(format!(
                "Operation ID '{operation_id}' for '{method}' in '{url}' is not unique"
            )));
        }
        ctx.operation_ids.push(operation_id.to_string());
    }

    if let Some(responses) = object_get(operation, "responses") {
        validate_responses(py, ctx, pool, responses)?;
    }

    let mut path_param_names = Vec::new();
    if let Some(parameters) = object_get(operation, "parameters") {
        validate_parameters(py, ctx, pool, parameters)?;
        path_param_names.extend(collect_path_param_names(parameters));
    }
    if let Some(parameters) = path_parameters {
        path_param_names.extend(collect_path_param_names(parameters));
    }
    path_param_names.sort();
    path_param_names.dedup();

    for param in path_template_params(url) {
        if !path_param_names.iter().any(|name| name == &param) {
            return Err(PranceError::Validation(format!(
                "Path parameter '{param}' for '{method}' operation in '{url}' was not resolved"
            )));
        }
    }
    Ok(())
}

fn collect_path_param_names(parameters: &Value) -> Vec<String> {
    let mut names = Vec::new();
    let Some(items) = array_items(parameters) else {
        return names;
    };
    for param in items {
        if object_get_str(param, "in") == Some("path") {
            if let Some(name) = object_get_str(param, "name") {
                names.push(name.to_string());
            }
        }
    }
    names
}

fn validate_parameters(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    parameters: &Value,
) -> Result<(), PranceError> {
    let Some(items) = array_items(parameters) else {
        return Ok(());
    };
    let mut seen = HashSet::new();
    for parameter in items {
        if let Some(schema) = object_get(parameter, "schema") {
            validate_schema(py, ctx, pool, schema, true)?;
        }
        if ctx.version == SpecVersion::V2_0 {
            validate_parameter_default(py, ctx.version, parameter, pool)?;
        }
        let name = object_get_str(parameter, "name").unwrap_or("");
        let location = object_get_str(parameter, "in").unwrap_or("");
        let key = (name.to_string(), location.to_string());
        if !seen.insert(key) {
            return Err(PranceError::Validation(format!(
                "Duplicate parameter `{name}`"
            )));
        }
    }
    Ok(())
}

fn validate_responses(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    responses: &Value,
) -> Result<(), PranceError> {
    let Some(entries) = object_entries(responses) else {
        return Ok(());
    };
    for (_, response) in entries {
        validate_response(py, ctx, pool, response)?;
    }
    Ok(())
}

fn validate_response(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    response: &Value,
) -> Result<(), PranceError> {
    match ctx.version {
        SpecVersion::V2_0 => {
            if let Some(schema) = object_get(response, "schema") {
                validate_schema(py, ctx, pool, schema, true)?;
            }
        }
        SpecVersion::V30 | SpecVersion::V31 => {
            if let Some(content) = object_get(response, "content") {
                let Some(entries) = object_entries(content) else {
                    return Ok(());
                };
                for (_, media_type) in entries {
                    if let Some(schema) = object_get(media_type, "schema") {
                        validate_schema(py, ctx, pool, schema, true)?;
                    }
                }
            }
        }
    }
    Ok(())
}

fn validate_schemas_map(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    schemas: &Value,
) -> Result<(), PranceError> {
    let Some(entries) = object_entries(schemas) else {
        return Ok(());
    };
    for (_, schema) in entries {
        validate_schema(py, ctx, pool, schema, true)?;
    }
    Ok(())
}

fn validate_schema(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    pool: &OpaquePool,
    schema: &Value,
    require_properties: bool,
) -> Result<(), PranceError> {
    let ptr = schema as *const Value;
    if !ctx.schema_visited.insert(ptr as usize) {
        return Ok(());
    }

    let resolved = ctx.resolve_schema_node(py, schema)?;

    let mut nested_properties = Vec::new();

    if let Some(all_of) = object_get(&resolved, "allOf") {
        if let Some(items) = array_items(all_of) {
            for inner in items {
                validate_schema(py, ctx, pool, inner, false)?;
                nested_properties.extend(collect_property_names(py, ctx, inner)?);
            }
        }
    }

    for keyword in ["anyOf", "oneOf"] {
        if let Some(items) = object_get(&resolved, keyword) {
            if let Some(branches) = array_items(items) {
                for inner in branches {
                    validate_schema(py, ctx, pool, inner, false)?;
                }
            }
        }
    }

    if let Some(not_schema) = object_get(&resolved, "not") {
        validate_schema(py, ctx, pool, not_schema, false)?;
    }

    if let Some(items) = object_get(&resolved, "items") {
        validate_schema(py, ctx, pool, items, false)?;
    }

    if let Some(properties) = object_get(&resolved, "properties") {
        if let Some(entries) = object_entries(properties) {
            for (_, prop_schema) in entries {
                validate_schema(py, ctx, pool, prop_schema, false)?;
            }
        }
    }

    if require_properties {
        if let Some(required) = object_get(&resolved, "required") {
            if let Some(required_names) = array_items(required) {
                let declared: HashSet<String> = object_get(&resolved, "properties")
                    .and_then(object_entries)
                    .map(|entries| {
                        entries
                            .iter()
                            .filter_map(|(k, _)| key_to_str(k).map(str::to_string))
                            .collect()
                    })
                    .unwrap_or_default();
                let nested: HashSet<String> = nested_properties.into_iter().collect();
                let mut extra = Vec::new();
                for name in required_names {
                    let Some(name_str) = value_as_str(name) else {
                        continue;
                    };
                    if !declared.contains(name_str) && !nested.contains(name_str) {
                        extra.push(name_str.to_string());
                    }
                }
                if !extra.is_empty() {
                    return Err(PranceError::Validation(format!(
                        "Required list has not defined properties: {extra:?}"
                    )));
                }
            }
        }
    }

    validate_schema_default(py, ctx.version, &resolved, pool)?;

    Ok(())
}

fn collect_property_names(
    py: Python<'_>,
    ctx: &mut SemanticContext<'_>,
    schema: &Value,
) -> Result<Vec<String>, PranceError> {
    let resolved = ctx.resolve_schema_node(py, schema)?;
    let mut names = Vec::new();
    if let Some(properties) = object_get(&resolved, "properties") {
        if let Some(entries) = object_entries(properties) {
            for (key, _) in entries {
                if let Some(name) = key_to_str(key) {
                    names.push(name.to_string());
                }
            }
        }
    }
    for keyword in ["allOf", "anyOf", "oneOf"] {
        if let Some(items) = object_get(&resolved, keyword) {
            if let Some(branches) = array_items(items) {
                for inner in branches {
                    names.extend(collect_property_names(py, ctx, inner)?);
                }
            }
        }
    }
    if let Some(items) = object_get(&resolved, "items") {
        names.extend(collect_property_names(py, ctx, items)?);
    }
    if let Some(not_schema) = object_get(&resolved, "not") {
        names.extend(collect_property_names(py, ctx, not_schema)?);
    }
    Ok(names)
}

fn value_as_str(value: &Value) -> Option<&str> {
    match value {
        Value::Str(s) => Some(s.as_str()),
        _ => None,
    }
}
