# -*- coding: utf-8 -*-
"""This module contains code for accessing values in nested data structures."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

def path_get(obj, path, defaultvalue = None):
  import collections

  if path is not None and not isinstance(path, collections.Sequence):
    raise TypeError("Path is a %s, but must be None or a Collection!" % (type(path),))

  if isinstance(obj, collections.Mapping):
    if path is None or len(path) < 1:
      return obj or defaultvalue
    return path_get(obj[path[0]], path[1:], defaultvalue)

  elif isinstance(obj, collections.Sequence):
    if path is None or len(path) < 1:
      return obj or defaultvalue
    if not isinstance(path[0], int):
      raise KeyError("Sequences need integer indices only.")
    return path_get(obj[path[0]], path[1:], defaultvalue)

  else:
    # Path must be empty.
    if path is not None and len(path) > 0:
      raise KeyError("Nopetiy nope nope")
    return obj or defaultvalue


def path_set(obj, path, value, **options):
  import collections

  create = options.get('create', False)

  def fill_sequence(seq, index, value_index_type):
    # print("Filling %s to %d (value index type: %s)" % (seq, index, value_index_type))
    while len(seq) < index:
      seq.append(None)

    if value_index_type == int:
      seq.append([])
    elif value_index_type == None:
      seq.append(None)
    else:
      seq.append({})
    # print("-> %s" % (seq,))

  def safe_idx(seq, index):
    try:
      return type(seq[index])
    except IndexError:
      return None

  # print('obj', obj, type(obj))
  # print('path', path)
  # print('value', value)

  if path is not None and not isinstance(path, collections.Sequence):
    raise TypeError("Path is a %s, but must be None or a Collection!" % (type(path),))

  if len(path) < 1:
    # FIXME not for value types?
    raise KeyError("Can't set without a path!")

  if isinstance(obj, collections.Mapping):
    # If we don't have a mutable mapping, we should raise a TypeError
    if not isinstance(obj, collections.MutableMapping):  # pragma: nocover
      raise TypeError("Mapping is not mutable: %s" % (type(obj),))
    # if path is None or len(path) < 1:
    #   return obj
    # # TODO check by key
    # return path_set(obj[path[0]], path[1:], value)

    # If the path has only one element, we just overwrite the element at the
    # given key. Otherwise we recurse.
    if len(path) == 1:
      if not create and path[0] not in obj:
        raise KeyError("Key '%s' not in Mapping!" % (path[0],))
      obj[path[0]] = value
    else:
      if create and path[0] not in obj:
        if type(path[1]) == int:
          obj[path[0]] = []
        else:
          obj[path[0]] = {}
      path_set(obj[path[0]], path[1:], value, create = create)

    return obj

  elif isinstance(obj, collections.Sequence):
    if not isinstance(path[0], int):
      raise KeyError("Sequences need integer indices only.")

    # If we don't have a mutable sequence, we should raise a TypeError
    if not isinstance(obj, collections.MutableSequence):
      raise TypeError("Sequence is not mutable: %s" % (type(obj),))

    # If we're supposed to create and the index at path[0] doesn't exist,
    # then we need to push some dummy objects.
    if create:
      fill_sequence(obj, path[0], safe_idx(path, 1))

    # If the path has only one element, we just overwrite the element at the
    # given index. Otherwise we recurse.
    # print('pl', len(path))
    if len(path) == 1:
      obj[path[0]] = value
    else:
      path_set(obj[path[0]], path[1:], value, create = create)

    return obj
  else:
    raise TypeError("Cannot set anything on type %s" % (type(obj),))
