"""Tests for the repository protocol and both implementations.

The in-memory fake proves DIP/LSP: same interface, interchangeable behavior.
"""

import pytest

from accounts.models import User
from documents.models import Document
from documents.repositories import DjangoDocumentRepository, DocumentRepository


class InMemoryDocumentRepository:
    """Test double implementing the same protocol (works without a database)."""

    def __init__(self) -> None:
        self._rows: dict[int, Document] = {}
        self._next_id = 1

    def add(self, document: Document) -> Document:
        document.pk = self._next_id
        self._rows[self._next_id] = document
        self._next_id += 1
        return document

    def get(self, document_id: int) -> Document | None:
        return self._rows.get(document_id)

    def list(self) -> list[Document]:
        return list(self._rows.values())

    def save(self, document: Document) -> Document:
        assert document.pk is not None
        self._rows[document.pk] = document
        return document

    def delete(self, document: Document) -> None:
        self._rows.pop(document.pk, None)


def test_both_repositories_satisfy_the_protocol() -> None:
    assert isinstance(DjangoDocumentRepository(), DocumentRepository)
    assert isinstance(InMemoryDocumentRepository(), DocumentRepository)


def test_in_memory_repository_roundtrip() -> None:
    repo = InMemoryDocumentRepository()
    doc = repo.add(
        Document(
            title="Draft",
            file_key="documents/draft.pdf",
            content_type="application/pdf",
            size=10,
        )
    )
    assert repo.get(doc.pk) is doc
    doc.title = "Draft v2"
    repo.save(doc)
    assert repo.get(doc.pk).title == "Draft v2"  # type: ignore[union-attr]
    assert repo.list() == [doc]
    repo.delete(doc)
    assert repo.get(doc.pk) is None


@pytest.mark.django_db
def test_django_repository_roundtrip() -> None:
    user = User.objects.create_user(username="dave", password="secret123")
    repo = DjangoDocumentRepository()
    doc = repo.add(
        Document(
            title="Report",
            file_key="documents/report.pdf",
            content_type="application/pdf",
            size=20,
            uploaded_by=user,
        )
    )
    assert repo.get(doc.pk) is not None
    doc.title = "Report final"
    repo.save(doc)
    assert repo.get(doc.pk).title == "Report final"  # type: ignore[union-attr]
    assert len(repo.list()) == 1
    repo.delete(doc)
    assert repo.get(doc.pk) is None
