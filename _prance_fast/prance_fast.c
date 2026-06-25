#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

/* --- helpers ----------------------------------------------------------- */

static int
mapping_contains(PyObject *obj, PyObject *key)
{
    if (PyDict_Check(obj)) {
        return PyDict_Contains(obj, key);
    }
    PyObject *item = PyObject_GetItem(obj, key);
    if (item != NULL) {
        Py_DECREF(item);
        return 1;
    }
    if (PyErr_ExceptionMatches(PyExc_KeyError)) {
        PyErr_Clear();
        return 0;
    }
    return -1;
}

static int
is_mapping(PyObject *obj)
{
    return (
        PyMapping_Check(obj)
        && !PySequence_Check(obj)
        && !PyUnicode_Check(obj)
        && !PyBytes_Check(obj)
    );
}

static int
is_mutable_mapping(PyObject *obj)
{
    return is_mapping(obj) && PyDict_Check(obj);
}

static int
is_sequence_not_str(PyObject *obj)
{
    return PySequence_Check(obj) && !PyUnicode_Check(obj) && !PyBytes_Check(obj);
}

static int
is_mutable_sequence(PyObject *obj)
{
    return is_sequence_not_str(obj) && PyList_Check(obj);
}

static PyObject *
value_or_default(PyObject *obj, PyObject *defaultvalue)
{
    if (obj != NULL) {
        int truthy = PyObject_IsTrue(obj);
        if (truthy < 0) {
            return NULL;
        }
        if (truthy) {
            return Py_NewRef(obj);
        }
    }
    if (defaultvalue != NULL) {
        return Py_NewRef(defaultvalue);
    }
    if (obj != NULL) {
        return Py_NewRef(obj);
    }
    Py_RETURN_NONE;
}

static Py_ssize_t
path_length(PyObject *path)
{
    if (path == NULL || path == Py_None) {
        return 0;
    }
    return PySequence_Size(path);
}

static PyObject *
path_item(PyObject *path, Py_ssize_t index)
{
    return PySequence_GetItem(path, index);
}

static PyObject *
path_slice(PyObject *path, Py_ssize_t start, Py_ssize_t end)
{
    return PySequence_GetSlice(path, start, end);
}

static int
path_is_valid(PyObject *path)
{
    if (path == NULL || path == Py_None) {
        return 1;
    }
    return PySequence_Check(path);
}

static PyObject *
path_append(PyObject *path, PyObject *part)
{
    Py_ssize_t len = path_length(path);
    PyObject *new_path = PyTuple_New(len + 1);
    if (new_path == NULL) {
        return NULL;
    }
    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject *item = path_item(path, i);
        if (item == NULL) {
            Py_DECREF(new_path);
            return NULL;
        }
        PyTuple_SET_ITEM(new_path, i, item);
    }
    Py_INCREF(part);
    PyTuple_SET_ITEM(new_path, len, part);
    return new_path;
}

static PyObject *
json_ref_escape(PyObject *part)
{
    if (!PyUnicode_Check(part)) {
        part = PyObject_Str(part);
        if (part == NULL) {
            return NULL;
        }
    }
    else {
        Py_INCREF(part);
    }

    PyObject *tilde = PyUnicode_FromString("~");
    PyObject *slash = PyUnicode_FromString("/");
    PyObject *tilde0 = PyUnicode_FromString("~0");
    PyObject *tilde1 = PyUnicode_FromString("~1");
    if (tilde == NULL || slash == NULL || tilde0 == NULL || tilde1 == NULL) {
        Py_XDECREF(part);
        Py_XDECREF(tilde);
        Py_XDECREF(slash);
        Py_XDECREF(tilde0);
        Py_XDECREF(tilde1);
        return NULL;
    }

    PyObject *step1 = PyUnicode_Replace(part, tilde, tilde0, -1);
    Py_DECREF(part);
    Py_DECREF(tilde);
    Py_DECREF(tilde0);
    if (step1 == NULL) {
        Py_DECREF(slash);
        Py_DECREF(tilde1);
        return NULL;
    }

    PyObject *step2 = PyUnicode_Replace(step1, slash, tilde1, -1);
    Py_DECREF(step1);
    Py_DECREF(slash);
    Py_DECREF(tilde1);
    return step2;
}

