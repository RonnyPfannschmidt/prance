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
    'tox>=2.9',
    'bumpversion>=0.5',
    'pytest>=3.4',
    'pytest-cov>=2.5',
    'flake8>=3.5',
    'pep8-naming>=0.5',
    'flake8-quotes>=0.14',
    'flake8_docstrings>=1.3',
    'sphinx>=1.7',
  ]

  icu_require = [
    'PyICU~=1.9',
  ]

  ssv_require = [
    'swagger-spec-validator~=2.1',
  ]

  osv_require = [
    'openapi-spec-validator~=0.2',
  ]

  # Run setup
  setup(
      name = 'prance',
      version = '0.12.1',
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
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
        'flex~=6.12',
        'requests~=2.18',
        'six~=1.11',
        'click~=6.7',
        'semver~=2.8',
      ],
      extras_require = {
        'dev': dev_require,
        'icu': icu_require,
        'ssv': ssv_require,
        'osv': osv_require,
      },
      entry_points={
          'console_scripts': [
              'prance=prance.cli:cli',
           ],
      },
      zip_safe = True,
      test_suite = 'tests',
      setup_requires = ['pytest-runner'],
      tests_require = dev_require,
  )
