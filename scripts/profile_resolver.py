"""Profile resolver to find remaining bottlenecks."""

from __future__ import annotations

import cProfile
import os
import pstats
import sys
import time

from prance.util.resolver import RefResolver


def make_chain_spec(num_models: int = 50) -> dict:
    """Spec with chain refs: Model_i -> Model_{i-1} -> ... -> Model_0."""
    definitions: dict[str, object] = {}
    for i in range(num_models):
        props: dict[str, object] = {
            "id": {"type": "integer"},
            "name": {"type": "string"},
        }
        if i > 0:
            props["parent"] = {"$ref": f"#/definitions/Model{i - 1}"}
        if i > 1:
            props["grandparent"] = {"$ref": f"#/definitions/Model{i - 2}"}
        definitions[f"Model{i}"] = {"type": "object", "properties": props}

    paths: dict[str, object] = {}
    for i in range(0, num_models, 2):
        paths[f"/api/v1/model{i}"] = {
            "get": {
                "responses": {
                    "200": {"schema": {"$ref": f"#/definitions/Model{i}"}},
                    "201": {
                        "schema": {"$ref": f"#/definitions/Model{(i+1) % num_models}"}
                    },
                }
            }
        }

    return {
        "swagger": "2.0",
        "info": {"title": "Test", "version": "1.0"},
        "basePath": "/",
        "paths": paths,
        "definitions": definitions,
    }


def make_flat_spec(num_models: int = 50) -> dict:
    """Spec with flat refs: many endpoints all ref the same models (no chains)."""
    definitions: dict[str, object] = {}
    for i in range(num_models):
        definitions[f"Model{i}"] = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }

    paths: dict[str, object] = {}
    for i in range(num_models * 2):
        paths[f"/api/v1/resource{i}"] = {
            "get": {
                "responses": {
                    "200": {"schema": {"$ref": f"#/definitions/Model{i % num_models}"}},
                }
            }
        }

    return {
        "swagger": "2.0",
        "info": {"title": "Test", "version": "1.0"},
        "basePath": "/",
        "paths": paths,
        "definitions": definitions,
    }


def time_resolve(spec: dict, url: str) -> float:
    """Time a single resolve_references call, return elapsed seconds."""
    t0 = time.perf_counter()
    r = RefResolver(spec, url)
    r.resolve_references()
    return time.perf_counter() - t0


def profile_resolve(spec: dict, url: str, label: str) -> None:
    """Run cProfile on a single resolution and print top functions."""
    prof = cProfile.Profile()
    prof.enable()
    r = RefResolver(spec, url)
    r.resolve_references()
    prof.disable()

    stats = pstats.Stats(prof)
    stats.strip_dirs()

    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")

    print("\n--- Top 25 by cumulative time ---")
    stats.sort_stats("cumulative")
    stats.print_stats(25)

    print("\n--- Top 25 by total (self) time ---")
    stats.sort_stats("tottime")
    stats.print_stats(25)

    print("\n--- Callers of top 10 self-time functions ---")
    stats.sort_stats("tottime")
    stats.print_callers(10)


def make_deep_linear_spec(depth: int = 500) -> dict:
    """Spec with a single linear $ref chain of *depth* hops (no cycles)."""
    schemas: dict[str, object] = {}
    for i in range(depth):
        schemas[f"S{i}"] = {"$ref": f"#/definitions/S{i + 1}"}
    schemas[f"S{depth}"] = {"type": "string"}
    return {
        "swagger": "2.0",
        "info": {"title": "Test", "version": "1.0"},
        "basePath": "/",
        "paths": {
            "/start": {
                "get": {"responses": {"200": {"schema": {"$ref": "#/definitions/S0"}}}}
            }
        },
        "definitions": schemas,
    }


def make_recursive_spec() -> dict:
    """Spec with a two-node cycle: A -> B -> A."""
    return {
        "swagger": "2.0",
        "info": {"title": "Test", "version": "1.0"},
        "basePath": "/",
        "paths": {
            "/start": {
                "get": {"responses": {"200": {"schema": {"$ref": "#/definitions/A"}}}}
            }
        },
        "definitions": {
            "A": {
                "type": "object",
                "properties": {"b": {"$ref": "#/definitions/B"}},
            },
            "B": {
                "type": "object",
                "properties": {"a": {"$ref": "#/definitions/A"}},
            },
        },
    }


