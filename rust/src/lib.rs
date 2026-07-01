mod convert;
mod error;
mod fetch;
mod parse;
mod path;
mod prefetch;
mod pyprimitives;
mod resolver;
mod url;
mod validate;
mod value;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use std::sync::{Arc, Mutex};

use crate::convert::{OpaquePool, py_to_value, value_to_py};
use crate::error::into_py_err;
use crate::prefetch::{build_cache_with_root, prefetch_external_documents};
use crate::resolver::{ResolveOptions, resolve_value};
use crate::url::{ParsedUrl, absurl};
use crate::validate::{load_openapi_spec, parse_and_validate, validate_openapi};
use crate::value::Value;

pub const RESOLVE_INTERNAL: u32 = 2;
pub const RESOLVE_HTTP: u32 = 4;
pub const RESOLVE_FILES: u32 = 8;
pub const RESOLVE_ALL: u32 = RESOLVE_INTERNAL | RESOLVE_HTTP | RESOLVE_FILES;
pub const TRANSLATE_EXTERNAL: u32 = 0;
pub const TRANSLATE_DEFAULT: u32 = 1;

const PREFETCH_THRESHOLD: usize = 2;

fn parse_options(dict: Option<&Bound<'_, PyDict>>) -> PyResult<ResolveOptions> {
    let mut opts = ResolveOptions::default();
    let Some(d) = dict else {
        return Ok(opts);
    };
    if let Ok(v) = d.get_item("copy_input") {
        if let Some(b) = v {
            opts.copy_input = b.extract().unwrap_or(true);
        }
    }
    if let Ok(v) = d.get_item("recursion_limit") {
        if let Some(n) = v {
            opts.recursion_limit = n.extract().unwrap_or(1);
        }
    }
    if let Ok(v) = d.get_item("resolve_types") {
        if let Some(n) = v {
            opts.resolve_types = n.extract().unwrap_or(RESOLVE_ALL);
        }
    }
    if let Ok(v) = d.get_item("resolve_method") {
        if let Some(n) = v {
            opts.resolve_method = n.extract().unwrap_or(TRANSLATE_DEFAULT);
        }
    }
    if let Ok(v) = d.get_item("encoding") {
        if let Some(s) = v {
            if !s.is_none() {
                opts.encoding = Some(s.extract()?);
            }
        }
    }
    if let Ok(v) = d.get_item("strict") {
        if let Some(b) = v {
            opts.strict = b.extract().unwrap_or(true);
        }
    }
    if let Ok(v) = d.get_item("fragment_copy") {
        if let Some(b) = v {
            opts.fragment_copy = b.extract().unwrap_or(true);
        }
    }
    if let Ok(v) = d.get_item("recursion_limit_handler") {
        if let Some(h) = v {
            if !h.is_none() {
                opts.recursion_limit_handler = Some(h.unbind());
            }
        }
    }
    Ok(opts)
}

fn resolve_internal(
    py: Python<'_>,
    value: Value,
    pool: OpaquePool,
    base_url: Option<ParsedUrl>,
    opts: &ResolveOptions,
) -> PyResult<(Value, OpaquePool)> {
    let opts = opts.clone_for_thread(py);
    let pool = Arc::new(Mutex::new(pool));
    let cache = build_cache_with_root(&value, base_url.as_ref(), opts.strict, pool.clone());
    prefetch_external_documents(
        &value,
        base_url.as_ref(),
        &opts,
        PREFETCH_THRESHOLD,
        &cache,
        py,
    )
    .map_err(into_py_err)?;

    let resolved = py
        .allow_threads(|| resolve_value(value, base_url, opts, cache))
        .map_err(into_py_err)?;
    let pool = Arc::try_unwrap(pool)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("pool still shared"))?
        .into_inner()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok((resolved, pool))
}

#[pyfunction]
#[pyo3(signature = (spec_string=None, url=None, content_type=None, **options))]
fn resolve_spec(
    py: Python<'_>,
    spec_string: Option<&str>,
    url: Option<&str>,
    content_type: Option<&str>,
    options: Option<&Bound<'_, PyDict>>,
) -> PyResult<PyObject> {
    let opts = parse_options(options)?;
    let pool = OpaquePool::new();

    let (mut value, base_url) = if let Some(text) = spec_string {
        let filename = url.unwrap_or("");
        let parsed = parse::parse_spec_text(text, filename, content_type, opts.strict)
            .map_err(into_py_err)?;
        let base = url.and_then(|u| absurl(u, None).ok());
        (parsed, base)
    } else if let Some(u) = url {
        let parsed_url = absurl(u, None).map_err(into_py_err)?;
        let text = fetch::fetch_url_text(py, &parsed_url, opts.encoding.as_deref())
            .map_err(into_py_err)?;
        let parsed = parse::parse_spec_text(&text, &parsed_url.path, content_type, opts.strict)
            .map_err(into_py_err)?;
        (parsed, Some(parsed_url))
    } else {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Either spec_string or url must be provided",
        ));
    };

    if opts.copy_input {
        value = value.deep_copy();
    }

    let (resolved, pool) = resolve_internal(py, value, pool, base_url, &opts)?;
    value_to_py(py, &resolved, &pool)
}

