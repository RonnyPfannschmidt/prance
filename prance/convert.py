# -*- coding: utf-8 -*-
"""
Functionality for converting from Swagger/OpenAPI 2.0 to OpenAPI 3.0.0.

The functions use https://mermade.org.uk/ APIs for conversion.
"""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


class ConversionError(ValueError):
  pass  # pragma: nocover


def convert_str(spec_str, filename = None, **kwargs):
  """
  Convert the serialized spec.

  We parse the spec first to ensure there is no parse error, then
  send it off to the API for conversion.

  :param str spec_str: The specifications as string.
  :param str filename: [optional] Filename to determine the format from.
  :param str content_type: [optional] Content type to determine the format
      from.
  :return: The converted spec and content type.
  :rtype: tuple
  :raises ParseError: when parsing fails.
  :raises ConversionError: when conversion fails.
  """
  # Parse, but discard the results. The function raises parse error.
  from .util.formats import parse_spec_details
  spec, content_type, extension = parse_spec_details(spec_str, filename,
      **kwargs)

  # Ok, parsing went fine, so let's convert.
  data = {
    'source': spec_str,
  }
  if filename is not None:
    data['filename'] = filename
  else:
    data['filename'] = 'openapi%s' % (extension,)

  headers = {
    'accept': '%s; charset=utf-8' % (content_type,)
  }

  # Convert via API
  import requests
  r = requests.post('https://mermade.org.uk/api/v1/convert', data = data,
      headers = headers)
  if not r.ok:  # pragma: nocover
    raise ConversionError('Could not convert spec: %d %s' % (
        r.status_code, r.reason))

  return r.text, '%s; %s' % (r.headers['content-type'], r.apparent_encoding)


def convert_url(url, cache = {}):
  """
  Fetch a URL, and try to convert it to OpenAPI 3.x.y.

  :param str url: The URL to fetch.
  :return: The converted spec and content type.
  :rtype: tuple
  :raises ParseError: when parsing fails.
  :raises ConversionError: when conversion fails.
  """
  # Fetch URL contents
  from .util.url import fetch_url_text
  content, content_type = fetch_url_text(url, cache)

  # Try converting
  return convert_str(content, None, content_type = content_type)
