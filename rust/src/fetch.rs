use std::fs;
use std::path::Path;

use chardetng::EncodingDetector;
use std::sync::{Arc, Mutex};

use dashmap::DashMap;
use encoding_rs::Encoding;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::convert::{OpaquePool, py_to_value};
use crate::error::PranceError;
use crate::url::{ParsedUrl, from_posix, urlresource};
use crate::value::Value;

#[derive(Clone, Hash, PartialEq, Eq)]
pub struct CacheKey {
    pub resource: String,
    pub strict: bool,
}

pub struct DocumentCache {
    text_cache: DashMap<String, (String, Option<String>)>,
    doc_cache: DashMap<CacheKey, Value>,
    pool: Arc<Mutex<OpaquePool>>,
}

impl DocumentCache {
    pub fn new(pool: Arc<Mutex<OpaquePool>>) -> Self {
        Self {
            text_cache: DashMap::new(),
            doc_cache: DashMap::new(),
            pool,
        }
    }

    pub fn pool(&self) -> &Arc<Mutex<OpaquePool>> {
        &self.pool
    }

    pub fn get_document(&self, key: &CacheKey) -> Option<Value> {
        self.doc_cache.get(key).map(|v| v.clone())
    }

    pub fn insert_document(&self, key: CacheKey, value: Value) {
        self.doc_cache.insert(key, value);
    }
}

impl Default for DocumentCache {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(OpaquePool::new())))
    }
}

pub fn detect_encoding(bytes: &[u8]) -> &'static Encoding {
    let mut detector = EncodingDetector::new();
    detector.feed(bytes, true);
    detector.guess(None, true)
}

pub fn read_file_bytes(path: &str, encoding: Option<&str>) -> Result<String, PranceError> {
    let mut platform_path = from_posix(path);
    if let Some(stripped) = platform_path.strip_prefix("file://") {
        platform_path = stripped.to_string();
    } else if let Some(stripped) = platform_path.strip_prefix("file:") {
        platform_path = stripped.to_string();
    }
    let bytes = fs::read(&platform_path).map_err(|e| {
        PranceError::Resolution(format!("File not found: {path} ({e})"))
    })?;

    if let Some(enc) = encoding {
        let encoding = Encoding::for_label(enc.as_bytes())
            .ok_or_else(|| PranceError::Io(format!("Unknown encoding: {enc}")))?;
        let (cow, _, _) = encoding.decode(&bytes);
        return Ok(cow.into_owned());
    }

    if let Ok(s) = std::str::from_utf8(&bytes) {
        return Ok(s.to_string());
    }

    let ext = Path::new(&platform_path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();
    if matches!(ext.as_str(), "json" | "yaml" | "yml" | "js") {
        if let Ok(s) = String::from_utf8(bytes.clone()) {
            return Ok(s);
        }
    }

    let encoding = detect_encoding(&bytes);
    let (cow, _, _) = encoding.decode(&bytes);
    Ok(cow.into_owned())
}

pub fn fetch_url_text(py: Python<'_>, url: &ParsedUrl, encoding: Option<&str>) -> Result<String, PranceError> {
    let url_mod = py.import("prance.util.url")?;
    let py_url = url.to_py_parse_result(py)?;
    let result = if let Some(enc) = encoding {
        let kwargs = PyDict::new(py);
        kwargs.set_item("encoding", enc)?;
        url_mod.call_method("fetch_url_text", (py_url,), Some(&kwargs))?
    } else {
        url_mod.call_method1("fetch_url_text", (py_url,))?
    };
    let content: String = result.get_item(0)?.extract()?;
    Ok(content)
}

pub fn fetch_url(
    py: Python<'_>,
    url: &ParsedUrl,
    cache: &DocumentCache,
    encoding: Option<&str>,
    strict: bool,
) -> Result<Value, PranceError> {
    let key = CacheKey {
        resource: urlresource(url),
        strict,
    };
    if let Some(doc) = cache.get_document(&key) {
        return Ok(doc.deep_copy());
    }

    let url_mod = py.import("prance.util.url")?;
    let py_url = url.to_py_parse_result(py)?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("strict", strict)?;
    kwargs.set_item("copy", false)?;
    if let Some(enc) = encoding {
        kwargs.set_item("encoding", enc)?;
    }
    let result = url_mod.call_method("fetch_url", (py_url,), Some(&kwargs))?;
    let mut pool = cache.pool().lock().map_err(|e| {
        PranceError::Value(format!("Opaque pool lock poisoned: {e}"))
    })?;
    let value = py_to_value(&result, &mut pool)
        .map_err(|e| PranceError::Value(e.to_string()))?;
    cache.insert_document(key, value.deep_copy());
    Ok(value)
}

pub fn fetch_url_text_cached(
    py: Python<'_>,
    url: &ParsedUrl,
    cache: &DocumentCache,
    encoding: Option<&str>,
) -> Result<String, PranceError> {
    let text_key = format!("text_{}", urlresource(url));
    if let Some(entry) = cache.text_cache.get(&text_key) {
        return Ok(entry.0.clone());
    }
    let text = fetch_url_text(py, url, encoding)?;
    cache.text_cache.insert(text_key, (text.clone(), None));
    Ok(text)
}
