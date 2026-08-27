from __future__ import annotations

from typing import Annotated
from uuid import UUID

from bai_platform.audit import AuditAction
from bai_platform.rbac import Permission
from fastapi import APIRouter, Depends, Query

from bai_api.deps import DB, Tenant, require
from bai_api.schemas import FactOut, RecordCreate, RecordOut

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
async def list_records(
    db: DB,
    ctx: Tenant,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    product: str | None = None,
) -> list[RecordOut]:
    """List records the caller may see.

    No org_id filter is applied here on purpose — RLS scopes the result. Adding
    one in Python would imply the isolation lives in this file, and it does not.
    """
    filters = {"product": f"eq.{product}"} if product else {}
    rows = await db.select("records", limit=limit, offset=offset, order="created_at.desc", **filters)
    return [RecordOut.from_row(r) for r in rows]


@router.post("", response_model=RecordOut, status_code=201)
async def create_record(
    payload: RecordCreate,
    db: DB,
    ctx: Annotated[object, Depends(require(Permission.RECORD_CREATE))],
) -> RecordOut:
    row = await db.insert(
        "records",
        {
            "org_id": str(ctx.org_id),  # type: ignore[attr-defined]
            "product": payload.product,
            "title": payload.title,
            "external_ref": payload.external_ref,
            "value_minor": payload.value_minor,
            "value_currency": payload.value_currency,
        },
    )
    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),  # type: ignore[attr-defined]
        "action": AuditAction.RECORD_CREATED.value,
        "actor_id": str(ctx.user_id),  # type: ignore[attr-defined]
        "subject_type": "record",
        "subject_id": row["id"],
        "metadata": {"product": payload.product},
    })
    return RecordOut.from_row(row)


@router.get("/{record_id}", response_model=RecordOut)
async def get_record(record_id: UUID, db: DB, ctx: Tenant) -> RecordOut:
    row = await db.one("records", str(record_id))
    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),
        "action": AuditAction.RECORD_VIEWED.value,
        "actor_id": str(ctx.user_id),
        "subject_type": "record",
        "subject_id": str(record_id),
        "metadata": {},
    })
    return RecordOut.from_row(row)


@router.get("/{record_id}/facts", response_model=list[FactOut])
async def record_facts(record_id: UUID, db: DB, ctx: Tenant) -> list[FactOut]:
    """Facts with their citations. Low-confidence facts are returned with
    display_state 'unknown' so the client cannot render them as findings."""
    rows = await db.select(
        "agent_facts", record_id=f"eq.{record_id}", order="confidence.desc", limit=200
    )
    return [FactOut.from_row(r) for r in rows]
