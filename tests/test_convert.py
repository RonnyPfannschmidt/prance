# -*- coding: utf-8 -*-
"""Test suite for prance.convert ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import convert

@pytest.fixture
def petstore_yaml():
  from prance.util import fs
  return fs.read_file('tests/OpenAPI-Specification/examples/v2.0/yaml/petstore.yaml')

@pytest.fixture
def petstore_json():
  from prance.util import fs
  return fs.read_file('tests/OpenAPI-Specification/examples/v2.0/json/petstore.json')


def test_convert_petstore_yaml(petstore_yaml):
  converted, content_type = convert.convert_str(petstore_yaml)

  # Check correct content type
  assert 'yaml' in content_type

  # Parsing can't fail.
  from prance.util import formats
  parsed = formats.parse_spec(converted, content_type = content_type)

  # Assert the correct target version
  assert 'openapi' in parsed
  assert parsed['openapi'].startswith('3.')


def test_convert_petstore_json(petstore_json):
  converted, content_type = convert.convert_str(petstore_json)

  # Check correct content type
  assert 'json' in content_type

  # Parsing can't fail.
  from prance.util import formats
  parsed = formats.parse_spec(converted, content_type = content_type)

  # Assert the correct target version
  assert 'openapi' in parsed
  assert parsed['openapi'].startswith('3.')


def test_convert_petstore_yaml_explicit_name(petstore_yaml):
  converted, content_type = convert.convert_str(petstore_yaml, filename = 'foo.yml')

  # Check correct content type
  assert 'yaml' in content_type


def test_convert_url():
  from prance.util import url
  converted, content_type = convert.convert_url(url.absurl('python://tests/petstore.yaml'))

  # Check correct content type
  assert 'yaml' in content_type

  # Parsing can't fail.
  from prance.util import formats
  parsed = formats.parse_spec(converted, content_type = content_type)

  # Assert the correct target version
  assert 'openapi' in parsed
  assert parsed['openapi'].startswith('3.')