static PyObject *
str_path(PyObject *path_of_obj)
{
    Py_ssize_t len = (path_of_obj == NULL) ? 0 : PySequence_Size(path_of_obj);
    if (len < 0) {
        return NULL;
    }
    if (len == 0) {
        return PyUnicode_FromString("/");
    }

    PyObject *parts = PyList_New(len);
    if (parts == NULL) {
        return NULL;
    }

    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject *part = PySequence_GetItem(path_of_obj, i);
        if (part == NULL) {
            Py_DECREF(parts);
            return NULL;
        }
        PyObject *escaped = json_ref_escape(part);
        Py_DECREF(part);
        if (escaped == NULL) {
            Py_DECREF(parts);
            return NULL;
        }
        PyList_SET_ITEM(parts, i, escaped);
    }

    PyObject *slash = PyUnicode_FromString("/");
    PyObject *joined = PyUnicode_Join(slash, parts);
    Py_DECREF(parts);
    if (joined == NULL) {
        Py_DECREF(slash);
        return NULL;
    }

    PyObject *result = PyUnicode_Concat(slash, joined);
    Py_DECREF(slash);
    Py_DECREF(joined);
    return result;
}

/* --- fast_deepcopy_json ------------------------------------------------ */

static PyObject *
fast_deepcopy_json_impl(PyObject *obj);

