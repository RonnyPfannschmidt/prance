use std::fmt;

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Array(Vec<Value>),
    Object(Vec<(Key, Value)>),
    Opaque(u32),
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum Key {
    Str(String),
    Int(i64),
    Opaque(u32),
}

impl Key {
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Key::Str(s) => Some(s),
            Key::Int(_) | Key::Opaque(_) => None,
        }
    }

    pub fn to_display(&self) -> String {
        match self {
            Key::Str(s) => s.clone(),
            Key::Int(i) => i.to_string(),
            Key::Opaque(id) => format!("<opaque:{id}>"),
        }
    }
}

impl Value {
    pub fn deep_copy(&self) -> Self {
        match self {
            Value::Null => Value::Null,
            Value::Bool(b) => Value::Bool(*b),
            Value::Int(i) => Value::Int(*i),
            Value::Float(f) => Value::Float(*f),
            Value::Str(s) => Value::Str(s.clone()),
            Value::Array(items) => Value::Array(items.iter().map(Value::deep_copy).collect()),
            Value::Object(entries) => Value::Object(
                entries
                    .iter()
                    .map(|(k, v)| (k.clone(), v.deep_copy()))
                    .collect(),
            ),
            Value::Opaque(id) => Value::Opaque(*id),
        }
    }

    pub fn is_mapping(&self) -> bool {
        matches!(self, Value::Object(_))
    }

    pub fn is_sequence(&self) -> bool {
        matches!(self, Value::Array(_))
    }
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Null => write!(f, "null"),
            Value::Bool(b) => write!(f, "{b}"),
            Value::Int(i) => write!(f, "{i}"),
            Value::Float(v) => write!(f, "{v}"),
            Value::Str(s) => write!(f, "{s}"),
            Value::Array(_) => write!(f, "[...]"),
            Value::Object(_) => write!(f, "{{...}}"),
            Value::Opaque(id) => write!(f, "<opaque:{id}>"),
        }
    }
}
