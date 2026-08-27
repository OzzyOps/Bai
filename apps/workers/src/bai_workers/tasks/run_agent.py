"""Durable agent execution.

This task is the practical expression of the five platform invariants. Read
``bai_platform.agents`` alongside it — the guarantees live there; this is the
loop that honours them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from bai_platform.agents import (
    AgentStep,
    BudgetExceeded,
    EscalationRequired,
    RunState,
)
from celery import shared_task

from bai_workers.services.store import Store

log = structlog.get_logger("bai.workers.agent")


@shared_task(
    name="bai.agent.run",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
)
def run_agent(self: Any, run_id: str, org_id: str) -> dict[str, Any]:
    """Execute one agent run to completion, escalation, or failure."""
    store = Store()
    log.bind(run_id=run_id, org_id=org_id)

    run = store.load_run(UUID(run_id))
    if run.state in (RunState.COMPLETED, RunState.CANCELLED):
        # Invariant 1: a redelivered message must not re-do finished work.
        log.info("agent.run.already_terminal", state=run.state.value)
        return {"run_id": run_id, "state": run.state.value, "resumed": False}

    store.set_run_state(run.id, RunState.RUNNING)
    run.autonomy = store.autonomy_grants(UUID(org_id))

    try:
        for step_name, payload in store.plan(run):
            # Invariant 1 again: skip anything already completed with this input.
            if run.already_done(step_name, payload):
                log.info("agent.step.skipped", step=step_name)
                continue

            step = AgentStep(
                id=store.new_id(), run_id=run.id, ordinal=len(run.steps),
                name=step_name, input_hash=AgentStep.hash_input(payload),
            )
            result = store.execute_step(run, step, payload)
            step.completed_at = datetime.now(UTC)
            run.steps.append(step)
            store.persist_step(step)

            # Invariant 2: every fact carries provenance. Fact.__post_init__
            # refuses to construct one without it, so this cannot silently pass.
            for fact in result.facts:
                run.record_fact(fact)
                store.persist_fact(run, fact)

            # Invariants 3 and 4: authorise before acting, never after.
            for action in result.actions:
                run.authorise(action)          # raises EscalationRequired
                store.execute_action(run, action)

    except EscalationRequired as esc:
        # Not an error. The correct outcome when a human must decide.
        store.open_escalation(run, esc)
        store.set_run_state(run.id, RunState.AWAITING_HUMAN)
        log.info("agent.run.escalated", action=esc.action.name, reason=esc.reason)
        return {"run_id": run_id, "state": "awaiting_human", "action": esc.action.name}

    except BudgetExceeded as exc:
        # Invariant 5: a hard stop, never a soft warning. Do not retry — the
        # ceiling will still be reached on the next attempt.
        store.set_run_state(run.id, RunState.FAILED, error=str(exc))
        log.exception("agent.run.budget_exceeded", error=str(exc))
        return {"run_id": run_id, "state": "failed", "reason": "budget_exceeded"}

    except Exception as exc:
        store.set_run_state(run.id, RunState.FAILED, error=str(exc))
        log.exception("agent.run.failed")
        raise

    store.set_run_state(run.id, RunState.COMPLETED)
    log.info(
        "agent.run.completed",
        steps=len(run.steps), facts=len(run.facts),
        uncertain=len(run.uncertain_facts), cost_minor=run.total_cost_minor,
    )
    return {
        "run_id": run_id,
        "state": "completed",
        "facts": len(run.facts),
        "uncertain": len(run.uncertain_facts),
    }


@shared_task(name="bai.agent.resume")
def resume_after_resolution(run_id: str, org_id: str, choice: str) -> dict[str, Any]:
    """Continue a run once a human has resolved its escalation.

    Completed steps are skipped by input hash, so resumption costs only the work
    that had not finished.
    """
    store = Store()
    store.apply_resolution(UUID(run_id), choice)
    return run_agent.apply(args=[run_id, org_id]).get()  # type: ignore[no-any-return]
