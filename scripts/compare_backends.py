#!/usr/bin/env python3
"""Compare resolver performance across Python, Cython, and Rust backends."""
from __future__ import annotations

import argparse
import importlib
import os
import statistics
import sys
import time
from contextlib import contextmanager
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_spec(path):
    """Load and parse an OpenAPI spec from a file path."""
    from prance.util import fs, formats

    return formats.parse_spec(fs.read_file(path), path)


def make_large_spec():
    """Build a synthetic OpenAPI spec with many shared internal refs."""
    schemas = {}
    for i in range(200):
        schemas[f"Model{i}"] = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "nested": {"$ref": "#/components/schemas/BaseModel"},
            },
        }
    schemas["BaseModel"] = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}}
        },
    }
    schemas["Tag"] = {"type": "object", "properties": {"label": {"type": "string"}}}
    paths = {
        f"/items/{idx}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/Model{idx % 200}"
                                }
                            }
                        },
                    }
                }
            }
        }
        for idx in range(100)
    }
    return {
        "openapi": "3.0.0",
        "info": {"title": "Benchmark", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": schemas},
    }


def bench(func, rounds=5, warmup=1):
    """Run *func* for *rounds* timed iterations and return mean time in ms."""
    for _ in range(warmup):
        func()
    timings = []
    for _ in range(rounds):
        start = time.perf_counter()
        func()
        timings.append(time.perf_counter() - start)
    return statistics.mean(timings) * 1000


@contextmanager
def backend_env(name):
    """Set PRANCE_BACKEND for the duration of a benchmark."""
    old = os.environ.get("PRANCE_BACKEND")
    os.environ["PRANCE_BACKEND"] = name
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("PRANCE_BACKEND", None)
        else:
            os.environ["PRANCE_BACKEND"] = old


def resolve_with_backend(backend, spec, url=None, **options):
    """Resolve references using the requested backend tier."""
    with backend_env(backend):
        resolver_mod = importlib.reload(importlib.import_module("prance.util.resolver"))
        res = resolver_mod.RefResolver(spec, url=url, copy_input=False, **options)
        res.resolve_references()


def mock_get_petstore(*args, **kwargs):
    from tests.mock_response import MockResponse, PETSTORE_YAML

    return MockResponse(text=PETSTORE_YAML)


def main():
    """Parse CLI args and print a comparison table across resolver backends."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args()

    petstore = load_spec("tests/specs/petstore.yaml")
    externals = load_spec("tests/specs/with_externals.yaml")
    large = make_large_spec()

    placeholder_url = f"file://{os.path.abspath('tests/specs/petstore.yaml')}"
    cases = [
        ("petstore", petstore, os.path.abspath("tests/specs/petstore.yaml"), {}),
        ("large_shared_refs", large, placeholder_url, {}),
        (
            "externals",
            externals,
            os.path.abspath("tests/specs/with_externals.yaml"),
            {},
        ),
    ]

    backends = ["python", "cython", "rust"]
    available = []
    for name in backends:
        with backend_env(name):
            resolver_mod = importlib.reload(
                importlib.import_module("prance.util.resolver")
            )
            if (
                name == "python"
                or resolver_mod.RefResolver is not resolver_mod._PythonRefResolver
            ):
                available.append(name)

    print(f"{'case':<20}", end="")
    for name in available:
        print(f" {name + '_ms':>12}", end="")
    print()
    print("-" * (20 + 13 * len(available)))

    for case_name, spec, url, options in cases:
        print(f"{case_name:<20}", end="")
        for backend in available:

            def run(s=spec, u=url, b=backend, o=options):
                if case_name == "externals":
                    with patch("requests.get", side_effect=mock_get_petstore):
                        resolve_with_backend(b, s, u, **o)
                else:
                    resolve_with_backend(b, s, u, **o)

            mean_ms = bench(run, rounds=args.rounds)
            print(f" {mean_ms:12.2f}", end="")
        print()


if __name__ == "__main__":
    main()
