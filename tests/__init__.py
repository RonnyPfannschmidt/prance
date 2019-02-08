# -*- coding: utf-8 -*-
"""Test suite module for prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

def run_if_present(*args):
  """
  Run the decorated function if any of the named modules are importable.

  The idea is that one of them must exist, but not all of them. If you have
  multiple mandatory modules, add multiple decorator lines.
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

  def wrapper(func):
    import functools
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      if len(exists[True]) > 0:
        return func(*args, **kwargs)

      import pytest
      pytest.skip('None of the following dependencies exist: %s'
          % (', '.join(exists[False]),))
    return wrapped
  return wrapper
