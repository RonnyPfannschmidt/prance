"""Tests for the bundled ``_prance_rs`` Rust extension primitives."""
import pytest


def _rebind_rust_bindings():
    """Restore Rust util hooks after parity fallback tests patch them away."""
    try:
        import _prance_rs
    except ImportError:
        return None

    from prance.util import iterators, path as path_mod, resolver, url as url_mod

    resolver._rust_deepcopy_json = _prance_rs.fast_deepcopy_json
    resolver._RustRefResolver = getattr(_prance_rs, "RefResolver", None)
    resolver.rust_resolve_spec = getattr(_prance_rs, "resolve_spec", None)
    resolver.rust_validate_openapi_spec = getattr(
        _prance_rs, "validate_openapi_spec", None
    )
    resolver.rust_load_openapi_spec = getattr(_prance_rs, "load_openapi_spec_py", None)
    resolver.rust_parse_and_validate_spec = getattr(
        _prance_rs, "parse_and_validate_spec", None
    )
    resolver.RefResolver = resolver._select_ref_resolver()
    path_mod._rust_path_get = _prance_rs.path_get
    path_mod._rust_path_set = _prance_rs.path_set
    iterators._rust_reference_iterator = _prance_rs.reference_iterator
    url_mod._rust_absurl = _prance_rs.absurl
    url_mod._rust_urlresource = _prance_rs.urlresource
    url_mod._rust_split_fragment_reference = _prance_rs.split_fragment_reference
    url_mod._rust_split_url_reference = _prance_rs.split_url_reference
    return _prance_rs


@pytest.fixture(autouse=True)
def _fresh_rust_bindings():
    _rebind_rust_bindings()
    yield


def test_prance_rs_extension_importable():
    import _prance_rs

    assert hasattr(_prance_rs, "fast_deepcopy_json")
    assert hasattr(_prance_rs, "path_get")
    assert hasattr(_prance_rs, "path_set")
    assert hasattr(_prance_rs, "reference_iterator")
    assert hasattr(_prance_rs, "urlresource")
    assert hasattr(_prance_rs, "absurl")
    assert hasattr(_prance_rs, "split_fragment_reference")
    assert hasattr(_prance_rs, "split_url_reference")
    assert hasattr(_prance_rs, "RefResolver")
    assert hasattr(_prance_rs, "validate_openapi_spec")
    assert hasattr(_prance_rs, "load_openapi_spec_py")
    assert hasattr(_prance_rs, "parse_and_validate_spec")


def test_prance_rs_wired_into_resolver():
    _prance_rs = _rebind_rust_bindings()
    from prance.util import resolver

    assert _prance_rs is not None
    assert resolver._rust_deepcopy_json is _prance_rs.fast_deepcopy_json
    if resolver._RustRefResolver is not None:
        assert resolver.RefResolver is resolver._RustRefResolver
    else:
        assert resolver.RefResolver is resolver._PythonRefResolver


def test_prance_rs_wired_into_path():
    _prance_rs = _rebind_rust_bindings()
    from prance.util import path as path_mod

    assert _prance_rs is not None
    assert path_mod._rust_path_get is _prance_rs.path_get
    assert path_mod._rust_path_set is _prance_rs.path_set


def test_prance_rs_wired_into_iterators():
    _prance_rs = _rebind_rust_bindings()
    from prance.util import iterators

    assert _prance_rs is not None
    assert iterators._rust_reference_iterator is _prance_rs.reference_iterator


def test_prance_rs_wired_into_validator():
    _prance_rs = _rebind_rust_bindings()
    from prance.util import resolver

    assert _prance_rs is not None
    assert resolver.rust_validate_openapi_spec is _prance_rs.validate_openapi_spec
    assert resolver.rust_load_openapi_spec is _prance_rs.load_openapi_spec_py
    assert resolver.rust_parse_and_validate_spec is _prance_rs.parse_and_validate_spec
    assert resolver.use_rust_validator()


def test_prance_rs_wired_into_url():
    _prance_rs = _rebind_rust_bindings()
    from prance.util import url as url_mod

    assert _prance_rs is not None
    assert url_mod._rust_absurl is _prance_rs.absurl
    assert url_mod._rust_urlresource is _prance_rs.urlresource
    assert url_mod._rust_split_fragment_reference is _prance_rs.split_fragment_reference
    assert url_mod._rust_split_url_reference is _prance_rs.split_url_reference
