"""Benchmarks for RefResolver / ResolvingParser hot paths."""
import os

import pytest

from prance.util import resolver


def _resolve(spec, url=None):
    res = resolver.RefResolver(spec, url=url)
    res.resolve_references()
    return res.specs


@pytest.mark.benchmark(group="resolver")
def test_bench_petstore(benchmark, petstore_spec):
    benchmark(_resolve, petstore_spec, url="tests/specs/petstore.yaml")


@pytest.mark.benchmark(group="resolver")
def test_bench_externals(benchmark, externals_spec):
    benchmark(
        _resolve,
        externals_spec,
        url=os.path.abspath("tests/specs/with_externals.yaml"),
    )


@pytest.mark.benchmark(group="resolver")
def test_bench_large_shared_refs(benchmark, large_shared_refs_spec):
    benchmark(_resolve, large_shared_refs_spec)
