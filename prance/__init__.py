# -*- coding: utf-8 -*-
"""
Prance implements parsers for Swagger/OpenAPI 2.0 API specs.

See https://openapis.org/ for details on the specification.

Included is a BaseParser that reads and validates swagger specs, and a
ResolvingParser that additionally resolves any $ref references.
"""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ('util', 'mixins', 'cli')
__version__ = '0.9.0'


# Define our own error class
class SwaggerValidationError(Exception):
  pass


from . import mixins

# Placeholder for when no URL is specified for the main spec file
import sys
if sys.platform == 'win32':  # pragma: nocover
  # Placeholder must be absolute
  _PLACEHOLDER_URL = 'file:///c:/__placeholder_url__.yaml'
else:
  _PLACEHOLDER_URL = 'file:///__placeholder_url__.yaml'


class BaseParser(mixins.YAMLMixin, mixins.JSONMixin, object):
  """
  The BaseParser loads, parses and validates Swagger/OpenAPI 2.0 specs.

  Uses :py:class:`YAMLMixin` and :py:class:`JSONMixin` for additional
  functionality.
  """

  BACKENDS = {
    'flex': '_validate_flex',
    'swagger-spec-validator': '_validate_swagger_spec_validator',
  }

  def __init__(self, url = None, spec_string = None, lazy = False, **kwargs):
    """
    Load, parse and validate specs.

    You can either provide a URL or a spec string, but not both.

    :param str url: The URL of the file to load. URLs missing a scheme are
      assumed to be file URLs.
    :param str spec_string: The specifications to parse.
    :param bool lazy: If true, do not load or parse anything. Instead wait for
      the parse function to be invoked.
    :param str backend: [optional] one of 'flex', 'swagger-spec-validator'.
      Determines the validation backend to use. Defaults to 'flex'.
    :param bool strict: [optional] Applies only to the 'swagger-spec-validator'
      backend. If False, accepts non-String keys by stringifying them before
      validation. Defaults to True.
    """
    assert url or spec_string and not (url and spec_string), \
        'You must provide either a URL to read, or a spec string to '\
        'parse, but not both!'

    # Keep the parameters around for later use
    self.url = None
    if url:
      from .util.url import absurl
      from .util.fs import abspath
      import os
      self.url = absurl(url, abspath(os.getcwd()))
    else:
      self.url = _PLACEHOLDER_URL

    self._spec_string = spec_string

    # Initialize variables we're filling later
    self.specification = None

    # Add kw args as options
    self._options = kwargs

    # Verify backend
    self._backend = self._options.get('backend', 'flex')
    if self._backend not in BaseParser.BACKENDS.keys():
      raise ValueError('Backend may only be one of %s!'
              % (BaseParser.BACKENDS.keys(), ))

    # Start parsing if lazy mode is not requested.
    if not lazy:
      self.parse()

  def parse(self):  # noqa: F811
    """
    When the BaseParser was lazily created, load and parse now.

    You can use this function to re-use an existing parser for parsing
    multiple files by setting its url property and then invoking this
    function.
    """
    # If we have a file name, we need to read that in.
    if self.url and self.url != _PLACEHOLDER_URL:
      from .util.url import fetch_url
      self.specification = fetch_url(self.url)

    # If we have a spec string, try to parse it.
    if self._spec_string:
      from .util.formats import parse_spec
      self.specification = parse_spec(self._spec_string, self.url)

    # Perform some sanitization in lenient mode.
    if not self._options.get('strict', True):
      from .util import stringify_keys
      self.specification = stringify_keys(self.specification)

    # If we have a parsed spec, convert it to JSON. Then we can validate
    # the JSON. At this point, we *require* a parsed specification to exist,
    # so we might as well assert.
    assert self.specification, 'No specification parsed, cannot validate!'

    self._validate()

  def _validate(self):
    # Validate the parsed specs, using the given validation backend.
    validator = getattr(self, BaseParser.BACKENDS[self._backend])
    validator()

  def _validate_flex(self):
    from flex.exceptions import ValidationError
    from flex.core import parse as validate
    try:
      validate(self.specification)
    except ValidationError as ex:
      raise SwaggerValidationError(str(ex))

  def _validate_swagger_spec_validator(self):
    from swagger_spec_validator.common import SwaggerValidationError as SSVErr
    from swagger_spec_validator.validator20 import validate_spec
    try:
      validate_spec(self.specification)
    except SSVErr as ex:
      raise SwaggerValidationError(str(ex))


class ResolvingParser(BaseParser):
  """The ResolvingParser extends BaseParser with resolving references."""

  def __init__(self, url = None, spec_string = None, lazy = False, **kwargs):
    """
    See :py:class:`BaseParser`.

    Resolves JSON pointers/references (i.e. '$ref' keys) before validating the
    specs. The implication is that self.specfication is fully resolved, and
    does not contain any references.
    """
    BaseParser.__init__(
        self,
        url = url,
        spec_string = spec_string,
        lazy = lazy,
        **kwargs
    )

  def _validate(self):
    # We have a problem with the BaseParser's validate function: the
    # jsonschema implementation underlying it does not accept relative
    # path references, but the Swagger specs allow them:
    # http://swagger.io/specification/#referenceObject
    # We therefore use our own resolver first, and validate later.
    from .util.resolver import RefResolver
    resolver = RefResolver(self.specification, self.url)
    resolver.resolve_references()
    self.specification = resolver.specs

    # Now validate - the BaseParser knows the specifics
    BaseParser._validate(self)
