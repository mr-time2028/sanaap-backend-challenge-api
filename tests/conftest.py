"""Shared fixtures for the test-suite."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import User


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> None:
    """Prevent throttle state from leaking between tests."""
    cache.clear()


@pytest.fixture()
def api() -> APIClient:
    return APIClient()


@pytest.fixture()
def user() -> User:
    return User.objects.create_user(
        username="hamid", password="secret123", email="hamid@example.com"
    )
