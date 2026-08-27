"""Persistence for workers.

This is the ONLY module that uses the Supabase service-role key. It bypasses
RLS because a worker acts for a tenant with no user in the request. Every method
therefore takes an explicit org_id and filters on it — the discipline RLS
normally provides for free must be applied by hand here.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from bai_platform.agents import (
    ActionSpec,
    AgentRun,
    AgentStep,
    Autonomy,
    EscalationRequired,
    Fact,
    RunState,
)


class StepResult:
    def __init__(self, facts: list[Fact] | None = None, actions: list[ActionSpec] | None = None):
        self.facts = facts or []
        self.actions = actions or []


class Store:
    def __init__(self, region: str | None = None) -> None:
        region = (region or os.environ.get("BAI_REGION", "eu")).upper()
        url = os.environ.get(f"SUPABASE_{region}_URL")
        key = os.environ.get(f"SUPABASE_{region}_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError(
                f"workers need SUPABASE_{region}_URL and SUPABASE_{region}_SERVICE_KEY. "
                f"Customer data must not cross a region boundary."
            )
        self._base = url.rstrip("/") + "/rest/v1"
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # ── low level ───────────────────────────────────────────────────────────
    def _post(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = httpx.post(f"{self._base}/{table}", headers=self._headers, json=payload, timeout=30)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else {}

    def _patch(self, table: str, row_id: UUID, payload: dict[str, Any]) -> None:
        r = httpx.patch(
            f"{self._base}/{table}", headers=self._headers,
            params={"id": f"eq.{row_id}"}, json=payload, timeout=30,
        )
        r.raise_for_status()

    def _get(self, table: str, **params: str) -> list[dict[str, Any]]:
        r = httpx.get(f"{self._base}/{table}", headers=self._headers, params=params, timeout=30)
        r.raise_for_status()
        rows: list[dict[str, Any]] = r.json()
        return rows

    @staticmethod
    def new_id() -> UUID:
        return uuid4()

    # ── runs ────────────────────────────────────────────────────────────────
    def load_run(self, run_id: UUID) -> AgentRun:
        rows = self._get("agent_runs", id=f"eq.{run_id}", select="*", limit="1")
        if not rows:
            raise LookupError(f"run {run_id} not found")
        row = rows[0]
        run = AgentRun(
            id=UUID(row["id"]),
            org_id=UUID(row["org_id"]),
            record_id=UUID(row["record_id"]) if row.get("record_id") else None,
            product=row["product"],
            state=RunState(row["state"]),
        )
        for s in self._get("agent_steps", run_id=f"eq.{run_id}", select="*", order="ordinal.asc"):
            run.steps.append(
                AgentStep(
                    id=UUID(s["id"]), run_id=run.id, ordinal=s["ordinal"], name=s["name"],
                    input_hash=s["input_hash"], output=s.get("output"),
                    tokens_in=s.get("tokens_in", 0), tokens_out=s.get("tokens_out", 0),
                    cost_minor=s.get("cost_minor", 0),
                    cost_currency=s.get("cost_currency", "USD"),
                    completed_at=(
                        datetime.fromisoformat(s["completed_at"]) if s.get("completed_at") else None
                    ),
                )
            )
        return run

    def set_run_state(self, run_id: UUID, state: RunState, *, error: str | None = None) -> None:
        payload: dict[str, Any] = {"state": state.value}
        if state in (RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED):
            payload["completed_at"] = datetime.now(UTC).isoformat()
        if error:
            payload["error"] = error[:2000]
        self._patch("agent_runs", run_id, payload)

    def autonomy_grants(self, org_id: UUID) -> dict[str, Autonomy]:
        rows = self._get("autonomy_grants", org_id=f"eq.{org_id}", select="action_name,level")
        return {r["action_name"]: Autonomy(r["level"]) for r in rows}

    # ── plan and execution ──────────────────────────────────────────────────
    def plan(self, run: AgentRun) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield (step_name, payload) pairs for this run.

        Products override this by registering a planner for their agent. The
        default is the generic ingest → extract → analyse → score sequence.
        """
        record = str(run.record_id) if run.record_id else ""
        yield "ingest", {"record_id": record}
        yield "extract", {"record_id": record}
        yield "analyse", {"record_id": record}
        yield "score", {"record_id": record}

    def execute_step(self, run: AgentRun, step: AgentStep, payload: dict[str, Any]) -> StepResult:
        """Run one step. Product agents supply the real implementation."""
        raise NotImplementedError(
            "register a product agent implementation; see apps/_product-template/agents/"
        )

    def execute_action(self, run: AgentRun, action: ActionSpec) -> None:
        raise NotImplementedError("register a connector; see bai_platform.connectors")

    # ── persistence ─────────────────────────────────────────────────────────
    def persist_step(self, step: AgentStep) -> None:
        self._post("agent_steps", {
            "id": str(step.id), "run_id": str(step.run_id), "ordinal": step.ordinal,
            "name": step.name, "input_hash": step.input_hash, "output": step.output,
            "tokens_in": step.tokens_in, "tokens_out": step.tokens_out,
            "cost_minor": step.cost_minor, "cost_currency": step.cost_currency,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        })

    def persist_fact(self, run: AgentRun, fact: Fact) -> None:
        head = fact.provenance[0]
        self._post("agent_facts", {
            "org_id": str(run.org_id), "run_id": str(run.id),
            "record_id": str(run.record_id) if run.record_id else None,
            "key": fact.key, "value": fact.value, "confidence": fact.confidence,
            "document_id": str(head.source_id), "locator": head.locator,
            "char_start": head.char_start, "char_end": head.char_end,
        })

    def open_escalation(self, run: AgentRun, esc: EscalationRequired) -> None:
        self._post("escalations", {
            "org_id": str(run.org_id), "run_id": str(run.id),
            "record_id": str(run.record_id) if run.record_id else None,
            "action_name": esc.action.name,
            "consequence": esc.action.consequence.value,
            "reversible": esc.action.reversible,
            "reason": esc.reason,
            "payload": esc.action.payload,
            "options": ["Approve", "Reject", "Ask a colleague"],
            "state": "open",
        })

    def apply_resolution(self, run_id: UUID, choice: str) -> None:
        self._patch("agent_runs", run_id, {"state": RunState.PENDING.value})

    # ── maintenance ─────────────────────────────────────────────────────────
    def expire_escalations(self, max_age_days: int) -> int:
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        stale = self._get(
            "escalations", state="eq.open", created_at=f"lt.{cutoff}", select="id"
        )
        for row in stale:
            self._patch("escalations", UUID(row["id"]), {"state": "expired"})
        return len(stale)

    def refresh_fx_rates(self) -> int:
        raise NotImplementedError("configure FX_PROVIDER and implement the fetch")

    def enforce_retention(self) -> dict[str, int]:
        raise NotImplementedError(
            "retention cascade: embeddings → chunks → documents. Never the audit trail."
        )
