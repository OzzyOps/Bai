"""Pydantic contracts. The source of truth for the OpenAPI spec and, through
`scripts/gen-types.sh`, for the frontend's TypeScript types."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from bai_platform.money import exponent_for
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MoneyOut(BaseModel):
    """Money crosses the wire as minor units plus a code — never a float.

    `formatted` is a convenience for logs and exports; clients should format
    with Intl.NumberFormat using the tenant's locale.
    """

    minor: int
    currency: str = Field(min_length=3, max_length=3)
    exponent: int

    @classmethod
    def of(cls, minor: int | None, currency: str | None) -> MoneyOut | None:
        if minor is None or currency is None:
            return None
        return cls(minor=minor, currency=currency, exponent=exponent_for(currency))


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    external_ref: str | None = Field(default=None, max_length=128)
    value_minor: int | None = None
    value_currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("value_currency")
    @classmethod
    def iso_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.isalpha():
            raise ValueError("currency must be an ISO 4217 alpha-3 code")
        return v.upper()

    @field_validator("value_minor")
    @classmethod
    def not_a_float(cls, v: int | None) -> int | None:
        if isinstance(v, bool):
            # bool is a subclass of int, so a stray True would otherwise be
            # accepted as 1 minor unit.
            raise TypeError("value_minor must be an integer of minor units, not a bool")
        return v


class RecordOut(BaseModel):
    id: UUID
    product: str
    title: str
    external_ref: str | None = None
    status: str
    value: MoneyOut | None = None
    created_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> RecordOut:
        return cls(
            id=row["id"],
            product=row["product"],
            title=row["title"],
            external_ref=row.get("external_ref"),
            status=row["status"],
            value=MoneyOut.of(row.get("value_minor"), row.get("value_currency")),
            created_at=row["created_at"],
        )


class FactOut(BaseModel):
    """Every fact carries its citation. There is no unattributed fact."""

    key: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    display_state: Literal["high", "medium", "unknown"]
    document_id: UUID
    locator: str
    char_start: int | None = None
    char_end: int | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> FactOut:
        c = float(row["confidence"])
        return cls(
            key=row["key"],
            value=row["value"],
            confidence=c,
            display_state="high" if c >= 0.90 else "medium" if c >= 0.70 else "unknown",
            document_id=row["document_id"],
            locator=row["locator"],
            char_start=row.get("char_start"),
            char_end=row.get("char_end"),
        )


class RunOut(BaseModel):
    id: UUID
    product: str
    agent: str
    state: str
    record_id: UUID | None = None
    cost: MoneyOut | None = None
    started_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> RunOut:
        return cls(
            id=row["id"], product=row["product"], agent=row["agent"], state=row["state"],
            record_id=row.get("record_id"),
            cost=MoneyOut.of(row.get("cost_minor"), row.get("cost_currency")),
            started_at=row["started_at"], completed_at=row.get("completed_at"),
        )


class EscalationOut(BaseModel):
    id: UUID
    run_id: UUID
    record_id: UUID | None = None
    action_name: str
    consequence: Literal["none", "reversible", "consequential"]
    reversible: bool
    reason: str
    confidence: float | None = None
    options: list[str] = Field(default_factory=list)
    state: str
    created_at: datetime

    @property
    def can_ever_be_automated(self) -> bool:
        return not (self.consequence == "consequential" and not self.reversible)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> EscalationOut:
        return cls(**{k: row[k] for k in
                      ("id", "run_id", "action_name", "consequence", "reversible",
                       "reason", "state", "created_at")},
                   record_id=row.get("record_id"),
                   confidence=row.get("confidence"),
                   options=row.get("options") or [])


class EscalationResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class RunStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: UUID
    agent: str = Field(min_length=1, max_length=64)


class Page(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
