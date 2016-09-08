# Prance
Swagger/OpenAPI 2.0 Parser for Python

[![Build Status](https://travis-ci.org/jfinkhaeuser/prance.svg?branch=master)](https://travis-ci.org/jfinkhaeuser/prance)
[![PyPI](https://img.shields.io/pypi/v/prance.svg?maxAge=2592000)](https://pypi.python.org/pypi/prance/)

Prances provices parsers for [Swagger/OpenAPI 2.0](http://swagger.io/specification/)
API specifications in Python. It uses [swagger_spec_validator](https://github.com/Yelp/swagger_spec_validator)
to validate specifications, but additionally resolves [JSON references](https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03)
in accordance with the Swagger spec.

Mostly the latter involves handling non-URI references; Swagger is fine with
providing relative file paths, whereas JSON references require URIs at this
point in time.

# Usage
## Code

Most likely you have spec file and want to parse it:

```python
from prance import ResolvingParser
parser = ResolvingParser('path/to/my/swagger.yaml')
parser.specification  # contains fully resolved specs as a dict
```

Prance also includes a non-resolving parser that does not follow JSON references,
in case you prefer that.

```python
from prance import BaseParser
parser = BaseParser('path/to/my/swagger.yaml')
parser.specification  # contains specs as a dict still containing JSON references
```

Largely, that's it. There is a whole slew of utility code that you may or may
not find useful, too. Look at the full documentation for details.

## Setup

Use [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) to
create a virtual environment and change to it or not, as you see fit.

Then install the requirements:

```bash
$ pip install -r requirements.txt
```

## Development

### Test Execution

Run the whole test suite:

```bash
$ python setup.py test
```

Run a single test scenario:

```bash
$ pytest tests/test_resolving_parser.py::test_basics
```

Run tests on multiple Python versions:

```bash
$ tox
```

Run tests on Python 2.7:

```bash
$ tox -e py27
```

A simple test coverage report is automatically generated.

# License

Licensed under MITNFA (MIT +no-false-attribs) License. See the
[LICENSE.txt](./LICENSE.txt) file for details.
