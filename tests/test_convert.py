# -*- coding: utf-8 -*-
"""Test suite for prance.convert ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018-2020 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from . import none_of

from prance import convert

@pytest.fixture
def petstore_yaml():
  from prance.util import fs
  return fs.read_file('tests/OpenAPI-Specification/examples/v2.0/yaml/petstore.yaml')

@pytest.fixture
def petstore_json():
  from prance.util import fs
  return fs.read_file('tests/OpenAPI-Specification/examples/v2.0/json/petstore.json')


@pytest.mark.requires_network()
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


@pytest.mark.requires_network()
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


@pytest.mark.requires_network()
def test_convert_petstore_yaml_explicit_name(petstore_yaml):
  converted, content_type = convert.convert_str(petstore_yaml, filename = 'foo.yml')

  # Check correct content type
  assert 'yaml' in content_type


@pytest.mark.requires_network()
def test_convert_url():
  from prance.util import url
  converted, content_type = convert.convert_url(url.absurl('python://tests/specs/petstore.yaml'))

  # Check correct content type
  assert 'yaml' in content_type

  # Parsing can't fail.
  from prance.util import formats
  parsed = formats.parse_spec(converted, content_type = content_type)

  # Assert the correct target version
  assert 'openapi' in parsed
  assert parsed['openapi'].startswith('3.')


@pytest.mark.requires_network()
@pytest.mark.xfail()
def test_convert_spec():
  from prance import BaseParser, ResolvingParser, ValidationError
  parser = BaseParser('tests/specs/petstore.yaml')

  # Conversion should fail with the default backend.
  with pytest.raises(ValidationError):
    converted = convert.convert_spec(parser.specification)

  # However, with the lazy flag it should work.
  converted = convert.convert_spec(parser.specification, lazy = True)
  assert isinstance(converted, BaseParser)

  # Passing a ResolvingParser class should also work.
  converted = convert.convert_spec(parser.specification, ResolvingParser, lazy = True)
  assert isinstance(converted, ResolvingParser)


@pytest.mark.requires_network()
@pytest.mark.xfail()
def test_convert_parser_lazy_swagger_backend():
  from prance import BaseParser, ResolvingParser, ValidationError
  parser = BaseParser('tests/specs/petstore.yaml')

  # Conversion should fail with the default backend.
  with pytest.raises(ValidationError):
    converted = convert.convert_spec(parser)

  # However, with the lazy flag it should work.
  converted = convert.convert_spec(parser, lazy = True)
  assert isinstance(converted, BaseParser)

  # Passing a ResolvingParser class should also work.
  converted = convert.convert_spec(parser, ResolvingParser, lazy = True)
  assert isinstance(converted, ResolvingParser)


@pytest.mark.skipif(none_of('openapi-spec-validator'), reason='Missing openapi-spec-validator')
@pytest.mark.requires_network()
def test_convert_parser_validated():
  from prance import BaseParser
  parser = BaseParser('tests/specs/petstore.yaml', backend = 'openapi-spec-validator')

  # Conversion should work: it's the right backend, and it validates.
  converted = convert.convert_spec(parser)
  assert isinstance(converted, BaseParser)
  assert converted.version_parsed[0] == 3
