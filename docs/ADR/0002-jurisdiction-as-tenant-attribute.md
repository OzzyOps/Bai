# ADR 0002 — Jurisdiction is a tenant attribute, never a global constant

**Status:** Accepted · **Date:** 2026-08-27 · **Owner:** SecOps
**Supersedes:** the UK/EU-only assumption from Phase 0 v2.0

## Context

The CEO set global compliance and multi-currency as a requirement. The initial
foundation assumed a single market (UK/EU, GBP, en-GB).

## Decision

No code path, schema, prompt, price or string may assume a country, currency,
language, legal basis or regulator. Every tenant carries `region`,
`jurisdictions[]`, `currency`, `locale` and `timezone`, and behaviour resolves
from those at runtime.

Residency is enforced by **physical separation** — one Supabase project and one
Fly region per BAi region, with no cross-region replication.

## Rationale

This is the most expensive decision to retrofit and among the cheapest to adopt
at genesis. Retrofitting means touching every query, every format call, every
price and every prompt — and the failures are silent: a JPY amount rendered with
two decimal places is off by a factor of 100 and looks completely plausible.

Physical separation also removes the cross-border transfer question entirely
rather than answering it with paperwork. There is no second copy to disclose, to
chase on erasure, or to explain to a regulator.

## Consequences

- **Cost:** six regions multiply infrastructure and operational burden from day
  one. Logged as risk R5, with the recommendation to *launch* on two regions
  while keeping the architecture six-region-ready.
- Money is `bigint` minor units plus ISO 4217 everywhere. Never a float, never
  assumed two decimals.
- Locale, currency and region resolve **independently** — a Brazilian tenant may
  hold a USD contract and report in EUR.
- FX rates are pinned and dated. Nothing converts at display time; a figure that
  moves with the spot rate cannot be budgeted against or reconciled later.
- The certification estate must be scoped around the **platform** so new products
  fall inside it without re-audit. Unconfirmed with an auditor — risk R4.
