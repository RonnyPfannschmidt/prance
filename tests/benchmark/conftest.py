"""Shared fixtures for resolver benchmarks."""
import pytest

from prance.util import formats
from prance.util import fs


def load_spec(path):
    content = fs.read_file(path)
    return formats.parse_spec(content, path)


@pytest.fixture
def petstore_spec():
    return load_spec("tests/specs/petstore.yaml")


@pytest.fixture
def externals_spec():
    return load_spec("tests/specs/with_externals.yaml")


def make_large_shared_refs_spec():
    """Synthetic OpenAPI 3 spec with many shared component schema refs."""
    schemas = {}
    for i in range(200):
        schemas[f"Model{i}"] = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "nested": {"$ref": "#/components/schemas/BaseModel"},
            },
        }

    schemas["BaseModel"] = {
        "type": "object",
        "properties": {
            "created_at": {"type": "string", "format": "date-time"},
            "tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}},
        },
    }
    schemas["Tag"] = {"type": "object", "properties": {"label": {"type": "string"}}}

    paths = {}
    for i in range(100):
        paths[f"/items/{i}"] = {
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

    return {
        "openapi": "3.0.0",
        "info": {"title": "Benchmark", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": schemas},
    }


@pytest.fixture
def large_shared_refs_spec():
    return make_large_shared_refs_spec()
