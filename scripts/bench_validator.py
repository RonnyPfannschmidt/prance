#!/usr/bin/env python3
"""Compare OpenAPI validation performance across Python and Rust backends."""
from __future__ import annotations

import argparse
import importlib
import os
import statistics
import sys
import time
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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
    """Set ``PRANCE_BACKEND`` for the duration of a benchmark."""
    old = os.environ.get("PRANCE_BACKEND")
    os.environ["PRANCE_BACKEND"] = name
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("PRANCE_BACKEND", None)
        else:
            os.environ["PRANCE_BACKEND"] = old


def validate_with_backend(backend, path):
    """Validate *path* using :class:`prance.BaseParser` with the given backend tier."""
    with backend_env(backend):
        import prance

        prance.BaseParser(path, backend="openapi-spec-validator")


def validate_rust_direct(path):
    """Validate *path* via the Rust ``parse_and_validate_spec`` entry point."""
    from prance.util.resolver import rust_parse_and_validate_spec

    rust_parse_and_validate_spec(url=os.path.abspath(path), strict=True)


def main():
    """Parse CLI args and print validation benchmark results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--spec",
        default="tests/specs/petstore.yaml",
        help="Spec file to validate (default: petstore)",
    )
    args = parser.parse_args()

    spec_path = os.path.abspath(args.spec)
    importlib.import_module("prance.util.resolver")

    rows = []
    with backend_env("python"):
        resolver_mod = importlib.reload(importlib.import_module("prance.util.resolver"))
        if resolver_mod.rust_validate_openapi_spec is None:
            print("Rust validator extension not built; skipping.")
            return
        rows.append(
            (
                "python",
                bench(lambda: validate_with_backend("python", spec_path), args.rounds),
            )
        )
        rows.append(
            (
                "rust (BaseParser)",
                bench(lambda: validate_with_backend("rust", spec_path), args.rounds),
            )
        )
        rows.append(
            (
                "rust (parse_and_validate)",
                bench(lambda: validate_rust_direct(spec_path), args.rounds),
            )
        )

    print(f"spec: {spec_path}")
    print(f"{'backend':<28} {'mean_ms':>10}")
    print("-" * 40)
    for name, mean_ms in rows:
        print(f"{name:<28} {mean_ms:10.2f}")


if __name__ == "__main__":
    main()
