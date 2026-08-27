"""Append-only audit trail.

The table grants INSERT and SELECT and nothing else — no role, including
``owner``, may UPDATE or DELETE. That is what makes the trail evidence rather
than a log. See ``supabase/migrations/*_audit.sql``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4

__all__ = ["AuditAction", "AuditEntry", "AuditLog", "AuditSink"]


class AuditAction(StrEnum):
    # access
    RECORD_VIEWED = "record.viewed"
    DOCUMENT_DOWNLOADED = "document.downloaded"
    # mutation
    RECORD_CREATED = "record.created"
    RECORD_UPDATED = "record.updated"
    RECORD_DELETED = "record.deleted"
    # agent
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    ACTION_EXECUTED = "action.executed"
    ACTION_ESCALATED = "action.escalated"
    ESCALATION_RESOLVED = "escalation.resolved"
    # privilege — the entries an auditor reads first
    ROLE_CHANGED = "member.role_changed"
    AUTONOMY_GRANTED = "autonomy.granted"
    AUTONOMY_REVOKED = "autonomy.revoked"
    RESTRICTION_GRANTED = "restriction.granted"
    # privacy
    DSR_EXPORTED = "dsr.exported"
    DSR_ERASED = "dsr.erased"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    org_id: UUID
    action: AuditAction
    actor_id: UUID | None                # None means the platform acted, not a person
    actor_is_agent: bool = False
    subject_type: str | None = None
    subject_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.actor_id is None and not self.actor_is_agent:
            raise ValueError(
                "an entry with no actor must be marked actor_is_agent; "
                "unattributed audit entries are forbidden"
            )
        # Metadata is read by auditors and support. It must never carry content.
        for banned in ("content", "document_text", "body", "raw", "prompt"):
            if banned in self.metadata:
                raise ValueError(f"audit metadata must not contain {banned!r}")

    def to_row(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "action": self.action.value,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_is_agent": self.actor_is_agent,
            "subject_type": self.subject_type,
            "subject_id": str(self.subject_id) if self.subject_id else None,
            "metadata": self.metadata,
            "at": self.at.isoformat(),
        }


class AuditSink(Protocol):
    def write(self, entries: list[AuditEntry]) -> None: ...


@dataclass(slots=True)
class AuditLog:
    """Buffers entries and flushes them as one batch.

    Flush is called on the way out of a request or task. If the flush fails the
    caller must fail too — an action that happened without an audit entry is
    worse than an action that did not happen.
    """

    sink: AuditSink
    _buffer: list[AuditEntry] = field(default_factory=list)

    def add(self, entry: AuditEntry) -> None:
        self._buffer.append(entry)

    def record(
        self,
        *,
        org_id: UUID,
        action: AuditAction,
        actor_id: UUID | None = None,
        actor_is_agent: bool = False,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        **metadata: Any,
    ) -> None:
        self.add(
            AuditEntry(
                org_id=org_id,
                action=action,
                actor_id=actor_id,
                actor_is_agent=actor_is_agent,
                subject_type=subject_type,
                subject_id=subject_id,
                metadata=metadata,
            )
        )

    def flush(self) -> int:
        if not self._buffer:
            return 0
        count = len(self._buffer)
        self.sink.write(self._buffer)
        self._buffer = []
        return count

    @property
    def pending(self) -> int:
        return len(self._buffer)
