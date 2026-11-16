"""Upload validation rules — safe file types only, bounded size."""

from __future__ import annotations

from django.core.exceptions import ValidationError

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_upload(*, file_name: str, content_type: str, size: int) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"Content type {content_type!r} is not allowed.")
    if size > MAX_UPLOAD_SIZE:
        raise ValidationError("File exceeds the 10 MB limit.")
    if not file_name or "/" in file_name or "\\" in file_name:
        raise ValidationError("Invalid file name.")
