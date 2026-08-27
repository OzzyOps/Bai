from __future__ import annotations

from typing import Annotated
from uuid import UUID

from bai_platform.audit import AuditAction
from bai_platform.rbac import Permission
from fastapi import APIRouter, Depends, Query

from bai_api.deps import DB, Tenant, require
from bai_api.schemas import RunOut, RunStart

router = APIRouter(prefix="/runs", tags=["agent runs"])


@router.get("", response_model=list[RunOut])
async def list_runs(
    db: DB,
    ctx: Tenant,
    record_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[RunOut]:
    # Passed explicitly rather than as **filters: unpacking an untyped dict into
    # a call that also takes `limit` lets a stray key silently override it.
    if record_id is None:
        rows = await db.select("agent_runs", order="started_at.desc", limit=limit)
    else:
        rows = await db.select(
            "agent_runs", order="started_at.desc", limit=limit, record_id=f"eq.{record_id}"
        )
    return [RunOut.from_row(r) for r in rows]


@router.post("", response_model=RunOut, status_code=202)
async def start_run(
    payload: RunStart,
    db: DB,
    ctx: Annotated[object, Depends(require(Permission.RUN_START))],
) -> RunOut:
    """Queue a run. Returns 202 — the work happens in a worker, not here.

    Analysis takes minutes. Doing it in a request would tie up a connection and
    lose the work on any restart; `agent_runs` is the durable record instead.
    """
    row = await db.insert("agent_runs", {
        "org_id": str(ctx.org_id),          # type: ignore[attr-defined]
        "record_id": str(payload.record_id),
        "product": "reconcile",
        "agent": payload.agent,
        "state": "pending",
        "started_by": str(ctx.user_id),     # type: ignore[attr-defined]
    })
    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),          # type: ignore[attr-defined]
        "action": AuditAction.RUN_STARTED.value,
        "actor_id": str(ctx.user_id),       # type: ignore[attr-defined]
        "subject_type": "agent_run",
        "subject_id": row["id"],
        "metadata": {"agent": payload.agent},
    })
    return RunOut.from_row(row)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: UUID, db: DB, ctx: Tenant) -> RunOut:
    return RunOut.from_row(await db.one("agent_runs", str(run_id)))
