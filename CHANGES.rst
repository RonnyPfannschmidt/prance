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
