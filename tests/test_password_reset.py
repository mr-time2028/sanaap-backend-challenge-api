"""Tests for the password-reset flow."""

import re

import pytest
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


@pytest.mark.django_db
def test_password_reset_full_flow(api: APIClient, user: User) -> None:
    response = api.post("/api/v1/auth/password-reset/", {"email": user.email})
    assert response.status_code == status.HTTP_200_OK

    body = str(mail.outbox[0].body)
    match = re.search(r"uid=(\S+)&token=(\S+)", body)
    assert match is not None
    uid, token = match.group(1), match.group(2)

    confirm = api.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "newSecret456"},
    )
    assert confirm.status_code == status.HTTP_200_OK

    old = api.post(
        "/api/v1/auth/login/", {"username": user.username, "password": "secret123"}
    )
    assert old.status_code == status.HTTP_401_UNAUTHORIZED
    new = api.post(
        "/api/v1/auth/login/", {"username": user.username, "password": "newSecret456"}
    )
    assert new.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_reset_with_invalid_token_fails(api: APIClient, user: User) -> None:
    response = api.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": "bogus", "token": "bogus", "new_password": "newSecret456"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_unknown_email_does_not_leak(api: APIClient, user: User) -> None:
    response = api.post("/api/v1/auth/password-reset/", {"email": "nobody@example.com"})
    assert response.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 0
