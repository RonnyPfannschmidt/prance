"""Parity tests between compiled and pure-Python resolver paths."""

import copy
import os

import pytest

from prance.util import fs, formats, resolver
from prance.util import iterators, path as path_mod, url as url_mod


def _resolve_with_python(specs, url, **options):
    res = resolver._PythonRefResolver(specs, url=url, **options)
    res.resolve_references()
    return res.specs


def _resolve_with_compiled(specs, url, **options):
    res = resolver.RefResolver(specs, url=url, **options)
    res.resolve_references()
    return res.specs


@pytest.mark.parametrize(
    "spec_path,url,options",
    [
        (
            "tests/specs/petstore.yaml",
            os.path.abspath("tests/specs/petstore.yaml"),
            {"copy_input": False},
        ),
        (
            "tests/specs/issue_78/openapi.json",
            fs.abspath("openapi.json"),
            {
                "resolve_types": resolver.RESOLVE_FILES,
                "resolve_method": resolver.TRANSLATE_EXTERNAL,
                "copy_input": False,
            },
        ),
    ],
)
def test_resolver_parity_compiled_vs_python(spec_path, url, options):
    specs = formats.parse_spec(fs.read_file(spec_path), spec_path)
    py_specs = copy.deepcopy(specs)
    cy_specs = copy.deepcopy(specs)
    py_result = _resolve_with_python(py_specs, url, **options)
    cy_result = _resolve_with_compiled(cy_specs, url, **options)
    assert py_result == cy_result


def test_resolver_uses_compiled_when_available():
    import _prance_fast

    assert resolver.RefResolver is _prance_fast.RefResolver


def test_resolver_python_fallback_when_compiled_missing(monkeypatch):
    monkeypatch.setattr(resolver, "_FastRefResolver", None)
    monkeypatch.setattr(resolver, "RefResolver", resolver._PythonRefResolver)
    specs = formats.parse_spec(
        fs.read_file("tests/specs/petstore.yaml"), "tests/specs/petstore.yaml"
    )
    res = resolver.RefResolver(
        specs,
        url=os.path.abspath("tests/specs/petstore.yaml"),
        copy_input=False,
    )
    res.resolve_references()
    assert "$ref" not in str(res.specs)


def test_resolver_import_fallback_without_extension(monkeypatch):
    monkeypatch.setattr(resolver, "_fast_deepcopy_json", None)
    assert resolver._deepcopy_specs({"a": 1}) == {"a": 1}


def test_url_python_fallback_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(url_mod, "_fast_absurl", None)
    monkeypatch.setattr(url_mod, "_fast_urlresource", None)
    monkeypatch.setattr(url_mod, "_fast_split_fragment_reference", None)
    monkeypatch.setattr(url_mod, "_fast_split_url_reference", None)
    monkeypatch.setattr(url_mod, "_fast_fetch_url_text", None)
    monkeypatch.setattr(url_mod, "_fast_fetch_url", None)

    base = url_mod.absurl(os.path.abspath("tests/specs/petstore.yaml"))
    resource = url_mod.urlresource(base)
    assert resource.startswith("file://")
    frag = url_mod.split_fragment_reference(base, "#/definitions/Pet")
    assert frag is not None
    assert url_mod.split_fragment_reference(None, "#/definitions/Pet") is None
    parsed, obj_path = url_mod.split_url_reference(base, "#/definitions/Pet")
    assert parsed.fragment
    assert obj_path

    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("openapi: 3.0.0\ninfo:\n  title: t\n  version: '1'\npaths: {}\n")
    file_url = url_mod.absurl(str(spec_file))
    text, _ = url_mod.fetch_url_text(file_url)
    assert "openapi" in text
    cache = {}
    parsed_spec = url_mod.fetch_url(file_url, cache=cache, copy=False)
    assert parsed_spec["openapi"] == "3.0.0"
    assert url_mod.fetch_url(file_url, cache=cache, copy=True)["openapi"] == "3.0.0"

    with pytest.raises(url_mod.ResolutionError):
        url_mod.absurl("relative.yaml")
    with pytest.raises(url_mod.ResolutionError):
        url_mod.absurl("#/only-fragment")


def test_path_python_fallback_paths(monkeypatch):
    monkeypatch.setattr(path_mod, "_fast_path_get", None)
    monkeypatch.setattr(path_mod, "_fast_path_set", None)

    obj = {"a": {"b": [1, {"c": 2}]}}
    assert path_mod.path_get(obj, ("a", "b", 1, "c")) == 2
    path_mod.path_set(obj, ("a", "b", 0), 9, create=True)
    assert obj["a"]["b"][0] == 9
    with pytest.raises(KeyError):
        path_mod.path_get(obj, ("missing",))
    with pytest.raises(TypeError):
        path_mod.path_get(42, ("x",))


def test_iterators_python_fallback(monkeypatch):
    monkeypatch.setattr(iterators, "_fast_reference_iterator", None)
    specs = {"paths": {"/x": {"$ref": "#/definitions/Y"}}, "definitions": {"Y": {}}}
    refs = list(iterators.reference_iterator(specs))
    assert refs == [("$ref", "#/definitions/Y", ("paths", "/x"))]
