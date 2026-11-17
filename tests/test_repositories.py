"""Tests for the document repository (Django adapter on the test database)."""

from datetime import date, timedelta

import pytest

from accounts.models import User
from documents.models import Document
from documents.repositories import DjangoDocumentRepository, DocumentCriteria


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


def test_search_by_title(db: None, user: User) -> None:
    Document.objects.create(
        title="Annual report",
        file_name="a.pdf",
        content_type="application/pdf",
        size=1,
        storage_key="k/a.pdf",
        uploaded_by=user,
    )
    Document.objects.create(
        title="Meeting notes",
        file_name="b.txt",
        content_type="text/plain",
        size=1,
        storage_key="k/b.txt",
        uploaded_by=user,
    )
    results = DjangoDocumentRepository().search(DocumentCriteria(title="report"))
    assert [d.title for d in results] == ["Annual report"]


def test_search_by_content_type(db: None, user: User) -> None:
    Document.objects.create(
        title="A",
        file_name="a.pdf",
        content_type="application/pdf",
        size=1,
        storage_key="k/a.pdf",
        uploaded_by=user,
    )
    Document.objects.create(
        title="B",
        file_name="b.txt",
        content_type="text/plain",
        size=1,
        storage_key="k/b.txt",
        uploaded_by=user,
    )
    results = DjangoDocumentRepository().search(
        DocumentCriteria(content_type="text/plain")
    )
    assert [d.title for d in results] == ["B"]


def test_search_by_uploaded_by(db: None, user: User) -> None:
    Document.objects.create(
        title="A",
        file_name="a.txt",
        content_type="text/plain",
        size=1,
        storage_key="k/a.txt",
        uploaded_by=user,
    )
    results = DjangoDocumentRepository().search(
        DocumentCriteria(uploaded_by=user.username)
    )
    assert len(results) == 1
    assert (
        DjangoDocumentRepository().search(DocumentCriteria(uploaded_by="someone-else"))
        == []
    )


def test_search_by_created_date(db: None, user: User) -> None:
    Document.objects.create(
        title="A",
        file_name="a.txt",
        content_type="text/plain",
        size=1,
        storage_key="k/a.txt",
        uploaded_by=user,
    )
    # Bounds are inclusive — the range is closed: [created_after, created_before].
    assert (
        len(
            DjangoDocumentRepository().search(
                DocumentCriteria(created_after=date.today())
            )
        )
        == 1
    )
    assert (
        DjangoDocumentRepository().search(
            DocumentCriteria(created_after=date.today() + timedelta(days=1))
        )
        == []
    )
    assert (
        len(
            DjangoDocumentRepository().search(
                DocumentCriteria(created_before=date.today())
            )
        )
        == 1
    )
    assert (
        DjangoDocumentRepository().search(
            DocumentCriteria(created_before=date.today() - timedelta(days=1))
        )
        == []
    )


def test_search_with_no_criteria_returns_all(db: None, user: User) -> None:
    Document.objects.create(
        title="A",
        file_name="a.txt",
        content_type="text/plain",
        size=1,
        storage_key="k/a.txt",
        uploaded_by=user,
    )
    assert len(DjangoDocumentRepository().search(DocumentCriteria())) == 1
