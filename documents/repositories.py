"""Persistence seam — Protocol + Django ORM adapter (DIP)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from documents.models import Document


@dataclass(frozen=True)
class DocumentCriteria:
    """Search criteria — the query language of the document store."""

    title: str | None = None  # case-insensitive contains
    content_type: str | None = None  # exact match
    uploaded_by: str | None = None  # username, exact match
    created_after: date | None = None
    created_before: date | None = None


class DocumentRepository(Protocol):
    def add(self, document: Document) -> Document: ...
    def get_by_id(self, document_id: int) -> Document | None: ...
    def list_all(self) -> list[Document]: ...
    def search(self, criteria: DocumentCriteria) -> list[Document]: ...
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

    def search(self, criteria: DocumentCriteria) -> list[Document]:
        queryset = Document.objects.all()
        if criteria.title:
            queryset = queryset.filter(title__icontains=criteria.title)
        if criteria.content_type:
            queryset = queryset.filter(content_type=criteria.content_type)
        if criteria.uploaded_by:
            queryset = queryset.filter(uploaded_by__username=criteria.uploaded_by)
        if criteria.created_after:
            queryset = queryset.filter(created_at__date__gte=criteria.created_after)
        if criteria.created_before:
            queryset = queryset.filter(created_at__date__lte=criteria.created_before)
        return list(queryset)

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

    def search(self, criteria: DocumentCriteria) -> list[Document]:
        results = self.list_all()
        if criteria.title:
            results = [d for d in results if criteria.title.lower() in d.title.lower()]
        if criteria.content_type:
            results = [d for d in results if d.content_type == criteria.content_type]
        if criteria.uploaded_by:
            results = [
                d
                for d in results
                if d.uploaded_by and d.uploaded_by.username == criteria.uploaded_by
            ]
        if criteria.created_after:
            results = [
                d for d in results if d.created_at.date() >= criteria.created_after
            ]
        if criteria.created_before:
            results = [
                d for d in results if d.created_at.date() <= criteria.created_before
            ]
        return results

    def update(self, document: Document) -> Document:
        self._documents[document.id] = document
        return document

    def delete(self, document_id: int) -> None:
        self._documents.pop(document_id, None)
