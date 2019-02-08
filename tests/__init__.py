# -*- coding: utf-8 -*-
"""Test suite module for prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

def _find_imports(*args):
  """
  Helper sorting the named modules into existing and not existing.
  """
  import importlib
  exists = {
    True: [],
    False: [],
  }

  for name in args:
    try:
      importlib.import_module(name)
      exists[True].append(name)
    except ImportError:
      exists[False].append(name)

  return exists


def none_of(*args):
  """
  Return true if none of the named modules exist, false otheriwse.
  """
  exists = _find_imports(*args)
  return len(exists[True]) == 0
