use crate::error::PranceError;
use crate::value::{Key, Value};

#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum PathPart {
    Key(String),
    Index(usize),
}

pub type Path = Vec<PathPart>;

pub fn path_get(value: &Value, path: &[PathPart]) -> Result<Value, PranceError> {
    path_get_impl(value, path, &[])
}

fn path_get_impl(value: &Value, path: &[PathPart], path_of_obj: &[PathPart]) -> Result<Value, PranceError> {
    if path.is_empty() {
        return Ok(value.clone());
    }

    match value {
        Value::Object(entries) => {
            let part = &path[0];
            let key = match part {
                PathPart::Key(k) => k,
                PathPart::Index(i) => {
                    return Err(PranceError::Resolution(format!(
                        "Object at \"{}\" does not contain key: {}",
                        str_path(path_of_obj),
                        i
                    )));
                }
            };
            for (k, v) in entries {
                if k.as_str() == Some(key) {
                    return path_get_impl(v, &path[1..], &append_path(path_of_obj, part));
                }
            }
            Err(PranceError::Resolution(format!(
                "Object at \"{}\" does not contain key: {}",
                str_path(path_of_obj),
                key
            )))
        }
        Value::Array(items) => {
            let idx = match &path[0] {
                PathPart::Index(i) => *i,
                PathPart::Key(k) => k.parse::<usize>().map_err(|_| {
                    PranceError::Resolution(format!(
                        "Sequence at \"{}\" needs integer indices only, but got: {}",
                        str_path(path_of_obj),
                        k
                    ))
                })?,
            };
            if idx >= items.len() {
                return Err(PranceError::Resolution(format!(
                    "Index out of bounds for sequence at \"{}\": {}",
                    str_path(path_of_obj),
                    idx
                )));
            }
            path_get_impl(&items[idx], &path[1..], &append_path(path_of_obj, &path[0]))
        }
        _ => {
            if path.is_empty() {
                Ok(value.clone())
            } else {
                Err(PranceError::Resolution(format!(
                    "Cannot get anything from type {}",
                    type_name(value)
                )))
            }
        }
    }
}

pub fn path_set(value: &mut Value, path: &[PathPart], new_value: Value) -> Result<(), PranceError> {
    if path.is_empty() {
        return Err(PranceError::Resolution(
            "Cannot set with an empty path!".into(),
        ));
    }
    path_set_impl(value, path, new_value)
}

fn path_set_impl(value: &mut Value, path: &[PathPart], new_value: Value) -> Result<(), PranceError> {
    if path.len() == 1 {
        return apply_leaf(value, &path[0], new_value);
    }

    match value {
        Value::Object(entries) => {
            let key = match &path[0] {
                PathPart::Key(k) => k.clone(),
                PathPart::Index(i) => i.to_string(),
            };
            for (k, v) in entries.iter_mut() {
                if k.as_str() == Some(&key) {
                    return path_set_impl(v, &path[1..], new_value);
                }
            }
            let mut child = match &path[1] {
                PathPart::Index(_) => Value::Array(Vec::new()),
                PathPart::Key(_) => Value::Object(Vec::new()),
            };
            path_set_impl(&mut child, &path[1..], new_value)?;
            entries.push((Key::Str(key), child));
            Ok(())
        }
        Value::Array(items) => {
            let idx = match &path[0] {
                PathPart::Index(i) => *i,
                PathPart::Key(k) => k.parse().map_err(|_| {
                    PranceError::Resolution("Sequences need integer indices only.".into())
                })?,
            };
            while items.len() <= idx {
                items.push(Value::Null);
            }
            path_set_impl(&mut items[idx], &path[1..], new_value)
        }
        _ => Err(PranceError::Resolution(format!(
            "Cannot set anything on type {}",
            type_name(value)
        ))),
    }
}

fn apply_leaf(value: &mut Value, part: &PathPart, new_value: Value) -> Result<(), PranceError> {
    match value {
        Value::Object(entries) => {
            let key = match part {
                PathPart::Key(k) => k.clone(),
                PathPart::Index(i) => i.to_string(),
            };
            for (k, v) in entries.iter_mut() {
                if k.as_str() == Some(&key) {
                    *v = new_value;
                    return Ok(());
                }
            }
            entries.push((Key::Str(key), new_value));
            Ok(())
        }
        Value::Array(items) => {
            let idx = match part {
                PathPart::Index(i) => *i,
                PathPart::Key(k) => k.parse().map_err(|_| {
                    PranceError::Resolution("Sequences need integer indices only.".into())
                })?,
            };
            while items.len() <= idx {
                items.push(Value::Null);
            }
            items[idx] = new_value;
            Ok(())
        }
        _ => Err(PranceError::Resolution(format!(
            "Cannot set anything on type {}",
            type_name(value)
        ))),
    }
}

pub fn obj_path_to_rust(obj_path: &[String]) -> Path {
    obj_path
        .iter()
        .map(|p| {
            if let Ok(i) = p.parse::<usize>() {
                PathPart::Index(i)
            } else {
                PathPart::Key(p.clone())
            }
        })
        .collect()
}

fn append_path(path: &[PathPart], part: &PathPart) -> Vec<PathPart> {
    let mut out = path.to_vec();
    out.push(part.clone());
    out
}

fn json_ref_escape(part: &str) -> String {
    part.replace('~', "~0").replace('/', "~1")
}

pub fn str_path(path: &[PathPart]) -> String {
    if path.is_empty() {
        return "/".into();
    }
    let parts: Vec<String> = path
        .iter()
        .map(|p| match p {
            PathPart::Key(k) => json_ref_escape(k),
            PathPart::Index(i) => i.to_string(),
        })
        .collect();
    format!("/{}", parts.join("/"))
}

fn type_name(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "bool",
        Value::Int(_) => "int",
        Value::Float(_) => "float",
        Value::Str(_) => "str",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
        Value::Opaque(_) => "opaque",
    }
}
