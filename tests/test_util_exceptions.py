# -*- coding: utf-8 -*-
"""Test suite prance.util.exceptions."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance.util import exceptions
from prance import ValidationError

def test_reraise_without_value():
  with pytest.raises(ValidationError) as caught:
    exceptions.raise_from(ValidationError, None)

  # The first is obvious from pytest.raises. The rest tests
  # known attributes
  assert caught.type == ValidationError
  assert str(caught.value) == ''


def test_reraise_with_value():
  with pytest.raises(ValidationError) as caught:
    try:
      raise RuntimeError("foo")
    except RuntimeError as inner:
      exceptions.raise_from(ValidationError, inner)

  # The first is obvious from pytest.raises. The rest tests
  # known attributes
  assert caught.type == ValidationError
  assert str(caught.value) == 'foo'
