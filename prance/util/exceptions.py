# -*- coding: utf-8 -*-
"""This submodule contains helpers for exception handling."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import six as _six


class _MessageMixin(object):
  def __unicode__(self):
    try:
      return self.args[0]
    except IndexError:
      return '%s.%s' % (self.__class__.__module__, self.__class__.__name__)

  if _six.PY3:
    __str__ = __unicode__
  else:
    def __str__(self):
      return unicode(self).encode('utf-8')  # noqa: F821


class ConversionError(_MessageMixin, ValueError):
  pass  # pragma: nocover


class ValidationError(_MessageMixin, ValueError):
  pass  # pragma: nocover


class SchemaError(_MessageMixin, TypeError):
  pass  # pragma: nocover


class ParseError(_MessageMixin, ValueError):
  pass  # pragma: nocover


class ResolutionError(_MessageMixin, LookupError):
  pass  # pragma: nocover
