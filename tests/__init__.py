# -*- coding: utf-8 -*-
"""Test suite module for prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

def run_if_present(name):
  import importlib
  exists = False
  try:
    importlib.import_module(name)
    exists = True
  except ImportError:
    pass

  print('exists', name, exists)

  def wrapper(func):
    import functools
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
      if exists:
        return func(*args, **kwargs)
      import pytest
      pytest.skip('Required dependency "%s" does not exist.' % (name,))
    return wrapped
  return wrapper
