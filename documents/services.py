"""Document use-cases — orchestrates storage and persistence behind Protocols."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from audit.observer import AuditObserver
from documents.events import DocumentEvent, DocumentObserver
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
    "local": lambda: LocalStorage(Path(settings.LOCAL_STORAGE_PATH)),
}


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: DocumentStorage,
        observers: Sequence[DocumentObserver] = (),
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._observers = list(observers)

    def _notify(self, event: DocumentEvent) -> None:
        for observer in self._observers:
            observer.on_document_event(event)

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
        document = self._repository.add(document)
        self._notify(
            DocumentEvent(
                action="created",
                document_id=document.pk,
                document_title=document.title,
                user=user,
                changes={"file_name": file_name, "size": len(data)},
            )
        )
        return document

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
        user: Any = None,
        title: str | None = None,
        description: str | None = None,
        file_name: str | None = None,
        content_type: str | None = None,
        data: bytes | None = None,
    ) -> Document:
        changes: dict[str, Any] = {}
        if title is not None and title != document.title:
            changes["title"] = {"old": document.title, "new": title}
        if description is not None and description != document.description:
            changes["description"] = {"old": document.description, "new": description}
        if data is not None and file_name is not None and content_type is not None:
            if file_name != document.file_name:
                changes["file_name"] = {"old": document.file_name, "new": file_name}
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
        updated = self._repository.update(document)
        if changes:
            self._notify(
                DocumentEvent(
                    action="updated",
                    document_id=updated.pk,
                    document_title=updated.title,
                    user=user,
                    changes=changes,
                )
            )
        return updated

    def delete(self, document: Document, *, user: Any = None) -> None:
        document_id = document.pk
        self._storage.delete(document.storage_key)
        self._repository.delete(document_id)
        self._notify(
            DocumentEvent(
                action="deleted",
                document_id=document_id,
                document_title=document.title,
                user=user,
                changes={"file_name": document.file_name},
            )
        )

    def download(self, document: Document) -> bytes:
        return self._storage.get(document.storage_key)

    def url_for(self, document: Document) -> str:
        return self._storage.url_for(document.storage_key)

    def compute_checksum(self, document_id: int) -> str:
        document = self.get(document_id)
        if document is None:
            return ""
        checksum = hashlib.sha256(self._storage.get(document.storage_key)).hexdigest()
        document.checksum = checksum
        self._repository.update(document)
        return checksum


def get_document_service() -> DocumentService:
    """Composition root — the ONLY place that knows which backend is real."""
    backend = settings.STORAGE_BACKEND
    if backend not in STORAGE_BACKENDS:
        raise ImproperlyConfigured(
            f"Unknown STORAGE_BACKEND {backend!r} — expected one of {sorted(STORAGE_BACKENDS)}."
        )
    return DocumentService(
        DjangoDocumentRepository(),
        STORAGE_BACKENDS[backend](),
        observers=[AuditObserver()],
    )
