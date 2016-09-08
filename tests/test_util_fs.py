# -*- coding: utf-8 -*-
"""Test suite for prance.util.fs ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import os

from prance.util import fs


def test_canonical():
  testname = 'tests/symlink_test'
  res = fs.canonical_filename(testname)
  expected = os.path.join(os.getcwd(), 'tests/with_externals.yaml')
  assert res == expected


def test_abspath_basics():
  testname = 'tests/with_externals.yaml'
  res = fs.abspath(testname)
  expected = os.path.join(os.getcwd(), testname)
  assert res == expected


def test_abspath_relative():
  testname = 'error.json'
  relative = os.path.join(os.getcwd(), 'tests/with_externals.yaml')
  res = fs.abspath(testname, relative)
  expected = os.path.join(os.getcwd(), 'tests', testname)
  assert res == expected


def test_abspath_relative_dir():
  testname = 'error.json'
  relative = os.path.join(os.getcwd(), 'tests')
  res = fs.abspath(testname, relative)
  expected = os.path.join(os.getcwd(), 'tests', testname)
  assert res == expected


def test_load_nobom():
  contents = fs.read_file('tests/petstore.yaml')
  assert contents.index(u'Swagger Petstore') >= 0, 'File reading failed!'


def test_load_utf8bom():
  contents = fs.read_file('tests/utf8bom.yaml')
  assert contents.index(u'söme välüe') >= 0, 'UTF-8 BOM handling failed!'
