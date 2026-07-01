use indexmap::IndexMap;
use serde_json::Value as JsonValue;

use crate::error::PranceError;
use crate::value::{Key, Value};

#[derive(Clone, Copy, PartialEq, Eq)]
enum Format {
    Yaml,
    Json,
}

fn format_preferences(filename: Option<&str>, content_type: Option<&str>) -> Vec<Format> {
    let mut best = Format::Json;

    if let Some(ct) = content_type {
        let ct = ct.split(';').next().unwrap_or(ct).trim();
        if ct == "application/json" || ct == "application/javascript" {
            best = Format::Json;
        } else if ct == "application/yaml" || ct == "text/yaml" {
            best = Format::Yaml;
        }
    } else if let Some(fname) = filename {
        let lower = fname.to_lowercase();
        if lower.ends_with(".yaml") || lower.ends_with(".yml") {
            best = Format::Yaml;
        } else if lower.ends_with(".json") || lower.ends_with(".js") {
            best = Format::Json;
        }
    }

    let mut formats = vec![Format::Yaml, Format::Json];
    formats.retain(|f| *f != best);
    formats.insert(0, best);
    formats
}

pub fn parse_spec_text(
    text: &str,
    filename: &str,
    content_type: Option<&str>,
    strict: bool,
) -> Result<Value, PranceError> {
    let formats = format_preferences(Some(filename), content_type);
    let mut last_err = String::new();
    for fmt in formats {
        match fmt {
            Format::Json => match parse_json(text) {
                Ok(v) => return Ok(maybe_stringify_keys(v, strict)),
                Err(e) => last_err = e.to_string(),
            },
            Format::Yaml => match parse_yaml(text, strict) {
                Ok(v) => return Ok(maybe_stringify_keys(v, strict)),
                Err(e) => last_err = e.to_string(),
            },
        }
    }
    Err(PranceError::Parse(format!(
        "Could not detect format of spec string: {last_err}"
    )))
}

fn parse_json(text: &str) -> Result<Value, PranceError> {
    let j: JsonValue = serde_json::from_str(text)
        .map_err(|e| PranceError::Parse(e.to_string()))?;
    json_to_value(&j)
}

fn parse_yaml(text: &str, strict: bool) -> Result<Value, PranceError> {
    let y: serde_yaml::Value = serde_yaml::from_str(text)
        .map_err(|e| PranceError::Parse(e.to_string()))?;
    yaml_to_value(&y, strict)
}

fn maybe_stringify_keys(value: Value, strict: bool) -> Value {
    if strict {
        value
    } else {
        stringify_keys(value)
    }
}

fn stringify_keys(value: Value) -> Value {
    match value {
        Value::Object(entries) => Value::Object(
            entries
                .into_iter()
                .map(|(k, v)| {
                    let key = match k {
                        Key::Str(s) => Key::Str(s),
                        Key::Int(i) => Key::Str(i.to_string()),
                        Key::Opaque(id) => Key::Str(format!("<opaque:{id}>")),
                    };
                    (key, stringify_keys(v))
                })
                .collect(),
        ),
        Value::Array(items) => Value::Array(items.into_iter().map(stringify_keys).collect()),
        other => other,
    }
}

fn json_to_value(j: &JsonValue) -> Result<Value, PranceError> {
    match j {
        JsonValue::Null => Ok(Value::Null),
        JsonValue::Bool(b) => Ok(Value::Bool(*b)),
        JsonValue::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(Value::Int(i))
            } else if let Some(f) = n.as_f64() {
                Ok(Value::Float(f))
            } else {
                Err(PranceError::Parse("Unsupported JSON number".into()))
            }
        }
        JsonValue::String(s) => Ok(Value::Str(s.clone())),
        JsonValue::Array(items) => {
            let mut out = Vec::with_capacity(items.len());
            for item in items {
                out.push(json_to_value(item)?);
            }
            Ok(Value::Array(out))
        }
        JsonValue::Object(map) => {
            let mut out = Vec::with_capacity(map.len());
            for (k, v) in map {
                out.push((Key::Str(k.clone()), json_to_value(v)?));
            }
            Ok(Value::Object(out))
        }
    }
}

fn yaml_to_value(y: &serde_yaml::Value, strict: bool) -> Result<Value, PranceError> {
    match y {
        serde_yaml::Value::Null => Ok(Value::Null),
        serde_yaml::Value::Bool(b) => Ok(Value::Bool(*b)),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(Value::Int(i))
            } else if let Some(u) = n.as_u64() {
                Ok(Value::Int(u as i64))
            } else if let Some(f) = n.as_f64() {
                Ok(Value::Float(f))
            } else {
                Err(PranceError::Parse("Unsupported YAML number".into()))
            }
        }
        serde_yaml::Value::String(s) => Ok(Value::Str(s.clone())),
        serde_yaml::Value::Sequence(items) => {
            let mut out = Vec::with_capacity(items.len());
            for item in items {
                out.push(yaml_to_value(item, strict)?);
            }
            Ok(Value::Array(out))
        }
        serde_yaml::Value::Mapping(map) => {
            let mut out = Vec::with_capacity(map.len());
            for (k, v) in map {
                let key = yaml_key_to_key(k, strict)?;
                out.push((key, yaml_to_value(v, strict)?));
            }
            Ok(Value::Object(out))
        }
        serde_yaml::Value::Tagged(tagged) => yaml_to_value(&tagged.value, strict),
    }
}

fn yaml_key_to_key(k: &serde_yaml::Value, strict: bool) -> Result<Key, PranceError> {
    match k {
        serde_yaml::Value::String(s) => Ok(Key::Str(s.clone())),
        serde_yaml::Value::Number(n) => {
            if strict {
                if let Some(i) = n.as_i64() {
                    return Ok(Key::Int(i));
                }
            }
            if let Some(i) = n.as_i64() {
                Ok(Key::Str(i.to_string()))
            } else {
                Ok(Key::Str(n.to_string()))
            }
        }
        serde_yaml::Value::Bool(b) => Ok(Key::Str(b.to_string())),
        other => Ok(Key::Str(format!("{other:?}"))),
    }
}

pub fn value_from_json_map(map: IndexMap<String, Value>) -> Value {
    Value::Object(map.into_iter().map(|(k, v)| (Key::Str(k), v)).collect())
}
