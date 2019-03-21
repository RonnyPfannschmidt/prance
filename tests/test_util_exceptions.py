# -*- coding: utf-8 -*-
"""Test suite prance.util.exceptions."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance.util import exceptions
from prance import ValidationError

def test_error_without_value():
  try:
    raise ValidationError()
  except Exception as exc:
    assert str(exc) == 'prance.util.exceptions.ValidationError'


def test_error_with_simple_value():
  try:
    raise ValidationError('simple')
  except Exception as exc:
    assert str(exc) == 'simple'


def test_error_with_multiline_value():
  try:
    raise ValidationError("""multi
line""")
  except Exception as exc:
    assert '\n' in str(exc)
