from uuid import uuid4

import pytest
from bai_platform.audit import AuditAction, AuditEntry, AuditLog


class Sink:
    def __init__(self) -> None:
        self.rows: list[AuditEntry] = []

    def write(self, entries: list[AuditEntry]) -> None:
        self.rows.extend(entries)


class TestAttribution:
    def test_unattributed_entry_rejected(self) -> None:
        with pytest.raises(ValueError, match="actor_is_agent"):
            AuditEntry(org_id=uuid4(), action=AuditAction.RECORD_VIEWED, actor_id=None)

    def test_agent_may_act_without_a_user(self) -> None:
        e = AuditEntry(
            org_id=uuid4(), action=AuditAction.ACTION_EXECUTED,
            actor_id=None, actor_is_agent=True,
        )
        assert e.actor_is_agent


class TestNoContentInMetadata:
    """The trail is read by auditors and support. It records what happened,
    never the customer content it happened to."""

    @pytest.mark.parametrize("key", ["content", "document_text", "body", "raw", "prompt"])
    def test_content_keys_rejected(self, key: str) -> None:
        with pytest.raises(ValueError, match=key):
            AuditEntry(
                org_id=uuid4(), action=AuditAction.RECORD_VIEWED,
                actor_id=uuid4(), metadata={key: "sensitive"},
            )


class TestBuffering:
    def test_flush_writes_once_and_clears(self) -> None:
        sink = Sink()
        log = AuditLog(sink=sink)
        org = uuid4()
        log.record(org_id=org, action=AuditAction.RECORD_VIEWED, actor_id=uuid4())
        log.record(org_id=org, action=AuditAction.RUN_STARTED, actor_id=uuid4())
        assert log.pending == 2
        assert log.flush() == 2
        assert log.pending == 0 and len(sink.rows) == 2

    def test_flushing_nothing_is_a_no_op(self) -> None:
        assert AuditLog(sink=Sink()).flush() == 0
