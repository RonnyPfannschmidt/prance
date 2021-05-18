
v0.21.1 (2021-05-18)
====================

* quickfix for a missed rst issue in readme

v0.21.0 (2021-05-18)
====================

Features
--------

- Implement initial part of maintainer switch

  * @RonnyPfannschmidt is the new maintainer, plans to move to jazzband
  * License is now MIT after coordination with Jens
  * begin to use pre-commit + pyupgrade
  * set up for setuptools_scm as bumpversion breaks with normalized configfiles (#93)
  * github actions
  * modernize setup.py/cfg
- return to towncrier default templates


v0.20.2
=======

* #83: Properly propagate strict mode down to nested resolvers.

v0.20.1
=======

Bugfix release:

* #85: Update dependencies, in particular chardet

* Miscellaneous: #86

v0.20.0
=======

* #77: Translate local references in external files by injecting them into the main
  specification.

* #78: Fix issue in RESOLVE_INTERNAL handling

v0.19.0
=======

* #72: Fix behaviour when attempting to resolve nonexistent local references: raise
  ResolutionError instead of what the OS provides.

* #69: Improve documenation with regards to JSON Schema and OpenAPI interoperability;
  some things are just not very well defined, and we make some strict assumptions
  in prance.

* Miscellaneous: #71

v0.18.3
=======

Bugfix release:

* #67: fix syntax warning.

* #69: when resolving references, if URL parsing fails, provide context on
  which URL was being parsed in error message.

v0.18.2
=======

Bugfix release:

* #65: fix error in resolving files only with ResolvingParser.

v0.18.1
=======

Maintenance release, focusing on change requests from users.

* #23: Add support for partial resolution, i.e. resolving only internal references,
  local files, HTTP URLs, or any combination thereof.

* #36: Improve error handling by mentioning strict mode when openapi-spec-validator
  raises TypeError with very little context.

* #46: Reduce reliance on network in tests. Tests that require a network connection
  can now be skipped via "-m 'not requires_network'". Other tests have mocked
  connections.

* #55: RefResolver could set recursion limits, but the ResolvingParser did not
  pass related options on to the resolver. Fixed that. Also create & use
  reference cache in ResolvingParser.

* #60: Improve output when resolving references, by indicating the type of problem
  (missing key, index out of bounds) in the object or sequence where the error
  occurred.


v0.17.0
=======

* #51: Try a lot more bytes when detecting file encoding. The new value is meant to
  be a multiple of sector/cluster size that's still reasonable on most OSes and
  volumes.

* #49: Remove Python 2.7 from supported/built versions. The CI vendors also don't love
  3.4 any longer. Instead, we've added 3.7 and 3.8 where available.

* Miscellaneous: #53


v0.16.2
=======

* #47: Fix deprecation warning by always preferring collections.abc over collections.


v0.16.1
=======

* #44: Add changelog generation via `towncrier <https://town-crier.readthedocs.io/en/latest/>`_
