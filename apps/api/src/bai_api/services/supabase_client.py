"""Supabase REST access, always as the caller.

The API forwards the user's JWT to PostgREST so every query runs under that
user's RLS policies. This is the whole isolation model: we do not filter by
org_id in Python and hope; Postgres refuses to return other tenants' rows.
"""

from __future__ import annotations

from typing import Any

import httpx
from bai_platform.i18n import Region

from bai_api.core.errors import APIError, Conflict, NotFound


class SupabaseREST:
    def __init__(self, base_url: str, anon_key: str, jwt: str, *, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/") + "/rest/v1"
        self._headers = {
            "apikey": anon_key,
            # The USER's token, not a service key. RLS applies.
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    async def _request(self, method: str, path: str, **kw: Any) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            res = await client.request(
                method, f"{self._base}{path}", headers={**self._headers, **kw.pop("headers", {})}, **kw
            )
        if res.status_code == 404:
            raise NotFound("That record does not exist, or you do not have access to it.")
        if res.status_code == 409:
            raise Conflict("That change conflicts with the current state. Nothing was changed.")
        if res.status_code >= 400:
            # PostgREST returns 42501 for an RLS denial. Present it as 404 so we
            # do not confirm the existence of another tenant's row.
            detail = res.text[:300]
            if "42501" in detail or "row-level security" in detail.lower():
                raise NotFound("That record does not exist, or you do not have access to it.")
            raise APIError(
                "The database rejected that request. Nothing was changed.",
                hint="Check the fields you supplied.",
                changed=False,
            )
        return res.json() if res.content else None

    async def select(
        self,
        table: str,
        *,
        columns: str = "*",
        order: str | None = None,
        limit: int = 50,
        offset: int = 0,
        **filters: str,
    ) -> list[dict[str, Any]]:
        params = {"select": columns, "limit": str(limit), "offset": str(offset), **filters}
        if order is not None:
            params["order"] = order
        rows = await self._request("GET", f"/{table}", params=params)
        return rows if isinstance(rows, list) else []

    async def one(self, table: str, row_id: str, *, columns: str = "*") -> dict[str, Any]:
        rows = await self.select(table, columns=columns, id=f"eq.{row_id}", limit=1)
        if not rows:
            raise NotFound("That record does not exist, or you do not have access to it.")
        return rows[0]

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self._request(
            "POST", f"/{table}", json=payload, headers={"Prefer": "return=representation"}
        )
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
        return {}

    async def update(self, table: str, row_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self._request(
            "PATCH",
            f"/{table}",
            params={"id": f"eq.{row_id}"},
            json=payload,
            headers={"Prefer": "return=representation"},
        )
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise NotFound("That record does not exist, or you do not have access to it.")
        return rows[0]


def client_for(region: Region, jwt: str) -> SupabaseREST:
    from bai_api.config import get_settings

    s = get_settings()
    return SupabaseREST(
        s.url_for(region), s.anon_key_for(region), jwt, timeout=s.request_timeout_seconds
    )
