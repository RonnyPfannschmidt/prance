"""Build configuration for the Rust _prance_rs extension."""
import os

from setuptools import setup
from setuptools_rust import Binding
from setuptools_rust import RustExtension

os.environ.setdefault("PYO3_USE_ABI3_FORWARD_COMPATIBILITY", "1")

setup(
    rust_extensions=[
        RustExtension(
            "_prance_rs",
            path="rust/Cargo.toml",
            binding=Binding.PyO3,
        )
    ],
)
