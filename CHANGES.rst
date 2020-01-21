v0.18.1
-------

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
-------
* #51: Try a lot more bytes when detecting file encoding. The new value is meant to
  be a multiple of sector/cluster size that's still reasonable on most OSes and
  volumes.

* #49: Remove Python 2.7 from supported/built versions. The CI vendors also don't love
  3.4 any longer. Instead, we've added 3.7 and 3.8 where available.

* Miscellaneous: #53


v0.16.2
-------
* #47: Fix deprecation warning by always preferring collections.abc over collections.


v0.16.1
-------
* #44: Add changelog generation via `towncrier <https://town-crier.readthedocs.io/en/latest/>`_
