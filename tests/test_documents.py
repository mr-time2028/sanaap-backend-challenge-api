"""API tests for the documents endpoints (fake storage — no MinIO needed)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from documents.repositories import DjangoDocumentRepository
from documents.services import DocumentService
from documents.storage import InMemoryDocumentStorage

CREDS = {"username": "hamid", "password": "secret123"}


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> DocumentService:
    service = DocumentService(DjangoDocumentRepository(), InMemoryDocumentStorage())
    monkeypatch.setattr("documents.views.get_document_service", lambda: service)
    return service


@pytest.fixture
def auth(api: APIClient, db: None) -> APIClient:
    User.objects.create_user(
        "hamid", "hamid@example.com", "secret123", role=UserRole.ADMIN
    )
    tokens = api.post("/api/v1/auth/login/", CREDS).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api


def upload(
    auth: APIClient, file: SimpleUploadedFile | None = None, title: str = "Doc"
) -> Response:
    if file is None:
        file = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
    return auth.post("/api/v1/documents/", {"file": file, "title": title})


def test_upload_returns_201(auth: APIClient) -> None:
    response = upload(auth)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["file_name"] == "doc.txt"


def test_upload_rejects_disallowed_type(auth: APIClient) -> None:
    response = upload(
        auth, file=SimpleUploadedFile("evil.sh", b"x", content_type="application/x-sh")
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_and_retrieve(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    assert len(auth.get("/api/v1/documents/").data) == 1
    assert auth.get(f"/api/v1/documents/{document_id}/").data["title"] == "Doc"


def test_retrieve_unknown_returns_404(auth: APIClient) -> None:
    assert auth.get("/api/v1/documents/999/").status_code == status.HTTP_404_NOT_FOUND


def test_patch_updates_metadata(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    response = auth.patch(
        f"/api/v1/documents/{document_id}/", {"title": "Renamed"}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Renamed"


def test_patch_unknown_returns_404(auth: APIClient) -> None:
    response = auth.patch("/api/v1/documents/999/", {"title": "X"}, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_rejects_disallowed_file(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    response = auth.patch(
        f"/api/v1/documents/{document_id}/",
        {"file": SimpleUploadedFile("evil.sh", b"x", content_type="application/x-sh")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_delete_removes_document(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    assert (
        auth.delete(f"/api/v1/documents/{document_id}/").status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        auth.get(f"/api/v1/documents/{document_id}/").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_delete_unknown_returns_404(auth: APIClient) -> None:
    assert (
        auth.delete("/api/v1/documents/999/").status_code == status.HTTP_404_NOT_FOUND
    )


def test_anonymous_is_rejected(api: APIClient) -> None:
    assert api.get("/api/v1/documents/").status_code == status.HTTP_401_UNAUTHORIZED