fn url_arg_to_parsed(py: Python<'_>, url: Option<&Bound<'_, PyAny>>) -> PyResult<Option<ParsedUrl>> {
    let Some(url) = url else {
        return Ok(None);
    };
    if url.is_none() {
        return Ok(None);
    }
    if let Ok(s) = url.extract::<String>() {
        return absurl(&s, None).map(Some).map_err(into_py_err);
    }
    let url_str: String = url.getattr("geturl")?.call0()?.extract()?;
    absurl(&url_str, None).map(Some).map_err(into_py_err)
}

#[pyclass]
struct RefResolver {
    specs: PyObject,
    url: Option<String>,
    parsed_url: Option<ParsedUrl>,
    options: ResolveOptions,
    resolved: Option<Value>,
    pool: OpaquePool,
}

#[pymethods]
impl RefResolver {
    #[new]
    #[pyo3(signature = (specs, url=None, **options))]
    fn new(
        py: Python<'_>,
        specs: Bound<'_, PyAny>,
        url: Option<&Bound<'_, PyAny>>,
        options: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        let mut opts = parse_options(options)?;
        let mut pool = OpaquePool::new();
        let _value = py_to_value(&specs, &mut pool)?;

        if !opts.copy_input {
            opts.copy_input = false;
        }

        let parsed_url = url_arg_to_parsed(py, url)?;
        let url_string = parsed_url.as_ref().map(|u| u.geturl());

        Ok(Self {
            specs: specs.unbind().into(),
            url: url_string,
            parsed_url,
            options: opts,
            resolved: None,
            pool,
        })
    }

    #[getter]
    fn get_specs(&self, py: Python<'_>) -> PyResult<PyObject> {
        if let Some(ref v) = self.resolved {
            value_to_py(py, v, &self.pool)
        } else {
            Ok(self.specs.clone_ref(py))
        }
    }

    #[setter]
    fn set_specs(&mut self, specs: PyObject) {
        self.specs = specs;
        self.resolved = None;
    }

    #[getter]
    fn get_parsed_url(&self, py: Python<'_>) -> PyResult<PyObject> {
        match &self.parsed_url {
            Some(u) => Ok(u.to_py_parse_result(py)?),
            None => Ok(py.None()),
        }
    }

    fn resolve_references(&mut self, py: Python<'_>) -> PyResult<()> {
        let mut pool = std::mem::take(&mut self.pool);
        let specs = self.specs.bind(py);
        let mut value = py_to_value(specs, &mut pool)?;

        if self.options.copy_input {
            value = value.deep_copy();
        }

        let (resolved, pool) =
            resolve_internal(py, value, pool, self.parsed_url.clone(), &self.options)?;
        self.resolved = Some(resolved);
        self.pool = pool;
        Ok(())
    }
}

#[pyfunction]
#[pyo3(signature = (spec, url=None, strict=true))]
fn validate_openapi_spec(
    py: Python<'_>,
    spec: Bound<'_, PyAny>,
    url: Option<&str>,
    strict: bool,
) -> PyResult<()> {
    let mut pool = OpaquePool::new();
    let value = py_to_value(&spec, &mut pool)?;
    validate_openapi(py, &value, &pool, strict, url).map_err(into_py_err)
}

#[pyfunction]
#[pyo3(signature = (spec_string=None, url=None, content_type=None, strict=true))]
fn load_openapi_spec_py(
    py: Python<'_>,
    spec_string: Option<&str>,
    url: Option<&str>,
    content_type: Option<&str>,
    strict: bool,
) -> PyResult<PyObject> {
    let (value, _) = load_openapi_spec(py, spec_string, url, content_type, strict).map_err(into_py_err)?;
    let pool = OpaquePool::new();
    value_to_py(py, &value, &pool)
}

#[pyfunction]
#[pyo3(signature = (spec_string=None, url=None, content_type=None, strict=true))]
fn parse_and_validate_spec(
    py: Python<'_>,
    spec_string: Option<&str>,
    url: Option<&str>,
    content_type: Option<&str>,
    strict: bool,
) -> PyResult<PyObject> {
    let value = parse_and_validate(py, spec_string, url, content_type, strict).map_err(into_py_err)?;
    let pool = OpaquePool::new();
    value_to_py(py, &value, &pool)
}

#[pymodule]
fn _prance_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RefResolver>()?;
    m.add_function(wrap_pyfunction!(resolve_spec, m)?)?;
    m.add_function(wrap_pyfunction!(validate_openapi_spec, m)?)?;
    m.add_function(wrap_pyfunction!(load_openapi_spec_py, m)?)?;
    m.add_function(wrap_pyfunction!(parse_and_validate_spec, m)?)?;
    m.add("RESOLVE_INTERNAL", RESOLVE_INTERNAL)?;
    m.add("RESOLVE_HTTP", RESOLVE_HTTP)?;
    m.add("RESOLVE_FILES", RESOLVE_FILES)?;
    m.add("RESOLVE_ALL", RESOLVE_ALL)?;
    m.add("TRANSLATE_EXTERNAL", TRANSLATE_EXTERNAL)?;
    m.add("TRANSLATE_DEFAULT", TRANSLATE_DEFAULT)?;
    pyprimitives::register(m)?;
    Ok(())
}
