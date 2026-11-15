"""Custom user model with an RBAC role."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    """Roles defined by the challenge: admin, editor, viewer."""

    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class User(AbstractUser):
    """Default authentication user, extended with an RBAC role."""

    role = models.CharField(
        max_length=16, choices=UserRole.choices, default=UserRole.VIEWER
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
