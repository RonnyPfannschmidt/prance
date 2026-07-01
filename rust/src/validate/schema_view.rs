use std::collections::HashSet;

use pyo3::prelude::*;

use crate::error::PranceError;
use crate::fetch::{CacheKey, DocumentCache, fetch_url};
use crate::path::{PathPart, path_get};
use crate::url::{ParsedUrl, absurl, split_url_reference, urlresource};
use crate::value::{Key, Value};

use super::SpecVersion;

pub struct SemanticContext<'a> {
    pub root: &'a Value,
    pub base_url: Option<ParsedUrl>,
    pub cache: DocumentCache,
    pub version: SpecVersion,
    pub operation_ids: Vec<String>,
    pub strict: bool,
    pub schema_visited: HashSet<usize>,
}

impl<'a> SemanticContext<'a> {
    pub fn new(
        root: &'a Value,
        base_url: Option<ParsedUrl>,
        version: SpecVersion,
        strict: bool,
    ) -> Self {
        Self {
            root,
            base_url,
            cache: DocumentCache::default(),
            version,
            operation_ids: Vec::new(),
            strict,
            schema_visited: HashSet::new(),
        }
    }

    pub fn resolve_schema_node(
        &mut self,
        py: Python<'_>,
        value: &Value,
    ) -> Result<Value, PranceError> {
        if let Some(ref_str) = object_get_str(value, "$ref") {
            if ref_str.starts_with('#') && self.base_url.is_none() {
                return self.resolve_fragment_ref(ref_str);
            }
            let referer = self
                .base_url
                .clone()
                .ok_or_else(|| PranceError::Validation("Missing base URL for $ref".into()))?;
            self.resolve_ref_value(py, ref_str, &referer)
        } else {
            Ok(value.clone())
        }
    }

    fn resolve_fragment_ref(&self, reference: &str) -> Result<Value, PranceError> {
        let fragment = &reference[1..];
        let mut obj_path: Vec<String> = fragment.split('/').map(String::from).collect();
        while obj_path.first().map(|s| s.is_empty()).unwrap_or(false) {
            obj_path.remove(0);
        }
        let path: Vec<PathPart> = obj_path
            .iter()
            .map(|p| PathPart::Key(p.replace("~1", "/").replace("~0", "~")))
            .collect();
        path_get(self.root, &path).map_err(|e| PranceError::Validation(e.to_string()))
    }

    fn resolve_ref_value(
        &mut self,
        py: Python<'_>,
        reference: &str,
        referer: &ParsedUrl,
    ) -> Result<Value, PranceError> {
        let (target_url, fragment_path) = split_url_reference(Some(referer), reference)
            .map_err(|e| PranceError::Validation(e.to_string()))?;
        let document = self.load_document(py, &target_url)?;
        if fragment_path.is_empty() {
            return Ok(document);
        }
        let path: Vec<PathPart> = fragment_path
            .iter()
            .map(|p| PathPart::Key(p.clone()))
            .collect();
        path_get(&document, &path).map_err(|e| PranceError::Validation(e.to_string()))
    }

    fn load_document(&mut self, py: Python<'_>, url: &ParsedUrl) -> Result<Value, PranceError> {
        if self.is_same_resource(url) {
            return Ok(self.root.clone());
        }
        let key = CacheKey {
            resource: urlresource(url),
            strict: self.strict,
        };
        if let Some(doc) = self.cache.get_document(&key) {
            return Ok(doc);
        }
        fetch_url(py, url, &self.cache, None, self.strict)
            .map_err(|e| PranceError::Validation(e.to_string()))
    }

    fn is_same_resource(&self, url: &ParsedUrl) -> bool {
        self.base_url
            .as_ref()
            .map(|base| urlresource(base) == urlresource(url))
            .unwrap_or(false)
    }
}

pub fn object_get<'v>(value: &'v Value, key: &str) -> Option<&'v Value> {
    let Value::Object(entries) = value else {
        return None;
    };
    entries
        .iter()
        .find(|(k, _)| k.as_str() == Some(key))
        .map(|(_, v)| v)
}

pub fn object_get_str<'v>(value: &'v Value, key: &str) -> Option<&'v str> {
    match object_get(value, key)? {
        Value::Str(s) => Some(s.as_str()),
        _ => None,
    }
}

pub fn object_entries(value: &Value) -> Option<&[(Key, Value)]> {
    match value {
        Value::Object(entries) => Some(entries.as_slice()),
        _ => None,
    }
}

pub fn array_items(value: &Value) -> Option<&[Value]> {
    match value {
        Value::Array(items) => Some(items.as_slice()),
        _ => None,
    }
}

pub fn key_to_str(key: &Key) -> Option<&str> {
    key.as_str()
}

pub fn parse_base_url(base_url: Option<&str>) -> Result<Option<ParsedUrl>, PranceError> {
    let Some(url) = base_url else {
        return Ok(None);
    };
    if url.is_empty() {
        return Ok(None);
    }
    match absurl(url, None) {
        Ok(parsed) => Ok(Some(parsed)),
        Err(PranceError::Resolution(_)) => {
            let cwd = std::env::current_dir().map_err(|e| {
                PranceError::Validation(format!("Cannot resolve base URL: {e}"))
            })?;
            let cwd_str = cwd.to_string_lossy();
            absurl(url, Some(cwd_str.as_ref()))
                .map(Some)
                .map_err(|e| PranceError::Validation(e.to_string()))
        }
        Err(e) => Err(PranceError::Validation(e.to_string())),
    }
}

pub fn path_template_params(url: &str) -> Vec<String> {
    let mut params = Vec::new();
    let mut chars = url.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '{' {
            let mut name = String::new();
            for ch in chars.by_ref() {
                if ch == '}' {
                    if !name.is_empty() {
                        params.push(name);
                    }
                    break;
                }
                name.push(ch);
            }
        }
    }
    params
}

const OPERATIONS: &[&str] = &[
    "get", "put", "post", "delete", "options", "head", "patch", "trace",
];

pub fn is_operation(key: &str) -> bool {
    OPERATIONS.contains(&key)
}
