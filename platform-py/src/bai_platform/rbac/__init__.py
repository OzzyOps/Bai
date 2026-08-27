"""RBAC for BAi. Five roles, defined once at platform level.

Products may add *permissions*; they may never add *roles*. This module is the
single source of truth, and the SQL policies in supabase/migrations must be kept
in lockstep with it — `tests/test_rbac_parity.py` asserts they agree.

Application-layer checks here are defence in depth. The authoritative boundary is
Postgres RLS. Never rely on this module alone for tenant isolation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = ["ROLE_PERMISSIONS", "Permission", "PermissionDenied", "Role", "has_permission"]


class PermissionDenied(PermissionError):
    """Raised when a caller lacks the required permission."""


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(StrEnum):
    # records
    RECORD_READ_ALL = "record:read:all"
    RECORD_READ_ASSIGNED = "record:read:assigned"
    RECORD_CREATE = "record:create"
    RECORD_UPDATE = "record:update"
    RECORD_DELETE = "record:delete"
    # documents
    DOCUMENT_READ = "document:read"
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    # agent runs
    RUN_READ = "run:read"
    RUN_START = "run:start"
    RUN_CANCEL = "run:cancel"
    # escalations — the queue that makes the product economics work
    ESCALATION_READ = "escalation:read"
    ESCALATION_RESOLVE = "escalation:resolve"
    # autonomy grants — separated from resolve on purpose
    AUTONOMY_GRANT = "autonomy:grant"
    # org
    MEMBER_MANAGE = "member:manage"
    BILLING_MANAGE = "billing:manage"
    AUDIT_READ = "audit:read"
    # restricted records
    RESTRICTION_GRANT = "restriction:grant"
    # data subject requests
    DSR_EXECUTE = "dsr:execute"


_VIEWER: Final[frozenset[Permission]] = frozenset({
    Permission.RECORD_READ_ASSIGNED,
    Permission.DOCUMENT_READ,
    Permission.RUN_READ,
    Permission.ESCALATION_READ,
})

# The load-bearing role: clears the exception queue without being able to
# change the record. That separation is what makes the queue delegable — and
# delegability is what makes the automation economically worthwhile.
_OPERATOR: Final[frozenset[Permission]] = _VIEWER | {
    Permission.RUN_START,
    Permission.ESCALATION_RESOLVE,
}

_MANAGER: Final[frozenset[Permission]] = _OPERATOR | {
    Permission.RECORD_CREATE,
    Permission.RECORD_UPDATE,
    Permission.DOCUMENT_CREATE,
    Permission.DOCUMENT_UPDATE,
    Permission.RUN_CANCEL,
}

_ADMIN: Final[frozenset[Permission]] = _MANAGER | {
    Permission.RECORD_READ_ALL,
    Permission.RECORD_DELETE,
    Permission.DOCUMENT_DELETE,
    Permission.MEMBER_MANAGE,
    Permission.AUDIT_READ,
    Permission.AUTONOMY_GRANT,
    Permission.RESTRICTION_GRANT,
    Permission.DSR_EXECUTE,
}

_OWNER: Final[frozenset[Permission]] = _ADMIN | {Permission.BILLING_MANAGE}

ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.VIEWER: _VIEWER,
    Role.OPERATOR: _OPERATOR,
    Role.MANAGER: _MANAGER,
    Role.ADMIN: _ADMIN,
    Role.OWNER: _OWNER,
}


def has_permission(role: Role | str, permission: Permission | str) -> bool:
    try:
        r = Role(role)
        p = Permission(permission)
    except ValueError:
        return False
    return p in ROLE_PERMISSIONS[r]


def require(role: Role | str, permission: Permission | str) -> None:
    """Raise unless the role holds the permission. Defence in depth only."""
    if not has_permission(role, permission):
        raise PermissionDenied(f"role {role!r} lacks {permission!r}")
