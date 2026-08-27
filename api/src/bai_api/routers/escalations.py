"""The exception queue.

`operator` may resolve an escalation without being able to change the record.
That separation is what makes the queue delegable, and delegability is what
makes the automation economically worthwhile.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from bai_platform.audit import AuditAction
from bai_platform.rbac import Permission
from fastapi import APIRouter, Depends, Query

from bai_api.core.errors import Conflict
from bai_api.deps import DB, Tenant, require
from bai_api.schemas import EscalationOut, EscalationResolve

router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get("", response_model=list[EscalationOut])
async def list_escalations(
    db: DB,
    ctx: Tenant,
    state: Annotated[str, Query(pattern="^(open|resolved|expired)$")] = "open",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[EscalationOut]:
    rows = await db.select(
        "escalations", state=f"eq.{state}", order="created_at.asc", limit=limit
    )
    return [EscalationOut.from_row(r) for r in rows]


@router.post("/{escalation_id}/resolve", response_model=EscalationOut)
async def resolve(
    escalation_id: UUID,
    payload: EscalationResolve,
    db: DB,
    ctx: Annotated[object, Depends(require(Permission.ESCALATION_RESOLVE))],
) -> EscalationOut:
    current = await db.one("escalations", str(escalation_id))
    if current["state"] != "open":
        raise Conflict(
            "That escalation has already been resolved. Nothing was changed.",
            hint="Refresh the queue to see the current state.",
        )
    if payload.choice not in (current.get("options") or []):
        raise Conflict(
            f"{payload.choice!r} is not one of the options for this escalation. "
            f"Nothing was changed.",
            hint=f"Choose one of: {', '.join(current.get('options') or [])}",
        )

    row = await db.update(
        "escalations",
        str(escalation_id),
        {
            "state": "resolved",
            "resolved_by": str(ctx.user_id),      # type: ignore[attr-defined]
            "resolution": payload.choice,
            "resolved_at": datetime.now(UTC).isoformat(),
        },
    )
    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),                # type: ignore[attr-defined]
        "action": AuditAction.ESCALATION_RESOLVED.value,
        "actor_id": str(ctx.user_id),             # type: ignore[attr-defined]
        "subject_type": "escalation",
        "subject_id": str(escalation_id),
        # metadata carries the decision, never the content it was about
        "metadata": {"choice": payload.choice, "action_name": current["action_name"]},
    })
    return EscalationOut.from_row(row)
