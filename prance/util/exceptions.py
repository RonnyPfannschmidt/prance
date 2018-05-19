# -*- coding: utf-8 -*-
"""This submodule contains helpers for exception handling."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


# Raise the given exception class from the caught exception, preserving
# stack trace and message as much as possible.
import six
if six.PY3:  # pragma: nocover
  six.exec_("""def raise_from(klass, from_value):
  try:
    if from_value is None:
      raise klass()
    raise klass(*from_value.args) from from_value
  finally:
    klass = None
""")
elif six.PY2:  # pragma: nocover
  six.exec_("""def raise_from(klass, from_value):
  try:
    if from_value is None:
      raise klass()
    import sys
    exc_info = sys.exc_info()
    raise klass, klass(*from_value.args), exc_info[2]
  finally:
    klass = None
""")
