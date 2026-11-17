"""Tests for JWT login, refresh and logout."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User

CREDS = {"username": "hamid", "password": "secret123"}


@pytest.mark.django_db
def test_login_returns_token_pair(api: APIClient, user: User) -> None:
    response = api.post("/api/v1/auth/login/", CREDS)
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_with_wrong_password_fails(api: APIClient, user: User) -> None:
    response = api.post(
        "/api/v1/auth/login/", {"username": "hamid", "password": "wrong"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_refresh_returns_new_access(api: APIClient, user: User) -> None:
    tokens = api.post("/api/v1/auth/login/", CREDS).data
    response = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api: APIClient, user: User) -> None:
    tokens = api.post("/api/v1/auth/login/", CREDS).data
    # Log in for the logout call — logout itself requires authentication.
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = api.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    api.credentials()  # drop the header again
    reuse = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    assert reuse.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_logout_without_payload_returns_400(api: APIClient, user: User) -> None:
    api.force_authenticate(user=user)
    response = api.post("/api/v1/auth/logout/", {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_login_is_throttled(api: APIClient, user: User) -> None:
    for _ in range(5):
        api.post("/api/v1/auth/login/", CREDS)
    response = api.post("/api/v1/auth/login/", CREDS)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
