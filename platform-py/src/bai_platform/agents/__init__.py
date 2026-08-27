"""Agent execution substrate for BAi.

Five invariants are enforced here rather than left to product code, because a
product that gets one wrong damages the whole portfolio's trust, not just itself:

  1. Durable runs      — every step persisted, resumable, never double-acting
  2. Provenance        — every fact carries source, locator, span, confidence
  3. Escalation        — a first-class outcome, not an error
  4. Reversibility     — every write is reversible or approved
  5. Budget            — per-tenant inference ceiling, enforced not advised
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4

__all__ = [
    "CONFIDENCE_FLOOR",
    "ActionSpec",
    "AgentRun",
    "AgentStep",
    "Autonomy",
    "BudgetExceeded",
    "Consequence",
    "EscalationRequired",
    "Fact",
    "Provenance",
    "RunState",
]

# Below this, a fact renders as `unknown` in the UI — never as a finding.
# Paired with the `color.confidence` / `color.semantic.unknown` design tokens.
CONFIDENCE_FLOOR: float = 0.70


class Autonomy(StrEnum):
    """Granted per action type, per tenant, on evidenced accuracy. Never global."""
    NONE = "none"                # always escalate
    SUGGEST = "suggest"          # propose, human executes
    ACT_WITH_APPROVAL = "act_with_approval"
    ACT = "act"                  # autonomous; only for reversible, non-consequential actions


class Consequence(StrEnum):
    NONE = "none"                # read-only
    REVERSIBLE = "reversible"    # can be undone by the platform
    CONSEQUENTIAL = "consequential"  # financial, legal, contractual, or irreversible


class RunState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EscalationRequired(Exception):
    """Not an error. The correct outcome when a human must decide."""

    def __init__(self, action: ActionSpec, reason: str) -> None:
        super().__init__(reason)
        self.action = action
        self.reason = reason


class BudgetExceeded(Exception):
    """Tenant inference ceiling reached. Hard stop, never a soft warning."""


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a fact came from. Mandatory — there is no unattributed fact."""
    source_id: UUID
    locator: str                 # page, row, cell, message id — domain-specific
    char_start: int | None = None
    char_end: int | None = None


@dataclass(frozen=True, slots=True)
class Fact:
    """A single assertion produced by an agent."""
    key: str
    value: Any
    confidence: float
    provenance: tuple[Provenance, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        if not self.provenance:
            raise ValueError(
                f"fact {self.key!r} has no provenance; unattributed facts are forbidden"
            )

    @property
    def is_certain(self) -> bool:
        return self.confidence >= CONFIDENCE_FLOOR

    @property
    def display_state(self) -> str:
        """Drives the design token the UI uses. Low confidence must never read as safe."""
        if self.confidence >= 0.90:
            return "high"
        if self.confidence >= CONFIDENCE_FLOOR:
            return "medium"
        return "unknown"


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """A thing an agent wants to do to the world."""
    name: str
    consequence: Consequence
    reversible: bool
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.consequence is Consequence.REVERSIBLE and not self.reversible:
            raise ValueError(f"action {self.name!r} declared reversible but is not")


class BudgetGuard(Protocol):
    def spend(self, org_id: UUID, minor_units: int, currency: str) -> None: ...
    def remaining(self, org_id: UUID) -> int: ...


@dataclass(slots=True)
class AgentStep:
    """One persisted step. Input hash makes replay idempotent — a resumed run
    never repeats an action it already completed."""
    id: UUID
    run_id: UUID
    ordinal: int
    name: str
    input_hash: str
    output: dict[str, Any] | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_minor: int = 0
    cost_currency: str = "USD"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @staticmethod
    def hash_input(payload: dict[str, Any]) -> str:
        canonical = repr(sorted(payload.items())).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(slots=True)
class AgentRun:
    """A durable, resumable agent execution."""
    id: UUID = field(default_factory=uuid4)
    org_id: UUID | None = None
    record_id: UUID | None = None
    product: str = ""
    state: RunState = RunState.PENDING
    steps: list[AgentStep] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    autonomy: dict[str, Autonomy] = field(default_factory=dict)

    # ── invariant 1: never double-act ───────────────────────────────────────
    def already_done(self, name: str, payload: dict[str, Any]) -> AgentStep | None:
        h = AgentStep.hash_input(payload)
        for s in self.steps:
            if s.name == name and s.input_hash == h and s.completed_at is not None:
                return s
        return None

    # ── invariants 3 & 4: escalation and reversibility ──────────────────────
    def authorise(self, action: ActionSpec) -> None:
        """Raise EscalationRequired unless this action may proceed unattended."""
        granted = self.autonomy.get(action.name, Autonomy.NONE)

        if action.consequence is Consequence.CONSEQUENTIAL:
            if granted is not Autonomy.ACT:
                raise EscalationRequired(
                    action,
                    f"{action.name} is consequential; autonomy is {granted.value}",
                )
            if not action.reversible:
                raise EscalationRequired(
                    action,
                    f"{action.name} is irreversible; a human must approve it",
                )
            return

        if granted in (Autonomy.NONE, Autonomy.SUGGEST):
            raise EscalationRequired(
                action, f"autonomy for {action.name} is {granted.value}"
            )
        if granted is Autonomy.ACT_WITH_APPROVAL:
            raise EscalationRequired(action, f"{action.name} requires approval")

    # ── invariant 2: provenance ─────────────────────────────────────────────
    def record_fact(self, fact: Fact) -> None:
        self.facts.append(fact)   # Fact.__post_init__ rejects unattributed facts

    @property
    def uncertain_facts(self) -> list[Fact]:
        return [f for f in self.facts if not f.is_certain]

    @property
    def total_cost_minor(self) -> int:
        return sum(s.cost_minor for s in self.steps)
