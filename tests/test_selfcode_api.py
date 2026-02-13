"""APIIntegrator testleri.

OpenAPI ayristirma, istemci uretimi, auth kod uretimi,
endpoint metot uretimi, dogrulama ve hiz sinirlandirma testleri.
"""

import pytest

from app.core.selfcode.api_integrator import APIIntegrator
from app.models.selfcode import (
    APIAuthType,
    APIClientConfig,
    APIEndpointSpec,
    APISpec,
)


# === Yardimci Fonksiyonlar ===


def _make_integrator(**kwargs) -> APIIntegrator:
    """Test icin APIIntegrator olusturur."""
    return APIIntegrator(**kwargs)


def _make_spec(**kwargs) -> APISpec:
    """Test icin APISpec olusturur."""
    defaults = {
        "title": "Test API",
        "base_url": "https://api.example.com",
        "endpoints": [
            APIEndpointSpec(path="/users", method="GET", description="Kullanicilari listele"),
        ],
    }
    defaults.update(kwargs)
    return APISpec(**defaults)


OPENAPI_SAMPLE = {
    "info": {"title": "Pet Store", "version": "1.0.0"},
    "servers": [{"url": "https://petstore.example.com/v1"}],
    "paths": {
        "/pets": {
            "get": {
                "summary": "List pets",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "array"},
                            }
                        }
                    }
                },
            },
            "post": {
                "summary": "Create pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    }
                },
                "responses": {"201": {}},
            },
        },
        "/pets/{petId}": {
            "get": {
                "summary": "Get pet by ID",
                "parameters": [
                    {"name": "petId", "in": "path", "schema": {"type": "string"}},
                ],
                "responses": {"200": {}},
            },
        },
    },
}

OPENAPI_WITH_AUTH = {
    "info": {"title": "Secure API", "version": "1.0.0"},
    "servers": [{"url": "https://secure.example.com"}],
    "paths": {},
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"},
        }
    },
}


# === Init Testleri ===


class TestInit:
    """APIIntegrator init testleri."""

    def test_defaults(self) -> None:
        ai = _make_integrator()
        assert ai.default_timeout == 30.0
        assert ai.default_retry == 3

    def test_custom(self) -> None:
        ai = _make_integrator(default_timeout=60.0, default_retry=5)
        assert ai.default_timeout == 60.0
        assert ai.default_retry == 5


# === ParseOpenapi Testleri ===


class TestParseOpenapi:
    """parse_openapi() testleri."""

    def test_basic_parse(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_SAMPLE)
        assert isinstance(spec, APISpec)
        assert spec.title == "Pet Store"

    def test_endpoints_parsed(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_SAMPLE)
        assert len(spec.endpoints) >= 3

    def test_base_url_parsed(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_SAMPLE)
        assert "petstore" in spec.base_url

    def test_version_parsed(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_SAMPLE)
        assert spec.version == "1.0.0"

    def test_auth_detected(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_WITH_AUTH)
        assert spec.auth_type == APIAuthType.BEARER

    def test_no_auth(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi(OPENAPI_SAMPLE)
        assert spec.auth_type == APIAuthType.NONE

    def test_empty_spec(self) -> None:
        ai = _make_integrator()
        spec = ai.parse_openapi({})
        assert spec.title == "API"
        assert len(spec.endpoints) == 0


# === GenerateClient Testleri ===


class TestGenerateClient:
    """generate_client() testleri."""

    def test_basic_generation(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec)
        assert isinstance(config, APIClientConfig)
        assert "class" in config.client_code

    def test_has_init(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec)
        assert "__init__" in config.client_code

    def test_has_close(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec)
        assert "close" in config.client_code

    def test_with_rate_limit(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec, rate_limit=10)
        assert config.rate_limit == 10
        assert "rate" in config.client_code.lower()

    def test_has_error_handling(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec)
        assert "retry" in config.client_code.lower()

    def test_spec_id_carried(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        config = ai.generate_client(spec)
        assert config.spec_id == spec.id


# === GenerateAuthCode Testleri ===


class TestGenerateAuthCode:
    """generate_auth_code() testleri."""

    def test_none_auth(self) -> None:
        ai = _make_integrator()
        code = ai.generate_auth_code(APIAuthType.NONE)
        assert code == "pass"

    def test_api_key_auth(self) -> None:
        ai = _make_integrator()
        code = ai.generate_auth_code(APIAuthType.API_KEY)
        assert "API-Key" in code or "api_key" in code.lower()

    def test_bearer_auth(self) -> None:
        ai = _make_integrator()
        code = ai.generate_auth_code(APIAuthType.BEARER)
        assert "Bearer" in code

    def test_basic_auth(self) -> None:
        ai = _make_integrator()
        code = ai.generate_auth_code(APIAuthType.BASIC)
        assert "Basic" in code


# === GenerateEndpointMethod Testleri ===


class TestGenerateEndpointMethod:
    """generate_endpoint_method() testleri."""

    def test_get_endpoint(self) -> None:
        ai = _make_integrator()
        ep = APIEndpointSpec(path="/users", method="GET")
        code = ai.generate_endpoint_method(ep)
        assert "async def" in code
        assert "get" in code

    def test_post_endpoint(self) -> None:
        ai = _make_integrator()
        ep = APIEndpointSpec(path="/users", method="POST", request_body={"type": "object"})
        code = ai.generate_endpoint_method(ep)
        assert "post" in code
        assert "data" in code

    def test_path_params(self) -> None:
        ai = _make_integrator()
        ep = APIEndpointSpec(
            path="/users/{user_id}", method="GET",
            parameters={"user_id": "string"},
        )
        code = ai.generate_endpoint_method(ep)
        assert "user_id" in code


# === ValidateSpec Testleri ===


class TestValidateSpec:
    """validate_spec() testleri."""

    def test_valid_spec(self) -> None:
        ai = _make_integrator()
        spec = _make_spec()
        issues = ai.validate_spec(spec)
        assert len(issues) == 0

    def test_missing_title(self) -> None:
        ai = _make_integrator()
        spec = _make_spec(title="")
        issues = ai.validate_spec(spec)
        assert any("baslik" in i.lower() or "title" in i.lower() for i in issues)

    def test_missing_base_url(self) -> None:
        ai = _make_integrator()
        spec = _make_spec(base_url="")
        issues = ai.validate_spec(spec)
        assert any("url" in i.lower() for i in issues)

    def test_no_endpoints(self) -> None:
        ai = _make_integrator()
        spec = _make_spec(endpoints=[])
        issues = ai.validate_spec(spec)
        assert any("endpoint" in i.lower() for i in issues)

    def test_invalid_method(self) -> None:
        ai = _make_integrator()
        ep = APIEndpointSpec(path="/test", method="INVALID")
        spec = _make_spec(endpoints=[ep])
        issues = ai.validate_spec(spec)
        assert any("metodu" in i.lower() or "method" in i.lower() for i in issues)


# === AddRateLimiting Testleri ===


class TestAddRateLimiting:
    """add_rate_limiting() testleri."""

    def test_code_appended(self) -> None:
        ai = _make_integrator()
        original = "class MyClient:\n    pass\n"
        result = ai.add_rate_limiting(original, 10)
        assert "rate" in result.lower()
        assert original.strip() in result


# === AddErrorHandling Testleri ===


class TestAddErrorHandling:
    """add_error_handling() testleri."""

    def test_code_appended(self) -> None:
        ai = _make_integrator()
        original = "class MyClient:\n    pass\n"
        result = ai.add_error_handling(original)
        assert "retry" in result.lower()
