"""Connector declarations and the registry.

Untested before. This is the boundary where an agent touches a system of
record, and the guarantee it carries — every write is reversible or approved —
is only as good as the declarations the registry refuses to accept.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from bai_platform.agents import Consequence
from bai_platform.connectors import (
    Connector,
    ConnectorAction,
    ConnectorError,
    ConnectorRegistry,
)

READ = ConnectorAction(
    name="list_invoices",
    description="Read invoices.",
    consequence=Consequence.NONE,
    reversible=False,
)
WRITE = ConnectorAction(
    name="post_invoice",
    description="Post an invoice.",
    consequence=Consequence.CONSEQUENTIAL,
    reversible=True,
    undo="void_invoice",
)
UNDO = ConnectorAction(
    name="void_invoice",
    description="Void a posted invoice.",
    consequence=Consequence.CONSEQUENTIAL,
    reversible=False,
)


class Ledger(Connector):
    key = "test_ledger"
    ACTIONS = (READ, WRITE, UNDO)

    def execute(self, action: ConnectorAction, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "action": action.name, "payload": payload}

    def health(self) -> bool:
        return True


# ── declarations ───────────────────────────────────────────────────────────


def test_a_reversible_action_must_name_how_it_is_reversed() -> None:
    """"Reversible" with no undo is a promise nothing can keep."""
    with pytest.raises(ValueError, match="names no undo action"):
        ConnectorAction(
            name="post_payment",
            description="",
            consequence=Consequence.CONSEQUENTIAL,
            reversible=True,
        )


def test_a_read_only_action_cannot_claim_reversibility() -> None:
    with pytest.raises(ValueError, match="read-only"):
        ConnectorAction(
            name="list_things",
            description="",
            consequence=Consequence.NONE,
            reversible=True,
            undo="unlist_things",
        )


def test_an_action_spec_carries_the_declaration_to_the_runner() -> None:
    spec = WRITE.to_spec({"invoice_id": "INV-1"})
    assert spec.name == "post_invoice"
    assert spec.consequence is Consequence.CONSEQUENTIAL
    assert spec.reversible is True
    assert spec.payload == {"invoice_id": "INV-1"}


# ── registry ───────────────────────────────────────────────────────────────


def test_registering_and_building_a_connector() -> None:
    registry = ConnectorRegistry()
    registry.register(Ledger)
    assert registry.keys() == ["test_ledger"]

    conn = registry.build("test_ledger", uuid4(), {"token": "x"})
    assert isinstance(conn, Ledger)
    assert conn.execute(WRITE, {"a": 1})["ok"] is True


def test_a_connector_without_a_key_is_refused() -> None:
    class Anonymous(Ledger):
        key = ""

    with pytest.raises(ValueError, match="class-level `key`"):
        ConnectorRegistry().register(Anonymous)


def test_a_duplicate_key_is_refused() -> None:
    registry = ConnectorRegistry()
    registry.register(Ledger)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Ledger)


def test_an_undo_the_connector_does_not_expose_is_refused_at_registration() -> None:
    """The check that matters. A connector claiming an action is reversible via
    an undo it cannot perform would let the runner grant autonomy for a write it
    can never take back — and it would only be discovered at the moment of
    needing to undo it."""

    class Broken(Connector):
        key = "broken"
        ACTIONS = (
            ConnectorAction(
                name="post_invoice",
                description="",
                consequence=Consequence.CONSEQUENTIAL,
                reversible=True,
                undo="void_invoice",   # never declared below
            ),
        )

        def execute(self, action: ConnectorAction, payload: dict[str, Any]) -> dict[str, Any]:
            return {}

        def health(self) -> bool:
            return True

    with pytest.raises(ValueError, match="which it does not expose"):
        ConnectorRegistry().register(Broken)


def test_building_an_unregistered_key_fails_without_claiming_a_mutation() -> None:
    with pytest.raises(ConnectorError) as exc:
        ConnectorRegistry().build("nope", uuid4(), {})
    assert exc.value.mutated is False


def test_an_undeclared_action_cannot_be_reached() -> None:
    """Anything not published is unreachable — which is what stops ingested
    document content from steering an agent into an action nobody offered."""
    conn = Ledger(uuid4(), {})
    assert conn.action("post_invoice") is WRITE
    with pytest.raises(ConnectorError, match="no action named"):
        conn.action("delete_everything")


def test_connector_errors_say_whether_the_remote_system_changed() -> None:
    """After a failure the only question that matters is whether to retry."""
    err = ConnectorError("timeout after the POST", mutated=True)
    assert err.mutated is True
    assert ConnectorError("refused before sending", mutated=False).mutated is False
