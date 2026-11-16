"""Document use-cases — orchestrates storage and persistence behind Protocols."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from documents.models import Document
from documents.repositories import (
    DjangoDocumentRepository,
    DocumentCriteria,
    DocumentRepository,
)
from documents.storage import DocumentStorage, LocalStorage, MinioStorage
from documents.validation import validate_upload

# The backend registry — the "switch" is data. A future backend (S3, GCS, ...)
# = a DocumentStorage class + one entry here.
STORAGE_BACKENDS: dict[str, Callable[[], DocumentStorage]] = {
    "minio": MinioStorage,
    "local": lambda: LocalStorage(Path(os.getenv("LOCAL_STORAGE_PATH", "var/files"))),
}


class DocumentService:
    def __init__(
        self, repository: DocumentRepository, storage: DocumentStorage
    ) -> None:
        self._repository = repository
        self._storage = storage

    def create(
        self,
        *,
        user: Any,
        title: str,
        description: str,
        file_name: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        validate_upload(file_name=file_name, content_type=content_type, size=len(data))
        key = self._storage.put(
            data=data, file_name=file_name, content_type=content_type
        )
        document = Document(
            title=title,
            description=description,
            file_name=file_name,
            content_type=content_type,
            size=len(data),
            storage_key=key,
            uploaded_by=user,
        )
        return self._repository.add(document)

    def get(self, document_id: int) -> Document | None:
        return self._repository.get_by_id(document_id)

    def list(self, criteria: DocumentCriteria | None = None) -> list[Document]:
        if criteria is None:
            return self._repository.list_all()
        return self._repository.search(criteria)

    def update(
        self,
        document: Document,
        *,
        title: str | None = None,
        description: str | None = None,
        file_name: str | None = None,
        content_type: str | None = None,
        data: bytes | None = None,
    ) -> Document:
        if data is not None and file_name is not None and content_type is not None:
            validate_upload(
                file_name=file_name, content_type=content_type, size=len(data)
            )
            self._storage.delete(document.storage_key)
            document.storage_key = self._storage.put(
                data=data, file_name=file_name, content_type=content_type
            )
            document.file_name = file_name
            document.content_type = content_type
            document.size = len(data)
        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        return self._repository.update(document)

    def delete(self, document: Document) -> None:
        self._storage.delete(document.storage_key)
        self._repository.delete(document.pk)

    def download(self, document: Document) -> bytes:
        return self._storage.get(document.storage_key)

    def url_for(self, document: Document) -> str:
        return self._storage.url_for(document.storage_key)


def get_document_service() -> DocumentService:
    """Composition root — the ONLY place that knows which backend is real."""
    backend = os.getenv("STORAGE_BACKEND", "minio")
    if backend not in STORAGE_BACKENDS:
        raise ImproperlyConfigured(
            f"Unknown STORAGE_BACKEND {backend!r} — expected one of {sorted(STORAGE_BACKENDS)}."
        )
    return DocumentService(DjangoDocumentRepository(), STORAGE_BACKENDS[backend]())
