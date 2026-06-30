"""Build configuration for Cython _prance_fast and Rust _prance_rs extensions."""
import os

from Cython.Build import cythonize
from setuptools import Extension, setup
from setuptools_rust import Binding, RustExtension

os.environ.setdefault("PYO3_USE_ABI3_FORWARD_COMPATIBILITY", "1")

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
    rust_extensions=[
        RustExtension(
            "_prance_rs",
            path="rust/Cargo.toml",
            binding=Binding.PyO3,
        )
    ],
)
