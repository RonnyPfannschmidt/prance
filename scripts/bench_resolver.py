#!/usr/bin/env python3
"""Run resolver benchmarks and print a summary table."""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from prance.util import fs, formats, resolver  # noqa: E402


def load_spec(path):
    return formats.parse_spec(fs.read_file(path), path)


def make_large_spec():
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
        "properties": {"tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}}},
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
                                "schema": {"$ref": f"#/components/schemas/Model{i % 200}"}
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


def bench_case(name, func, rounds=5, warmup=1):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    args = parser.parse_args()

    petstore = load_spec("tests/specs/petstore.yaml")
    externals = load_spec("tests/specs/with_externals.yaml")
    large = make_large_spec()
    petstore_url = os.path.abspath("tests/specs/petstore.yaml")
    externals_url = os.path.abspath("tests/specs/with_externals.yaml")

    cases = [
        (
            "petstore",
            lambda: resolver.RefResolver(
                petstore, url=petstore_url
            ).resolve_references(),
        ),
        (
            "large_shared_refs",
            lambda: resolver.RefResolver(
                large, url=f"file://{petstore_url}"
            ).resolve_references(),
        ),
    ]

    try:
        import _prance_fast  # noqa: F401

        backend = "tier_b (_prance_fast)"
    except ImportError:
        backend = "baseline (pure Python)"

    print(f"Backend: {backend}")
    print(f"{'case':<22} {'mean_ms':>10} {'min_ms':>10} {'max_ms':>10}")
    print("-" * 56)
    for name, func in cases:
        result = bench_case(name, func, rounds=args.rounds, warmup=args.warmup)
        print(
            f"{result['name']:<22} "
            f"{result['mean_ms']:10.2f} "
            f"{result['min_ms']:10.2f} "
            f"{result['max_ms']:10.2f}"
        )


if __name__ == "__main__":
    main()
