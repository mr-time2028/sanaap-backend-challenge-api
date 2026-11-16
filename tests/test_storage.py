"""Tests for the storage seam: fakes, local backend, MinIO facade with a fake client."""

import io
from pathlib import Path

import pytest

from documents.storage import InMemoryDocumentStorage, LocalStorage, MinioStorage


def test_fake_put_get_roundtrip() -> None:
    storage = InMemoryDocumentStorage()
    key = storage.put(data=b"hello", file_name="a.txt", content_type="text/plain")
    assert storage.get(key) == b"hello"


def test_fake_keys_are_unique() -> None:
    storage = InMemoryDocumentStorage()
    first = storage.put(data=b"x", file_name="a.txt", content_type="text/plain")
    second = storage.put(data=b"x", file_name="a.txt", content_type="text/plain")
    assert first != second


def test_fake_delete_removes_object() -> None:
    storage = InMemoryDocumentStorage()
    key = storage.put(data=b"x", file_name="a.txt", content_type="text/plain")
    storage.delete(key)
    with pytest.raises(KeyError):
        storage.get(key)


def test_local_storage_roundtrip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    key = storage.put(data=b"hello", file_name="a.txt", content_type="text/plain")
    assert storage.get(key) == b"hello"
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.get(key)


class FakeResponse:
    """Stands in for the urllib3 response returned by Minio.get_object."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeMinio:
    """Duck-typed stand-in for minio.Minio — records calls, stores objects."""

    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.removed: list[tuple[str, str]] = []
        self.responses: list[FakeResponse] = []

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(
        self, bucket: str, key: str, stream: io.BytesIO, length: int, content_type: str
    ) -> None:
        self.objects[(bucket, key)] = stream.read()

    def get_object(self, bucket: str, key: str) -> FakeResponse:
        response = FakeResponse(self.objects[(bucket, key)])
        self.responses.append(response)
        return response

    def remove_object(self, bucket: str, key: str) -> None:
        self.removed.append((bucket, key))
        self.objects.pop((bucket, key), None)


@pytest.fixture
def minio_storage(monkeypatch: pytest.MonkeyPatch) -> tuple[MinioStorage, FakeMinio]:
    fake = FakeMinio()
    monkeypatch.setattr("documents.storage._minio_client", lambda: fake)
    monkeypatch.setenv("MINIO_BUCKET", "documents")
    return MinioStorage(), fake


def test_minio_put_creates_bucket_and_key(
    minio_storage: tuple[MinioStorage, FakeMinio],
) -> None:
    storage, fake = minio_storage
    key = storage.put(data=b"payload", file_name="a.txt", content_type="text/plain")
    assert fake.buckets == {"documents"}
    assert key.endswith("/a.txt")
    assert fake.objects[("documents", key)] == b"payload"


def test_minio_keys_are_unique(minio_storage: tuple[MinioStorage, FakeMinio]) -> None:
    storage, _ = minio_storage
    first = storage.put(data=b"x", file_name="a.txt", content_type="text/plain")
    second = storage.put(data=b"x", file_name="a.txt", content_type="text/plain")
    assert first != second


def test_minio_get_reads_and_releases(
    minio_storage: tuple[MinioStorage, FakeMinio],
) -> None:
    storage, fake = minio_storage
    key = storage.put(data=b"payload", file_name="a.txt", content_type="text/plain")
    assert storage.get(key) == b"payload"
    response = fake.responses[0]
    assert response.closed and response.released


def test_minio_delete_removes_object(
    minio_storage: tuple[MinioStorage, FakeMinio],
) -> None:
    storage, fake = minio_storage
    key = storage.put(data=b"payload", file_name="a.txt", content_type="text/plain")
    storage.delete(key)
    assert fake.removed == [("documents", key)]
