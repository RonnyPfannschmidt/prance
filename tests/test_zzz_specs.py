# -*- coding: utf-8 -*-
"""Test OpenAPI specs examples."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance import ResolvingParser
from prance import SwaggerValidationError
from prance.util.fs import FileNotFoundError

def make_name(path, parser, backend, version, file_format, entry):
  import os.path
  basename = os.path.splitext(entry)[0]
  basename = basename.replace('-', '_')
  version = version.replace('.', '')
  backend = backend.replace('-', '_')

  name = '_'.join(['test', parser, backend, version, file_format, basename])
  return name

# Generate test cases at import.
# One case per combination of:
# - parser (base, resolving)
# - validation backend (flex, swagger-spec-validator)
# - spec version (v2.0 only so far)
# - file format
# - file
# That gives >50 test cases
import os, os.path
base = 'tests/OpenAPI-Specification/examples'

for parser in ('BaseParser', 'ResolvingParser'):
  for backend in ('flex', 'swagger-spec-validator'):
    for version in os.listdir(base):
      version_dir = os.path.join(base, version)
      for file_format in os.listdir(version_dir):
        format_dir = os.path.join(version_dir, file_format)
        if not os.path.isdir(format_dir):
          continue  # effectively skips v3.0 for now

        for entry in os.listdir(format_dir):
          full = os.path.join(format_dir, entry)
          testcase_name = None
          if os.path.isfile(full):
            testcase_name = make_name(full, parser, backend, version, file_format, entry)
          elif os.path.isdir(full):
            if parser == 'BaseParser':
              continue  # skip separate files for the BaseParser
            full = os.path.join(full, 'spec/swagger.%s' % (file_format))
            if os.path.isfile(full):
              testcase_name = make_name(full, parser, backend, version, file_format, entry)
          full = os.path.abspath(full)

          if testcase_name:
            dirname = os.path.dirname(full)
            code = """
def %s():
  import os
  cur = os.getcwd()

  os.chdir('%s')

  from prance import %s
  try:
    parser = %s('%s', backend = '%s')
  finally:
    os.chdir(cur)
""" % (testcase_name, dirname, parser, parser, full, backend)
            print(code)
            exec(code, globals(), globals())
