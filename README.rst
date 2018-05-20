|Posix Build Status| |Windows Build Status| |Docs| |License|
|PyPI| |Python Versions| |Package Format| |Package Status|

Prance provides parsers for `Swagger/OpenAPI
2.0 and 3.0 <http://swagger.io/specification/>`__ API specifications in Python.
It uses `flex <https://github.com/pipermerriam/flex>`__,
`swagger\_spec\_validator <https://github.com/Yelp/swagger_spec_validator>`__
or `openapi\_spec\_validator <https://github.com/p1c2u/openapi-spec-validator>`__
to validate specifications, but additionally resolves `JSON
references <https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
in accordance with the OpenAPI spec.

Mostly the latter involves handling non-URI references; OpenAPI is fine
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

    # Fetch URL, validate and resolve.
    $ prance validate http://petstore.swagger.io/v2/swagger.json
    Processing "http://petstore.swagger.io/v2/swagger.json"...
     -> Resolving external references.
    Validates OK as Swagger/OpenAPI 2.0!

Validation is not the only feature of prance. One of the side effects of
resolving is that from a spec with references, one can create a fully resolved
output spec. In the past, this was done via options to the `validate` command,
but now there's a specific command just for this purpose:

.. code:: bash

    # Compile spec
    $ prance compile path/to/input.yml path/to/output.yml


Lastly, with the arrival of OpenAPI 3.0.0, it becomes useful for tooling to
convert older specs to the new standard. Instead of re-inventing the wheel,
prance just provides a CLI command for passing specs to the web API of
`swagger2openapi <https://github.com/Mermade/swagger2openapi>`__ - a working
internet connection is therefore required for this command:

.. code:: bash

    # Convert spec
    $ prance compile path/to/swagger.yml path/to/openapi.yml


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


Compatibility
-------------

Different validation backends support different features.

+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| Backend                | Python Version | OpenAPI Version | Strict Mode | Notes                                                 | Available From | Link                                                                              |
+========================+================+=================+=============+=======================================================+================+===================================================================================+
| swagger-spec-validator | 2 and 3        | 2.0 only        | yes         | Slow; does not accept integer keys (see strict mode). | prance 0.1     | `swagger\_spec\_validator <https://github.com/Yelp/swagger_spec_validator>`__     |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| flex                   | 2 and 3        | 2.0 only        | n/a         | Fastest; the default, and always required.            | prance 0.8     | `flex <https://github.com/pipermerriam/flex>`__                                   |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| openapi-spec-validator | 3 only         | 2.0 and 3.0     | yes         | Slow; does not accept integer keys (see strict mode). | prance 0.11    | `openapi\_spec\_validator <https://github.com/p1c2u/openapi-spec-validator>`__    |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+

You can select the backend in the constructor of the parser(s):

.. code:: python

    parser = ResolvingParser('http://petstore.swagger.io/v2/swagger.json', backend = 'openapi-spec-validator')


Only the default backend is included in the dependencies; others are detected at run-time. If you
install them, they can be used:

.. code:: bash

    $ pip install openapi-spec-validator
    $ pip install prance
    $ prance validate --backend=openapi-spec-validator path/to/spec.yml


*A note on strict mode:* The OpenAPI specs are a little ambiguous. On the one hand, they use JSON
references and JSON schema a fair bit. But on the other hand, what they specify as examples does
not always match the JSON specs.

Most notably, JSON only accepts string keys in objects. However, some keys in the specs tend to be
integer values, most notably the status codes for responses. Strict mode rejects non-string keys;
the default lenient mode accepts them.

Since the `flex` validator is not based on JSON, it does not have this issue. The `strict` option
therefore does not apply here.


Extensions
----------

Prance includes the ability to reference outside swagger definitions
in outside Python packages. Such a package must already be importable
(i.e. installed), and be accessible via the
`ResourceManager API <https://setuptools.readthedocs.io/en/latest/pkg_resources.html#resourcemanager-api>`__
(some more info `here <https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files>`__).

For example, you might create a package `common_swag` with the file
`base.yaml` containing the definition

.. code:: yaml

    definitions:
      Severity:
        type: string
        enum:
        - INFO
        - WARN
        - ERROR
        - FATAL

In the `setup.py` for `common_swag` you would add lines such as

.. code:: python

    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        '': '*.yaml'
    }

Then, having installed `common_swag` into some application, you could
now write

.. code:: yaml

    definitions:
      Message:
        type: object
        properties:
          severity:
            $ref: 'python://common_swag/base.yaml#/definitions/Severity'
          code:
            type: string
          summary:
            type: string
          description:
            type: string
        required:
        - severity
        - summary

Contributing
============

See `CONTRIBUTING.md <https://github.com/jfinkhaeuser/prance/blob/master/CONTRIBUTING.md>`__ for details.

License
=======

Licensed under MITNFA (MIT +no-false-attribs) License. See the
`LICENSE.txt <https://github.com/jfinkhaeuser/prance/blob/master/LICENSE.txt>`__ file for details.

.. |Posix Build Status| image:: https://travis-ci.org/jfinkhaeuser/prance.svg?branch=master
   :target: https://travis-ci.org/jfinkhaeuser/prance
.. |Windows Build Status| image:: https://ci.appveyor.com/api/projects/status/ic7lo8r95mkee7di/branch/master?svg=true
   :target: https://ci.appveyor.com/project/jfinkhaeuser/prance
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
