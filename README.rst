|Posix Build Status| |Windows Build Status| |Docs| |License|
|PyPI| |Python Versions| |Package Format| |Package Status| |FOSSA Status| |Liberapay|

|Logo|

Prance provides parsers for `Swagger/OpenAPI
2.0 and 3.0 <http://swagger.io/specification/>`__ API specifications in Python.
It uses `openapi\_spec\_validator <https://github.com/p1c2u/openapi-spec-validator>`__,
`swagger\_spec\_validator <https://github.com/Yelp/swagger_spec_validator>`__ or
`flex <https://github.com/pipermerriam/flex>`__
to validate specifications, but additionally resolves `JSON
references <https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
in accordance with the OpenAPI spec.

Mostly the latter involves handling non-URI references; OpenAPI is fine
with providing relative file paths, whereas JSON references require URIs
at this point in time.

Prance is `up for adoption <https://github.com/jfinkhaeuser/prance/issues/91>`__.

Usage
=====

Installation
------------

Prance is available from PyPI, and can be installed via pip:

.. code:: bash

    $ pip install prance

Note that this will install the code, but additional subpackages must be specified
to unlock various pieces of functionality. At minimum, a parsing backend must be
installed. For the CLI functionality, you need further dependencies.

The recommended installation installs the CLI, uses ICU and installs one validation
backend:

.. code:: bash

    $ pip install prance[osv,icu,cli]

Make sure you have `ICU Unicode Library <http://site.icu-project.org/home>`__ installed,
as well as Python dev library before running the commands above. If not, use the
following commands:

**Ubuntu**

.. code:: bash

    $ sudo apt-get install libicu-dev
    $ sudo apt-get install python3-dev


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
output spec. In the past, this was done via options to the ``validate`` command,
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
    $ prance convert path/to/swagger.yml path/to/openapi.yml


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
``prance.util.fs.abspath`` to convert them.

URLs can also be parsed:

.. code:: python

    parser = ResolvingParser('http://petstore.swagger.io/v2/swagger.json')

Largely, that's it. There is a whole slew of utility code that you may
or may not find useful, too. Look at the `full documentation
<https://jfinkhaeuser.github.io/prance/#api-modules>`__ for details.


Compatibility
-------------

*Python Versions*

Version 0.16.2 is the last version supporting Python 2. It was released on
Nov 12th, 2019. Python 2 reaches end of life at the end of 2019. If you wish
for updates to the Python 2 supported packages, please contact the maintainer
directly.

Until fairly recently, we also tested with `PyPy <https://www.pypy.org/>`__.
Unfortunately, Travis isn't very good at supporting this. So in the absence
of spare time, they're disabled. `Issue 50 <https://github.com/jfinkhaeuser/prance/issues/50>`__
tracks progress on that.

Similarly, but less critically, Python 3.4 is no longer receiving a lot of
love from CI vendors, so automated builds on that version are no longer
supported.

*Backends*

Different validation backends support different features.

+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| Backend                | Python Version | OpenAPI Version | Strict Mode | Notes                                                 | Available From | Link                                                                              |
+========================+================+=================+=============+=======================================================+================+===================================================================================+
| swagger-spec-validator | 2 and 3        | 2.0 only        | yes         | Slow; does not accept integer keys (see strict mode). | prance 0.1     | `swagger\_spec\_validator <https://github.com/Yelp/swagger_spec_validator>`__     |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| flex                   | 2 and 3        | 2.0 only        | n/a         | Fastest; unfortunately deprecated.                    | prance 0.8     | `flex <https://github.com/pipermerriam/flex>`__                                   |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+
| openapi-spec-validator | 2 and 3        | 2.0 and 3.0     | yes         | Slow; does not accept integer keys (see strict mode). | prance 0.11    | `openapi\_spec\_validator <https://github.com/p1c2u/openapi-spec-validator>`__    |
+------------------------+----------------+-----------------+-------------+-------------------------------------------------------+----------------+-----------------------------------------------------------------------------------+

You can select the backend in the constructor of the parser(s):

