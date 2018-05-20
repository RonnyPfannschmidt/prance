# -*- coding: utf-8 -*-
"""This module contains code for accessing values in nested data structures."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


def path_get(obj, path, defaultvalue = None):
  """
  Retrieve the value from obj indicated by path.

  Like dict.get(), except:

    - Any Mapping or Sequence is supported.
    - Path is itself a Sequence; the first part is applied to the passed
      object, the second part to the value returned from this operation, and
      so forth recursively.

  :param mixed obj: The Sequence or Mapping from which to retrieve values.
  :param Sequence path: A Sequence of zero or more key/index elements.
  :param mixed defaultvalue: If the value at the path does not exist and this
    parameter is not None, it is returned. Otherwise an error is raised.
  """
  import collections

  if path is not None and not isinstance(path, collections.Sequence):
    raise TypeError('Path is a %s, but must be None or a Collection!'
            % (type(path),))

  if isinstance(obj, collections.Mapping):
    if path is None or len(path) < 1:
      return obj or defaultvalue
    return path_get(obj[path[0]], path[1:], defaultvalue)

  elif isinstance(obj, collections.Sequence):
    if path is None or len(path) < 1:
      return obj or defaultvalue

    if not isinstance(path[0], int):
      raise KeyError('Sequences need integer indices only.')

    return path_get(obj[path[0]], path[1:], defaultvalue)

  else:
    # Path must be empty.
    if path is not None and len(path) > 0:
      raise TypeError('Cannot get anything from type %s!' % (type(obj),))
    return obj or defaultvalue


def path_set(obj, path, value, **options):
  """
  Set the value in obj indicated by path.

  Setter anologous to path_get() above.

  As setting values is a write operation, this function optionally creates
  intermediate objects to ensure all elements of path can be dereferenced.

  :param mixed obj: The Sequence or Mapping from which to retrieve values.
  :param Sequence path: A Sequence of zero or more key/index elements.
  :param mixed value: The value to set.
  :param bool create: [optional] Flag indicating whether to create
    intermediate values or not. Defaults to False.
  """
  import collections

  # Retrieve options
  create = options.get('create', False)

  def fill_sequence(seq, index, value_index_type):
    """
    Fill the sequence seq with elements until index can be accessed.

    Fills with None except for the indexed element. That is either a dict or
    a list, depending on the value_index_type. If the latter is an int, a
    list is added. If the latter is None (unknown), None is added. Otherwise
    a dict is added.
    """
    if len(seq) > index:
      return

    while len(seq) < index:
      seq.append(None)

    if value_index_type == int:
      seq.append([])
    elif value_index_type is None:
      seq.append(None)
    else:
      seq.append({})

  def safe_idx(seq, index):
    """
    Safely index a sequence.

    Much like dict.get with default value, except returns None instead of
    raising IndexError.
    """
    try:
      return type(seq[index])
    except IndexError:
      return None

  # print('obj', obj, type(obj))
  # print('path', path)
  # print('value', value)

  if path is not None and not isinstance(path, collections.Sequence):
    raise TypeError('Path is a %s, but must be None or a Collection!'
            % (type(path),))

  if len(path) < 1:
    raise KeyError('Cannot set with an empty path!')

  if isinstance(obj, collections.Mapping):
    # If we don't have a mutable mapping, we should raise a TypeError
    if not isinstance(obj, collections.MutableMapping):  # pragma: nocover
      raise TypeError('Mapping is not mutable: %s' % (type(obj),))

    # If the path has only one element, we just overwrite the element at the
    # given key. Otherwise we recurse.
    if len(path) == 1:
      if not create and path[0] not in obj:
        # dicts would normally silently create, but we have to make it
        # explicit to fulfil our contract.
        raise KeyError('Key "%s" not in Mapping!' % (path[0],))
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
    # If we don't have a mutable sequence, we should raise a TypeError
    if not isinstance(obj, collections.MutableSequence):
      raise TypeError('Sequence is not mutable: %s' % (type(obj),))

    # Ensure integer indices
    if not isinstance(path[0], int):
      raise KeyError('Sequences need integer indices only.')

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
    raise TypeError('Cannot set anything on type %s!' % (type(obj),))
