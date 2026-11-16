"""Tests for the OpenAPI schema and Swagger UI."""

from rest_framework import status
from rest_framework.test import APIClient


def test_schema_endpoint_returns_openapi(api: APIClient) -> None:
    response = api.get("/api/schema/")
    assert response.status_code == status.HTTP_200_OK
    schema = response.data  # raw dict — works whatever the content type
    assert schema["openapi"].startswith("3.")
    assert "/api/v1/auth/login/" in schema["paths"]


def test_swagger_ui_loads(api: APIClient) -> None:
    response = api.get("/api/docs/")
    assert response.status_code == status.HTTP_200_OK


def test_schema_documents_all_endpoints(api: APIClient) -> None:
    schema = api.get("/api/schema/").data
    for path in [
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/password-reset/",
        "/api/v1/auth/password-reset/confirm/",
        "/api/v1/users/",
    ]:
        assert path in schema["paths"], path
    assert any(p.endswith("/role/") for p in schema["paths"])
    assert schema["paths"]["/api/v1/auth/login/"]["post"]["summary"] == "Log in"
    assert "jwtAuth" in schema["components"]["securitySchemes"]
