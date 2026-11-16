"""Audit trail — who changed what, and when."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATED = "created", "Document created"
    UPDATED = "updated", "Document updated"
    DELETED = "deleted", "Document deleted"


class AuditLog(models.Model):
    action = models.CharField(max_length=16, choices=AuditAction.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    document_pk = models.IntegerField()  # snapshot — survives document deletion
    document_title = models.CharField(max_length=255)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} · {self.document_title}"
