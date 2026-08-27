"""Anthropic access, model routing, prompt caching and the budget guard.

Cost is engineered here rather than hoped for. Three levers, in order of size:
prompt-cache the domain rubric, route extraction to a cheaper model than
reasoning, and never re-analyse a document whose hash has not changed
(``bai_platform.ingestion``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from bai_platform.agents import BudgetExceeded
from bai_platform.money import Money

__all__ = ["PRICING", "BudgetLedger", "LLMClient", "ModelRouter", "Task", "TokenUsage"]


class Task(StrEnum):
    """What the call is for. Determines which model answers it."""

    EXTRACTION = "extraction"     # pull structured fields out of text
    CLASSIFY = "classify"         # route, label, triage
    REASONING = "reasoning"       # analysis, synthesis, judgement
    SUMMARY = "summary"


# Prices are USD per million tokens and MUST carry the date they were checked.
# Never present a stale price as current — re-verify before quoting to a customer.
PRICING: dict[str, dict[str, Any]] = {
    "claude-opus-5":            {"in": 5.00, "out": 25.00, "as_of": date(2026, 8, 27)},
    "claude-sonnet-5":          {"in": 3.00, "out": 15.00, "as_of": date(2026, 8, 27)},
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00, "as_of": date(2026, 8, 27)},
}

_DEFAULT_ROUTES: dict[Task, str] = {
    Task.EXTRACTION: "claude-sonnet-5",
    Task.CLASSIFY: "claude-haiku-4-5-20251001",
    Task.SUMMARY: "claude-sonnet-5",
    Task.REASONING: "claude-opus-5",
}


@dataclass(frozen=True, slots=True)
class ModelRouter:
    """Maps a task to a model. Overridable per tenant for enterprise pinning."""

    routes: dict[Task, str] = field(default_factory=lambda: dict(_DEFAULT_ROUTES))

    def model_for(self, task: Task) -> str:
        model = self.routes.get(task)
        if model is None:
            raise ValueError(f"no model routed for task {task!r}")
        if model not in PRICING:
            raise ValueError(f"model {model!r} has no pricing entry; refusing to call it")
        return model


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def cost(self, model: str) -> Money:
        """USD cost in minor units. Cache reads bill at 10% of input, writes at 125%."""
        p = PRICING[model]
        billed_in = (
            self.input_tokens
            + self.cache_read_tokens * 0.10
            + self.cache_write_tokens * 1.25
        )
        usd = (billed_in * p["in"] + self.output_tokens * p["out"]) / 1_000_000
        return Money(round(usd * 100), "USD")


class BudgetLedger(Protocol):
    def spent_this_month(self, org_id: UUID) -> Money: ...
    def ceiling(self, org_id: UUID) -> Money: ...
    def add(self, org_id: UUID, amount: Money) -> None: ...


@dataclass
class LLMClient:
    """Thin wrapper enforcing routing and the budget ceiling.

    ``transport`` is any callable with the Anthropic messages signature, so the
    platform is testable without a network and without a key.
    """

    transport: Any
    ledger: BudgetLedger
    router: ModelRouter = field(default_factory=ModelRouter)

    def complete(
        self,
        *,
        org_id: UUID,
        task: Task,
        system: str | list[dict[str, Any]],
        messages: list[dict[str, Any]],
        max_tokens: int = 2048,
    ) -> tuple[str, TokenUsage, Money]:
        self._assert_budget(org_id)
        model = self.router.model_for(task)

        response = self.transport(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )

        usage = TokenUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0),
            output_tokens=getattr(response.usage, "output_tokens", 0),
            cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        )
        cost = usage.cost(model)
        self.ledger.add(org_id, cost)

        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        return text, usage, cost

    def _assert_budget(self, org_id: UUID) -> None:
        spent, ceiling = self.ledger.spent_this_month(org_id), self.ledger.ceiling(org_id)
        if spent.minor >= ceiling.minor:
            raise BudgetExceeded(
                f"org {org_id} has spent {spent.format()} of {ceiling.format()} this month"
            )

    @staticmethod
    def cacheable_system(rubric: str, *, extra: str = "") -> list[dict[str, Any]]:
        """Build a system prompt whose stable rubric is cached.

        The rubric is the largest and most repeated part of every call, so
        caching it is the single biggest cost lever available.
        """
        blocks: list[dict[str, Any]] = [
            {"type": "text", "text": rubric, "cache_control": {"type": "ephemeral"}}
        ]
        if extra:
            blocks.append({"type": "text", "text": extra})
        return blocks


def budget_alert_level(spent: Money, ceiling: Money) -> int | None:
    """Return 70, 90 or 100 when a threshold is crossed, else None."""
    if ceiling.minor <= 0:
        return None
    pct = spent.minor / ceiling.minor * 100
    for threshold in (100, 90, 70):
        if pct >= threshold:
            return threshold
    return None
