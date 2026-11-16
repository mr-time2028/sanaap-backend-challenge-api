"""Permissions for the audit trail — admins only."""

from __future__ import annotations

from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User, UserRole


class AuditLogPermission(BasePermission):
    message = "Only administrators can view the audit log."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user.is_authenticated and cast(User, user).role == UserRole.ADMIN)
