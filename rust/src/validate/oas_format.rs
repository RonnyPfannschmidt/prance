use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use serde_json::Value as JsonValue;

use crate::error::PranceError;
use crate::validate::SpecVersion;

pub fn check_oas_format(
    version: SpecVersion,
    format: &str,
    instance: &JsonValue,
) -> Result<(), PranceError> {
    let valid = match format {
        "int32" => is_int32(instance),
        "int64" => is_int64(instance),
        "float" => is_float(instance),
        "double" => is_double(instance),
        "password" => true,
        "byte" if matches!(version, SpecVersion::V30 | SpecVersion::V2_0) => is_byte(instance),
        "binary" if matches!(version, SpecVersion::V30 | SpecVersion::V2_0) => is_binary(instance),
        _ => return Ok(()),
    };
    if valid {
        Ok(())
    } else {
        Err(PranceError::Validation(format!(
            "{} is not a \"{format}\"",
            instance_display(instance)
        )))
    }
}

fn instance_display(instance: &JsonValue) -> String {
    match instance {
        JsonValue::String(s) => s.clone(),
        other => other.to_string(),
    }
}

fn is_int32(instance: &JsonValue) -> bool {
    match instance {
        JsonValue::Bool(_) => true,
        JsonValue::Number(n) => n
            .as_i64()
            .map(in_openapi_int32)
            .unwrap_or(true),
        _ => true,
    }
}

fn is_int64(instance: &JsonValue) -> bool {
    match instance {
        JsonValue::Bool(_) => true,
        JsonValue::Number(n) => n
            .as_i64()
            .map(in_openapi_int64)
            .unwrap_or(true),
        _ => true,
    }
}

fn in_openapi_int32(i: i64) -> bool {
    i > -(1i64 << 31) - 1 && i < 1i64 << 31
}

fn in_openapi_int64(i: i64) -> bool {
    let v = i as i128;
    v > -(1i128 << 63) - 1 && v < (1i128 << 63)
}

fn is_float(instance: &JsonValue) -> bool {
    match instance {
        JsonValue::Number(n) if n.is_i64() || n.is_u64() => true,
        JsonValue::Number(n) => n.as_f64().map(|f| (f as f32) as f64 == f).unwrap_or(false),
        _ => true,
    }
}

fn is_double(instance: &JsonValue) -> bool {
    match instance {
        JsonValue::Number(n) if n.is_i64() || n.is_u64() => true,
        JsonValue::Number(n) => n.is_f64(),
        _ => true,
    }
}

fn is_binary(instance: &JsonValue) -> bool {
    match instance {
        JsonValue::String(_) => false,
        _ => true,
    }
}

fn is_byte(instance: &JsonValue) -> bool {
    let JsonValue::String(s) = instance else {
        return true;
    };
    let Ok(decoded) = STANDARD.decode(s.as_bytes()) else {
        return false;
    };
    STANDARD.encode(decoded) == *s
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn int32_in_range() {
        assert!(is_int32(&json!(42)));
        assert!(is_int32(&json!(2_147_483_647)));
        assert!(!is_int32(&json!(2_147_483_648)));
    }

    #[test]
    fn byte_roundtrip() {
        assert!(is_byte(&json!("Zm9v")));
        assert!(!is_byte(&json!("not-base64!!!")));
    }
}
