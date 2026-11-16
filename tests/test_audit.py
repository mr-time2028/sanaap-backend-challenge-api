"""Tests for the audit trail (Observer -> AuditLog)."""

from __future__ import annotations

import pytest

from accounts.models import User
from audit.models import AuditAction, AuditLog
from audit.observer import AuditObserver
from documents.models import Document
from documents.repositories import InMemoryDocumentRepository
from documents.services import DocumentService
from documents.storage import InMemoryDocumentStorage


@pytest.fixture
def service() -> DocumentService:
    return DocumentService(
        InMemoryDocumentRepository(),
        InMemoryDocumentStorage(),
        observers=[AuditObserver()],
    )


def create_doc(service: DocumentService, user: User | None = None) -> Document:
    return service.create(
        user=user,
        title="Doc",
        description="",
        file_name="doc.txt",
        content_type="text/plain",
        data=b"body",
    )


def test_created_is_recorded(db: None, service: DocumentService) -> None:
    user = User.objects.create_user("hamid", "hamid@example.com", "secret123")
    document = create_doc(service, user)
    log = AuditLog.objects.get()
    assert log.action == AuditAction.CREATED
    assert log.user == user
    assert log.document_pk == document.pk
    assert log.document_title == "Doc"


def test_delete_keeps_snapshot(db: None, service: DocumentService) -> None:
    user = User.objects.create_user("hamid", "hamid@example.com", "secret123")
    document = create_doc(service, user)
    document_id = document.pk
    service.delete(document, user=user)
    log = AuditLog.objects.filter(action=AuditAction.DELETED).get()
    assert log.document_pk == document_id
    assert log.document_title == "Doc"


def test_update_records_diff(db: None, service: DocumentService) -> None:
    user = User.objects.create_user("hamid", "hamid@example.com", "secret123")
    document = create_doc(service, user)
    service.update(document, title="New", user=user)
    log = AuditLog.objects.filter(action=AuditAction.UPDATED).get()
    assert log.changes["title"] == {"old": "Doc", "new": "New"}


def test_user_is_optional(db: None, service: DocumentService) -> None:
    create_doc(service, None)
    assert AuditLog.objects.get().user is None
