#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dist utils for Prance.

This should work within tox, and install all required dependencies for testing
from `requirements_dev.txt`.
"""


def read_requirements(filename):
  """Read the given file for requirements."""
  from pip.req import parse_requirements

  return [
    str(item.req) for item in parse_requirements(filename, session = False)
  ]


if __name__ == '__main__':
  # Get setup function
  try:
    from setuptools import setup, find_packages
  except ImportError:
    from distutils.core import setup, find_packages

  # Read requirements files
  requirements = read_requirements('requirements.txt')
  test_requirements = read_requirements('requirements_dev.txt')

  # Run setup
  setup(
      name = 'prance',
      version = '0.1.0',
      description = 'Swagger/OpenAPI 2.0 Parser',
      long_description = """\
Prances provices parsers for Swagger/OpenAPI 2.0 API specifications in Python.
It uses `swagger_spec_validator` to validate specifications, but additionally
resolves JSON references in accordance with the Swagger spec.""",
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords = 'swagger openapi parsing',
      author = 'Jens Finkhaeuser',
      author_email = 'jens@finkhaeuser.de',
      url = 'https://github.com/jfinkhaeuser/prance',
      license = 'MITNFA',
      packages = find_packages(exclude = ['ez_setup', 'examples', 'tests']),
      include_package_data = True,
      install_requires = requirements,
      zip_safe = True,
      test_suite = 'tests',
      setup_requires = ['pytest-runner'],
      tests_require = test_requirements,
  )
