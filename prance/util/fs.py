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


def detect_encoding(filename):
  """
  Detect the named file's character encoding.

  :param str filename: The name of the file to detect the encoding of.
  :return: The file encoding.
  :rtype: str
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

  return encoding


def read_file(filename, encoding = None):
  """
  Read and decode a file, taking BOMs into account.

  If no encoding is given, `detect_encoding` is used to detect an encoding.
  However, if `detect_encoding` returns ASCII, `read_file` instead switches to
  UTF-8. That's a superset of ASCII, so should be a safer default in modern
  times.

  :param str filename: The name of the file to read.
  :param str encoding: The encoding to use. If not given, detect_encoding is
      used to determine the encoding.
  :return: The file contents.
  :rtype: unicode string
  """

  if not encoding:
    # Detect encoding
    encoding = detect_encoding(filename)

    # Instead of ascii (if that was detected), default to utf-8
    if encoding == 'ascii':
      encoding = 'utf-8'

  # Finally, read the file in the detected encoding
  import io
  with io.open(filename, mode = 'r', encoding = encoding) as handle:
    return handle.read()
