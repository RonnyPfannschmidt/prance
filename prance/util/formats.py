# -*- coding: utf-8 -*-
"""This submodule contains file format related utility code for Prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


class ParseError(ValueError):
  pass


# Basic parse functions
def __parse_yaml(spec_str):  # noqa: N802
  import yaml, yaml.parser
  try:
    return yaml.load(spec_str)
  except yaml.parser.ParserError as err:
    raise ParseError(str(err))


def __parse_json(spec_str):  # noqa: N802
  import json
  try:
    return json.loads(spec_str)
  except ValueError as err:
    raise ParseError(str(err))


# Map file name extensions to parse functions
__EXT_TO_PARSER = {
  ('.yaml', '.yml'): __parse_yaml,
  ('.json', '.js'): __parse_json,
}

__MIME_TO_PARSER = {
  ('application/json', 'application/javascript'): __parse_json,
  ('application/x-yaml', 'text/yaml'): __parse_yaml,
}


def parse_spec(spec_str, filename = None, **kwargs):
  """
  Return a parsed dict of the given spec string.

  The default format is assumed to be YAML, but if you provide a filename,
  its extension is used to determine whether YAML or JSON should be
  parsed.

  :param str spec_str: The specifications as string.
  :param str filename: [optional] Filename to determine the format from.
  :param str content_type: [optional] Content type to determine the format
      from.
  :return: The specifications.
  :rtype: dict
  """
  # Fetch optional content type
  content_type = kwargs.get('content_type', None)

  # Select the correct parser.
  # 1) If there is neither file name nor content type, use a heuristic.
  # 2) If there is a file name but no content type, use the file extension.
  # 3) If there is no file name, but a content type, use the content type.
  # 4) If both are present, prefer the content type.
  # 5) use a heuristic either way to catch bad content types, file names,
  #    etc. The selection process above is just the most likely match!
  parser = None

  if filename and not content_type:
    from os.path import splitext
    _, ext = splitext(filename)

    for extensions in __EXT_TO_PARSER.keys():
      if ext in extensions:
        parser = __EXT_TO_PARSER[extensions]

  elif content_type:
    # Split off the first part of the content type; for us, that's enough.
    content_type = content_type.split(';')[0]

    for ctypes in __MIME_TO_PARSER.keys():
      if content_type in ctypes:
        parser = __MIME_TO_PARSER[ctypes]

  # If we have no parser yet, we need to use a heuristic. This is tricky;
  # Swagger is largely YAML-based, but JSON is used for remote references. In
  # the end, JSON is probably more likely to match.
  if not parser:
    parser = __parse_json

  # Use the heuristic. It basically says to try the parser we found now first,
  # but then use all the other parsers in sequence until we've got a result.
  parsers = list(__EXT_TO_PARSER.values())
  parsers.remove(parser)
  parsers.insert(0, parser)
  for parser in parsers:
    try:
      return parser(spec_str)
    except ParseError:
      pass

  # All failed!
  raise ParseError('Could not detect format of spec string!')
