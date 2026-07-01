use pyo3::exceptions::{PyIndexError, PyKeyError, PyTypeError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

use crate::error::into_py_err;
use crate::url::{ParsedUrl, absurl, split_fragment_reference, split_url_reference, urlresource};

fn url_to_parsed(_py: Python<'_>, url: &Bound<'_, PyAny>) -> PyResult<ParsedUrl> {
    if let Ok(s) = url.extract::<String>() {
        return absurl(&s, None).map_err(into_py_err);
    }
    let scheme: String = url.getattr("scheme")?.extract()?;
    let netloc: String = url.getattr("netloc")?.extract()?;
    let path: String = url.getattr("path")?.extract()?;
    let params: String = url.getattr("params")?.extract().unwrap_or_default();
    let query: String = url.getattr("query")?.extract().unwrap_or_default();
    let fragment: String = url.getattr("fragment")?.extract().unwrap_or_default();
    Ok(ParsedUrl {
        scheme,
        netloc,
        path,
        params,
        query,
        fragment,
    })
}

fn optional_url_to_parsed(
    py: Python<'_>,
    url: Option<&Bound<'_, PyAny>>,
) -> PyResult<Option<ParsedUrl>> {
    let Some(url) = url else {
        return Ok(None);
    };
    if url.is_none() {
        return Ok(None);
    }
    Ok(Some(url_to_parsed(py, url)?))
}

fn parsed_to_py(py: Python<'_>, url: &ParsedUrl) -> PyResult<PyObject> {
    url.to_py_parse_result(py)
}

fn json_ref_escape(part: &str) -> String {
    part.replace('~', "~0").replace('/', "~1")
}

fn str_path(path: &[Py<PyAny>], py: Python<'_>) -> PyResult<String> {
    if path.is_empty() {
        return Ok("/".into());
    }
    let mut parts = Vec::with_capacity(path.len());
    for p in path {
        let s: String = p.bind(py).extract()?;
        parts.push(json_ref_escape(&s));
    }
    Ok(format!("/{}", parts.join("/")))
}

fn sequence_path(path: &Bound<'_, PyAny>) -> PyResult<Vec<Py<PyAny>>> {
    if path.is_instance_of::<PyTuple>() || path.is_instance_of::<PyList>() {
        path.try_iter()?.map(|p| Ok(p?.unbind())).collect()
    } else {
        Ok(Vec::new())
    }
}

#[pyfunction]
#[pyo3(name = "urlresource")]
fn urlresource_py(py: Python<'_>, url: &Bound<'_, PyAny>) -> PyResult<String> {
    let parsed = url_to_parsed(py, url)?;
    Ok(urlresource(&parsed))
}

#[pyfunction]
#[pyo3(name = "absurl")]
#[pyo3(signature = (url, relative_to=None))]
fn absurl_py(
    py: Python<'_>,
    url: &Bound<'_, PyAny>,
    relative_to: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    let url_str = if let Ok(s) = url.extract::<String>() {
        s
    } else {
        url.getattr("geturl")?.call0()?.extract()?
    };
    let rel_str = if let Some(rel) = relative_to {
        if rel.is_none() {
            None
        } else if let Ok(s) = rel.extract::<String>() {
            Some(s)
        } else {
            Some(rel.getattr("geturl")?.call0()?.extract()?)
        }
    } else {
        None
    };
    let parsed = absurl(&url_str, rel_str.as_deref()).map_err(into_py_err)?;
    parsed_to_py(py, &parsed)
}

#[pyfunction]
#[pyo3(name = "split_fragment_reference")]
fn split_fragment_reference_py(
    py: Python<'_>,
    base_url: Option<&Bound<'_, PyAny>>,
    reference: &str,
) -> PyResult<Option<PyObject>> {
    let base = optional_url_to_parsed(py, base_url)?;
    let result = split_fragment_reference(base.as_ref(), reference);
    match result {
        None => Ok(None),
        Some((url, obj_path)) => {
            let tuple = PyTuple::new(py, [parsed_to_py(py, &url)?, obj_path_to_py(py, &obj_path)?])?;
            Ok(Some(tuple.into()))
        }
    }
}

#[pyfunction]
#[pyo3(name = "split_url_reference")]
fn split_url_reference_py(
    py: Python<'_>,
    base_url: Option<&Bound<'_, PyAny>>,
    reference: &str,
) -> PyResult<PyObject> {
    let base = optional_url_to_parsed(py, base_url)?;
    let (url, obj_path) =
        split_url_reference(base.as_ref(), reference).map_err(into_py_err)?;
    PyTuple::new(py, [parsed_to_py(py, &url)?, obj_path_to_py(py, &obj_path)?]).map(|t| t.into())
}

fn obj_path_to_py(py: Python<'_>, obj_path: &[String]) -> PyResult<PyObject> {
    let tuple = PyTuple::new(py, obj_path.iter().map(|s| s.as_str()))?;
    Ok(tuple.into())
}

#[pyfunction]
fn fast_deepcopy_json(obj: &Bound<'_, PyAny>) -> PyResult<PyObject> {
    deepcopy_json(obj)
}

fn deepcopy_json(obj: &Bound<'_, PyAny>) -> PyResult<PyObject> {
    let py = obj.py();
    if obj.is_none() {
        return Ok(py.None());
    }
    if obj.is_instance_of::<PyBool>() {
        return Ok(obj.clone().unbind());
    }
    if obj.is_instance_of::<PyInt>() || obj.is_instance_of::<PyFloat>() || obj.is_instance_of::<PyString>() {
        return Ok(obj.clone().unbind());
    }
    if let Ok(d) = obj.downcast::<PyDict>() {
        let out = PyDict::new(py);
        for (k, v) in d.iter() {
            out.set_item(deepcopy_json(&k)?, deepcopy_json(&v)?)?;
        }
        return Ok(out.into());
    }
    if let Ok(l) = obj.downcast::<PyList>() {
        let out = PyList::empty(py);
        for item in l.iter() {
            out.append(deepcopy_json(&item)?)?;
        }
        return Ok(out.into());
    }
    if let Ok(t) = obj.downcast::<PyTuple>() {
        let mut items = Vec::with_capacity(t.len());
        for item in t.iter() {
            items.push(deepcopy_json(&item)?);
        }
        return PyTuple::new(py, items).map(|t| t.into());
    }
    Err(PyTypeError::new_err(format!(
        "fast_deepcopy_json does not support type {}",
        obj.get_type().name()?
    )))
}

fn extend_path(path_of_obj: &[Py<PyAny>], py: Python<'_>, segment: &Py<PyAny>) -> Vec<Py<PyAny>> {
    let mut next: Vec<Py<PyAny>> = path_of_obj.iter().map(|p| p.clone_ref(py)).collect();
    next.push(segment.clone_ref(py));
    next
}

#[pyfunction]
#[pyo3(signature = (obj, path, defaultvalue=None, path_of_obj=None))]
fn path_get(
    obj: &Bound<'_, PyAny>,
    path: Option<&Bound<'_, PyAny>>,
    defaultvalue: Option<&Bound<'_, PyAny>>,
    path_of_obj: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    let path_parts = match path {
        None => Vec::new(),
        Some(p) => {
            if !p.is_instance_of::<PyTuple>() && !p.is_instance_of::<PyList>() {
                return Err(PyTypeError::new_err(format!(
                    "Path is a {}, but must be None or a Collection!",
                    p.get_type().name()?
                )));
            }
            sequence_path(p)?
        }
    };
    let path_of_obj_vec = match path_of_obj {
        Some(p) => sequence_path(p)?,
        None => Vec::new(),
    };
    path_get_impl(obj.py(), obj, &path_parts, 0, defaultvalue, &path_of_obj_vec)
}

fn path_get_impl(
    py: Python<'_>,
    obj: &Bound<'_, PyAny>,
    path: &[Py<PyAny>],
    path_idx: usize,
    defaultvalue: Option<&Bound<'_, PyAny>>,
    path_of_obj: &[Py<PyAny>],
) -> PyResult<PyObject> {
    if let Ok(d) = obj.downcast::<PyDict>() {
        if path_idx >= path.len() {
            return value_or_default(obj, defaultvalue);
        }
        let key = path[path_idx].bind(py);
        if !d.contains(&key)? {
            let path_str = str_path(path_of_obj, py)?;
            let key_repr: String = key.extract().unwrap_or_else(|_| "?".into());
            return Err(PyKeyError::new_err(format!(
                "Object at \"{path_str}\" does not contain key: {key_repr}"
            )));
        }
        let value = d.get_item(&key)?.ok_or_else(|| {
            PyKeyError::new_err(format!("Missing key: {key_repr}", key_repr = key))
        })?;
        let next_path = extend_path(path_of_obj, py, &path[path_idx]);
        return path_get_impl(py, &value, path, path_idx + 1, defaultvalue, &next_path);
    }

    if let Ok(seq) = obj.downcast::<PyList>() {
        if path_idx >= path.len() {
            return value_or_default(obj, defaultvalue);
        }
        let idx_obj = path[path_idx].bind(py);
        let idx: usize = idx_obj.extract().map_err(|_| {
            let path_str = str_path(path_of_obj, py).unwrap_or_else(|_| "/".into());
            PyKeyError::new_err(format!(
                "Sequence at \"{path_str}\" needs integer indices only, but got: {idx_obj}"
            ))
        })?;
        if idx >= seq.len() {
            let path_str = str_path(path_of_obj, py)?;
            return Err(PyIndexError::new_err(format!(
                "Index out of bounds for sequence at \"{path_str}\": {idx}"
            )));
        }
        let next_path = extend_path(path_of_obj, py, &path[path_idx]);
        return path_get_impl(py, &seq.get_item(idx)?, path, path_idx + 1, defaultvalue, &next_path);
    }

    if let Ok(seq) = obj.downcast::<PyTuple>() {
        if path_idx >= path.len() {
            return value_or_default(obj, defaultvalue);
        }
        let idx_obj = path[path_idx].bind(py);
        let idx: usize = idx_obj.extract().map_err(|_| {
            let path_str = str_path(path_of_obj, py).unwrap_or_else(|_| "/".into());
            PyKeyError::new_err(format!(
                "Sequence at \"{path_str}\" needs integer indices only, but got: {idx_obj}"
            ))
        })?;
        if idx >= seq.len() {
            let path_str = str_path(path_of_obj, py)?;
            return Err(PyIndexError::new_err(format!(
                "Index out of bounds for sequence at \"{path_str}\": {idx}"
            )));
        }
        let next_path = extend_path(path_of_obj, py, &path[path_idx]);
        return path_get_impl(py, &seq.get_item(idx)?, path, path_idx + 1, defaultvalue, &next_path);
    }

    if path_idx < path.len() {
        return Err(PyTypeError::new_err(format!(
            "Cannot get anything from type {}!",
            obj.get_type().name()?
        )));
    }
    value_or_default(obj, defaultvalue)
}

fn value_or_default(
    obj: &Bound<'_, PyAny>,
    defaultvalue: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    if !obj.is_none() {
        return Ok(obj.clone().unbind());
    }
    if let Some(d) = defaultvalue {
        if !d.is_none() {
            return Ok(d.clone().unbind());
        }
    }
    Ok(obj.clone().unbind())
}

#[pyfunction]
#[pyo3(signature = (obj, path, value, create=false))]
fn path_set(
    obj: &Bound<'_, PyAny>,
    path: &Bound<'_, PyAny>,
    value: &Bound<'_, PyAny>,
    create: bool,
) -> PyResult<PyObject> {
    if !path.is_instance_of::<PyTuple>() && !path.is_instance_of::<PyList>() {
        return Err(PyTypeError::new_err(format!(
            "Path is a {}, but must be None or a Collection!",
            path.get_type().name()?
        )));
    }
    let path_parts = sequence_path(path)?;
    if path_parts.is_empty() {
        return Err(PyKeyError::new_err("Cannot set with an empty path!"));
    }
    path_set_impl(obj.py(), obj, &path_parts, 0, value, create)?;
    Ok(obj.clone().unbind())
}

fn path_set_impl(
    py: Python<'_>,
    obj: &Bound<'_, PyAny>,
    path: &[Py<PyAny>],
    path_idx: usize,
    value: &Bound<'_, PyAny>,
    create: bool,
) -> PyResult<()> {
    if let Ok(d) = obj.downcast::<PyDict>() {
        let key = path[path_idx].bind(py);
        if path_idx + 1 >= path.len() {
            if !create && !d.contains(&key)? {
                let key_repr: String = key.extract().unwrap_or_else(|_| "?".into());
                return Err(PyKeyError::new_err(format!("Key \"{key_repr}\" not in Mapping!")));
            }
            d.set_item(&key, value)?;
            return Ok(());
        }
        let child = if let Some(existing) = d.get_item(&key)? {
            existing
        } else {
            if !create {
                let key_repr: String = key.extract().unwrap_or_else(|_| "?".into());
                return Err(PyKeyError::new_err(format!("Key \"{key_repr}\" not in Mapping!")));
            }
            let next_key = path[path_idx + 1].bind(py);
            let new_child: PyObject = if next_key.extract::<i64>().is_ok() {
                PyList::empty(py).into()
            } else {
                PyDict::new(py).into()
            };
            d.set_item(&key, &new_child)?;
            new_child.bind(py).clone()
        };
        return path_set_impl(py, &child, path, path_idx + 1, value, create);
    }

    if let Ok(seq) = obj.downcast::<PyList>() {
        let idx_obj = path[path_idx].bind(py);
        let idx: usize = idx_obj.extract().map_err(|_| {
            PyKeyError::new_err("Sequences need integer indices only.")
        })?;
        if create {
            fill_sequence(seq, idx, path, path_idx + 1, py)?;
        }
        if path_idx + 1 >= path.len() {
            seq.set_item(idx, value)?;
            return Ok(());
        }
        let child = seq.get_item(idx)?;
        return path_set_impl(py, &child, path, path_idx + 1, value, create);
    }

    if obj.downcast::<PyTuple>().is_ok() {
        return Err(PyTypeError::new_err(format!(
            "Sequence is not mutable: {}",
            obj.get_type().name()?
        )));
    }

    Err(PyTypeError::new_err(format!(
        "Cannot set anything on type {}!",
        obj.get_type().name()?
    )))
}

fn fill_sequence(
    seq: &Bound<'_, PyList>,
    index: usize,
    path: &[Py<PyAny>],
    next_idx: usize,
    py: Python<'_>,
) -> PyResult<()> {
    while seq.len() < index {
        seq.append(py.None())?;
    }
    if seq.len() == index {
        let value_index_type = path
            .get(next_idx)
            .map(|k| k.bind(py).extract::<i64>().ok())
            .flatten();
        if value_index_type.is_some() {
            seq.append(PyList::empty(py))?;
        } else if next_idx >= path.len() {
            seq.append(py.None())?;
        } else {
            seq.append(PyDict::new(py))?;
        }
    }
    Ok(())
}

enum RefStackItem {
    ExitPath,
    PathSegment(Py<PyAny>),
    Container(Py<PyAny>),
}

#[pyclass]
struct ReferenceIterator {
    stack: Vec<RefStackItem>,
    path_stack: Vec<Py<PyAny>>,
}

#[pymethods]
impl ReferenceIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> PyResult<Option<PyObject>> {
        let py = slf.py();

        while let Some(item) = slf.stack.pop() {
            match item {
                RefStackItem::ExitPath => {
                    slf.path_stack.pop();
                    continue;
                }
                RefStackItem::PathSegment(seg) => {
                    slf.path_stack.push(seg);
                    continue;
                }
                RefStackItem::Container(container) => {
                    let item_bound = container.bind(py);

                    if let Ok(d) = item_bound.downcast::<PyDict>() {
                        let keys: Vec<Bound<'_, PyAny>> = d.keys().iter().collect();
                        for key in keys.into_iter().rev() {
                            let value = d.get_item(&key)?.ok_or_else(|| {
                                PyKeyError::new_err("Missing dict key during reference iteration")
                            })?;
                            let key_str: String = key.extract()?;
                            if key_str == "$ref" {
                                let path_tuple = PyTuple::new(
                                    py,
                                    slf.path_stack.iter().map(|p| p.bind(py).clone()),
                                )?;
                                let result = PyTuple::new(
                                    py,
                                    [
                                        PyString::new(py, &key_str).as_any(),
                                        value.as_any(),
                                        path_tuple.as_any(),
                                    ],
                                )?;
                                return Ok(Some(result.into()));
                            }
                            if value.is_instance_of::<PyDict>()
                                || value.is_instance_of::<PyList>()
                                || value.is_instance_of::<PyTuple>()
                            {
                                slf.stack.push(RefStackItem::ExitPath);
                                slf.stack.push(RefStackItem::Container(value.unbind()));
                                slf.stack.push(RefStackItem::PathSegment(key.unbind()));
                            }
                        }
                    } else if let Ok(seq) = item_bound.downcast::<PyList>() {
                        for idx in (0..seq.len()).rev() {
                            let value = seq.get_item(idx)?;
                            if value.is_instance_of::<PyDict>()
                                || value.is_instance_of::<PyList>()
                                || value.is_instance_of::<PyTuple>()
                            {
                                slf.stack.push(RefStackItem::ExitPath);
                                slf.stack.push(RefStackItem::Container(value.unbind()));
                                slf.stack.push(RefStackItem::PathSegment(
                                    idx.into_pyobject(py)?.into_any().unbind(),
                                ));
                            }
                        }
                    } else if let Ok(seq) = item_bound.downcast::<PyTuple>() {
                        for idx in (0..seq.len()).rev() {
                            let value = seq.get_item(idx)?;
                            if value.is_instance_of::<PyDict>()
                                || value.is_instance_of::<PyList>()
                                || value.is_instance_of::<PyTuple>()
                            {
                                slf.stack.push(RefStackItem::ExitPath);
                                slf.stack.push(RefStackItem::Container(value.unbind()));
                                slf.stack.push(RefStackItem::PathSegment(
                                    idx.into_pyobject(py)?.into_any().unbind(),
                                ));
                            }
                        }
                    }
                }
            }
        }
        Ok(None)
    }
}

