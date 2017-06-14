# -*- coding: utf-8 -*-
"""Test suite for prance.cli ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from click.testing import CliRunner

from prance import cli


@pytest.fixture
def runner():
  return CliRunner()


def test_validate_defaults(runner):
  # Good example
  result = runner.invoke(cli.validate, ['tests/petstore.yaml'])
  assert result.exit_code == 0
  expected = """Processing "tests/petstore.yaml"...
 -> Resolving external references.
Validates OK as Swagger/OpenAPI 2.0!
"""
  assert result.output == expected

  # Bad example
  result = runner.invoke(cli.validate, ['tests/definitions.yaml'])
  assert result.exit_code == 1
  assert 'SwaggerValidationError' in result.output


def test_validate_multiple(runner):
  result = runner.invoke(cli.validate,
      ['tests/petstore.yaml', 'tests/petstore.yaml'])
  assert result.exit_code == 0
  expected = """Processing "tests/petstore.yaml"...
 -> Resolving external references.
Validates OK as Swagger/OpenAPI 2.0!
Processing "tests/petstore.yaml"...
 -> Resolving external references.
Validates OK as Swagger/OpenAPI 2.0!
"""
  assert result.output == expected


def test_validate_no_resolve(runner):
  # Good example
  result = runner.invoke(cli.validate, ['--no-resolve', 'tests/petstore.yaml'])
  assert result.exit_code == 0
  expected = """Processing "tests/petstore.yaml"...
 -> Not resolving external references.
Validates OK as Swagger/OpenAPI 2.0!
"""
  assert result.output == expected


def test_validate_output_too_many_inputs(runner):
  result = runner.invoke(cli.validate,
      ['-o', 'foo', 'tests/petstore.yaml', 'tests/petstore.yaml'])
  assert result.exit_code == 2
  assert 'If --output-file is given,' in result.output


def test_validate_output(runner):
  import os, os.path
  curdir = os.getcwd()

  outnames = ['foo.json', 'foo.yaml']
  for outname in outnames:
    with runner.isolated_filesystem():
      result = runner.invoke(cli.validate,
          ['-o', outname, os.path.join(curdir, 'tests/petstore.yaml')])
      assert result.exit_code == 0

      # There also must be a 'foo' file now.
      files = [f for f in os.listdir('.') if os.path.isfile(f)]
      assert outname in files

      # Ensure a UTF-8 file encoding.
      from prance.util import fs
      assert 'utf-8' in fs.detect_encoding(outname, default_to_utf8 = False,
                                           read_all = True)

      # Now do a full encoding detection, too

      # The 'foo' file must be a valid swagger spec.
      result = runner.invoke(cli.validate, [outname])
      assert result.exit_code == 0
