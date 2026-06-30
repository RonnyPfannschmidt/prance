"""Build configuration for the Cython _prance_fast extension."""

from setuptools import Extension, setup
from Cython.Build import cythonize

CYTHON_DIRECTIVES = {
    "language_level": "3",
    "boundscheck": False,
    "wraparound": False,
}

setup(
    ext_modules=cythonize(
        [Extension("_prance_fast", ["cython/prance_fast.pyx"])],
        compiler_directives=CYTHON_DIRECTIVES,
    ),
)
