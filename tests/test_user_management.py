"""Tests for admin-only user management."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserRole


@pytest.fixture()
def admin_user() -> User:
    return User.objects.create_user(
        username="admin", password="secret123", role=UserRole.ADMIN
    )


@pytest.mark.django_db
def test_admin_can_create_user_with_role(api: APIClient, admin_user: User) -> None:
    api.force_authenticate(user=admin_user)
    response = api.post(
        "/api/v1/users/",
        {"username": "sara", "password": "Str0ngPass!", "role": UserRole.EDITOR},
    )
    assert response.status_code == status.HTTP_201_CREATED
    created = User.objects.get(username="sara")
    assert created.role == UserRole.EDITOR
    assert created.check_password("Str0ngPass!")


@pytest.mark.django_db
def test_admin_can_change_role(api: APIClient, admin_user: User, user: User) -> None:
    api.force_authenticate(user=admin_user)
    response = api.patch(f"/api/v1/users/{user.pk}/role/", {"role": UserRole.EDITOR})
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.role == UserRole.EDITOR


@pytest.mark.django_db
def test_role_update_unknown_user_returns_404(api: APIClient, admin_user: User) -> None:
    api.force_authenticate(user=admin_user)
    response = api.patch("/api/v1/users/9999/role/", {"role": UserRole.EDITOR})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_non_admin_cannot_create_users(api: APIClient, user: User) -> None:
    api.force_authenticate(user=user)
    response = api.post(
        "/api/v1/users/",
        {"username": "intruder", "password": "Str0ngPass!", "role": UserRole.ADMIN},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_list_users(api: APIClient, admin_user: User, user: User) -> None:
    api.force_authenticate(user=admin_user)
    response = api.get("/api/v1/users/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
