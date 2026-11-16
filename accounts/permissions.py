"""Custom DRF permissions."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import UserRole


class IsAdminRole(BasePermission):
    """Allow only users with the admin role."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        # getattr keeps this safe for anonymous users (no role attribute).
        return bool(
            user.is_authenticated and getattr(user, "role", None) == UserRole.ADMIN
        )