static PyObject *
fast_deepcopy_dict(PyObject *obj)
{
    PyObject *copy = PyDict_New();
    if (copy == NULL) {
        return NULL;
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;
    while (PyDict_Next(obj, &pos, &key, &value)) {
        PyObject *value_copy = fast_deepcopy_json_impl(value);
        if (value_copy == NULL) {
            Py_DECREF(copy);
            return NULL;
        }
        if (PyDict_SetItem(copy, key, value_copy) < 0) {
            Py_DECREF(value_copy);
            Py_DECREF(copy);
            return NULL;
        }
        Py_DECREF(value_copy);
    }
    return copy;
}

static PyObject *
fast_deepcopy_list(PyObject *obj)
{
    Py_ssize_t size = PyList_GET_SIZE(obj);
    PyObject *copy = PyList_New(size);
    if (copy == NULL) {
        return NULL;
    }

    for (Py_ssize_t i = 0; i < size; i++) {
        PyObject *item = PyList_GET_ITEM(obj, i);
        PyObject *item_copy = fast_deepcopy_json_impl(item);
        if (item_copy == NULL) {
            Py_DECREF(copy);
            return NULL;
        }
        PyList_SET_ITEM(copy, i, item_copy);
    }
    return copy;
}

static PyObject *
fast_deepcopy_json_impl(PyObject *obj)
{
    if (obj == NULL || obj == Py_None) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    if (PyBool_Check(obj) || PyLong_Check(obj) || PyFloat_Check(obj) || PyUnicode_Check(obj)) {
        return Py_NewRef(obj);
    }
    if (PyDict_Check(obj) || PyList_Check(obj)) {
        if (Py_EnterRecursiveCall(" while deep-copying JSON data")) {
            return NULL;
        }
        PyObject *result = PyDict_Check(obj)
            ? fast_deepcopy_dict(obj)
            : fast_deepcopy_list(obj);
        Py_LeaveRecursiveCall();
        return result;
    }
    PyErr_Format(PyExc_TypeError, "fast_deepcopy_json does not support type %s", Py_TYPE(obj)->tp_name);
    return NULL;
}

static PyObject *
fast_deepcopy_json(PyObject *self, PyObject *obj)
{
    return fast_deepcopy_json_impl(obj);
}

/* --- path_get ---------------------------------------------------------- */

static PyObject *
path_get_impl(PyObject *obj, PyObject *path, PyObject *defaultvalue, PyObject *path_of_obj)
{
    if (!path_is_valid(path)) {
        PyErr_Format(PyExc_TypeError, "Path is a %s, but must be None or a Collection!", Py_TYPE(path)->tp_name);
        return NULL;
    }

    Py_ssize_t path_len = path_length(path);

    if (is_mapping(obj)) {
        if (path_len < 1) {
            return value_or_default(obj, defaultvalue);
        }

        PyObject *key = path_item(path, 0);
        if (key == NULL) {
            return NULL;
        }
        int contains = mapping_contains(obj, key);
        if (contains < 0) {
            Py_DECREF(key);
            return NULL;
        }
        if (!contains) {
            PyObject *path_str = str_path(path_of_obj);
            if (path_str == NULL) {
                Py_DECREF(key);
                return NULL;
            }
            PyObject *key_text = PyObject_Str(key);
            if (key_text == NULL) {
                Py_DECREF(path_str);
                Py_DECREF(key);
                return NULL;
            }
            PyErr_Format(PyExc_KeyError, "Object at \"%U\" does not contain key: %U", path_str, key_text);
            Py_DECREF(path_str);
            Py_DECREF(key_text);
            Py_DECREF(key);
            return NULL;
        }

        PyObject *next = PyObject_GetItem(obj, key);
        if (next == NULL) {
            Py_DECREF(key);
            return NULL;
        }
        PyObject *next_path = path_slice(path, 1, path_len);
        if (next_path == NULL) {
            Py_DECREF(key);
            Py_DECREF(next);
            return NULL;
        }
        PyObject *next_path_of_obj = path_append(path_of_obj, key);
        Py_DECREF(key);
        if (next_path_of_obj == NULL) {
            Py_DECREF(next_path);
            Py_DECREF(next);
            return NULL;
        }
        if (Py_EnterRecursiveCall(" while resolving path")) {
            Py_DECREF(next_path);
            Py_DECREF(next_path_of_obj);
            Py_DECREF(next);
            return NULL;
        }
        PyObject *result = path_get_impl(next, next_path, defaultvalue, next_path_of_obj);
        Py_LeaveRecursiveCall();
        Py_DECREF(next_path);
        Py_DECREF(next_path_of_obj);
        Py_DECREF(next);
        return result;
    }

    if (is_sequence_not_str(obj)) {
        if (path_len < 1) {
            return value_or_default(obj, defaultvalue);
        }

        PyObject *idx_obj = path_item(path, 0);
        if (idx_obj == NULL) {
            return NULL;
        }
        PyObject *idx_long = PyNumber_Long(idx_obj);
        if (idx_long == NULL) {
            PyObject *path_str = str_path(path_of_obj);
            if (path_str == NULL) {
                Py_DECREF(idx_obj);
                return NULL;
            }
            PyObject *idx_text = PyObject_Str(idx_obj);
            if (idx_text == NULL) {
                Py_DECREF(path_str);
                Py_DECREF(idx_obj);
                return NULL;
            }
            PyErr_Format(PyExc_KeyError, "Sequence at \"%U\" needs integer indices only, but got: %U", path_str, idx_text);
            Py_DECREF(path_str);
            Py_DECREF(idx_text);
            Py_DECREF(idx_obj);
            return NULL;
        }
        Py_DECREF(idx_obj);
        Py_ssize_t idx = PyLong_AsSsize_t(idx_long);
        Py_DECREF(idx_long);
        if (idx == -1 && PyErr_Occurred()) {
            return NULL;
        }

        Py_ssize_t seq_len = PySequence_Size(obj);
        if (seq_len < 0) {
            return NULL;
        }
        if (idx < 0 || idx >= seq_len) {
            PyObject *path_str = str_path(path_of_obj);
            if (path_str == NULL) {
                return NULL;
            }
            PyErr_Format(PyExc_IndexError, "Index out of bounds for sequence at \"%U\": %zd", path_str, idx);
            Py_DECREF(path_str);
            return NULL;
        }

        PyObject *next = PySequence_GetItem(obj, idx);
        if (next == NULL) {
            return NULL;
        }
        PyObject *next_path = path_slice(path, 1, path_len);
        if (next_path == NULL) {
            Py_DECREF(next);
            return NULL;
        }
        PyObject *idx_key = PyLong_FromSsize_t(idx);
        if (idx_key == NULL) {
            Py_DECREF(next);
            Py_DECREF(next_path);
            return NULL;
        }
        PyObject *next_path_of_obj = path_append(path_of_obj, idx_key);
        Py_DECREF(idx_key);
        if (next_path_of_obj == NULL) {
            Py_DECREF(next);
            Py_DECREF(next_path);
            return NULL;
        }
        if (Py_EnterRecursiveCall(" while resolving path")) {
            Py_DECREF(next_path);
            Py_DECREF(next_path_of_obj);
            Py_DECREF(next);
            return NULL;
        }
        PyObject *result = path_get_impl(next, next_path, defaultvalue, next_path_of_obj);
        Py_LeaveRecursiveCall();
        Py_DECREF(next_path);
        Py_DECREF(next_path_of_obj);
        Py_DECREF(next);
        return result;
    }

    if (path_len > 0) {
        PyErr_Format(PyExc_TypeError, "Cannot get anything from type %s!", Py_TYPE(obj)->tp_name);
        return NULL;
    }
    return value_or_default(obj, defaultvalue);
}

static PyObject *
path_get(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"obj", "path", "defaultvalue", "path_of_obj", NULL};
    PyObject *obj;
    PyObject *path;
    PyObject *defaultvalue = Py_None;
    PyObject *path_of_obj = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO|OO", kwlist, &obj, &path, &defaultvalue, &path_of_obj)) {
        return NULL;
    }
    if (path_of_obj == NULL) {
        path_of_obj = PyTuple_New(0);
        if (path_of_obj == NULL) {
            return NULL;
        }
        PyObject *result = path_get_impl(obj, path, defaultvalue, path_of_obj);
        Py_DECREF(path_of_obj);
        return result;
    }
    return path_get_impl(obj, path, defaultvalue, path_of_obj);
}

