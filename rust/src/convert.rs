use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

use crate::value::{Key, Value};

pub struct OpaquePool {
    objects: Vec<Py<PyAny>>,
}

impl OpaquePool {
    pub fn new() -> Self {
        Self {
            objects: Vec::new(),
        }
    }

    pub fn push(&mut self, obj: Bound<'_, PyAny>) -> u32 {
        let id = self.objects.len() as u32;
        self.objects.push(obj.unbind());
        id
    }

    pub fn get(&self, id: u32) -> Option<&Py<PyAny>> {
        self.objects.get(id as usize)
    }
}

impl Default for OpaquePool {
    fn default() -> Self {
        Self::new()
    }
}

pub fn py_to_value(obj: &Bound<'_, PyAny>, pool: &mut OpaquePool) -> PyResult<Value> {
    if obj.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(b) = obj.downcast::<PyBool>() {
        return Ok(Value::Bool(b.is_true()));
    }
    if let Ok(i) = obj.downcast::<PyInt>() {
        return Ok(Value::Int(i.extract()?));
    }
    if let Ok(f) = obj.downcast::<PyFloat>() {
        return Ok(Value::Float(f.value()));
    }
    if let Ok(s) = obj.downcast::<PyString>() {
        return Ok(Value::Str(s.to_string_lossy().into()));
    }
    if let Ok(d) = obj.downcast::<PyDict>() {
        let mut entries = Vec::with_capacity(d.len());
        for (k, v) in d.iter() {
            let key = py_to_key(&k, pool)?;
            entries.push((key, py_to_value(&v, pool)?));
        }
        return Ok(Value::Object(entries));
    }
    if let Ok(l) = obj.downcast::<PyList>() {
        let mut items = Vec::with_capacity(l.len());
        for item in l.iter() {
            items.push(py_to_value(&item, pool)?);
        }
        return Ok(Value::Array(items));
    }
    if let Ok(t) = obj.downcast::<PyTuple>() {
        let mut items = Vec::with_capacity(t.len());
        for item in t.iter() {
            items.push(py_to_value(&item, pool)?);
        }
        return Ok(Value::Array(items));
    }

    let id = pool.push(obj.clone());
    Ok(Value::Opaque(id))
}

fn py_to_key(obj: &Bound<'_, PyAny>, pool: &mut OpaquePool) -> PyResult<Key> {
    if let Ok(s) = obj.downcast::<PyString>() {
        return Ok(Key::Str(s.to_string_lossy().into()));
    }
    if let Ok(i) = obj.downcast::<PyInt>() {
        return Ok(Key::Int(i.extract()?));
    }
    let id = pool.push(obj.clone());
    Ok(Key::Opaque(id))
}

pub fn value_to_py(py: Python<'_>, value: &Value, pool: &OpaquePool) -> PyResult<PyObject> {
    match value {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => Ok(PyBool::new(py, *b).to_owned().into_any().into()),
        Value::Int(i) => Ok(i.into_pyobject(py).unwrap().into_any().into()),
        Value::Float(f) => Ok(f.into_pyobject(py).unwrap().into_any().into()),
        Value::Str(s) => Ok(s.into_pyobject(py).unwrap().into_any().into()),
        Value::Array(items) => {
            let list = PyList::empty(py);
            for item in items {
                list.append(value_to_py(py, item, pool)?)?;
            }
            Ok(list.into())
        }
        Value::Object(entries) => {
            let dict = PyDict::new(py);
            for (k, v) in entries {
                dict.set_item(key_to_py(py, k, pool)?, value_to_py(py, v, pool)?)?;
            }
            Ok(dict.into())
        }
        Value::Opaque(id) => {
            if let Some(obj) = pool.get(*id) {
                Ok(obj.clone_ref(py))
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Opaque pool missing id {id}"
                )))
            }
        }
    }
}

fn key_to_py(py: Python<'_>, key: &Key, pool: &OpaquePool) -> PyResult<PyObject> {
    match key {
        Key::Str(s) => Ok(s.into_pyobject(py).unwrap().into_any().into()),
        Key::Int(i) => Ok(i.into_pyobject(py).unwrap().into_any().into()),
        Key::Opaque(id) => {
            if let Some(obj) = pool.get(*id) {
                Ok(obj.clone_ref(py))
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Opaque pool missing key id {id}"
                )))
            }
        }
    }
}
