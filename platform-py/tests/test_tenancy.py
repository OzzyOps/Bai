"""Tenant context resolution.

This module had no tests at all, which is the wrong place to have none: every
RLS policy in the database derives org_id from the same JWT this code reads, so
a disagreement between the two is exactly the bug that leaks one tenant's data
into another's session. The tests below pin the fail-closed behaviour.
"""

from __future__ import annotations

import base64
import json
from uuid import UUID

import pytest
from bai_platform.i18n import Region, TenantLocale
from bai_platform.rbac import Role
from bai_platform.tenancy import InvalidToken, TenantContext, decode_claims

ORG = "00000000-0000-0000-0000-0000000000a1"
USER = "00000000-0000-0000-0000-00000000a001"


def make_jwt(claims: dict[str, object]) -> str:
    """A structurally valid, deliberately unsigned token."""

    def seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'none'})}.{seg(claims)}.signature"


ORG_ROW = {
    "id": ORG,
    "region": "eu",
    "locale": "de-DE",
    "currency": "EUR",
    "timezone": "Europe/Berlin",
    "jurisdictions": ["DE", "AT"],
}


def test_decode_reads_claims_without_verifying() -> None:
    claims = decode_claims(make_jwt({"sub": USER, "org_id": ORG, "role": "admin"}))
    assert claims["org_id"] == ORG


@pytest.mark.parametrize(
    "token",
    ["", "not-a-jwt", "only.two", "a.!!!notbase64!!!.c"],
)
def test_malformed_tokens_are_rejected(token: str) -> None:
    with pytest.raises(InvalidToken):
        decode_claims(token)


def test_a_payload_that_is_not_an_object_is_rejected() -> None:
    seg = base64.urlsafe_b64encode(b"[1,2,3]").decode().rstrip("=")
    with pytest.raises(InvalidToken):
        decode_claims(f"aGVhZGVy.{seg}.sig")


def test_context_is_built_from_claims_plus_the_org_row() -> None:
    ctx = TenantContext.from_claims(
        {"sub": USER, "org_id": ORG, "role": "manager", "tier": "scale"},
        org_row=ORG_ROW,
    )
    assert ctx.org_id == UUID(ORG)
    assert ctx.user_id == UUID(USER)
    assert ctx.role is Role.MANAGER
    assert ctx.tier == "scale"
    assert ctx.region is Region.EU
    assert ctx.locale.currency == "EUR"
    assert ctx.locale.jurisdictions == ("DE", "AT")


@pytest.mark.parametrize("missing", ["sub", "org_id", "role"])
def test_a_missing_required_claim_fails_closed(missing: str) -> None:
    claims: dict[str, object] = {"sub": USER, "org_id": ORG, "role": "admin"}
    del claims[missing]
    with pytest.raises(InvalidToken, match=missing):
        TenantContext.from_claims(claims, org_row=ORG_ROW)


def test_a_token_pointing_at_another_org_is_refused() -> None:
    """The single most important assertion in this file.

    If the token says org B and the row we read says org A, something upstream
    is broken and continuing would attribute one tenant's request to another.
    """
    other = dict(ORG_ROW, id="00000000-0000-0000-0000-0000000000b1")
    with pytest.raises(InvalidToken, match="does not match"):
        TenantContext.from_claims(
            {"sub": USER, "org_id": ORG, "role": "admin"}, org_row=other
        )


def test_an_unknown_role_is_refused_rather_than_defaulted() -> None:
    with pytest.raises(InvalidToken, match="unknown role"):
        TenantContext.from_claims(
            {"sub": USER, "org_id": ORG, "role": "superuser"}, org_row=ORG_ROW
        )


def test_log_fields_carry_no_customer_content() -> None:
    ctx = TenantContext.from_claims(
        {"sub": USER, "org_id": ORG, "role": "viewer"}, org_row=ORG_ROW
    )
    fields = ctx.log_fields()
    assert set(fields) == {"org_id", "user_id", "role", "region", "tier"}
    # No email, no name, no document text — nothing that would make a log a
    # personal-data store.
    assert all(isinstance(v, str) for v in fields.values())


def test_locale_and_currency_are_independent() -> None:
    """A Brazilian tenant may hold USD. Deriving one from the other is the bug."""
    loc = TenantLocale(region=Region.BR, locale="pt-BR", currency="USD", timezone="America/Sao_Paulo")
    assert loc.currency == "USD"
    assert loc.residency == "BRA"


@pytest.mark.parametrize(
    ("locale", "currency"),
    [("de", "EUR"), ("de-DE", "EURO"), ("de-DE", "EU")],
)
def test_malformed_locale_or_currency_is_refused(locale: str, currency: str) -> None:
    with pytest.raises(ValueError):
        TenantLocale(region=Region.EU, locale=locale, currency=currency, timezone="UTC")


def test_every_region_has_an_endpoint_and_a_residency() -> None:
    """A region with no endpoint would silently fall back to another region's
    database, which is the one thing physical isolation exists to prevent."""
    from bai_platform.i18n import REGION_ENDPOINTS

    for region in Region:
        entry = REGION_ENDPOINTS[region]
        assert entry["supabase_env"] and entry["fly_region"] and entry["residency"]

    # Each region points at its own project and its own Fly region.
    assert len({e["supabase_env"] for e in REGION_ENDPOINTS.values()}) == len(Region)
    assert len({e["fly_region"] for e in REGION_ENDPOINTS.values()}) == len(Region)
