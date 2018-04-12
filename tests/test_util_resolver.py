# -*- coding: utf-8 -*-
"""Test suite for prance.util.resolver ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import pytest

from prance.util import fs
from prance.util import resolver
from prance.util.url import ResolutionError


def get_specs(fname):
  specs = fs.read_file(fname)

  from prance.util import formats
  specs = formats.parse_spec(specs, fname)

  return specs


def recursion_limit_handler_none(limit, refstring):
  return None


@pytest.fixture
def externals_file():
  return get_specs('tests/with_externals.yaml')


@pytest.fixture
def recursive_objs_file():
  return get_specs('tests/recursive_objs.yaml')


@pytest.fixture
def recursive_files_file():
  return get_specs('tests/recursive_files.yaml')


@pytest.fixture
def recursion_limit_file():
  return get_specs('tests/recursion_limit.yaml')


@pytest.fixture
def recursion_limit_files_file():
  return get_specs('tests/recursion_limit_files.yaml')


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
  from prance.util import fs
  res = resolver.RefResolver(externals_file,
      fs.abspath('tests/with_externals.yaml'))
  res.resolve_references()


def test_resolver_missing_reference(missing_file):
  import os.path
  res = resolver.RefResolver(missing_file,
      fs.abspath('tests/missing_reference.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Cannot resolve')


def test_resolver_recursive_objects(recursive_objs_file):
  # Recursive references to objects are a problem
  import os.path
  res = resolver.RefResolver(recursive_objs_file,
      fs.abspath('tests/recursive_objs.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Recursion reached limit')


def test_resolver_recursive_files(recursive_files_file):
  # Recursive references to files are not a problem
  import os.path
  res = resolver.RefResolver(recursive_files_file,
      fs.abspath('tests/recursive_files.yaml'))
  res.resolve_references()


def test_recursion_limit_do_not_recurse_raise(recursion_limit_file):
  # Expect the default behaviour to raise.
  import os.path
  res = resolver.RefResolver(recursion_limit_file,
      fs.abspath('tests/recursion_limit.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Recursion reached limit of 1')


def test_recursion_limit_do_not_recurse_ignore(recursion_limit_file):
  # If we overload the handler, we should not get an error but should
  # also simply not have the 'next' field - or it should be None
  import os.path
  res = resolver.RefResolver(recursion_limit_file,
      fs.abspath('tests/recursion_limit.yaml'),
      recursion_limit_handler = recursion_limit_handler_none)
  res.resolve_references()

  from prance.util import formats
  contents = formats.serialize_spec(res.specs, 'foo.yaml')

  # The effect of returning None on recursion limit should be that
  # despite having recursion, the outermost reference to
  # definitions/Pet should get resolved.
  assert 'properties' in res.specs['paths']['/pets']['get']['responses']['200']['schema']

  # However, the 'next' field should not be resolved.
  assert res.specs['paths']['/pets']['get']['responses']['200']['schema']['properties']['next']['schema'] is None


def test_recursion_limit_set_limit_ignore(recursion_limit_file):
  # If we overload the handler, and set the recursion limit higher,
  # we should get nested Pet objects a few levels deep.

  import os.path
  res = resolver.RefResolver(recursion_limit_file,
      fs.abspath('tests/recursion_limit.yaml'),
      recursion_limit = 2,
      recursion_limit_handler = recursion_limit_handler_none)
  res.resolve_references()

  from prance.util import formats
  contents = formats.serialize_spec(res.specs, 'foo.yaml')

  # The effect of returning None on recursion limit should be that
  # despite having recursion, the outermost reference to
  # definitions/Pet should get resolved.
  assert 'properties' in res.specs['paths']['/pets']['get']['responses']['200']['schema']

  # However, the 'next' field should be resolved due to the higher recursion limit
  next_field = res.specs['paths']['/pets']['get']['responses']['200']['schema']['properties']['next']['schema']
  assert next_field is not None

  # But the 'next' field of the 'next' field should not be resolved.
  assert next_field['properties']['next']['schema'] is None


def test_recursion_limit_do_not_recurse_raise_files(recursion_limit_files_file):
  # Expect the default behaviour to raise.
  import os.path
  res = resolver.RefResolver(recursion_limit_files_file,
      fs.abspath('tests/recursion_limit_files.yaml'))
  with pytest.raises(ResolutionError) as exc:
    res.resolve_references()

  assert str(exc.value).startswith('Recursion reached limit of 1')


def test_recursion_limit_do_not_recurse_ignore_files(recursion_limit_files_file):
  # If we overload the handler, we should not get an error but should
  # also simply not have the 'next' field - or it should be None
  import os.path
  res = resolver.RefResolver(recursion_limit_files_file,
      fs.abspath('tests/recursion_limit_files.yaml'),
      recursion_limit_handler = recursion_limit_handler_none)
  res.resolve_references()

  from prance.util import formats
  contents = formats.serialize_spec(res.specs, 'foo.yaml')

  # The effect of returning None on recursion limit should be that
  # despite having recursion, the outermost reference to
  # definitions/Pet should get resolved.
  assert 'properties' in res.specs['paths']['/pets']['get']['responses']['200']['schema']

  # However, the 'next' field should not be resolved.
  assert res.specs['paths']['/pets']['get']['responses']['200']['schema']['properties']['next']['schema'] is None


def test_recursion_limit_set_limit_ignore_files(recursion_limit_files_file):
  # If we overload the handler, and set the recursion limit higher,
  # we should get nested Pet objects a few levels deep.

  import os.path
  res = resolver.RefResolver(recursion_limit_files_file,
      fs.abspath('tests/recursion_limit_files.yaml'),
      recursion_limit = 2,
      recursion_limit_handler = recursion_limit_handler_none)
  res.resolve_references()

  from prance.util import formats
  contents = formats.serialize_spec(res.specs, 'foo.yaml')

  # The effect of returning None on recursion limit should be that
  # despite having recursion, the outermost reference to
  # definitions/Pet should get resolved.
  assert 'properties' in res.specs['paths']['/pets']['get']['responses']['200']['schema']

  # However, the 'next' field should be resolved due to the higher recursion limit
  next_field = res.specs['paths']['/pets']['get']['responses']['200']['schema']['properties']['next']['schema']
  assert next_field is not None

  # But the 'next' field of the 'next' field should not be resolved.
  assert next_field['properties']['next']['schema'] is None