def stress_deep_chains(url: str) -> None:
    """Test resolver robustness on deeply nested linear $ref chains."""
    print("\n=== Stress: deep linear $ref chains ===\n")
    print(f"{'depth':>8}  {'time_ms':>10}  {'status':>20}")
    print("-" * 44)

    for depth in (50, 100, 250, 500, 1000, 2000, 5000):
        spec = make_deep_linear_spec(depth)
        try:
            t0 = time.perf_counter()
            r = RefResolver(spec, url)
            r.resolve_references()
            elapsed = time.perf_counter() - t0
            print(f"{depth:>8}  {elapsed*1000:>10.1f}  {'OK':>20}")
        except RecursionError:
            print(f"{depth:>8}  {'—':>10}  {'RecursionError':>20}")
        except Exception as e:
            name = type(e).__name__
            print(f"{depth:>8}  {'—':>10}  {name:>20}")
        sys.stdout.flush()


def stress_recursive_refs(url: str) -> None:
    """Test resolver behaviour on cyclic schemas with various recursion_limit values."""
    from prance.util.resolver import keep_ref_on_recursion

    print("\n=== Stress: cyclic $ref (A->B->A) with increasing recursion_limit ===\n")
    print(f"{'reclimit':>10}  {'time_ms':>10}  {'status':>20}")
    print("-" * 46)

    for limit in (1, 5, 50, 200, 500, 1000):
        spec = make_recursive_spec()
        try:
            t0 = time.perf_counter()
            r = RefResolver(
                spec,
                url,
                recursion_limit=limit,
                recursion_limit_handler=keep_ref_on_recursion,
            )
            r.resolve_references()
            elapsed = time.perf_counter() - t0
            print(f"{limit:>10}  {elapsed*1000:>10.1f}  {'OK':>20}")
        except RecursionError:
            print(f"{limit:>10}  {'—':>10}  {'RecursionError':>20}")
        except Exception as e:
            name = type(e).__name__
            print(f"{limit:>10}  {'—':>10}  {name:>20}")
        sys.stdout.flush()


def main() -> None:
    """Run scaling tests and cProfile on various spec shapes."""
    url = "file:///tmp/test.json"

    # --- Phase 1: Scaling test ---
    print("=== Phase 1: Scaling — chain spec (Model_i refs Model_{i-1}) ===\n")
    print(f"{'models':>8}  {'time_ms':>10}  {'ratio':>8}")
    print("-" * 32)

    base_time = None
    profile_n = 5
    for n in (5, 10, 20, 30, 50, 75, 100, 150, 200):
        elapsed = time_resolve(make_chain_spec(n), url)
        if base_time is None:
            base_time = elapsed
        ratio = elapsed / base_time
        print(f"{n:>8}  {elapsed*1000:>10.1f}  {ratio:>8.1f}x")
        sys.stdout.flush()

        if elapsed < 2:
            profile_n = n

        if elapsed > 15:
            print("  (stopping — too slow)")
            break

    print("\n=== Phase 2: Scaling — flat spec (no ref chains) ===\n")
    print(f"{'models':>8}  {'time_ms':>10}  {'ratio':>8}")
    print("-" * 32)

    base_time = None
    for n in (10, 50, 100, 200, 500):
        elapsed = time_resolve(make_flat_spec(n), url)
        if base_time is None:
            base_time = elapsed
        ratio = elapsed / base_time
        print(f"{n:>8}  {elapsed*1000:>10.1f}  {ratio:>8.1f}x")
        sys.stdout.flush()

        if elapsed > 15:
            print("  (stopping)")
            break

    # --- Phase 3: cProfile the petstore ---
    spec_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tests", "specs", "petstore.yaml")
    )
    import prance

    petstore = prance.BaseParser(spec_path, strict=False)
    profile_resolve(petstore.specification, petstore.url, "petstore.yaml")

    # --- Phase 4: cProfile the chain spec at profile_n ---
    profile_resolve(make_chain_spec(profile_n), url, f"chain spec ({profile_n} models)")

    # --- Phase 5: cProfile the flat spec ---
    profile_resolve(make_flat_spec(100), url, "flat spec (100 models)")

    # --- Phase 6: Stress tests for deep hierarchies ---
    stress_deep_chains(url)
    stress_recursive_refs(url)


if __name__ == "__main__":
    main()
