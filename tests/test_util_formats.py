# -*- coding: utf-8 -*-
"""Test suite for prance.util.formats ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import pytest

from prance.util import formats


def test_parse_yaml():
  yaml = """---
foo: bar
"""
  parsed = formats.parse_spec(yaml, 'foo.yaml')
  assert parsed['foo'] == 'bar', 'Did not parse with explicit YAML'

  parsed = formats.parse_spec(yaml)
  assert parsed['foo'] == 'bar', 'Did not parse with implicit YAML'


def test_parse_yaml_ctype():
  yaml = """---
foo: bar
"""
  parsed = formats.parse_spec(yaml, None, content_type = 'text/yaml')
  assert parsed['foo'] == 'bar', 'Did not parse with explicit YAML'


def test_parse_json():
  json = '{ "foo": "bar" }'

  parsed = formats.parse_spec(json, 'foo.js')
  assert parsed['foo'] == 'bar', 'Did not parse with explicit JSON'


def test_parse_json_ctype():
  json = '{ "foo": "bar" }'

  parsed = formats.parse_spec(json, None, content_type = 'application/json')
  assert parsed['foo'] == 'bar', 'Did not parse with explicit JSON'


def test_parse_unknown():
  with pytest.raises(formats.ParseError):
    formats.parse_spec('{-')


def test_parse_unknown_ext():
  with pytest.raises(formats.ParseError):
    formats.parse_spec('{-', 'asdf.xml')


def test_parse_unknown_ctype():
  with pytest.raises(formats.ParseError):
    formats.parse_spec('{-', None, content_type = 'text/xml')
