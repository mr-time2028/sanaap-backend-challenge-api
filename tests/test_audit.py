"""Tests for the audit trail (Observer -> AuditLog)."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from audit.models import AuditAction, AuditLog
from audit.observer import AuditObserver
from documents.models import Document
from documents.repositories import DjangoDocumentRepository, InMemoryDocumentRepository
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


CREDS = {"username": "hamid", "password": "secret123"}


def auth_as(api: APIClient, role: UserRole) -> APIClient:
    User.objects.create_user("hamid", "hamid@example.com", "secret123", role=role)
    tokens = api.post("/api/v1/auth/login/", CREDS).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api


@pytest.fixture
def admin_api(api: APIClient, db: None) -> APIClient:
    return auth_as(api, UserRole.ADMIN)


@pytest.fixture
def audited_api(monkeypatch: pytest.MonkeyPatch) -> DocumentService:
    service = DocumentService(
        DjangoDocumentRepository(),
        InMemoryDocumentStorage(),
        observers=[AuditObserver()],
    )
    monkeypatch.setattr("documents.views.get_document_service", lambda: service)
    monkeypatch.setattr("documents.tasks.get_document_service", lambda: service)
    return service


def test_admin_can_read_audit_log(admin_api: APIClient) -> None:
    assert admin_api.get("/api/v1/audit-logs/").status_code == status.HTTP_200_OK


def test_editor_cannot_read_audit_log(api: APIClient, db: None) -> None:
    client = auth_as(api, UserRole.EDITOR)
    assert client.get("/api/v1/audit-logs/").status_code == status.HTTP_403_FORBIDDEN


def test_anonymous_cannot_read_audit_log(api: APIClient) -> None:
    assert api.get("/api/v1/audit-logs/").status_code == status.HTTP_401_UNAUTHORIZED


def test_document_changes_are_recorded_end_to_end(
    admin_api: APIClient, audited_api: DocumentService
) -> None:
    admin_api.post(
        "/api/v1/documents/",
        {
            "file": SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain"),
            "title": "Doc",
        },
    )
    response = admin_api.get("/api/v1/audit-logs/")
    assert response.data["count"] == 1
    entry = response.data["results"][0]
    assert entry["action"] == "created"
    assert entry["username"] == "hamid"
    assert entry["document_title"] == "Doc"
