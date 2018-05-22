# -*- coding: utf-8 -*-
"""Test suite for prance.data ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import data

@pytest.fixture
def petstore_parser():
  from prance import ResolvingParser
  return ResolvingParser('tests/petstore.yaml')


def test_validate_schema():
  # Taken directly from jsonschema documentation
  schema = {
    "type" : "object",
    "properties" : {
      "price" : {"type" : "number"},
      "name" : {"type" : "string"},
    },
  }

  # If no exception is raised by validate(), the instance is valid.
  res = data.validate_schema({"name" : "Eggs", "price" : 34.99}, schema)
  assert res is True

  from prance.util.exceptions import ValidationError
  with pytest.raises(ValidationError):
    data.validate_schema({"name" : "Eggs", "price" : "Invalid"}, schema)

  # Try a bad schema
  from prance.util.exceptions import SchemaError
  with pytest.raises(SchemaError):
    data.validate_schema({'foo': 123}, {'type': 'does-not-exist'})


def test_validate_specs(petstore_parser):
  # Valid error from the specs
  res = data.validate_specs({'code': 123, 'message': 'foo'},
          petstore_parser.specification, ('definitions', 'Error'))
  assert res is True

  # Valid error from the specs
  from prance.util.exceptions import ValidationError
  with pytest.raises(ValidationError):
    data.validate_specs({'code': 'bar', 'message': 'foo'},
          petstore_parser.specification, ('definitions', 'Error'))
  with pytest.raises(ValidationError):
    data.validate_specs({'code': 123, 'message': 42},
          petstore_parser.specification, ('definitions', 'Error'))

  # Let's give a bad path - one that does not exist.
  with pytest.raises(KeyError):
    res = data.validate_specs({'code': 123, 'message': 'foo'},
            petstore_parser.specification, ('frooble',))
