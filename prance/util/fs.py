# -*- coding: utf-8 -*-
"""This submodule contains file system utilities for Prance."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


# Re-define an error for Python 2.7
import six
if six.PY2:
  FileNotFoundError = OSError  # pragma: no cover
else:
  FileNotFoundError = FileNotFoundError  # pragma: no cover


def from_posix(fname):
  """
  Convert a path from posix-like, to the platform format.

  :param str fname: The filename in posix-like format.
  :return: The filename in the format of the platform.
  :rtype: str
  """
  import sys
  if sys.platform == 'win32':  # pragma: nocover
    if fname[0] == '/':
      fname = fname[1:]
    fname = fname.replace('/', '\\')
  return fname


def to_posix(fname):
  """
  Convert a path to posix-like format.

  :param str fname: The filename to convert to posix format.
  :return: The filename in posix-like format.
  :rtype: str
  """
  import sys
  if sys.platform == 'win32':  # pragma: nocover
    import os.path
    if os.path.isabs(fname):
      fname = '/' + fname
    fname = fname.replace('\\', '/')
  return fname


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
  fname = from_posix(filename)
  if relative_to and not os.path.isabs(fname):
    relative_to = from_posix(relative_to)
    if os.path.isdir(relative_to):
      fname = os.path.join(relative_to, fname)
    else:
      fname = os.path.join(os.path.dirname(relative_to), fname)

  # Make the result canonical
  fname = canonical_filename(fname)
  return to_posix(fname)


def canonical_filename(filename):
  """
  Return the canonical version of a file name.

  The canonical version is defined as the absolute path, and all file system
  links dereferenced.

  :param str filename: The filename to make canonical.
  :return: The canonical filename.
  :rtype: str
  """
  import os, os.path

  path = from_posix(filename)
  while True:
    path = os.path.abspath(path)
    try:
      p = os.path.dirname(path)
      # os.readlink doesn't exist in windows python2.7
      try:
        deref_path = os.readlink(path)
      except AttributeError:  # pragma: no cover
        return path
      path = os.path.join(p, deref_path)
    except OSError:
      return path


def detect_encoding(filename, default_to_utf8 = True, **kwargs):
  """
  Detect the named file's character encoding.

  If the first parts of the file appear to be ASCII, this function returns
  'UTF-8', as that's a safe superset of ASCII. This can be switched off by
  changing the `default_to_utf8` parameter.

  :param str filename: The name of the file to detect the encoding of.
  :param bool default_to_utf8: Defaults to True. Set to False to disable
      treating ASCII files as UTF-8.
  :param bool read_all: Keyword argument; if True, reads the entire file
      for encoding detection.
  :return: The file encoding.
  :rtype: str
  """
  # Read no more than 32 bytes or the file's size
  import os.path
  filename = from_posix(filename)
  file_len = os.path.getsize(filename)
  read_len = min(32, file_len)

  # ... unless we're supposed to!
  if kwargs.get('read_all', False):
    read_len = file_len

  # Read the first read_len bytes raw, so we can detect the encoding
  with open(filename, 'rb') as raw_handle:
    raw = raw_handle.read(read_len)

  # Detect the encoding the file specfies, if any.
  import codecs
  if raw.startswith(codecs.BOM_UTF8):
    encoding = 'utf-8-sig'
  else:
    # Detect encoding using the best detector available
    try:
      # First try ICU. ICU will report ASCII in the first 32 Bytes as
      # ISO-8859-1, which isn't exactly wrong, but maybe optimistic.
      import icu
      encoding = icu.CharsetDetector(raw).detect().getName().lower()
    except ImportError:
      # If that doesn't work, try chardet - it's not got native components,
      # which is a bonus in some environments, but it's not as precise.
      import chardet
      encoding = chardet.detect(raw)['encoding'].lower()

      # Chardet is more brutal in that it reports ASCII if none of the first
      # Bytes contain high bits. To emulate ICU, we just bump up the detected
      # encoding.
      if encoding == 'ascii':
        encoding = 'iso-8859-1'

    # Return UTF-8 if that is what we're supposed to default to
    if default_to_utf8 and encoding in ('ascii', 'iso-8859-1'):
      encoding = 'utf-8'

  return encoding


def read_file(filename, encoding = None):
  """
  Read and decode a file, taking BOMs into account.

  :param str filename: The name of the file to read.
  :param str encoding: The encoding to use. If not given, detect_encoding is
      used to determine the encoding.
  :return: The file contents.
  :rtype: unicode string
  """
  filename = from_posix(filename)
  if not encoding:
    # Detect encoding
    encoding = detect_encoding(filename)

  # Finally, read the file in the detected encoding
  import io
  with io.open(filename, mode = 'r', encoding = encoding) as handle:
    return handle.read()


def write_file(filename, contents, encoding = None):
  """
  Write a file with the given encoding.

  The default encoding is 'utf-8'. It's recommended not to change that for
  JSON or YAML output.

  :param str filename: The name of the file to read.
  :param str contents: The file contents to write.
  :param str encoding: The encoding to use. If not given, detect_encoding is
      used to determine the encoding.
  """
  if not encoding:
    encoding = 'utf-8'

  import io
  fname = from_posix(filename)
  with io.open(fname, mode = 'w', encoding = encoding) as handle:
    handle.write(contents)
