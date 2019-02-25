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
    'tox>=3.7',
    'bumpversion>=0.5',
    'pytest>=4.2',
    'pytest-cov>=2.6',
    'flake8>=3.7',
    'pep8-naming>=0.8',
    'flake8-quotes>=1.0',
    'flake8_docstrings>=1.3',
    'sphinx>=1.8',
  ]

  icu_require = [
    'PyICU~=2.2',
  ]

  ssv_require = [
    'swagger-spec-validator~=2.4',
  ]

  osv_require = [
    'openapi-spec-validator>0.2,>=0.2.1',
  ]

  flex_require = [
    'flex~=6.13',
  ]

  cli_require = [
    'click~=7.0',
  ]

  # Run setup
  setup(
      name = 'prance',
      version = '0.14.1',
      description = 'Resolving Swagger/OpenAPI 2.0 and 3.0.0 Parser',
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
        'Programming Language :: Python :: 3.7',
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
        'PyYAML>=5,>=5.1b1',
        'requests~=2.21',
        'six~=1.12',
        'semver~=2.8',
      ],
      extras_require = {
        'dev': dev_require,
        'icu': icu_require,
        'ssv': ssv_require,
        'osv': osv_require,
        'flex': flex_require,
        'cli': cli_require,
      },
      entry_points={
          'console_scripts': [
              'prance=prance.cli:cli [cli]',
           ],
      },
      zip_safe = True,
      test_suite = 'tests',
      setup_requires = ['pytest-runner'],
      tests_require = dev_require,
  )
