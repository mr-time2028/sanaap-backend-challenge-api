"""Audit recorder — an Observer of document events."""

from __future__ import annotations

from accounts.models import User
from audit.models import AuditAction, AuditLog
from documents.events import DocumentEvent


class AuditObserver:
    def on_document_event(self, event: DocumentEvent) -> None:
        AuditLog.objects.create(
            action=AuditAction(event.action),
            user=event.user if isinstance(event.user, User) else None,
            document_pk=event.document_id,
            document_title=event.document_title,
            changes=event.changes,
        )
