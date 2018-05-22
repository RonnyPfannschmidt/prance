# -*- coding: utf-8 -*-
"""Data related functionality for prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


def validate_json_schema(data, schema, subschema = None):
  """
  Validate data against a JSON schema.

  Careful with JSON schema: if there are no validation keywords specified
  in the schema, all data will be valid!

  :param mixed data: The data to validate.
  :param mixed schema: The schema to validate against.
  :param mixed subschema: [optional] If provided, the specific subschema
      of the schema to validate against. In this case, the data is validated
      against the subschema, but the entire schema is used for e.g. reference
      resolution.
  :return: True if validation is successful.
  :rtype: bool
  :raises: prance.util.exceptions.SchemaError if the schema is invalid.
  :raises: prance.util.exceptions.ValidationError if the data is invalid.
  """
  # Perform validation with jsonschema
  from jsonschema.validators import validator_for
  from jsonschema.exceptions import ValidationError as JSEValidationError
  from jsonschema.exceptions import SchemaError as JSESchemaError

  try:
    # Get validator
    validator = validator_for(schema)

    # Validate schema itself
    validator.check_schema(schema)

    # Now validate with the subschema - if it's None, validate() will use the
    # entire schema, exactly like we want.
    validator(schema).validate(data, _schema = subschema)
  except JSEValidationError as exc:
    from .util.exceptions import raise_from, ValidationError
    raise_from(ValidationError, exc)
  except JSESchemaError as exc:
    from .util.exceptions import raise_from, SchemaError
    raise_from(SchemaError, exc)

  # Just in case the result is tested
  return True


def validate_schema_object(data, schema):
  """
  Validate data against a JSON schema and the OpenAPI specs.

  The OpenAPI specs are a little more restrictive when it comes
  to Schema Objects than JSON Schema is. We therefore first
  validate the schema against the OpenAPI specs, before validating
  the data object.

  :param mixed data: The data to validate.
  :param mixed schema: The schema to validate against.
  :return: True if validation is successful.
  :rtype: bool
  :raises: prance.util.exceptions.SchemaError if the schema is invalid.
  :raises: prance.util.exceptions.ValidationError if the data is invalid.
  """
  from .util import validation_backends
  if 'openapi-spec-validator' not in validation_backends():
    raise ImportError('The "openapi-spec-validator" backend is required for '
        'data validation, as only OpenAPI 3 specs are permitted here.')

  # First, ensure that the schema is valid according to the OpenAPI
  # specs.
  from .util.exceptions import ValidationError
  try:
    from openapi_spec_validator import schema_v3
    validate_json_schema(schema, schema_v3,
        subschema = schema_v3['definitions']['schemaOrReference'])
  except ValidationError as exc:
    from .util.exceptions import raise_from, SchemaError
    raise_from(SchemaError, exc)

  # Next, validate data according to the sub schema
  return validate_json_schema(data, schema)


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
  return validate_json_schema(data, schema)
