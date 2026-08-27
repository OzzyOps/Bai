"""RBAC is defence in depth. The authoritative boundary is Postgres RLS —
`test_rls.py` asserts the policies agree with this matrix."""
from itertools import pairwise

import pytest
from bai_platform.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    PermissionDenied,
    Role,
    has_permission,
    require,
)

LADDER = [Role.VIEWER, Role.OPERATOR, Role.MANAGER, Role.ADMIN, Role.OWNER]


@pytest.mark.parametrize(("lower", "higher"), list(pairwise(LADDER)))
def test_roles_are_strictly_monotonic(lower: Role, higher: Role) -> None:
    assert ROLE_PERMISSIONS[lower] < ROLE_PERMISSIONS[higher]


class TestOperatorSeparation:
    """The load-bearing role: clears the queue without being able to change the record."""

    def test_operator_resolves_escalations(self) -> None:
        assert has_permission(Role.OPERATOR, Permission.ESCALATION_RESOLVE)

    def test_operator_cannot_update_records(self) -> None:
        assert not has_permission(Role.OPERATOR, Permission.RECORD_UPDATE)


class TestPrivilegeCeilings:
    def test_manager_cannot_manage_members(self) -> None:
        assert not has_permission(Role.MANAGER, Permission.MEMBER_MANAGE)

    def test_manager_cannot_read_all_records(self) -> None:
        assert not has_permission(Role.MANAGER, Permission.RECORD_READ_ALL)

    def test_only_owner_manages_billing(self) -> None:
        assert has_permission(Role.OWNER, Permission.BILLING_MANAGE)
        assert not has_permission(Role.ADMIN, Permission.BILLING_MANAGE)

    @pytest.mark.parametrize(
        "perm",
        [Permission.AUTONOMY_GRANT, Permission.RESTRICTION_GRANT, Permission.DSR_EXECUTE],
    )
    def test_sensitive_grants_are_admin_or_above(self, perm: Permission) -> None:
        assert has_permission(Role.ADMIN, perm)
        assert not has_permission(Role.MANAGER, perm)


class TestFailClosed:
    def test_unknown_role_denied(self) -> None:
        assert not has_permission("superuser", Permission.RECORD_READ_ALL)

    def test_unknown_permission_denied(self) -> None:
        assert not has_permission(Role.OWNER, "record:nuke")

    def test_require_raises(self) -> None:
        with pytest.raises(PermissionDenied):
            require(Role.VIEWER, Permission.RECORD_DELETE)
