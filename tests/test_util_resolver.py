# -*- coding: utf-8 -*-
"""Test suite for prance.util.resolver ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import pytest

from prance.util import resolver
from prance.util.url import ResolutionError


def get_specs(fname):
  from prance.util import fs
  specs = fs.read_file(fname)

  from prance.util import formats
  specs = formats.parse_spec(specs, fname)

  return specs


@pytest.fixture
def externals_file():
  return get_specs('tests/with_externals.yaml')


@pytest.fixture
def recursive_file():
  return get_specs('tests/recursive.yaml')


@pytest.fixture
def missing_file():
  return get_specs('tests/missing_reference.yaml')


def test_resolver_noname(externals_file):
  res = resolver.RefResolver(externals_file)
  # Can't build a fragment URL without reference
  with pytest.raises(ResolutionError):
    res.resolve_references()


def test_resolver_named(externals_file):
  import os.path
  res = resolver.RefResolver(externals_file,
      os.path.abspath('tests/with_externals.yaml'))
  res.resolve_references()


def test_resolver_missing_reference(missing_file):
  import os.path
  res = resolver.RefResolver(missing_file,
      os.path.abspath('tests/missing_reference.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Cannot resolve')


def test_resolver_recursive(recursive_file):
  import os.path
  res = resolver.RefResolver(recursive_file,
      os.path.abspath('tests/recursive.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Recursion detected')
