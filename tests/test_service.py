"""Service tests — InMemory fakes: no database, no MinIO."""

import hashlib
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError

from accounts.models import User
from documents.models import Document
from documents.repositories import DocumentCriteria, InMemoryDocumentRepository
from documents.services import DocumentService, get_document_service
from documents.storage import InMemoryDocumentStorage, LocalStorage, MinioStorage


@pytest.fixture
def service() -> DocumentService:
    return DocumentService(InMemoryDocumentRepository(), InMemoryDocumentStorage())


def make_document(
    service: DocumentService,
    *,
    title: str = "Doc",
    description: str = "",
    file_name: str = "doc.txt",
    content_type: str = "text/plain",
    data: bytes = b"body",
) -> Document:
    return service.create(
        user=None,
        title=title,
        description=description,
        file_name=file_name,
        content_type=content_type,
        data=data,
    )


def test_create_stores_metadata_and_bytes(service: DocumentService) -> None:
    document = make_document(service)
    assert document.pk == 1
    found = service.get(1)
    assert found is not None
    assert found.storage_key == document.storage_key


def test_create_rejects_disallowed_type(service: DocumentService) -> None:
    with pytest.raises(ValidationError):
        make_document(service, content_type="application/x-sh")


def test_create_rejects_oversized_file(service: DocumentService) -> None:
    with pytest.raises(ValidationError):
        make_document(service, data=b"x" * (10 * 1024 * 1024 + 1))


def test_create_rejects_unsafe_file_name(service: DocumentService) -> None:
    with pytest.raises(ValidationError):
        make_document(service, file_name="evil/../a.txt")
    with pytest.raises(ValidationError):
        make_document(service, file_name="")


def test_update_replaces_file_and_metadata(service: DocumentService) -> None:
    document = make_document(service)
    updated = service.update(
        document,
        title="New",
        data=b"v2",
        file_name="new.txt",
        content_type="text/plain",
    )
    assert updated.title == "New"
    assert updated.size == 2


def test_update_metadata_only_keeps_file(service: DocumentService) -> None:
    document = make_document(service)
    updated = service.update(document, title="Renamed", description="d")
    assert updated.title == "Renamed"
    assert updated.size == 4


def test_delete_removes_document(service: DocumentService) -> None:
    document = make_document(service)
    service.delete(document)
    assert service.list() == []


def test_minio_is_the_default_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert isinstance(get_document_service()._storage, MinioStorage)


def test_local_backend_is_wired_when_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
    assert isinstance(get_document_service()._storage, LocalStorage)


def test_unknown_storage_backend_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3-unknown")
    with pytest.raises(ImproperlyConfigured):
        get_document_service()


def test_list_with_criteria_filters_results() -> None:
    service = DocumentService(InMemoryDocumentRepository(), InMemoryDocumentStorage())
    service.create(
        user=User(username="hamid"),
        title="Annual report",
        description="",
        file_name="a.pdf",
        content_type="application/pdf",
        data=b"a",
    )
    service.create(
        user=User(username="sara"),
        title="Meeting notes",
        description="",
        file_name="b.txt",
        content_type="text/plain",
        data=b"b",
    )

    assert [d.title for d in service.list(DocumentCriteria(title="report"))] == [
        "Annual report"
    ]
    assert [d.title for d in service.list(DocumentCriteria(uploaded_by="sara"))] == [
        "Meeting notes"
    ]
    assert len(service.list(DocumentCriteria(content_type="text/plain"))) == 1
    assert len(service.list()) == 2


def test_compute_checksum_hashes_file_content() -> None:
    service = DocumentService(InMemoryDocumentRepository(), InMemoryDocumentStorage())
    document = service.create(
        user=None,
        title="Doc",
        description="",
        file_name="doc.txt",
        content_type="text/plain",
        data=b"body",
    )
    assert service.compute_checksum(document.pk) == hashlib.sha256(b"body").hexdigest()


def test_compute_checksum_missing_document_returns_empty() -> None:
    service = DocumentService(InMemoryDocumentRepository(), InMemoryDocumentStorage())
    assert service.compute_checksum(999) == ""