/* --- path_set ---------------------------------------------------------- */

static PyObject *
safe_idx_type(PyObject *seq, Py_ssize_t index)
{
    if (index < 0 || index >= PySequence_Size(seq)) {
        Py_RETURN_NONE;
    }
    PyObject *item = PySequence_GetItem(seq, index);
    if (item == NULL) {
        return NULL;
    }
    PyObject *typ = (PyObject *)Py_TYPE(item);
    Py_INCREF(typ);
    Py_DECREF(item);
    return typ;
}

static int
fill_sequence(PyObject *seq, Py_ssize_t index, PyObject *value_index_type)
{
    Py_ssize_t size = PyList_GET_SIZE(seq);
    if (size > index) {
        return 0;
    }

    while (PyList_GET_SIZE(seq) < index) {
        if (PyList_Append(seq, Py_None) < 0) {
            return -1;
        }
    }

    PyObject *placeholder;
    if (value_index_type == (PyObject *)&PyLong_Type) {
        placeholder = PyList_New(0);
    }
    else if (value_index_type == Py_None) {
        Py_INCREF(Py_None);
        placeholder = Py_None;
    }
    else {
        placeholder = PyDict_New();
    }
    if (placeholder == NULL) {
        return -1;
    }
    int rc = PyList_Append(seq, placeholder);
    Py_DECREF(placeholder);
    return rc;
}

