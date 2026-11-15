"""Document metadata model (the file bytes live in object storage)."""

from django.conf import settings
from django.db import models


class Document(models.Model):
    """A stored document: metadata in the database, file in object storage."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file_key = models.CharField(
        max_length=512, help_text="Object-storage key of the file."
    )
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField(default=0, help_text="File size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
