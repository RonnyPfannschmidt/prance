# -*- coding: utf-8 -*-
"""This submodule contains code for fetching/parsing URLs."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


import six.moves.urllib.parse as parse


class ResolutionError(LookupError):
  pass


def urlresource(url):
  """
  Return the resource part of a parsed URL.

  The resource part is defined as the part without query, parameters or
  fragment. Just the scheme, netloc and path remains.

  :param tuple url: A parsed URL
  :return: The resource part of the URL
  :rtype: str
  """
  res_list = list(url)[0:3] + [None, None, None]
  return parse.ParseResult(*res_list).geturl()


def absurl(url, relative_to = None):
  """
  Turn relative file URLs into absolute file URLs.

  This is necessary, because while JSON pointers do not allow relative file
  URLs, Swagger/OpenAPI explicitly does. We need to make relative paths
  absolute before passing them off to jsonschema for verification.

  Non-file URLs are left untouched. URLs without scheme are assumed to be file
  URLs.

  :param str/tuple url: The input URL.
  :param str/tuple relative_to: [optional] The URL to which the input URL is
      relative.
  :return: The output URL, parsed into components.
  :rtype: tuple
  """
  # Parse input URL, if necessary
  parsed = url
  if not isinstance(parsed, tuple):
    parsed = parse.urlparse(url)

  # Any non-file scheme we just return immediately.
  if parsed.scheme not in (None, '', 'file'):
    return parsed

  # Parse up the reference URL
  reference = relative_to
  if reference and not isinstance(reference, tuple):
    reference = parse.urlparse(reference)

  # If the input URL has no path, we assume only its fragment matters.
  # That is, we'll have to set the fragment of the reference URL to that
  # of the input URL, and return the result.
  import os.path
  result_list = None
  if not parsed.path:
    if not reference or not reference.path:
      raise ResolutionError('Cannot build an absolute file URL from a fragment'
          ' without a reference with path!')
    result_list = list(reference)
    result_list[5] = parsed.fragment
  elif os.path.isabs(parsed.path):
    # We have an absolute path, so we can ignore the reference entirely!
    result_list = list(parsed)
    result_list[0] = 'file'  # in case it was empty
  else:
    # If we have a relative path, we require a reference.
    if not reference:
      raise ResolutionError('Cannot build an absolute file URL from a relative'
          ' path without a reference!')
    if reference.scheme not in (None, '', 'file'):
      raise ResolutionError('Cannot build an absolute file URL with a non-file'
          ' reference!')

    result_list = list(parsed)
    result_list[0] = 'file'  # in case it was empty
    from .fs import abspath
    result_list[2] = abspath(parsed.path, reference.path)

  # Reassemble the result and return it
  result = parse.ParseResult(*result_list)
  return result


def fetch_url(url):
  """
  Fetch the URL and parse the contents.

  If the URL is a file URL, the format used for parsing depends on the file
  extension. Otherwise, YAML is assumed.

  :param tuple url: The url, parsed as returned by `absurl` above.
  :return: The parsed file.
  :rtype: dict
  """
  # Fetch contents according to scheme. We assume requests can handle all the
  # non-file schemes, or throw otherwise.
  content = None
  content_type = None
  if url.scheme in (None, '', 'file'):
    from .fs import read_file
    content = read_file(url.path)
  else:
    import requests
    response = requests.get(url.geturl())
    content_type = response.headers['content-type']
    content = response.text

  # Now return the parsed results
  from .formats import parse_spec
  return parse_spec(content, url.path, content_type = content_type)
