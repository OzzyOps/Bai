"""Connector protocol.

Connectors are the barrier to entry and the place agents touch systems of
record. Every action a connector exposes must declare its consequence and its
reversibility up front; the agent runner refuses to act on anything that has
not declared them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar
from uuid import UUID

from bai_platform.agents import ActionSpec, Consequence

__all__ = ["Connector", "ConnectorAction", "ConnectorError", "ConnectorRegistry"]


class ConnectorError(RuntimeError):
    """A connector failed. Carries whether the remote system was mutated."""

    def __init__(self, message: str, *, mutated: bool) -> None:
        super().__init__(message)
        self.mutated = mutated


@dataclass(frozen=True, slots=True)
class ConnectorAction:
    """A capability a connector exposes to an agent."""

    name: str
    description: str
    consequence: Consequence
    reversible: bool
    undo: str | None = None            # name of the action that reverses this one
    schema: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reversible and not self.undo:
            raise ValueError(
                f"{self.name!r} claims to be reversible but names no undo action"
            )
        if self.consequence is Consequence.NONE and self.reversible:
            raise ValueError(f"{self.name!r} is read-only; reversibility is meaningless")

    def to_spec(self, payload: dict[str, Any]) -> ActionSpec:
        return ActionSpec(
            name=self.name,
            consequence=self.consequence,
            reversible=self.reversible,
            payload=payload,
        )


class Connector(ABC):
    """Base class for every integration.

    Subclasses declare ACTIONS. Anything not declared cannot be invoked — an
    agent cannot reach a capability the connector did not publish, which is what
    stops ingested content from steering it somewhere unexpected.
    """

    key: ClassVar[str]
    ACTIONS: ClassVar[tuple[ConnectorAction, ...]] = ()

    def __init__(self, org_id: UUID, credentials: dict[str, str]) -> None:
        self.org_id = org_id
        self._credentials = credentials

    def action(self, name: str) -> ConnectorAction:
        for a in self.ACTIONS:
            if a.name == name:
                return a
        raise ConnectorError(
            f"{self.key} exposes no action named {name!r}", mutated=False
        )

    @abstractmethod
    def execute(self, action: ConnectorAction, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform the action. Raise ConnectorError(mutated=...) on failure."""

    @abstractmethod
    def health(self) -> bool:
        """Cheap reachability check used by the runbook and status page."""


class ConnectorRegistry:
    """Per-process registry. Products register connectors at import time."""

    def __init__(self) -> None:
        self._types: dict[str, type[Connector]] = {}

    def register(self, cls: type[Connector]) -> type[Connector]:
        if not getattr(cls, "key", None):
            raise ValueError(f"{cls.__name__} must define a class-level `key`")
        if cls.key in self._types:
            raise ValueError(f"connector key {cls.key!r} is already registered")
        for a in cls.ACTIONS:
            if a.reversible and a.undo not in {x.name for x in cls.ACTIONS}:
                raise ValueError(
                    f"{cls.key}.{a.name} names undo {a.undo!r}, which it does not expose"
                )
        self._types[cls.key] = cls
        return cls

    def build(self, key: str, org_id: UUID, credentials: dict[str, str]) -> Connector:
        if key not in self._types:
            raise ConnectorError(f"no connector registered for {key!r}", mutated=False)
        return self._types[key](org_id, credentials)

    def keys(self) -> list[str]:
        return sorted(self._types)


registry = ConnectorRegistry()
