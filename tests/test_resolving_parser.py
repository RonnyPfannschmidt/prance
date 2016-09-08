# -*- coding: utf-8 -*-
"""Test suite for prance.ResolvingParser ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import ResolvingParser


@pytest.fixture
def petstore_parser():
  return ResolvingParser('tests/petstore.yaml')


@pytest.fixture
def with_externals_parser():
  return ResolvingParser('tests/with_externals.yaml')


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
