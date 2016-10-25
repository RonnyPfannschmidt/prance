# -*- coding: utf-8 -*-
"""
Prance implements parsers for Swagger/OpenAPI 2.0 API specs.

See https://openapis.org/ for details on the specification.

Included is a BaseParser that reads and validates swagger specs, and a
ResolvingParser that additionally resolves any $ref references.
"""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ('util', 'cli')
__version__ = '0.2.1'


# Just re-use the error, but hide the namespace
from swagger_spec_validator.common import SwaggerValidationError  # noqa: F401

from .mixins import YAMLMixin, JSONMixin


class BaseParser(YAMLMixin, JSONMixin, object):
  """
  The BaseParser loads, parses and validates Swagger/OpenAPI 2.0 specs.

  Uses :py:class:`YAMLMixin` and :py:class:`YAMLMixin` for additional
  functionality.
  """

  def __init__(self, filename = None, spec_string = None, lazy = False):
    """
    Load, parse and validate specs.

    You can either provide a filename or a spec string, but not both.

    :param str filename: The name of the file to load.
    :param str spec_string: The specifications to parse.
    :param bool lazy: If true, do not load or parse anything. Instead wait for
      the parse function to be invoked.
    """
    assert filename or spec_string and not (filename and spec_string), \
        'You must provide either a file name to read, or a spec string to '\
        'parse, but not both!'

    # Keep the parameters around for later use
    self.filename = None
    if filename:
      from .util.fs import canonical_filename
      self.filename = canonical_filename(filename)

    self._spec_string = spec_string

    # Initialize variables we're filling later
    self.specification = None

    # Start parsing if lazy mode is not requested.
    if not lazy:
      self.parse()

  def parse(self):  # noqa: F811
    """
    When the BaseParser was lazily created, load and parse now.

    You can use this function to re-use an existing parser for parsing
    multiple files by setting its filename property and then invoking this
    function.
    """
    # If we have a file name, we need to read that in.
    if self.filename:
      from .util.fs import read_file
      self._spec_string = read_file(self.filename)

    # If we have a spec string, try to parse it.
    if self._spec_string:
      from .util.formats import parse_spec
      self.specification = parse_spec(self._spec_string, self.filename)

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

  def __init__(self, filename = None, spec_string = None, lazy = False):
    """
    See :py:class:`BaseParser`.

    Resolves JSON pointers/references (i.e. '$ref' keys) before validating the
    specs. The implication is that self.specfication is fully resolved, and
    does not contain any references.
    """
    BaseParser.__init__(
        self,
        filename = filename,
        spec_string = spec_string,
        lazy = lazy
    )

  def _validate(self):
    # We have a problem with the BaseParser's validate function: the
    # jsonschema implementation underlying it does not accept relative
    # path references, but the Swagger specs allow them:
    # http://swagger.io/specification/#referenceObject
    # We therefore use our own resolver first, and validate later.
    from .util.resolver import RefResolver
    resolver = RefResolver(self.specification, self.filename)
    resolver.resolve_references()
    self.specification = resolver.specs

    # Now validate - the BaseParser knows the specifics
    BaseParser._validate(self)
