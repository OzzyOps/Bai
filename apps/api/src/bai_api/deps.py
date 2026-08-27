"""Request dependencies: authentication, tenant context, permission checks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from bai_platform.i18n import Region
from bai_platform.rbac import Permission, has_permission
from bai_platform.tenancy import InvalidToken, TenantContext, decode_claims
from fastapi import Depends, Header

from bai_api.core.errors import Forbidden, NotAuthenticated
from bai_api.services.supabase_client import SupabaseREST, client_for


async def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotAuthenticated(
            "You are not signed in.",
            hint="Send an Authorization: Bearer <token> header.",
        )
    return authorization.split(" ", 1)[1].strip()


async def tenant(token: Annotated[str, Depends(bearer_token)]) -> TenantContext:
    """Resolve the caller.

    Claims are read unverified here — Supabase verified the signature at the
    edge, and Postgres verifies it again via auth.jwt() on every query. The org
    row is then read UNDER RLS, so a forged org_id claim cannot widen access:
    the read simply returns nothing.
    """
    try:
        claims = decode_claims(token)
        region = Region(claims.get("region", "eu"))
    except (InvalidToken, ValueError) as exc:
        raise NotAuthenticated("Your session token is not valid.", hint="Sign in again.") from exc

    rest = client_for(region, token)
    rows = await rest.select("orgs", limit=1)
    if not rows:
        raise NotAuthenticated("Your session is not attached to an organisation.")

    try:
        return TenantContext.from_claims(claims, org_row=rows[0])
    except InvalidToken as exc:
        raise NotAuthenticated(str(exc), hint="Sign in again.") from exc


async def db(
    ctx: Annotated[TenantContext, Depends(tenant)],
    token: Annotated[str, Depends(bearer_token)],
) -> SupabaseREST:
    return client_for(ctx.region, token)


def require(
    permission: Permission,
) -> Callable[[TenantContext], Awaitable[TenantContext]]:
    """Route guard. Defence in depth — RLS is the authoritative boundary."""

    async def guard(ctx: Annotated[TenantContext, Depends(tenant)]) -> TenantContext:
        if not has_permission(ctx.role, permission):
            raise Forbidden(
                f"Your role ({ctx.role.value}) cannot do that.",
                hint="An owner or admin can change your role in Settings → Members.",
            )
        return ctx

    return guard


Tenant = Annotated[TenantContext, Depends(tenant)]
DB = Annotated[SupabaseREST, Depends(db)]
