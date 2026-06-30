#!/usr/bin/env python3
"""Run resolver benchmarks and print a summary table."""
from __future__ import annotations

import argparse
import copy
import os
import statistics
import sys
import time
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from prance.util import fs, formats, resolver  # noqa: E402


def load_spec(path):
    """Load and parse an OpenAPI spec from a file path."""
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
        f"/items/{i}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/Model{i % 200}"
                                }
                            }
                        },
                    }
                }
            }
        }
        for i in range(100)
    }
    return {
        "openapi": "3.0.0",
        "info": {"title": "Benchmark", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": schemas},
    }


def mock_get_petstore(*args, **kwargs):
    from tests.mock_response import MockResponse, PETSTORE_YAML

    return MockResponse(text=PETSTORE_YAML)


def bench_case(name, func, rounds=5, warmup=1):
    """Run *func* for *rounds* timed iterations and return timing stats in ms."""
    for _ in range(warmup):
        func()
    timings = []
    for _ in range(rounds):
        start = time.perf_counter()
        func()
        timings.append(time.perf_counter() - start)
    return {
        "name": name,
        "mean_ms": statistics.mean(timings) * 1000,
        "min_ms": min(timings) * 1000,
        "max_ms": max(timings) * 1000,
    }


def resolve_only(specs, url, **options):
    resolver.RefResolver(copy.deepcopy(specs), url=url, **options).resolve_references()


def resolve_externals(specs, url, **options):
    with patch("requests.get", side_effect=mock_get_petstore):
        resolve_only(specs, url, **options)


def resolve_and_validate(url, **options):
    from prance import ResolvingParser

    with patch("requests.get", side_effect=mock_get_petstore):
        ResolvingParser(url, backend="openapi-spec-validator", **options)


def main():
    """Parse CLI args and print resolver benchmark results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    args = parser.parse_args()

    petstore = load_spec("tests/specs/petstore.yaml")
    externals = load_spec("tests/specs/with_externals.yaml")
    issue_78 = load_spec("tests/specs/issue_78/openapi.json")
    large = make_large_spec()
    petstore_url = os.path.abspath("tests/specs/petstore.yaml")
    externals_url = os.path.abspath("tests/specs/with_externals.yaml")
    issue_78_url = fs.abspath("openapi.json")

    common = {"copy_input": False}
    fast_shared = {**common, "fragment_copy": False}

    cases = [
        (
            "petstore",
            lambda: resolve_only(petstore, petstore_url, **common),
        ),
        (
            "large_shared_refs",
            lambda: resolve_only(large, f"file://{petstore_url}", **common),
        ),
        (
            "large_no_frag_copy",
            lambda: resolve_only(large, f"file://{petstore_url}", **fast_shared),
        ),
        (
            "issue_78_translate",
            lambda: resolve_only(
                issue_78,
                issue_78_url,
                resolve_types=resolver.RESOLVE_FILES,
                resolve_method=resolver.TRANSLATE_EXTERNAL,
                **common,
            ),
        ),
        (
            "externals",
            lambda: resolve_externals(externals, externals_url, **common),
        ),
        (
            "externals+validate",
            lambda: resolve_and_validate(externals_url, **common),
        ),
    ]

    try:
        import _prance_fast  # noqa: F401

        backend = "tier_b (_prance_fast)"
    except ImportError:
        backend = "baseline (pure Python)"

    print(f"Backend: {backend}")
    print(f"{'case':<24} {'mean_ms':>10} {'min_ms':>10} {'max_ms':>10}")
    print("-" * 58)
    for name, func in cases:
        result = bench_case(name, func, rounds=args.rounds, warmup=args.warmup)
        print(
            f"{result['name']:<24} "
            f"{result['mean_ms']:10.2f} "
            f"{result['min_ms']:10.2f} "
            f"{result['max_ms']:10.2f}"
        )


if __name__ == "__main__":
    main()