static PyObject *
path_set_impl(PyObject *obj, PyObject *path, PyObject *value, int create)
{
    if (path == NULL || path == Py_None) {
        PyErr_SetString(PyExc_TypeError, "object of type 'NoneType' has no len()");
        return NULL;
    }
    if (!path_is_valid(path)) {
        PyErr_Format(PyExc_TypeError, "Path is a %s, but must be None or a Collection!", Py_TYPE(path)->tp_name);
        return NULL;
    }

    Py_ssize_t path_len = path_length(path);
    if (path_len < 1) {
        PyErr_SetString(PyExc_KeyError, "Cannot set with an empty path!");
        return NULL;
    }

    if (is_mapping(obj)) {
        if (!is_mutable_mapping(obj)) {
            PyErr_Format(PyExc_TypeError, "Mapping is not mutable: %s", Py_TYPE(obj)->tp_name);
            return NULL;
        }

        PyObject *key = path_item(path, 0);
        if (key == NULL) {
            return NULL;
        }
        if (path_len == 1) {
            if (!create && !PyDict_Contains(obj, key)) {
                PyErr_Format(PyExc_KeyError, "Key \"%R\" not in Mapping!", key);
                Py_DECREF(key);
                return NULL;
            }
            if (PyDict_SetItem(obj, key, value) < 0) {
                Py_DECREF(key);
                return NULL;
            }
            Py_DECREF(key);
            Py_RETURN_NONE;
        }

        if (create && !PyDict_Contains(obj, key)) {
            PyObject *next_key = path_item(path, 1);
            if (next_key == NULL) {
                Py_DECREF(key);
                return NULL;
            }
            PyObject *container = PyLong_Check(next_key) ? PyList_New(0) : PyDict_New();
            Py_DECREF(next_key);
            if (container == NULL) {
                Py_DECREF(key);
                return NULL;
            }
            if (PyDict_SetItem(obj, key, container) < 0) {
                Py_DECREF(container);
                Py_DECREF(key);
                return NULL;
            }
            Py_DECREF(container);
        }

        PyObject *next = PyDict_GetItemWithError(obj, key);
        if (next == NULL) {
            if (!PyErr_Occurred()) {
                PyErr_Format(PyExc_KeyError, "%R", key);
            }
            Py_DECREF(key);
            return NULL;
        }
        Py_DECREF(key);
        PyObject *next_path = path_slice(path, 1, path_len);
        if (next_path == NULL) {
            return NULL;
        }
        if (Py_EnterRecursiveCall(" while resolving path")) {
            Py_DECREF(next_path);
            return NULL;
        }
        PyObject *result = path_set_impl(next, next_path, value, create);
        Py_LeaveRecursiveCall();
        Py_DECREF(next_path);
        return result;
    }

    if (is_sequence_not_str(obj)) {
        if (!is_mutable_sequence(obj)) {
            PyErr_Format(PyExc_TypeError, "Sequence is not mutable: %s", Py_TYPE(obj)->tp_name);
            return NULL;
        }

        PyObject *idx_obj = path_item(path, 0);
        if (idx_obj == NULL) {
            return NULL;
        }
        PyObject *idx_long = PyNumber_Long(idx_obj);
        Py_DECREF(idx_obj);
        if (idx_long == NULL) {
            PyErr_SetString(PyExc_KeyError, "Sequences need integer indices only.");
            return NULL;
        }
        Py_ssize_t idx = PyLong_AsSsize_t(idx_long);
        Py_DECREF(idx_long);
        if (idx == -1 && PyErr_Occurred()) {
            return NULL;
        }

        if (create) {
            PyObject *next_type = safe_idx_type(path, 1);
            if (next_type == NULL) {
                return NULL;
            }
            if (fill_sequence(obj, idx, next_type) < 0) {
                Py_DECREF(next_type);
                return NULL;
            }
            Py_DECREF(next_type);
        }

        if (path_len == 1) {
            if (PyList_SetItem(obj, idx, Py_NewRef(value)) < 0) {
                return NULL;
            }
            Py_RETURN_NONE;
        }

        PyObject *next = PyList_GetItem(obj, idx);
        if (next == NULL) {
            return NULL;
        }
        PyObject *next_path = path_slice(path, 1, path_len);
        if (next_path == NULL) {
            return NULL;
        }
        if (Py_EnterRecursiveCall(" while resolving path")) {
            Py_DECREF(next_path);
            return NULL;
        }
        PyObject *result = path_set_impl(next, next_path, value, create);
        Py_LeaveRecursiveCall();
        Py_DECREF(next_path);
        return result;
    }

    PyErr_Format(PyExc_TypeError, "Cannot set anything on type %s!", Py_TYPE(obj)->tp_name);
    return NULL;
}

static PyObject *
path_set(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"obj", "path", "value", "create", NULL};
    PyObject *obj;
    PyObject *path;
    PyObject *value;
    int create = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO|p", kwlist, &obj, &path, &value, &create)) {
        return NULL;
    }
    PyObject *status = path_set_impl(obj, path, value, create);
    if (status == NULL) {
        return NULL;
    }
    Py_DECREF(status);
    return Py_NewRef(obj);
}

/* --- reference_iterator ------------------------------------------------ */

typedef struct {
    PyObject_HEAD
    PyObject *stack;
} ReferenceIteratorObject;

