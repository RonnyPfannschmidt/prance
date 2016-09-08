# -*- coding: utf-8 -*-
"""This submodule contains specialty iterators over specs."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


def reference_iterator(specs, path = ()):
  """
  Iterate through the given specs, returning only references.

  The iterator returns three values:
    - The key, mimicking the behaviour of other iterators, although
      it will always equal '$ref'
    - The value
    - The path to the item. This is a tuple of all the item's ancestors,
      in sequence, so that you can reasonably easily find the containing
      item.
  """
  # Due to the differences in Python 2.7 and 3.0, we have to first find which
  # basic iterator to use.
  try:
    basic_iterator = getattr(specs, 'viewitems')  # 2.7
  except AttributeError:
    basic_iterator = getattr(specs, 'items')      # 3.x

  # We need to iterate through the nested specification dict, so let's
  # start with an appropriate iterator. We can immediately optimize it by
  # only returning '$ref' items.
  import collections

  for key, value in basic_iterator():
    if isinstance(value, collections.Mapping):
      for inner in reference_iterator(value, path + (key,)):
        yield inner
    elif key == '$ref':
      yield key, value, path