#[pyfunction]
#[pyo3(signature = (specs, path=None))]
fn reference_iterator(py: Python<'_>, specs: &Bound<'_, PyAny>, path: Option<&Bound<'_, PyAny>>) -> PyResult<Py<ReferenceIterator>> {
    let mut stack = Vec::new();
    if specs.is_instance_of::<PyDict>()
        || specs.is_instance_of::<PyList>()
        || specs.is_instance_of::<PyTuple>()
    {
        stack.push(RefStackItem::Container(specs.clone().unbind()));
    }
    let path_stack = match path {
        Some(p) => sequence_path(p)?.into_iter().map(|s| s).collect(),
        None => Vec::new(),
    };
    Py::new(
        py,
        ReferenceIterator {
            stack,
            path_stack,
        },
    )
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(urlresource_py, m)?)?;
    m.add_function(wrap_pyfunction!(absurl_py, m)?)?;
    m.add_function(wrap_pyfunction!(split_fragment_reference_py, m)?)?;
    m.add_function(wrap_pyfunction!(split_url_reference_py, m)?)?;
    m.add_function(wrap_pyfunction!(fast_deepcopy_json, m)?)?;
    m.add_function(wrap_pyfunction!(path_get, m)?)?;
    m.add_function(wrap_pyfunction!(path_set, m)?)?;
    m.add_function(wrap_pyfunction!(reference_iterator, m)?)?;
    m.add_class::<ReferenceIterator>()?;
    Ok(())
}
