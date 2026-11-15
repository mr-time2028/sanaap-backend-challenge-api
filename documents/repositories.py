"""Document repository: port (Protocol) + Django ORM adapter.

High-level code depends on the ``DocumentRepository`` protocol only
(Dependency Inversion); ``DjangoDocumentRepository`` is the concrete adapter.
Unit tests can substitute an in-memory fake with the same interface.
"""

from typing import Protocol, runtime_checkable

from documents.models import Document


@runtime_checkable
class DocumentRepository(Protocol):
    """What the domain needs from a document store."""

    def add(self, document: Document) -> Document:
        """Persist a new document and return it (with its id)."""
        ...

    def get(self, document_id: int) -> Document | None:
        """Return the document with this id, or None."""
        ...

    def list(self) -> list[Document]:
        """Return all documents, newest first."""
        ...

    def save(self, document: Document) -> Document:
        """Persist changes to an existing document."""
        ...

    def delete(self, document: Document) -> None:
        """Delete the document."""
        ...


class DjangoDocumentRepository:
    """Django ORM implementation of ``DocumentRepository``."""

    def add(self, document: Document) -> Document:
        document.save()
        return document

    def get(self, document_id: int) -> Document | None:
        return Document.objects.filter(pk=document_id).first()

    def list(self) -> list[Document]:
        return list(Document.objects.order_by("-created_at"))

    def save(self, document: Document) -> Document:
        document.save()
        return document

    def delete(self, document: Document) -> None:
        document.delete()
