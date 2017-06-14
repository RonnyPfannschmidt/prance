# -*- coding: utf-8 -*-
"""Test suite for prance.ResolvingParser ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import ResolvingParser
from prance import SwaggerValidationError

@pytest.fixture
def petstore_parser():
  return ResolvingParser('tests/petstore.yaml')


@pytest.fixture
def with_externals_parser():
  return ResolvingParser('tests/with_externals.yaml')


@pytest.fixture
def petstore_parser_from_string():
  yaml = None
  with open('tests/petstore.yaml', 'rb') as f:
    x = f.read()
    yaml = x.decode('utf8')
  return ResolvingParser(spec_string = yaml)


@pytest.fixture
def issue_1_parser():
  return ResolvingParser('tests/issue_1.json')


def test_basics(petstore_parser):
  assert petstore_parser.specification, 'No specs loaded!'


def test_petstore_resolve(petstore_parser):
  assert petstore_parser.specification, 'No specs loaded!'

  # The petstore references /definitions/Pet in /definitions/Pets, and uses
  # /definitions/Pets in the 200 response to the /pets path. So let's check
  # whether we can find something of /definitions/Pet there...
  res = petstore_parser.specification['paths']['/pets']['get']['responses']
  assert res['200']['schema']['type'] == 'array', 'Did not resolve right!'


def test_with_externals_resolve(with_externals_parser):
  assert with_externals_parser.specification, 'No specs loaded!'

  # The specs are a simplified version of the petstore example, with some
  # external references.
  # - Test that the list pets call returns the right thing from the external
  #   definitions.yaml
  res = with_externals_parser.specification['paths']['/pets']['get']
  res = res['responses']
  assert res['200']['schema']['type'] == 'array'

  # - Test that the get single pet call returns the right thing from the
  #   remote petstore definition
  res = with_externals_parser.specification['paths']['/pets/{petId}']['get']
  res = res['responses']
  assert 'id' in res['200']['schema']['required']

  # - Test that error responses contain a message from error.json
  res = with_externals_parser.specification['paths']['/pets']['get']
  res = res['responses']
  assert 'message' in res['default']['schema']['required']


def test_relative_urls_from_string(petstore_parser_from_string):
  # This must succeed
  assert petstore_parser_from_string.yaml(), 'Did not get YAML representation of specs!'


def test_issue_1_relative_path_references(issue_1_parser):
  # Must resolve references correctly
  params = issue_1_parser.specification["paths"]["/test"]["parameters"]
  assert 'id' in params[0]['schema']['required']


def test_issue_5_integer_keys():
  # Must fail in implicit strict mode.
  with pytest.raises(SwaggerValidationError):
    ResolvingParser('tests/issue_5.yaml')

  # Must fail in explicit strict mode.
  with pytest.raises(SwaggerValidationError):
    ResolvingParser('tests/issue_5.yaml', strict = True)

  # Must succeed in non-strict/lenient mode
  parser = ResolvingParser('tests/issue_5.yaml', strict = False)
  assert '200' in parser.specification['paths']['/test']['post']['responses']
