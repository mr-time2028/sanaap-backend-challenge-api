"""Tests for models."""

from accounts.models import User, UserRole
from documents.models import Document


def test_user_str_and_roles(db: None) -> None:
    user = User.objects.create_user(
        "hamid", "hamid@example.com", "secret123", role=UserRole.EDITOR
    )
    assert "hamid" in str(user)
    assert user.role == UserRole.EDITOR


def test_document_str(db: None, user: User) -> None:
    document = Document.objects.create(
        title="Spec",
        file_name="spec.pdf",
        content_type="application/pdf",
        size=1,
        storage_key="k/spec.pdf",
        uploaded_by=user,
    )
    assert str(document) == "Spec"
