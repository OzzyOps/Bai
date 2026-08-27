"""Celery application.

Workers are the ONLY place the Supabase service-role key exists. They need to
write agent facts and runs on behalf of a tenant with no user in the request,
so they bypass RLS — which is exactly why nothing user-facing runs here.
"""

from __future__ import annotations

import os

from celery import Celery

broker = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery("bai", broker=broker, backend=broker)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # An agent run is long and expensive. Acknowledge only after it completes so
    # a worker dying mid-run puts the work back rather than losing it.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    broker_transport_options={"visibility_timeout": 3600},
    task_default_retry_delay=30,
    task_max_retries=3,
)

app.conf.beat_schedule = {
    "expire-stale-escalations": {
        "task": "bai.escalations.expire_stale",
        "schedule": 3600.0,
    },
    "refresh-fx-rates": {
        "task": "bai.fx.refresh",
        "schedule": 86400.0,   # rates are pinned and dated, never live at display time
    },
    "enforce-retention": {
        "task": "bai.retention.enforce",
        "schedule": 86400.0,
    },
}

app.autodiscover_tasks(["bai_workers.tasks"])
