"""Celery tasks — thin adapters around DocumentService."""

from __future__ import annotations

from celery import shared_task

from documents.services import get_document_service


@shared_task
def process_document(document_id: int) -> str:
    """Background pipeline for a stored file — checksum today, thumbnails/AV later."""
    return get_document_service().compute_checksum(document_id)
