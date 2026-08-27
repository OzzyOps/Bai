# ADR 0001 — Tenant isolation in Postgres RLS, not application code

**Status:** Accepted · **Date:** 2026-08-27 · **Owner:** Tech Lead

## Context

BAi is multi-tenant and will host several products on one substrate. Isolation
can live in the application (every query filtered by `org_id`) or in the database
(RLS policies evaluated by Postgres).

## Decision

**Isolation is enforced by Postgres RLS.** Every tenant table carries `org_id`.
Every policy derives it from the JWT. User-facing services forward the caller's
token; the service-role key exists only in workers.

## Rationale

Application-layer isolation **fails open**. One forgotten `WHERE` clause in one
handler exposes every tenant, and nothing detects it until someone reports seeing
another company's data.

Engine-layer isolation **fails closed**. A missing policy returns nothing, which
surfaces as a visible bug in development rather than a silent breach in
production.

The asymmetry matters more here than in a single-product company: with one shared
platform, a single leak damages every product's trust, not one product's.

## Consequences

- Every new tenant table needs a policy **and** a cross-org test before merge.
  `scripts/assert_rls_coverage.sql` fails CI otherwise.
- Application-layer permission checks remain, as defence in depth and for good
  error messages. They are explicitly **not** the boundary.
- Workers bypass RLS and must filter by `org_id` by hand. This is why nothing
  user-facing runs in a worker.
- Queries in routers deliberately omit an `org_id` filter. That is not an
  oversight; adding one would imply isolation lives in Python.

## Alternatives rejected

**Schema-per-tenant** — clean isolation, but migrations across thousands of
schemas become the dominant operational cost.

**Database-per-tenant** — strongest isolation, unaffordable at mid-market price
points, and connection management becomes the bottleneck.
