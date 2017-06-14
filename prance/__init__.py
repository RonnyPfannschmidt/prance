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
__version__ = '0.6.1'


# Just re-use the error, but hide the namespace
from swagger_spec_validator.common import SwaggerValidationError  # noqa: F401

from . import mixins

# Placeholder for when no URL is specified for the main spec file
_PLACEHOLDER_URL = 'file:///__placeholder_url__.yaml'


class BaseParser(mixins.YAMLMixin, mixins.JSONMixin, object):
  """
  The BaseParser loads, parses and validates Swagger/OpenAPI 2.0 specs.

  Uses :py:class:`YAMLMixin` and :py:class:`JSONMixin` for additional
  functionality.
  """

  def __init__(self, url = None, spec_string = None, lazy = False, **kwargs):
    """
    Load, parse and validate specs.

    You can either provide a URL or a spec string, but not both.

    :param str url: The URL of the file to load. URLs missing a scheme are
      assumed to be file URLs.
    :param str spec_string: The specifications to parse.
    :param bool lazy: If true, do not load or parse anything. Instead wait for
      the parse function to be invoked.
    :param bool strict: [optional] if False, accepts non-String keys by
      stringifying them before validation. Defaults to True.
    """
    assert url or spec_string and not (url and spec_string), \
        'You must provide either a URL to read, or a spec string to '\
        'parse, but not both!'

    # Keep the parameters around for later use
    self.url = None
    if url:
      from .util.url import absurl
      import os
      self.url = absurl(url, os.getcwd())
    else:
      self.url = _PLACEHOLDER_URL

    self._spec_string = spec_string

    # Initialize variables we're filling later
    self.specification = None

    # Add kw args as options
    self._options = kwargs

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
    # Validate the parsed specs.
    from swagger_spec_validator.validator20 import validate_spec
    validate_spec(self.specification)


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
