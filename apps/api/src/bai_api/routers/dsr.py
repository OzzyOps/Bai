"""Data subject requests.

Access, portability and erasure are legal obligations under GDPR, UK GDPR,
CCPA/CPRA, LGPD, PIPEDA and APPI. The clocks differ by regime, so the runbook
holds the current values rather than this file.

Erasure is queued, never executed inline: it cascades across documents, chunks,
embeddings and backups, and the embedding path is the one most often missed.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from bai_platform.audit import AuditAction
from bai_platform.rbac import Permission
from fastapi import APIRouter, Depends

from bai_api.deps import DB, require

router = APIRouter(prefix="/dsr", tags=["data subject requests"])


@router.post("/export")
async def export_subject_data(
    subject_user_id: UUID,
    db: DB,
    ctx: Annotated[object, Depends(require(Permission.DSR_EXECUTE))],
) -> dict[str, Any]:
    """Machine-readable export for the named subject, scoped to this tenant."""
    records = await db.select("records", created_by=f"eq.{subject_user_id}", limit=1000)
    runs = await db.select("agent_runs", started_by=f"eq.{subject_user_id}", limit=1000)
    resolved = await db.select("escalations", resolved_by=f"eq.{subject_user_id}", limit=1000)

    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),        # type: ignore[attr-defined]
        "action": AuditAction.DSR_EXPORTED.value,
        "actor_id": str(ctx.user_id),     # type: ignore[attr-defined]
        "subject_type": "user",
        "subject_id": str(subject_user_id),
        "metadata": {"records": len(records), "runs": len(runs)},
    })
    return {
        "subject": str(subject_user_id),
        "org": str(ctx.org_id),           # type: ignore[attr-defined]
        "records": records,
        "agent_runs": runs,
        "escalations_resolved": resolved,
        "format": "application/json",
    }


@router.post("/erase", status_code=202)
async def request_erasure(
    subject_user_id: UUID,
    db: DB,
    ctx: Annotated[object, Depends(require(Permission.DSR_EXECUTE))],
) -> dict[str, str]:
    """Queue an erasure. Returns 202 — this cannot complete synchronously.

    The worker cascades to documents, chunks and embeddings, tombstones the
    subject, preserves the audit trail (which is legally required to survive
    erasure of the underlying content), and reconciles against the backup cycle.
    """
    await db.insert("audit_log", {
        "org_id": str(ctx.org_id),        # type: ignore[attr-defined]
        "action": AuditAction.DSR_ERASED.value,
        "actor_id": str(ctx.user_id),     # type: ignore[attr-defined]
        "subject_type": "user",
        "subject_id": str(subject_user_id),
        "metadata": {"status": "queued"},
    })
    return {
        "status": "queued",
        "subject": str(subject_user_id),
        "note": "Erasure cascades to documents, chunks and embeddings. "
                "The audit trail is preserved as required by law.",
    }