typedef struct {
    PyObject *path;
    PyObject *container;
    PyObject *keys;
    Py_ssize_t index;
    int is_dict;
} WalkFrame;

static void
walkframe_dealloc(WalkFrame *frame)
{
    Py_XDECREF(frame->path);
    Py_XDECREF(frame->container);
    Py_XDECREF(frame->keys);
    PyMem_Free(frame);
}

static void
walkframe_capsule_destructor(PyObject *capsule)
{
    WalkFrame *frame = (WalkFrame *)PyCapsule_GetPointer(capsule, "WalkFrame");
    if (frame != NULL) {
        walkframe_dealloc(frame);
    }
}

static WalkFrame *
walkframe_new(PyObject *path, PyObject *container)
{
    WalkFrame *frame = PyMem_Malloc(sizeof(WalkFrame));
    if (frame == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    Py_INCREF(path);
    Py_INCREF(container);
    frame->path = path;
    frame->container = container;
    frame->keys = NULL;
    frame->index = 0;
    frame->is_dict = PyDict_Check(container);
    if (frame->is_dict) {
        frame->keys = PyDict_Keys(container);
        if (frame->keys == NULL) {
            walkframe_dealloc(frame);
            return NULL;
        }
    }
    return frame;
}

static int
push_child(PyObject *stack, PyObject *parent_path, PyObject *key, PyObject *value)
{
    if (!is_mapping(value) && !is_sequence_not_str(value)) {
        return 0;
    }
    PyObject *new_path = path_append(parent_path, key);
    if (new_path == NULL) {
        return -1;
    }
    WalkFrame *frame = walkframe_new(new_path, value);
    Py_DECREF(new_path);
    if (frame == NULL) {
        return -1;
    }
    PyObject *frame_obj = PyCapsule_New(frame, "WalkFrame", walkframe_capsule_destructor);
    if (frame_obj == NULL) {
        walkframe_dealloc(frame);
        return -1;
    }
    if (PyList_Append(stack, frame_obj) < 0) {
        Py_DECREF(frame_obj);
        return -1;
    }
    Py_DECREF(frame_obj);
    return 0;
}

static PyObject *
reference_iterator_next(ReferenceIteratorObject *self)
{
    PyObject *dollar_ref = PyUnicode_FromString("$ref");
    if (dollar_ref == NULL) {
        return NULL;
    }

    while (PyList_GET_SIZE(self->stack) > 0) {
        Py_ssize_t top = PyList_GET_SIZE(self->stack) - 1;
        PyObject *frame_obj = PyList_GET_ITEM(self->stack, top);
        WalkFrame *frame = PyCapsule_GetPointer(frame_obj, "WalkFrame");
        if (frame == NULL) {
            Py_DECREF(dollar_ref);
            return NULL;
        }

        if (frame->is_dict) {
            Py_ssize_t key_count = PyList_GET_SIZE(frame->keys);
            if (frame->index >= key_count) {
                PyList_SetSlice(self->stack, top, top + 1, NULL);
                continue;
            }

            PyObject *key = PyList_GET_ITEM(frame->keys, frame->index++);
            PyObject *value = PyDict_GetItemWithError(frame->container, key);
            if (value == NULL) {
                if (!PyErr_Occurred()) {
                    PyErr_SetString(
                        PyExc_RuntimeError,
                        "mapping changed size during reference iteration"
                    );
                }
                Py_DECREF(dollar_ref);
                return NULL;
            }

            if (PyUnicode_Check(key) && PyUnicode_CompareWithASCIIString(key, "$ref") == 0) {
                PyObject *result = PyTuple_Pack(3, dollar_ref, value, frame->path);
                Py_DECREF(dollar_ref);
                return result;
            }

            if (push_child(self->stack, frame->path, key, value) < 0) {
                Py_DECREF(dollar_ref);
                return NULL;
            }
            continue;
        }

        Py_ssize_t list_len = PyList_GET_SIZE(frame->container);
        if (frame->index >= list_len) {
            PyList_SetSlice(self->stack, top, top + 1, NULL);
            continue;
        }

        PyObject *idx = PyLong_FromSsize_t(frame->index);
        PyObject *value = PyList_GET_ITEM(frame->container, frame->index++);
        if (idx == NULL) {
            Py_DECREF(dollar_ref);
            return NULL;
        }
        if (push_child(self->stack, frame->path, idx, value) < 0) {
            Py_DECREF(idx);
            Py_DECREF(dollar_ref);
            return NULL;
        }
        Py_DECREF(idx);
    }

    Py_DECREF(dollar_ref);
    return NULL;
}

static PyObject *
reference_iterator_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"specs", "path", NULL};
    PyObject *specs;
    PyObject *path = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|O", kwlist, &specs, &path)) {
        return NULL;
    }
    if (path == NULL) {
        path = PyTuple_New(0);
    }
    else {
        Py_INCREF(path);
    }
    if (path == NULL) {
        return NULL;
    }

    ReferenceIteratorObject *self = (ReferenceIteratorObject *)type->tp_alloc(type, 0);
    if (self == NULL) {
        Py_DECREF(path);
        return NULL;
    }

    self->stack = PyList_New(0);
    if (self->stack == NULL) {
        Py_DECREF(path);
        Py_DECREF(self);
        return NULL;
    }

    if (is_mapping(specs) || is_sequence_not_str(specs)) {
        WalkFrame *root = walkframe_new(path, specs);
        Py_DECREF(path);
        if (root == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        PyObject *frame_obj = PyCapsule_New(root, "WalkFrame", walkframe_capsule_destructor);
        if (frame_obj == NULL) {
            walkframe_dealloc(root);
            Py_DECREF(self);
            return NULL;
        }
        if (PyList_Append(self->stack, frame_obj) < 0) {
            Py_DECREF(frame_obj);
            Py_DECREF(self);
            return NULL;
        }
        Py_DECREF(frame_obj);
    }
    else {
        Py_DECREF(path);
    }

    return (PyObject *)self;
}

