#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dist utils for Prance.

This should work within tox, and install all required dependencies for testing.
"""

if __name__ == '__main__':
  # Get setup function
  try:
    from setuptools import setup, find_packages
  except ImportError:
    from distutils.core import setup, find_packages

  dev_require = [
    'tox>=2.7',
    'bumpversion>=0.5',
    'pytest>=3.1',
    'pytest-cov>=2.4',
    'flake8>=3.3',
    'pep8-naming>=0.4',
    'flake8-quotes>=0.9',
    'flake8_docstrings>=1.1',
    'sphinx>=1.6',
  ]

  icu_require = [
    'PyICU~=1.9',
  ]

  # Run setup
  setup(
      name = 'prance',
      version = '0.6.1',
      description = 'Swagger/OpenAPI 2.0 Parser',
      long_description = open('README.rst').read(),
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
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
      install_requires = [
        'chardet~=3.0',
        'PyYAML~=3.12',
        'swagger-spec-validator~=2.1',
        'dpath~=1.4',
        'requests~=2.17',
        'six~=1.10',
        'click~=6.7',
      ],
      extras_require = {
        'dev': dev_require,
        'icu': icu_require,
      },
      scripts = [
        'scripts/prance',
      ],
      zip_safe = True,
      test_suite = 'tests',
      setup_requires = ['pytest-runner'],
      tests_require = dev_require,
  )
