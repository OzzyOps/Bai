"""Model routing, cost arithmetic and the budget ceiling.

Untested before. This is the module that spends money, and the ceiling is the
only thing standing between a runaway loop and an Anthropic bill, so its
behaviour is pinned here rather than assumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from bai_platform.agents import BudgetExceeded
from bai_platform.llm import (
    PRICING,
    LLMClient,
    ModelRouter,
    Task,
    TokenUsage,
    budget_alert_level,
)
from bai_platform.money import Money


@dataclass
class FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class FakeBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list[FakeBlock]
    usage: FakeUsage


class FakeLedger:
    """In-memory ledger. The real one is a Postgres table."""

    def __init__(self, ceiling_minor: int, spent_minor: int = 0) -> None:
        self._ceiling = Money(ceiling_minor, "USD")
        self._spent = Money(spent_minor, "USD")
        self.additions: list[Money] = []

    def spent_this_month(self, org_id: UUID) -> Money:
        return self._spent

    def ceiling(self, org_id: UUID) -> Money:
        return self._ceiling

    def add(self, org_id: UUID, amount: Money) -> None:
        self.additions.append(amount)
        self._spent = Money(self._spent.minor + amount.minor, "USD")


def transport_returning(text: str, usage: FakeUsage):
    calls: list[dict[str, object]] = []

    def _transport(**kwargs: object) -> FakeResponse:
        calls.append(kwargs)
        return FakeResponse(content=[FakeBlock(text=text)], usage=usage)

    _transport.calls = calls  # type: ignore[attr-defined]
    return _transport


# ── routing ────────────────────────────────────────────────────────────────


def test_each_task_routes_to_a_model_that_has_a_price() -> None:
    router = ModelRouter()
    for task in Task:
        assert router.model_for(task) in PRICING


def test_an_unpriced_model_is_refused_rather_than_called() -> None:
    """Calling a model with no pricing entry means spending money we cannot
    account for, so the router refuses instead of guessing a price."""
    router = ModelRouter(routes={Task.REASONING: "claude-not-a-real-model"})
    with pytest.raises(ValueError, match="no pricing entry"):
        router.model_for(Task.REASONING)


def test_an_unrouted_task_is_refused() -> None:
    router = ModelRouter(routes={})
    with pytest.raises(ValueError, match="no model routed"):
        router.model_for(Task.SUMMARY)


def test_every_price_carries_the_date_it_was_checked() -> None:
    """A stale price presented as current is a commercial claim, not a bug."""
    for model, entry in PRICING.items():
        assert entry["as_of"] is not None, f"{model} has no as_of date"


# ── cost ───────────────────────────────────────────────────────────────────


def test_cost_is_minor_units_of_usd() -> None:
    # 1M input + 1M output on sonnet at 3.00 / 15.00 = $18.00 = 1800 minor
    cost = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000).cost("claude-sonnet-5")
    assert cost == Money(1800, "USD")


def test_cache_reads_are_cheaper_than_fresh_input() -> None:
    fresh = TokenUsage(input_tokens=1_000_000, output_tokens=0).cost("claude-sonnet-5")
    cached = TokenUsage(input_tokens=0, output_tokens=0, cache_read_tokens=1_000_000).cost("claude-sonnet-5")
    assert cached.minor < fresh.minor
    assert cached.minor == round(fresh.minor * 0.10)


def test_cache_writes_cost_more_than_fresh_input() -> None:
    fresh = TokenUsage(input_tokens=1_000_000, output_tokens=0).cost("claude-sonnet-5")
    written = TokenUsage(input_tokens=0, output_tokens=0, cache_write_tokens=1_000_000).cost("claude-sonnet-5")
    assert written.minor > fresh.minor


# ── the ceiling ────────────────────────────────────────────────────────────


def test_a_call_within_budget_completes_and_is_billed() -> None:
    ledger = FakeLedger(ceiling_minor=10_000)
    transport = transport_returning("answer", FakeUsage(input_tokens=1000, output_tokens=500))
    client = LLMClient(transport=transport, ledger=ledger)

    text, usage, cost = client.complete(
        org_id=uuid4(), task=Task.SUMMARY, system="rubric", messages=[]
    )

    assert text == "answer"
    assert usage.input_tokens == 1000
    assert ledger.additions == [cost]


def test_the_ceiling_stops_the_call_before_it_is_made() -> None:
    """Checked before the transport runs, not after. A ceiling enforced after
    the spend is not a ceiling."""
    ledger = FakeLedger(ceiling_minor=1_000, spent_minor=1_000)
    transport = transport_returning("never", FakeUsage())
    client = LLMClient(transport=transport, ledger=ledger)

    with pytest.raises(BudgetExceeded):
        client.complete(org_id=uuid4(), task=Task.SUMMARY, system="r", messages=[])

    assert transport.calls == []  # type: ignore[attr-defined]


def test_only_text_blocks_are_returned() -> None:
    ledger = FakeLedger(ceiling_minor=10_000)

    def transport(**_: object) -> FakeResponse:
        return FakeResponse(
            content=[FakeBlock("kept"), FakeBlock("dropped", type="thinking")],
            usage=FakeUsage(input_tokens=1),
        )

    client = LLMClient(transport=transport, ledger=ledger)
    text, _, _ = client.complete(org_id=uuid4(), task=Task.SUMMARY, system="r", messages=[])
    assert text == "kept"


def test_the_rubric_is_marked_cacheable_and_the_extra_is_not() -> None:
    blocks = LLMClient.cacheable_system("stable rubric", extra="per-request context")
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]


@pytest.mark.parametrize(
    ("spent", "expected"),
    [(0, None), (699, None), (700, 70), (899, 70), (900, 90), (1000, 100), (5000, 100)],
)
def test_budget_alerts_fire_at_the_stated_thresholds(spent: int, expected: int | None) -> None:
    assert budget_alert_level(Money(spent, "USD"), Money(1000, "USD")) == expected


def test_no_alert_when_no_ceiling_is_set() -> None:
    assert budget_alert_level(Money(500, "USD"), Money(0, "USD")) is None
