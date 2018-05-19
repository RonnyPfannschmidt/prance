# -*- coding: utf-8 -*-
"""Test suite for prance.util.fs ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import os
import sys

import pytest

from prance.util import fs


def test_canonical():
  testname = 'tests/symlink_test'
  if sys.platform != "win32":
    res = fs.canonical_filename(testname)
    expected = os.path.join(os.getcwd(), 'tests/with_externals.yaml')
    assert res == expected

def test_to_posix_rel():
  test = "tests/with_externals.yaml"
  assert fs.to_posix(os.path.normpath(test)) == test

def test_to_posix_abs():
  if sys.platform == "win32":
    test = "c:\\windows\\notepad.exe"
    expected = "/c:/windows/notepad.exe"
  else:
    test = "/etc/passwd"
    expected = test
  assert fs.to_posix(test) == expected

def test_from_posix_rel():
  test = "tests/with_externals.yaml"
  assert fs.from_posix(test) == os.path.normpath(test)

def test_from_posix_abs():
  if sys.platform == "win32":
    test = "/c:/windows/notepad.exe"
    expected = "c:\\windows\\notepad.exe"
  else:
    test = "/etc/passwd"
    expected = test
  assert fs.from_posix(test) == expected

def test_abspath_basics():
  testname = os.path.normpath('tests/with_externals.yaml')
  res = fs.abspath(testname)
  expected = fs.to_posix(os.path.join(os.getcwd(), testname))
  assert res == expected

def test_abspath_relative():
  testname = 'error.json'
  relative = os.path.join(os.getcwd(), 'tests/with_externals.yaml')
  res = fs.abspath(testname, relative)
  expected = fs.to_posix(os.path.join(os.getcwd(), 'tests', testname))
  assert res == expected


def test_abspath_relative_dir():
  testname = 'error.json'
  relative = os.path.join(os.getcwd(), 'tests')
  res = fs.abspath(testname, relative)
  expected = fs.to_posix(os.path.join(os.getcwd(), 'tests', testname))
  assert res == expected


def test_detect_encoding():
  # Quick detection should yield utf-8 for the petstore file.
  assert fs.detect_encoding('tests/petstore.yaml') == 'utf-8'

  # Really, it should be detected as ISO-8859-1 as a superset of ASCII
  assert fs.detect_encoding('tests/petstore.yaml',
                            default_to_utf8 = False) == 'iso-8859-1'

  # Deep inspection should yield UTF-8 again.
  assert fs.detect_encoding('tests/petstore.yaml',
                            default_to_utf8 = False,
                            read_all = True) == 'utf-8'

  # The UTF-8 file with BOM should be detected properly
  assert fs.detect_encoding('tests/utf8bom.yaml') == 'utf-8-sig'


def test_load_nobom():
  contents = fs.read_file('tests/petstore.yaml')
  assert contents.index(u'Swagger Petstore') >= 0, 'File reading failed!'


def test_load_utf8bom():
  contents = fs.read_file('tests/utf8bom.yaml')
  assert contents.index(u'söme välüe') >= 0, 'UTF-8 BOM handling failed!'


def test_load_utf8bom_override():
  with pytest.raises(UnicodeDecodeError):
    fs.read_file('tests/utf8bom.yaml', 'ascii')


def test_write_file():
  # What we're doing here has really nothing to do with click's CliRunner,
  # but since we have it, we might as well use its sandboxing feature.
  from click.testing import CliRunner
  runner = CliRunner()
  with runner.isolated_filesystem():
    test_text = u'söme täxt'
    fs.write_file('test.out', test_text)

    # File must have been written
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    assert 'test.out' in files

    # File contents must work
    contents = fs.read_file('test.out')
    assert test_text == contents


def test_write_file_bom():
  # What we're doing here has really nothing to do with click's CliRunner,
  # but since we have it, we might as well use its sandboxing feature.
  from click.testing import CliRunner
  runner = CliRunner()
  with runner.isolated_filesystem():
    test_text = u'söme täxt'
    fs.write_file('test.out', test_text, 'utf-8-sig')

    # File must have been written
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    assert 'test.out' in files

    # Encoding must match the one we've given
    encoding = fs.detect_encoding('test.out')
    assert encoding == 'utf-8-sig'

    # File contents must work
    contents = fs.read_file('test.out')
    assert test_text == contents
