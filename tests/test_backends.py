# -*- coding: utf-8 -*-
"""Test suite focusing on validation backend features."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import BaseParser
from prance import ValidationError
from prance.util import validation_backends

def test_bad_backend():
  with pytest.raises(ValueError):
    BaseParser('tests/petstore.yaml', backend = 'does_not_exist')


def test_flex_issue_5_integer_keys():
  # Must succeed with default (flex) parser; note the parser does not stringify the response code
  parser = BaseParser('tests/issue_5.yaml', backend = 'flex')
  assert 200 in parser.specification['paths']['/test']['post']['responses']


def test_flex_validate_success():
  parser = BaseParser('tests/petstore.yaml', backend = 'flex')


def test_flex_validate_failure():
  with pytest.raises(ValidationError):
    parser = BaseParser('tests/missing_reference.yaml', backend = 'flex')


if 'swagger-spec-validator' in validation_backends():
  def test_swagger_spec_validator_issue_5_integer_keys():
    # Must fail in implicit strict mode.
    with pytest.raises(ValidationError):
      BaseParser('tests/issue_5.yaml', backend = 'swagger-spec-validator')

    # Must fail in explicit strict mode.
    with pytest.raises(ValidationError):
      BaseParser('tests/issue_5.yaml', backend = 'swagger-spec-validator', strict = True)

    # Must succeed in non-strict/lenient mode
    parser = BaseParser('tests/issue_5.yaml', backend = 'swagger-spec-validator', strict = False)
    assert '200' in parser.specification['paths']['/test']['post']['responses']


  def test_swagger_spec_validator_validate_success():
    parser = BaseParser('tests/petstore.yaml', backend = 'swagger-spec-validator')


  def test_swagger_spec_validator_validate_failure():
    with pytest.raises(ValidationError):
      parser = BaseParser('tests/missing_reference.yaml', backend = 'swagger-spec-validator')


if 'openapi-spec-validator' in validation_backends():
  def test_openapi_spec_validator_issue_5_integer_keys():
    # Must fail in implicit strict mode.
    with pytest.raises(ValidationError):
      BaseParser('tests/issue_5.yaml', backend = 'openapi-spec-validator')

    # Must fail in explicit strict mode.
    with pytest.raises(ValidationError):
      BaseParser('tests/issue_5.yaml', backend = 'openapi-spec-validator', strict = True)

    # Must succeed in non-strict/lenient mode
    parser = BaseParser('tests/issue_5.yaml', backend = 'openapi-spec-validator', strict = False)
    assert '200' in parser.specification['paths']['/test']['post']['responses']


  def test_openapi_spec_validator_validate_success():
    parser = BaseParser('tests/petstore.yaml', backend = 'openapi-spec-validator')


  def test_openapi_spec_validator_validate_failure():
    with pytest.raises(ValidationError):
      parser = BaseParser('tests/missing_reference.yaml', backend = 'openapi-spec-validator')
