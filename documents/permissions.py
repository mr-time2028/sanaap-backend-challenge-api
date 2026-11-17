"""DRF adapter for the role policies — maps HTTP methods to policy checks."""

from __future__ import annotations

from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from documents.policies import get_role_policy


class DocumentPermission(BasePermission):
    message = "Your role does not allow this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        policy = get_role_policy(cast(User, user))
        if request.method == "POST":
            return policy.can_upload()
        if request.method in ("PUT", "PATCH"):
            return policy.can_update()
        if request.method == "DELETE":
            return policy.can_delete()
        return policy.can_download()  # GET / HEAD / OPTIONS