.. code:: python

    parser = ResolvingParser('http://petstore.swagger.io/v2/swagger.json', backend = 'openapi-spec-validator')


No backend is included in the dependencies; they are detected at run-time. If you install them,
they can be used:

.. code:: bash

    $ pip install openapi-spec-validator
    $ pip install prance
    $ prance validate --backend=openapi-spec-validator path/to/spec.yml

*A note on flex usage:* While flex is the fastest validation backend, unfortunately it is no longer
maintained and there are issues with its dependencies. For one thing, it depends on a version of `PyYAML`
that contains security flaws. For another, it depends explicitly on older versions of `click`.

If you use the flex subpackage, therefore, you do so at your own risk.

*Compatibility*

See `COMPATIBILITY.rst <https://github.com/jfinkhaeuser/prance/blob/master/COMPATIBILITY.rst>`__
for a list of known issues.


Partial Reference Resolution
----------------------------

It's possible to instruct the parser to only resolve some kinds of references.
This allows e.g. resolving references from external URLs, whilst keeping local
references (i.e. to local files, or file internal) intact.

.. code:: python

    from prance import ResolvingParser
    from prance.util.resolver import RESOLVE_HTTP

    parser = ResolvingParser('/path/to/spec', resolve_types = RESOLVE_HTTP)


Multiple types can be specified by OR-ing constants together:

.. code:: python

    from prance import ResolvingParser
    from prance.util.resolver import RESOLVE_HTTP, RESOLVE_FILES

    parser = ResolvingParser('/path/to/spec', resolve_types = RESOLVE_HTTP | RESOLVE_FILES)


Extensions
----------

Prance includes the ability to reference outside swagger definitions
in outside Python packages. Such a package must already be importable
(i.e. installed), and be accessible via the
`ResourceManager API <https://setuptools.readthedocs.io/en/latest/pkg_resources.html#resourcemanager-api>`__
(some more info `here <https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files>`__).

For example, you might create a package ``common_swag`` with the file
``base.yaml`` containing the definition

.. code:: yaml

    definitions:
      Severity:
        type: string
        enum:
        - INFO
        - WARN
        - ERROR
        - FATAL

In the ``setup.py`` for ``common_swag`` you would add lines such as

.. code:: python

    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        '': '*.yaml'
    }

Then, having installed ``common_swag`` into some application, you could
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

Professional support is available through `finkhaeuser consulting <https://finkhaeuser.de>`__.

License
=======

Licensed under MITNFA (MIT +no-false-attribs) License. See the
`LICENSE.txt <https://github.com/jfinkhaeuser/prance/blob/master/LICENSE.txt>`__ file for details.

"Prancing unicorn" logo image Copyright (c) Jens Finkhaeuser. All rights reserved.
Made by `Moreven B <http://morevenb.com/>`__.

.. |Posix Build Status| image:: https://travis-ci.org/jfinkhaeuser/prance.svg?branch=master
   :target: https://travis-ci.org/jfinkhaeuser/prance
.. |Windows Build Status| image:: https://ci.appveyor.com/api/projects/status/ic7lo8r95mkee7di/branch/master?svg=true
   :target: https://ci.appveyor.com/project/jfinkhaeuser/prance
.. |Docs| image:: https://img.shields.io/badge/docs-passing-brightgreen.svg
   :target: https://jfinkhaeuser.github.io/prance/
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
.. |FOSSA Status| image:: https://app.fossa.io/api/projects/git%2Bgithub.com%2Fjfinkhaeuser%2Fprance.svg?type=shield
   :target: https://app.fossa.io/projects/git%2Bgithub.com%2Fjfinkhaeuser%2Fprance?ref=badge_shield
.. |Liberapay| image:: http://img.shields.io/liberapay/receives/jfinkhaeuser.svg?logo=liberapay
   :target: https://liberapay.com/jfinkhaeuser/donate
.. |Logo| image:: https://raw.githubusercontent.com/jfinkhaeuser/prance/master/docs/images/prance_logo_256.png

