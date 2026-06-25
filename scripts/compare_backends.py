#!/usr/bin/env python3
"""Compare resolver performance across the pure-Python and Tier B backends."""

from __future__ import annotations

import argparse
import importlib
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_spec(path):
    from prance.util import fs, formats

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
        f"/items/{idx}": {
            "get": {
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/Model{idx % 200}"}
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
    for _ in range(warmup):
        func()
    timings = []
    for _ in range(rounds):
        start = time.perf_counter()
        func()
        timings.append(time.perf_counter() - start)
    return statistics.mean(timings) * 1000


def resolve_python(spec, url=None):
    import prance.util.iterators as iterators
    import prance.util.path as path_mod
    import prance.util.resolver as resolver_mod

    iterators._fast_reference_iterator = None
    path_mod._fast_path_get = None
    path_mod._fast_path_set = None
    resolver_mod._fast_deepcopy_json = None
    res = resolver_mod.RefResolver(spec, url=url)
    res.resolve_references()


def resolve_tier_b(spec, url=None):
    res_mod = importlib.reload(importlib.import_module("prance.util.resolver"))
    res = res_mod.RefResolver(spec, url=url)
    res.resolve_references()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args()

    petstore = load_spec("tests/specs/petstore.yaml")
    externals = load_spec("tests/specs/with_externals.yaml")
    large = make_large_spec()
    externals_url = os.path.abspath("tests/specs/with_externals.yaml")

    placeholder_url = f"file://{os.path.abspath('tests/specs/petstore.yaml')}"
    cases = [
        ("petstore", petstore, os.path.abspath("tests/specs/petstore.yaml")),
        ("large_shared_refs", large, placeholder_url),
    ]

    backends = [
        ("python", resolve_python),
        ("tier_b", resolve_tier_b),
    ]

    backend_cases = {
        "python": cases,
        "tier_b": cases,
    }

    print(f"{'case':<20}", end="")
    for name, _ in backends:
        print(f" {name + '_ms':>12}", end="")
    print()
    print("-" * (20 + 13 * len(backends)))

    for case_name, spec, url in cases:
        print(f"{case_name:<20}", end="")
        for backend_name, resolver in backends:
            if case_name not in {c[0] for c in backend_cases[backend_name]}:
                print(f" {'n/a':>12}", end="")
                continue
            mean_ms = bench(
                lambda s=spec, u=url, r=resolver: r(s, u),
                rounds=args.rounds,
            )
            print(f" {mean_ms:12.2f}", end="")
        print()


if __name__ == "__main__":
    main()
