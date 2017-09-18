|Build Status| |Docs| |License|
|PyPI| |Python Versions| |Package Format| |Package Status|

Prance provides parsers for `Swagger/OpenAPI
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

    # Fetch URL, validate and resolve.
    $ prance validate http://petstore.swagger.io/v2/swagger.json
    Processing "http://petstore.swagger.io/v2/swagger.json"...
     -> Resolving external references.
    Validates OK as Swagger/OpenAPI 2.0!



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

On Windows, the code reacts correctly if you pass posix-like paths
(``/c:/swagger``) or if the path is relative.  If you pass absolute
windows path (like ``c:\swagger.yaml``), you can use
`prance.util.fs.abspath` to convert them.

URLs can also be parsed:

.. code:: python

    parser = ResolvingParser('http://petstore.swagger.io/v2/swagger.json')

Largely, that's it. There is a whole slew of utility code that you may
or may not find useful, too. Look at the `full documentation
<https://jfinkhaeuser.github.io/prance/#api-modules>`__ for details.

Contributing
============

See `CONTRIBUTING.md <https://github.com/jfinkhaeuser/prance/blob/master/CONTRIBUTING.md>`__ for details.

License
=======

Licensed under MITNFA (MIT +no-false-attribs) License. See the
`LICENSE.txt <https://github.com/jfinkhaeuser/prance/blob/master/LICENSE.txt>`__ file for details.

.. |Build Status| image:: https://travis-ci.org/jfinkhaeuser/prance.svg?branch=master
   :target: https://travis-ci.org/jfinkhaeuser/prance
.. |Docs| image:: https://readthedocs.org/projects/prance/badge/?version=latest
   :target: http://prance.readthedocs.io/en/latest/
.. |License| image:: https://img.shields.io/pypi/l/prance.svg
   :target: https://pypi.python.org/pypi/prance/
.. |PyPI| image:: https://img.shields.io/pypi/v/prance.svg
   :target: https://pypi.python.org/pypi/prance/
.. |Package Format| image:: https://img.shields.io/pypi/format/prance.svg
   :target: https://pypi.python.org/pypi/prance/
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/prance.svg
   :target: https://pypi.python.org/pypi/prance/
.. |Package Status| image:: https://img.shields.io/pypi/status/prance.svg
   :target: https://pypi.python.org/pypi/prance/
