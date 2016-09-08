# -*- coding: utf-8 -*-
"""This submodule contains file system utilities for Prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


# Re-define an error for Python 2.7
try:
  FileNotFoundError = FileNotFoundError
except NameError:
  FileNotFoundError = OSError


def abspath(filename, relative_to = None):
  """
  Return the absolute path of a file relative to a reference file.

  If no reference file is given, this function works identical to
  `canonical_filename`.

  :param str filename: The filename to make absolute.
  :param str relative_to: [optional] the reference file name.
  :return: The absolute path
  :rtype: str
  """
  # Create filename relative to the reference, if it exists.
  import os.path
  fname = filename
  if relative_to and not os.path.isabs(fname):
    if os.path.isdir(relative_to):
      fname = os.path.join(relative_to, fname)
    else:
      fname = os.path.join(os.path.dirname(relative_to), fname)

  # Make the result canonical
  return canonical_filename(fname)


def canonical_filename(filename):
  """
  Return the canonical version of a file name.

  The canonical version isdefined as the absolute path, and all file system
  links dereferenced.

  :param str filename: The filename to make canonical.
  :return: The canonical filename.
  :rtype: str
  """
  import os, os.path

  path = filename
  while True:
    path = os.path.abspath(path)
    try:
      p = os.path.dirname(path)
      path = os.path.join(p, os.readlink(path))
    except OSError:
      return path


def read_file(filename):
  """
  Read and decode a file, taking BOMs into account.

  :param str filename: The name of the file to read.
  :return: The file contents.
  :rtype: unicode string
  """
  # Read no more than 32 bytes or the file's size
  import os.path
  read_len = min(32, os.path.getsize(filename))

  # Read the first read_len bytes raw, so we can detect the encoding
  with open(filename, 'rb') as raw_handle:
    raw = raw_handle.read(read_len)

  # Detect the encoding the file specfies, if any.
  import codecs
  if raw.startswith(codecs.BOM_UTF8):
    encoding = 'utf-8-sig'
  else:
    import chardet
    res = chardet.detect(raw)
    encoding = res['encoding']

  # Finally, read the file in the detected encoding
  import io
  with io.open(filename, mode = 'r', encoding = encoding) as handle:
    return handle.read()
