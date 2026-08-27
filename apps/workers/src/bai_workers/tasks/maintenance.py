"""Scheduled maintenance: escalation expiry, FX refresh, retention enforcement."""

from __future__ import annotations

from typing import Any

import structlog
from celery import shared_task

from bai_workers.services.store import Store

log = structlog.get_logger("bai.workers.maintenance")


@shared_task(name="bai.escalations.expire_stale")
def expire_stale(max_age_days: int = 30) -> dict[str, int]:
    """Expire escalations nobody answered.

    An expired escalation is never auto-approved — it is closed unresolved and
    reported. Silently proceeding because a human did not reply would defeat the
    entire escalation boundary.
    """
    n = Store().expire_escalations(max_age_days)
    log.info("escalations.expired", count=n, max_age_days=max_age_days)
    return {"expired": n}


@shared_task(name="bai.fx.refresh")
def refresh_fx() -> dict[str, Any]:
    """Pin today's FX rates.

    Rates are stored with their source and timestamp. Nothing converts at
    display time — a figure that moves with the spot rate is one nobody can
    budget against or reconcile later.
    """
    n = Store().refresh_fx_rates()
    log.info("fx.refreshed", pairs=n)
    return {"pairs": n}


@shared_task(name="bai.retention.enforce")
def enforce_retention() -> dict[str, int]:
    """Delete data past the tenant's configured retention.

    Order matters: embeddings first, then chunks, then documents. Deleting the
    document first orphans its embeddings, which is the erasure path most
    commonly missed in a RAG system. The audit trail is never deleted.
    """
    result = Store().enforce_retention()
    log.info("retention.enforced", **result)
    return result
