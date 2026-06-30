"""Tests for the bundled ``_prance_fast`` Cython extension."""
import pytest


def test_prance_fast_extension_importable():
    import _prance_fast

    assert hasattr(_prance_fast, "fast_deepcopy_json")
    assert hasattr(_prance_fast, "path_get")
    assert hasattr(_prance_fast, "path_set")
    assert hasattr(_prance_fast, "reference_iterator")
    assert hasattr(_prance_fast, "RefResolver")


def test_prance_fast_wired_into_resolver():
    from prance.util import resolver

    assert resolver._fast_deepcopy_json is not None
    assert resolver._FastRefResolver is not None
    assert resolver.RefResolver is resolver._FastRefResolver


def test_prance_fast_wired_into_path():
    from prance.util import path as path_mod

    assert path_mod._fast_path_get is not None
    assert path_mod._fast_path_set is not None


def test_prance_fast_wired_into_iterators():
    from prance.util import iterators

    assert iterators._fast_reference_iterator is not None
