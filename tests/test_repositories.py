"""Tests for the document repository (Django adapter on the test database)."""

import pytest

from accounts.models import User
from documents.models import Document
from documents.repositories import DjangoDocumentRepository


@pytest.fixture
def document(db: None, user: User) -> Document:
    return Document.objects.create(
        title="Report",
        file_name="report.pdf",
        content_type="application/pdf",
        size=10,
        storage_key="abc/report.pdf",
        uploaded_by=user,
    )


def test_add_and_get(document: Document) -> None:
    found = DjangoDocumentRepository().get_by_id(document.id)
    assert found is not None
    assert found.title == "Report"


def test_get_missing_returns_none(db: None) -> None:
    assert DjangoDocumentRepository().get_by_id(999) is None


def test_list_all(document: Document) -> None:
    assert len(DjangoDocumentRepository().list_all()) == 1


def test_delete(document: Document) -> None:
    repo = DjangoDocumentRepository()
    repo.delete(document.id)
    assert repo.get_by_id(document.id) is None
