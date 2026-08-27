"""Tenant context resolution.

Application code never chooses a tenant. It receives one, resolved from the
caller's JWT, and passes it down. The authoritative isolation boundary is the
RLS policy in Postgres; this module exists so the application can *fail early*
and *log correctly*, not so it can decide who sees what.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from bai_platform.i18n import Region, TenantLocale
from bai_platform.rbac import Role

__all__ = ["InvalidToken", "TenantContext", "decode_claims"]


class InvalidToken(ValueError):
    """The JWT is malformed or missing required claims."""


def _b64url(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def decode_claims(jwt: str) -> dict[str, Any]:
    """Read claims WITHOUT verifying the signature.

    Verification happens at the edge (Supabase Auth / API gateway) and again in
    Postgres via ``auth.jwt()``. This helper is for populating request context
    and logs only — never for an authorisation decision.
    """
    try:
        _, payload, _ = jwt.split(".")
        claims = json.loads(_b64url(payload))
    except Exception as exc:
        raise InvalidToken("token is not a well-formed JWT") from exc
    if not isinstance(claims, dict):
        raise InvalidToken("token payload is not an object")
    return claims


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Everything downstream code may know about who is calling."""

    org_id: UUID
    user_id: UUID
    role: Role
    locale: TenantLocale
    tier: str = "growth"

    @classmethod
    def from_claims(cls, claims: dict[str, Any], *, org_row: dict[str, Any]) -> TenantContext:
        """Build from JWT claims plus the org row read under RLS.

        ``org_row`` supplies locale, currency and region — never the JWT, because
        those change without the token being reissued.
        """
        for required in ("sub", "org_id", "role"):
            if not claims.get(required):
                raise InvalidToken(f"token is missing the {required!r} claim")

        if str(org_row["id"]) != str(claims["org_id"]):
            # A token pointing at a different org than the row we just read means
            # something upstream is broken. Fail closed and loudly.
            raise InvalidToken("token org_id does not match the org record")

        try:
            role = Role(claims["role"])
        except ValueError as exc:
            raise InvalidToken(f"unknown role {claims['role']!r}") from exc

        return cls(
            org_id=UUID(str(claims["org_id"])),
            user_id=UUID(str(claims["sub"])),
            role=role,
            tier=str(claims.get("tier", "growth")),
            locale=TenantLocale(
                region=Region(org_row["region"]),
                locale=org_row["locale"],
                currency=org_row["currency"],
                timezone=org_row.get("timezone", "UTC"),
                jurisdictions=tuple(org_row.get("jurisdictions") or ()),
            ),
        )

    @property
    def region(self) -> Region:
        return self.locale.region

    def log_fields(self) -> dict[str, str]:
        """Safe to emit. Contains no customer content and no personal data."""
        return {
            "org_id": str(self.org_id),
            "user_id": str(self.user_id),
            "role": self.role.value,
            "region": self.region.value,
            "tier": self.tier,
        }
