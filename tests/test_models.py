"""Tests for the custom user and document models."""

import pytest

from accounts.models import User, UserRole
from documents.models import Document


@pytest.mark.django_db
def test_user_default_role_is_viewer() -> None:
    user = User.objects.create_user(username="alice", password="secret123")
    assert user.role == UserRole.VIEWER


@pytest.mark.django_db
def test_user_can_have_editor_role() -> None:
    user = User.objects.create_user(
        username="bob", password="secret123", role=UserRole.EDITOR
    )
    assert user.role == UserRole.EDITOR


@pytest.mark.django_db
def test_document_stores_metadata_and_owner() -> None:
    user = User.objects.create_user(username="carol", password="secret123")
    doc = Document.objects.create(
        title="Contract",
        description="A signed contract",
        file_key="documents/contract.pdf",
        content_type="application/pdf",
        size=1234,
        uploaded_by=user,
    )
    assert doc.pk is not None
    assert doc.uploaded_by == user
    assert str(doc) == "Contract"
