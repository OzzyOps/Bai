"""The five agent invariants. A product that breaks one damages the whole
portfolio's trust, not just its own."""
import datetime as dt
from uuid import uuid4

import pytest
from bai_platform.agents import (
    ActionSpec,
    AgentRun,
    AgentStep,
    Autonomy,
    Consequence,
    EscalationRequired,
    Fact,
    Provenance,
)


@pytest.fixture
def src() -> Provenance:
    return Provenance(source_id=uuid4(), locator="p.4", char_start=10, char_end=40)


class TestProvenance:
    """Invariant 2 — there is no unattributed fact."""

    def test_unattributed_fact_rejected(self) -> None:
        with pytest.raises(ValueError, match="provenance"):
            Fact(key="total", value=1, confidence=0.9, provenance=())

    def test_confidence_range_enforced(self, src: Provenance) -> None:
        with pytest.raises(ValueError):
            Fact(key="x", value=1, confidence=1.4, provenance=(src,))


class TestUncertaintyIsVisible:
    """A low-confidence result rendered neutrally reads as 'safe'. That is a trust failure."""

    @pytest.mark.parametrize(
        ("confidence", "state"), [(0.95, "high"), (0.78, "medium"), (0.40, "unknown")]
    )
    def test_display_state(self, src: Provenance, confidence: float, state: str) -> None:
        assert Fact("k", 1, confidence, (src,)).display_state == state

    def test_uncertain_facts_are_surfaced(self, src: Provenance) -> None:
        run = AgentRun(org_id=uuid4(), product="test")
        run.record_fact(Fact("a", 1, 0.95, (src,)))
        run.record_fact(Fact("b", 2, 0.40, (src,)))
        assert len(run.uncertain_facts) == 1


class TestEscalationBoundary:
    """Invariants 3 and 4."""

    def test_consequential_blocked_by_default(self) -> None:
        run = AgentRun(org_id=uuid4())
        with pytest.raises(EscalationRequired):
            run.authorise(ActionSpec("post_payment", Consequence.CONSEQUENTIAL, reversible=False))

    def test_irreversible_blocked_even_with_full_autonomy(self) -> None:
        run = AgentRun(org_id=uuid4(), autonomy={"post_payment": Autonomy.ACT})
        with pytest.raises(EscalationRequired, match="irreversible"):
            run.authorise(ActionSpec("post_payment", Consequence.CONSEQUENTIAL, reversible=False))

    @pytest.mark.parametrize(
        "granted", [Autonomy.NONE, Autonomy.SUGGEST, Autonomy.ACT_WITH_APPROVAL]
    )
    def test_reversible_action_needs_explicit_grant(self, granted: Autonomy) -> None:
        run = AgentRun(org_id=uuid4(), autonomy={"tag": granted})
        with pytest.raises(EscalationRequired):
            run.authorise(ActionSpec("tag", Consequence.REVERSIBLE, reversible=True))

    def test_granted_reversible_action_proceeds(self) -> None:
        run = AgentRun(org_id=uuid4(), autonomy={"tag": Autonomy.ACT})
        run.authorise(ActionSpec("tag", Consequence.REVERSIBLE, reversible=True))

    def test_connector_cannot_lie_about_reversibility(self) -> None:
        with pytest.raises(ValueError):
            ActionSpec("bad", Consequence.REVERSIBLE, reversible=False)


class TestDurability:
    """Invariant 1 — a resumed run never repeats a completed action."""

    def test_replay_detects_completed_step(self) -> None:
        run = AgentRun(org_id=uuid4())
        payload = {"doc": "d1", "mode": "x"}
        run.steps.append(
            AgentStep(uuid4(), run.id, 0, "extract", AgentStep.hash_input(payload),
                      completed_at=dt.datetime.now(dt.UTC))
        )
        assert run.already_done("extract", payload) is not None
        assert run.already_done("extract", {"mode": "x", "doc": "d1"}) is not None
        assert run.already_done("extract", {"doc": "d2", "mode": "x"}) is None
