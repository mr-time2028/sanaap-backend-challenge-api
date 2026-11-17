"""API tests for the documents endpoints (fake storage — no MinIO needed)."""

import hashlib
from datetime import date, timedelta

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
    monkeypatch.setattr("documents.tasks.get_document_service", lambda: service)
    return service


def auth_as(api: APIClient, role: UserRole) -> APIClient:
    User.objects.create_user("hamid", "hamid@example.com", "secret123", role=role)
    tokens = api.post("/api/v1/auth/login/", CREDS).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api


@pytest.fixture
def auth(api: APIClient, db: None) -> APIClient:
    return auth_as(api, UserRole.ADMIN)


@pytest.fixture
def editor(api: APIClient, db: None) -> APIClient:
    return auth_as(api, UserRole.EDITOR)


@pytest.fixture
def viewer(api: APIClient, db: None) -> APIClient:
    return auth_as(api, UserRole.VIEWER)


def upload(
    auth: APIClient, file: SimpleUploadedFile | None = None, title: str = "Doc"
) -> Response:
    if file is None:
        file = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
    return auth.post("/api/v1/documents/", {"file": file, "title": title})


def seed_document(
    service: DocumentService,
    *,
    title: str = "Doc",
    content_type: str = "text/plain",
    data: bytes = b"hello",
) -> int:
    owner = User.objects.get(username="hamid")
    document = service.create(
        user=owner,
        title=title,
        description="",
        file_name="doc.txt",
        content_type=content_type,
        data=data,
    )
    return document.pk


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
    assert len(auth.get("/api/v1/documents/").data["results"]) == 1
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


def test_viewer_can_list_and_download(
    viewer: APIClient, fake_storage: DocumentService
) -> None:
    document_id = seed_document(fake_storage)
    assert viewer.get("/api/v1/documents/").status_code == status.HTTP_200_OK
    response = viewer.get(f"/api/v1/documents/{document_id}/download/")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"hello"


def test_viewer_cannot_upload(viewer: APIClient) -> None:
    assert upload(viewer).status_code == status.HTTP_403_FORBIDDEN


def test_viewer_cannot_delete(viewer: APIClient, fake_storage: DocumentService) -> None:
    document_id = seed_document(fake_storage)
    assert (
        viewer.delete(f"/api/v1/documents/{document_id}/").status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_editor_can_upload_and_update(editor: APIClient) -> None:
    document_id = upload(editor).data["id"]
    response = editor.patch(
        f"/api/v1/documents/{document_id}/", {"title": "Renamed"}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK


def test_editor_cannot_delete(editor: APIClient, fake_storage: DocumentService) -> None:
    document_id = seed_document(fake_storage)
    assert (
        editor.delete(f"/api/v1/documents/{document_id}/").status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_url_endpoint_returns_presigned_url(
    viewer: APIClient, fake_storage: DocumentService
) -> None:
    document_id = seed_document(fake_storage)
    response = viewer.get(f"/api/v1/documents/{document_id}/url/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["url"].startswith("memory://")
    assert response.data["expires_in"] == 3600


def test_url_unknown_returns_404(viewer: APIClient) -> None:
    assert (
        viewer.get("/api/v1/documents/999/url/").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_download_unknown_returns_404(viewer: APIClient) -> None:
    assert (
        viewer.get("/api/v1/documents/999/download/").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_filter_by_title(auth: APIClient, fake_storage: DocumentService) -> None:
    seed_document(fake_storage, title="Annual report")
    seed_document(fake_storage, title="Meeting notes")
    response = auth.get("/api/v1/documents/?title=report")
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Annual report"


def test_filter_by_content_type(auth: APIClient, fake_storage: DocumentService) -> None:
    seed_document(fake_storage, title="A", content_type="application/pdf", data=b"%PDF")
    seed_document(fake_storage, title="B", content_type="text/plain")
    response = auth.get("/api/v1/documents/?content_type=text/plain")
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "B"


def test_filter_by_uploaded_by(auth: APIClient, fake_storage: DocumentService) -> None:
    seed_document(fake_storage)
    assert auth.get("/api/v1/documents/?uploaded_by=hamid").data["count"] == 1
    assert auth.get("/api/v1/documents/?uploaded_by=nobody").data["count"] == 0


def test_filter_by_created_date(auth: APIClient, fake_storage: DocumentService) -> None:
    seed_document(fake_storage)
    past = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=1)).isoformat()
    assert auth.get(f"/api/v1/documents/?created_after={past}").data["count"] == 1
    assert auth.get(f"/api/v1/documents/?created_after={future}").data["count"] == 0
    assert auth.get(f"/api/v1/documents/?created_before={today}").data["count"] == 1
    assert auth.get(f"/api/v1/documents/?created_before={past}").data["count"] == 0


def test_invalid_date_filter_returns_400(auth: APIClient) -> None:
    assert (
        auth.get("/api/v1/documents/?created_after=notadate").status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_pagination_shape_and_pages(
    auth: APIClient, fake_storage: DocumentService
) -> None:
    for i in range(3):
        seed_document(fake_storage, title=f"Doc {i}")
    response = auth.get("/api/v1/documents/?page=1&page_size=2")
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2
    assert response.data["next"] is not None
    assert response.data["previous"] is None
    page2 = auth.get("/api/v1/documents/?page=2&page_size=2")
    assert len(page2.data["results"]) == 1
    assert page2.data["next"] is None


def test_page_size_defaults_to_ten(
    auth: APIClient, fake_storage: DocumentService
) -> None:
    for i in range(12):
        seed_document(fake_storage, title=f"Doc {i}")
    response = auth.get("/api/v1/documents/")
    assert len(response.data["results"]) == 10
    assert response.data["count"] == 12


def test_upload_triggers_background_checksum(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    document = auth.get(f"/api/v1/documents/{document_id}/").data
    assert document["checksum"] == hashlib.sha256(b"hello").hexdigest()


def test_file_replacement_recomputes_checksum(auth: APIClient) -> None:
    document_id = upload(auth).data["id"]
    auth.patch(
        f"/api/v1/documents/{document_id}/",
        {"file": SimpleUploadedFile("new.txt", b"v2", content_type="text/plain")},
    )
    document = auth.get(f"/api/v1/documents/{document_id}/").data
    assert document["checksum"] == hashlib.sha256(b"v2").hexdigest()
