|Build Status| |PyPI|

Prances provices parsers for `Swagger/OpenAPI
2.0 <http://swagger.io/specification/>`__ API specifications in Python.
It uses
`swagger\_spec\_validator <https://github.com/Yelp/swagger_spec_validator>`__
to validate specifications, but additionally resolves `JSON
references <https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
in accordance with the Swagger spec.

Mostly the latter involves handling non-URI references; Swagger is fine
with providing relative file paths, whereas JSON references require URIs
at this point in time.

Usage
=====

Command Line Interface
----------------------

After installing prance, a CLI is available for validating (and resolving
external references in) specs:

.. code:: bash

    # Validates with resolving
    $ prance validate path/to/swagger.yml

    # Validates without resolving
    $ prance validate --no-resolve path/to/swagger.yml

    # Validates and resolves, and writes the results to output.yaml
    $ prance validate -o output.yaml path/to/swagger.yml


Code
----

Most likely you have spec file and want to parse it:

.. code:: python

    from prance import ResolvingParser
    parser = ResolvingParser('path/to/my/swagger.yaml')
    parser.specification  # contains fully resolved specs as a dict

Prance also includes a non-resolving parser that does not follow JSON
references, in case you prefer that.

.. code:: python

    from prance import BaseParser
    parser = BaseParser('path/to/my/swagger.yaml')
    parser.specification  # contains specs as a dict still containing JSON references

Largely, that's it. There is a whole slew of utility code that you may
or may not find useful, too. Look at the `full documentation
<https://jfinkhaeuser.github.io/prance/#api-modules>`__ for details.

Setup
-----

Use
`virtualenv <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`__
to create a virtual environment and change to it or not, as you see fit.

Then install the requirements:

.. code:: bash

    $ pip install -r requirements.txt

Documentation
-------------

After setup, run the following to generate documentation:

.. code:: bash

    $ python setup.py build_sphinx

Development
-----------

Test Execution
~~~~~~~~~~~~~~

Run the whole test suite:

.. code:: bash

    $ python setup.py test

Run a single test scenario:

.. code:: bash

    $ pytest tests/test_resolving_parser.py::test_basics

Run tests on multiple Python versions:

.. code:: bash

    $ tox

Run tests on Python 2.7:

.. code:: bash

    $ tox -e py27

A simple test coverage report is automatically generated.

License
=======

Licensed under MITNFA (MIT +no-false-attribs) License. See the
`LICENSE.txt <https://github.com/jfinkhaeuser/prance/blob/master/LICENSE.txt>`__ file for details.

.. |Build Status| image:: https://travis-ci.org/jfinkhaeuser/prance.svg?branch=master
   :target: https://travis-ci.org/jfinkhaeuser/prance
.. |PyPI| image:: https://img.shields.io/pypi/v/prance.svg?maxAge=2592000
   :target: https://pypi.python.org/pypi/prance/
