"""Tests for the RBAC role policies (Strategy)."""

import pytest

from accounts.models import User, UserRole
from documents.policies import RolePolicy, get_role_policy


def policy_for(role: UserRole) -> RolePolicy:
    return get_role_policy(User(username="u", role=role))


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.ADMIN, (True, True, True, True)),
        (UserRole.EDITOR, (True, True, False, True)),
        (UserRole.VIEWER, (False, False, False, True)),
    ],
)
def test_role_matrix(role: UserRole, expected: tuple[bool, bool, bool, bool]) -> None:
    policy = policy_for(role)
    assert (
        policy.can_upload(),
        policy.can_update(),
        policy.can_delete(),
        policy.can_download(),
    ) == expected


def test_unknown_role_falls_back_to_most_restrictive() -> None:
    user = User(username="mystery")
    user.role = "root"  # a role missing from POLICIES
    policy = get_role_policy(user)
    assert not policy.can_upload()
    assert not policy.can_delete()
    assert policy.can_download()