static void
reference_iterator_dealloc(ReferenceIteratorObject *self)
{
    Py_XDECREF(self->stack);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
reference_iterator_iter(PyObject *self)
{
    Py_INCREF(self);
    return self;
}

static PyObject *
reference_iterator_iternext(ReferenceIteratorObject *self)
{
    return reference_iterator_next(self);
}

static PyTypeObject ReferenceIteratorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_prance_fast.ReferenceIterator",
    .tp_basicsize = sizeof(ReferenceIteratorObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_dealloc = (destructor)reference_iterator_dealloc,
    .tp_iter = reference_iterator_iter,
    .tp_iternext = (iternextfunc)reference_iterator_iternext,
    .tp_new = reference_iterator_new,
};

static PyObject *
reference_iterator(PyObject *self, PyObject *args, PyObject *kwargs)
{
    return reference_iterator_new(&ReferenceIteratorType, args, kwargs);
}

/* --- module ------------------------------------------------------------ */

static PyMethodDef module_methods[] = {
    {"fast_deepcopy_json", (PyCFunction)fast_deepcopy_json, METH_O, "Deep-copy JSON-compatible Python objects."},
    {"path_get", (PyCFunction)path_get, METH_VARARGS | METH_KEYWORDS, "Get a nested value by path tuple."},
    {"path_set", (PyCFunction)path_set, METH_VARARGS | METH_KEYWORDS, "Set a nested value by path tuple."},
    {"reference_iterator", (PyCFunction)reference_iterator, METH_VARARGS | METH_KEYWORDS, "Iterate $ref entries in a spec."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_prance_fast",
    .m_doc = "Fast C helpers for prance reference resolution.",
    .m_size = -1,
    .m_methods = module_methods,
};

PyMODINIT_FUNC
PyInit__prance_fast(void)
{
    PyObject *module = PyModule_Create(&moduledef);
    if (module == NULL) {
        return NULL;
    }

    if (PyType_Ready(&ReferenceIteratorType) < 0) {
        Py_DECREF(module);
        return NULL;
    }

    Py_INCREF(&ReferenceIteratorType);
    if (PyModule_AddObject(module, "ReferenceIterator", (PyObject *)&ReferenceIteratorType) < 0) {
        Py_DECREF(&ReferenceIteratorType);
        Py_DECREF(module);
        return NULL;
    }

    return module;
}
