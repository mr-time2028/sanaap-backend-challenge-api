"""Storage seam — Protocol with MinIO (Facade + Singleton), local-filesystem,
and in-memory backends. Nothing outside this module knows MinIO.
New backends (S3, GCS, ...) = a class implementing DocumentStorage + one
entry in services.STORAGE_BACKENDS."""

from __future__ import annotations

import io
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from minio import Minio


class DocumentStorage(Protocol):
    def put(self, *, data: bytes, file_name: str, content_type: str) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


@lru_cache(maxsize=1)
def _minio_client() -> Minio:
    """Singleton client — created once per process, reused."""
    return Minio(
        os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000"),
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        secure=False,
    )


class MinioStorage:
    """Facade over MinIO."""

    def __init__(self) -> None:
        self._client = _minio_client()
        self._bucket = os.getenv("MINIO_BUCKET", "documents")

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put(self, *, data: bytes, file_name: str, content_type: str) -> str:
        self._ensure_bucket()
        key = f"{uuid.uuid4().hex}/{file_name}"
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def get(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)


class LocalStorage:
    """Local-filesystem backend — same Protocol, for STORAGE_BACKEND=local."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def put(self, *, data: bytes, file_name: str, content_type: str) -> str:
        key = f"{uuid.uuid4().hex}/{file_name}"
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return (self._root / key).read_bytes()

    def delete(self, key: str) -> None:
        (self._root / key).unlink(missing_ok=True)


class InMemoryDocumentStorage:
    """Fake for tests — zero external services."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, *, data: bytes, file_name: str, content_type: str) -> str:
        key = f"{uuid.uuid4().hex}/{file_name}"
        self._objects[key] = data
        return key

    def get(self, key: str) -> bytes:
        return self._objects[key]

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)
