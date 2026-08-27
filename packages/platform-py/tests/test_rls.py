"""Cross-org isolation tests.

Referenced by .github/workflows/ci.yml. These run against a live local Supabase
(`supabase start && supabase db reset`) because RLS cannot be unit-tested — the
policy is evaluated by Postgres, so the only honest test uses Postgres.

Skipped when no database is configured, so `pytest` still passes locally.
"""

from __future__ import annotations

import os

import pytest

DB_URL = os.environ.get("SUPABASE_DB_URL")
pytestmark = pytest.mark.skipif(
    not DB_URL, reason="SUPABASE_DB_URL not set; start Supabase to run isolation tests"
)

psycopg = pytest.importorskip("psycopg")

ORG_A = "00000000-0000-0000-0000-0000000000a1"
ORG_B = "00000000-0000-0000-0000-0000000000b1"
USER_A = "00000000-0000-0000-0000-00000000a001"
USER_B = "00000000-0000-0000-0000-00000000b001"


def as_user(conn, *, org_id: str, user_id: str, role: str) -> None:
    """Impersonate an authenticated user so RLS policies evaluate."""
    conn.execute("set local role authenticated")
    conn.execute(
        "select set_config('request.jwt.claims', %s, true)",
        (f'{{"sub":"{user_id}","org_id":"{org_id}","role":"{role}"}}',),
    )


@pytest.fixture
def conn():
    with psycopg.connect(DB_URL, autocommit=False) as c:
        yield c
        c.rollback()


TENANT_TABLES = [
    "records", "documents", "document_chunks", "agent_runs",
    "agent_steps", "agent_facts", "escalations", "autonomy_grants", "audit_log",
]


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_cross_org_read_returns_nothing(conn, table: str) -> None:
    """A user of org A must never see a row belonging to org B."""
    with conn.transaction():
        as_user(conn, org_id=ORG_A, user_id=USER_A, role="admin")
        rows = conn.execute(
            f"select count(*) from public.{table} where org_id = %s", (ORG_B,)
        ).fetchone()
        assert rows[0] == 0, f"{table} leaked rows from another org"


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_rls_is_enabled(conn, table: str) -> None:
    row = conn.execute(
        "select relrowsecurity from pg_class where relname = %s", (table,)
    ).fetchone()
    assert row and row[0], f"RLS is not enabled on {table}"


def test_audit_log_is_append_only(conn) -> None:
    """No role, including owner, may rewrite history.

    Two defences guard this: the migration REVOKEs update/delete, and a trigger
    raises on any mutation. The outer defence fires first, so asserting only the
    trigger's exception type would fail against a correctly configured database.
    Assert the property — the write is refused — then prove the inner defence
    separately below, so neither can silently stop working behind the other.
    """
    with conn.transaction():
        as_user(conn, org_id=ORG_A, user_id=USER_A, role="owner")
        with pytest.raises(
            (psycopg.errors.InsufficientPrivilege, psycopg.errors.RaiseException)
        ):
            conn.execute("update public.audit_log set action = 'tampered'")


def test_audit_trigger_blocks_mutation_for_a_privileged_connection(conn) -> None:
    """The innermost defence, tested on its own.

    Three things stop an UPDATE on audit_log: the migration's REVOKE, the
    absence of any UPDATE policy, and the trigger. For an ordinary user the
    first two fire and the trigger is never reached — so a broken trigger would
    go unnoticed until the day something connects with elevated rights (a
    migration, a support script, a service-role worker).

    This runs as the connection's own role, which is not subject to RLS, so the
    trigger is the only thing left. Rolled back either way.
    """
    with conn.transaction(), pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("update public.audit_log set action = 'tampered'")

    with conn.transaction(), pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("delete from public.audit_log")


def test_audit_fixture_is_not_empty(conn) -> None:
    """Guards the test above from passing vacuously.

    A per-row trigger never fires on an empty table, so `update audit_log`
    would succeed with 0 rows and prove nothing. The seed must supply rows.
    """
    with conn.transaction():
        rows = conn.execute("select count(*) from public.audit_log").fetchone()
        assert rows[0] > 0, "seed.sql supplies no audit rows; append-only test is vacuous"


def test_cannot_self_grant_restricted_access(conn) -> None:
    """Granting yourself access to a restricted record is the exact escalation
    the restriction table exists to prevent.

    The WITH CHECK clause rejects the row outright rather than filtering it, so
    the honest assertion is that the statement is refused — not that it quietly
    inserts nothing.
    """
    with conn.transaction():
        as_user(conn, org_id=ORG_A, user_id=USER_A, role="admin")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "insert into public.record_restriction_grants (record_id, user_id) "
                "select id, %s from public.records limit 1",
                (USER_A,),
            )


def test_restricted_record_is_invisible_without_a_grant(conn) -> None:
    """The restriction is only real if the row actually disappears.

    Org B's restricted record must be invisible to org B's own admin — the
    control that survives enterprise security review is the one that excludes
    the administrator too.
    """
    with conn.transaction():
        as_user(conn, org_id=ORG_B, user_id=USER_B, role="admin")
        rows = conn.execute(
            "select count(*) from public.records where external_ref = 'B-2'"
        ).fetchone()
        assert rows[0] == 0, "a restricted record was visible without an explicit grant"

        visible = conn.execute(
            "select count(*) from public.records where external_ref = 'B-1'"
        ).fetchone()
        assert visible[0] == 1, "an unrestricted record in the user's own org was hidden"


def test_cannot_grant_autonomy_for_irreversible_action(conn) -> None:
    """Invariant 4 is enforced by a database trigger, not only in Python."""
    with conn.transaction():
        as_user(conn, org_id=ORG_A, user_id=USER_A, role="owner")
        with pytest.raises(psycopg.errors.RaiseException, match="irreversible"):
            conn.execute(
                "insert into public.autonomy_grants "
                "(org_id, action_name, level, consequence, reversible) "
                "values (%s, 'post_payment', 'act', 'consequential', false)",
                (ORG_A,),
            )


def test_reading_records_does_not_recurse_when_a_restriction_exists(conn) -> None:
    """Regression: policy recursion made `records` unreadable.

    `record_visible` read record_restrictions, whose policy read records, whose
    policy called record_visible. With one restriction row present, a plain
    count over records died with 54001 statement_too_complex — the core table
    unreadable for the entire org. Fixed in 20260101001000 by making the policy
    helpers SECURITY DEFINER so they do not re-enter RLS.

    The seed keeps a restricted record in org B precisely so this stays honest.
    """
    with conn.transaction():
        restricted = conn.execute(
            "select count(*) from public.record_restrictions"
        ).fetchone()
        assert restricted[0] > 0, "no restriction rows; this regression test proves nothing"

    for org, user in ((ORG_A, USER_A), (ORG_B, USER_B)):
        with conn.transaction():
            as_user(conn, org_id=org, user_id=user, role="admin")
            conn.execute("select count(*) from public.records").fetchone()
            conn.execute("select count(*) from public.documents").fetchone()
            conn.execute("select count(*) from public.escalations").fetchone()


def test_policy_helpers_have_a_pinned_search_path(conn) -> None:
    """A SECURITY DEFINER function without a pinned search_path is an
    escalation waiting to happen: the caller shadows `public` and the function
    runs their code with the definer's rights."""
    rows = conn.execute(
        """
        select p.proname, p.proconfig
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and p.prosecdef
        """
    ).fetchall()
    assert rows, "expected at least one SECURITY DEFINER helper"
    for name, config in rows:
        assert config and any(
            c.startswith("search_path=") for c in config
        ), f"{name} is SECURITY DEFINER with no pinned search_path"
