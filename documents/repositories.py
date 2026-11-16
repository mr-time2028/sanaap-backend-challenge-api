"""Persistence seam — Protocol + Django ORM adapter (DIP)."""

from __future__ import annotations

from typing import Protocol

from documents.models import Document


class DocumentRepository(Protocol):
    def add(self, document: Document) -> Document: ...
    def get_by_id(self, document_id: int) -> Document | None: ...
    def list_all(self) -> list[Document]: ...
    def update(self, document: Document) -> Document: ...
    def delete(self, document_id: int) -> None: ...


class DjangoDocumentRepository:
    def add(self, document: Document) -> Document:
        document.save()
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        try:
            return Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return None

    def list_all(self) -> list[Document]:
        return list(Document.objects.all())

    def update(self, document: Document) -> Document:
        document.save()
        return document

    def delete(self, document_id: int) -> None:
        Document.objects.filter(pk=document_id).delete()


class InMemoryDocumentRepository:
    """Fake for tests — no database."""

    def __init__(self) -> None:
        self._documents: dict[int, Document] = {}
        self._next_id = 1

    def add(self, document: Document) -> Document:
        new_id = self._next_id
        self._next_id += 1
        document.id = new_id
        self._documents[new_id] = document
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        return self._documents.get(document_id)

    def list_all(self) -> list[Document]:
        return list(self._documents.values())

    def update(self, document: Document) -> Document:
        self._documents[document.id] = document
        return document

    def delete(self, document_id: int) -> None:
        self._documents.pop(document_id, None)
