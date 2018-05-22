# -*- coding: utf-8 -*-
"""Data related functionality for prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


def validate_schema(data, schema):
  """
  Validate data against a JSON schema.

  Careful with JSON schema: if there are no validation keywords specified
  in the schema, all data will be valid!

  :param mixed data: The data to validate.
  :param mixed schema: The schema to validate against.
  :return: True if validation is successful.
  :rtype: bool
  :raises: prance.util.exceptions.SchemaError if the schema is invalid.
  :raises: prance.util.exceptions.ValidationError if the data is invalid.
  """
  # Perform minimal validation of the schema itself

  # Perform validation with jsonschema
  from jsonschema import validate
  from jsonschema.exceptions import ValidationError as JSEValidationError
  from jsonschema.exceptions import SchemaError as JSESchemaError

  try:
    validate(data, schema)
  except JSEValidationError as exc:
    from .util.exceptions import raise_from, ValidationError
    raise_from(ValidationError, exc)
  except JSESchemaError as exc:
    from .util.exceptions import raise_from, SchemaError
    raise_from(SchemaError, exc)

  # Just in case the result is tested
  return True


def validate_specs(data, specs, path = None):
  """
  Validate data against part of a spec, indicated by path.

  :param mixed data: The data to validate.
  :param mixed spec: The specification to use.
  :param mixed path: The path to use for finding the validation
    schema in the spec. Uses prance.util.path.
  :return: True if validation is successful.
  :rtype: bool
  :raises: prance.util.exceptions.SchemaError if the schema is invalid.
  :raises: prance.util.exceptions.ValidationError if the data is invalid.
  """
  # First, grab the relevant schema from the specs.
  from .util.path import path_get
  schema = path_get(specs, path)

  # Then validate with that schema.
  return validate_schema(data, schema)
