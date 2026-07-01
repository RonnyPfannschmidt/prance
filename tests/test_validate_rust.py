"""Tests for the Rust OpenAPI validator (``validate_openapi_spec``)."""
import pytest

from . import none_of
from prance import BaseParser
from prance import ValidationError
from prance.util import formats
from prance.util import fs
from prance.util.resolver import rust_validate_openapi_spec
from prance.util.resolver import use_rust_validator


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_validate_openapi_spec_exported():
    import _prance_rs

    assert hasattr(_prance_rs, "validate_openapi_spec")
    assert rust_validate_openapi_spec is _prance_rs.validate_openapi_spec


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_petstore_parity():
    spec = formats.parse_spec(
        fs.read_file("tests/specs/petstore.yaml"), "tests/specs/petstore.yaml"
    )
    rust_validate_openapi_spec(spec, url="tests/specs/petstore.yaml", strict=True)
    BaseParser("tests/specs/petstore.yaml", backend="openapi-spec-validator")


@pytest.mark.skipif(
    none_of("openapi-spec-validator"),
    reason="Missing dependencies: openapi-spec-validator",
)
@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_issue_5_integer_keys_strict():
    with pytest.raises(ValidationError):
        BaseParser(
            "tests/specs/issue_5.yaml",
            backend="openapi-spec-validator",
            strict=True,
        )


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_missing_reference():
    with pytest.raises(ValidationError):
        BaseParser(
            "tests/specs/missing_reference.yaml",
            backend="openapi-spec-validator",
        )


@pytest.mark.skipif(
    none_of("openapi-spec-validator"),
    reason="Missing dependencies: openapi-spec-validator",
)
@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_issue_20_version_on_failure():
    parser = BaseParser(
        "tests/specs/issue_20.yaml",
        backend="openapi-spec-validator",
        strict=False,
        lazy=True,
    )
    assert not parser.valid
    assert parser.version_parsed == ()

    with pytest.raises(ValidationError):
        parser.parse()

    assert not parser.valid
    assert parser.version_parsed == (3, 0, 0)


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_parse_and_validate_spec_exported():
    import _prance_rs

    from prance.util.resolver import rust_parse_and_validate_spec

    assert hasattr(_prance_rs, "parse_and_validate_spec")
    assert hasattr(_prance_rs, "load_openapi_spec_py")
    assert rust_parse_and_validate_spec is _prance_rs.parse_and_validate_spec


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_parse_and_validate_petstore():
    from prance.util.resolver import rust_parse_and_validate_spec

    spec = rust_parse_and_validate_spec(
        url="tests/specs/petstore.yaml",
        strict=True,
    )
    assert spec["swagger"] == "2.0"


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_invalid_default_int32():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "Bad": {
                    "type": "integer",
                    "format": "int32",
                    "default": 2**31,
                }
            }
        },
    }
    with pytest.raises(ValidationError, match=r"int32"):
        rust_validate_openapi_spec(spec, strict=True)


@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_swagger2_definitions_walk():
    spec = {
        "swagger": "2.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "definitions": {
            "Bad": {
                "type": "integer",
                "format": "int32",
                "default": 2**31,
            }
        },
    }
    with pytest.raises(ValidationError, match=r"int32"):
        rust_validate_openapi_spec(spec, strict=True)


@pytest.mark.skipif(
    none_of("openapi-spec-validator"),
    reason="Missing dependencies: openapi-spec-validator",
)
@pytest.mark.skipif(
    not use_rust_validator(), reason="Rust validator extension not available"
)
def test_rust_validator_issue_5_integer_keys_lenient():
    parser = BaseParser(
        "tests/specs/issue_5.yaml",
        backend="openapi-spec-validator",
        strict=False,
    )
    assert "200" in parser.specification["paths"]["/test"]["post"]["responses"]
