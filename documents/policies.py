"""Role policies for document actions — the Strategy.

One policy class per role; the matrix lives in one place. New rules (e.g.
"editors may only edit their own documents") = one method change here.
"""

from __future__ import annotations

from typing import Protocol

from accounts.models import User, UserRole


class RolePolicy(Protocol):
    def can_upload(self) -> bool: ...
    def can_update(self) -> bool: ...
    def can_delete(self) -> bool: ...
    def can_download(self) -> bool: ...


class AdminPolicy:
    def can_upload(self) -> bool:
        return True

    def can_update(self) -> bool:
        return True

    def can_delete(self) -> bool:
        return True

    def can_download(self) -> bool:
        return True


class EditorPolicy:
    def can_upload(self) -> bool:
        return True

    def can_update(self) -> bool:
        return True

    def can_delete(self) -> bool:
        return False

    def can_download(self) -> bool:
        return True


class ViewerPolicy:
    def can_upload(self) -> bool:
        return False

    def can_update(self) -> bool:
        return False

    def can_delete(self) -> bool:
        return False

    def can_download(self) -> bool:
        return True


POLICIES: dict[str, RolePolicy] = {
    UserRole.ADMIN: AdminPolicy(),
    UserRole.EDITOR: EditorPolicy(),
    UserRole.VIEWER: ViewerPolicy(),
}


def get_role_policy(user: User) -> RolePolicy:
    """Fail closed: a role missing from the matrix gets the most restrictive policy."""
    return POLICIES.get(user.role, ViewerPolicy())
