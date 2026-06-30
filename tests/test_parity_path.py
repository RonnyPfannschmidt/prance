"""Parity tests for compiled path_set vs pure-Python implementation."""

import copy

import pytest

from prance.util.path import _python_path_set, path_set


def _set_with_python(obj, path, value, create=False):
    return _python_path_set(copy.deepcopy(obj), path, value, create=create)


def _set_with_compiled(obj, path, value, create=False):
    return path_set(copy.deepcopy(obj), path, value, create=create)


@pytest.mark.parametrize(
    "obj,path,value,create",
    [
        ({"foo": "bar"}, ("foo",), "new", False),
        ({"foo": {"bar": "baz"}}, ("foo", "bar"), "new", False),
        ({"foo": [0]}, ("foo", 0), 42, False),
        ([{"foo": "bar"}], (0, "foo"), 42, False),
        ([], (1, 0), "something", True),
        ({}, ("foo",), "bar", True),
        ({}, ("foo", "bar"), "baz", True),
        ({}, ("foo", 0), 42, True),
        ([], (0, "foo"), 42, True),
        ({}, (0,), 42, True),
        ({"foo": [123]}, ("foo", 0), 42, True),
        ([42, [1, 2]], (1, 0), "something", False),
        ([42], (0,), "something", False),
    ],
)
def test_path_set_parity_compiled_vs_python(obj, path, value, create):
    py_result = _set_with_python(obj, path, value, create=create)
    cy_result = _set_with_compiled(obj, path, value, create=create)
    assert py_result == cy_result


def test_path_set_compiled_raises_like_python():
    with pytest.raises(IndexError):
        path_set([], (0,), "x")
    with pytest.raises(KeyError):
        path_set({}, ("missing",), "x")
