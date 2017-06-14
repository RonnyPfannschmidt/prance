# -*- coding: utf-8 -*-
"""This submodule contains file format related utility code for Prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


class ParseError(ValueError):
  pass  # pragma: no cover


def __format_preferences(filename, content_type):  # noqa: N802
  """
  Detect the format based on file name and content type.

  Each parameter may be None, so a heuristic can be used in the end.

  :return: A tuple of format strings, in the optimal order to try.
  :rtype: tuple
  """
  # Select the correct format.
  # 1) If there is neither file name nor content type, use a heuristic.
  # 2) If there is a file name but no content type, use the file extension.
  # 3) If there is no file name, but a content type, use the content type.
  # 4) If both are present, prefer the content type.
  # 5) use a heuristic either way to catch bad content types, file names,
  #    etc. The selection process above is just the most likely match!
  best = None

  if filename and not content_type:
    from os.path import splitext
    _, ext = splitext(filename)

    for extensions in __EXT_TO_FORMAT.keys():
      if ext in extensions:
        best = __EXT_TO_FORMAT[extensions]

  elif content_type:
    # Split off the first part of the content type; for us, that's enough.
    content_type = content_type.split(';')[0]

    for ctypes in __MIME_TO_FORMAT.keys():
      if content_type in ctypes:
        best = __MIME_TO_FORMAT[ctypes]

  # If we have no best format yet, we need to use a heuristic. This is tricky;
  # Swagger is largely YAML-based, but JSON is used for remote references. In
  # the end, JSON is probably more likely to match.
  if not best:
    best = 'JSON'

  # Now assemble an ordered list of formats to return, with the best format
  # first.
  formats = list(__EXT_TO_FORMAT.values())
  formats.remove(best)
  formats.insert(0, best)

  return tuple(formats)


# Basic parse functions
def __parse_yaml(spec_str):  # noqa: N802
  import yaml, yaml.parser, six
  try:
    return yaml.safe_load(six.text_type(spec_str))
  except yaml.parser.ParserError as err:
    raise ParseError(str(err))


def __parse_json(spec_str):  # noqa: N802
  import json, six
  try:
    return json.loads(six.text_type(spec_str))
  except ValueError as err:
    raise ParseError(str(err))


# Basic serialization functions
def __serialize_yaml(specs):  # noqa: N802
  # I don't know what the PyYAML authors smoked, but in order for it to parse
  # unicode specs and not mess encoding up, you need to allow_unicode and
  # explicitly set the encoding to None.
  import yaml
  utf = yaml.dump(specs,
                  allow_unicode = True,
                  encoding = None,
                  default_flow_style = False)

  import six
  return six.text_type(utf)


def __serialize_json(specs):  # noqa: N802
  # The default encoding is utf-8, no need to specify it. But we need to switch
  # off ensure_ascii, otherwise we do not get a unicode string back.
  import json
  utf = json.dumps(specs, ensure_ascii = False, indent = 2)

  import six
  return six.text_type(utf)


# Map file name extensions to parse/serialize functions
__EXT_TO_FORMAT = {
  ('.yaml', '.yml'): 'YAML',
  ('.json', '.js'): 'JSON',
}

__MIME_TO_FORMAT = {
  ('application/json', 'application/javascript'): 'JSON',
  ('application/x-yaml', 'text/yaml'): 'YAML',
}


__FORMAT_TO_PARSER = {
  'YAML': __parse_yaml,
  'JSON': __parse_json,
}

__FORMAT_TO_SERIALIZER = {
  'YAML': __serialize_yaml,
  'JSON': __serialize_json,
}


def parse_spec(spec_str, filename = None, **kwargs):
  """
  Return a parsed dict of the given spec string.

  The default format is assumed to be JSON, but if you provide a filename,
  its extension is used to determine whether YAML or JSON should be
  parsed.

  :param str spec_str: The specifications as string.
  :param str filename: [optional] Filename to determine the format from.
  :param str content_type: [optional] Content type to determine the format
      from.
  :return: The specifications.
  :rtype: dict
  """
  # Fetch optional content type & determine formats
  content_type = kwargs.get('content_type', None)
  formats = __format_preferences(filename, content_type)

  # Try parsing each format in order
  for f in formats:
    parser = __FORMAT_TO_PARSER[f]
    try:
      return parser(spec_str)
    except ParseError:
      pass

  # All failed!
  raise ParseError('Could not detect format of spec string!')


def serialize_spec(specs, filename = None, **kwargs):
  """
  Return a serialized version of the given spec.

  The default format is assumed to be JSON, but if you provide a filename,
  its extension is used to determine whether YAML or JSON should be
  parsed.

  :param str specs: The specifications as dict.
  :param str filename: [optional] Filename to determine the format from.
  :param str content_type: [optional] Content type to determine the format
      from.
  :return: The serialized specifications.
  :rtype: str
  """
  # Fetch optional content type & determine formats
  content_type = kwargs.get('content_type', None)
  formats = __format_preferences(filename, content_type)

  # Instead of trying to parse various formats, we only serialize to the first
  # one in the list - nothing else makes much sense.
  serializer = __FORMAT_TO_SERIALIZER[formats[0]]
  return serializer(specs)
