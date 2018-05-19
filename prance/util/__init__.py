# -*- coding: utf-8 -*-
"""This submodule contains utility code for Prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ('iterators', 'fs', 'formats', 'resolver', 'url', 'path',
    'exceptions')


def stringify_keys(data):
  """
  Recursively stringify keys in a dict-like object.

  :param dict-like data: A dict-like object to stringify keys in.
  :return: A new dict-like object of the same type with stringified keys,
      but the same values.
  """
  import collections
  assert isinstance(data, collections.Mapping)

  ret = type(data)()
  import six
  for key, value in six.iteritems(data):
    if not isinstance(key, six.string_types):
      key = str(key)
    if isinstance(value, collections.Mapping):
      value = stringify_keys(value)
    ret[key] = value
  return ret


def validation_backends():
  """
  Return a list of validation backends supported by the environment.

  Validation backends other than 'flex' are optional.
  """
  ret = ['flex']

  try:
    import swagger_spec_validator  # noqa: F401
    ret.append('swagger-spec-validator')
  except (ImportError, SyntaxError):  # pragma: nocover
    pass

  try:
    import openapi_spec_validator  # noqa: F401
    ret.append('openapi-spec-validator')
  except (ImportError, SyntaxError):  # pragma: nocover
    pass

  return tuple(ret)
