# BAi Platform — Foundational Tech Architecture
**Version:** 2.0 (v1.0 void) · **Phase 0 Genesis** · **Owner:** TL Pod
**Governing constraint:** enterprise B2B SaaS · multi-tenant · RBAC-enforced · UK/EU residency
**Scope:** the shared substrate every "by BAi" product is built on. No product internals — a
product is a *domain layer* over this, delivered in Phase 3.

---

## 1. Stack Decision Record

| Layer | Choice | Rationale | Rejected |
|---|---|---|---|
| Frontend | React 19 + TypeScript (strict) + Vite | Fast HMR, no framework lock-in, static deploy | Next.js — SSR adds a server auth surface an authed app doesn't need |
| Styling | Tailwind v4 + shadcn/ui | Tokens compile into the theme; owned components, not a dependency | MUI — fights the token system |
| State | TanStack Query + Zustand | Server state ≠ client state | Redux — ceremony without benefit |
| Backend | Python 3.12 + FastAPI + Pydantic v2 | Async, typed contracts, auto-OpenAPI → generated TS client | Django — ORM redundant beside Supabase |
| Packages | `uv` (Python) · `pnpm` (JS) | Lockfile-first, fast | poetry / npm |
| Orchestration | Celery + Redis | Agentic runs are minutes-long, must be durable and retryable | FastAPI BackgroundTasks — no durability |
| Database | Supabase Postgres 16, EU-West (London) | RLS = tenant isolation in the engine, not the app | Raw RDS — rebuilds auth/storage/realtime by hand |
| Vectors | `pgvector`, same Postgres | One store; RLS applies to embeddings too | Pinecone — a second system with a separate auth model |
| Auth | Supabase Auth + SAML SSO (enterprise) | JWT carries tenant + role claims consumed directly by RLS | Auth0 — cost, worse RLS integration |
| Files | Supabase Storage, private buckets | Same RLS model, short-TTL signed URLs | S3 direct — separate policy surface |
| AI | Anthropic Claude via API | Long-context reasoning; enterprise terms; zero-retention routing | — |
| CI/CD | GitHub Actions | PR gates, environments, OIDC deploys | — |
| Hosting | Vercel (web) · Fly.io **LHR** (API + workers) | EU residency end-to-end | US regions — breaks the residency promise |
| Telemetry | PostHog (EU Cloud) + Sentry | Product analytics + errors, both EU-resident | Mixpanel — US-default residency |

### The rule everything else serves

> **Tenant isolation is enforced by Postgres Row Level Security, never by application code.**
> Every tenant table carries `org_id`. Every policy derives `org_id` from the JWT. User-facing
> routes use the caller's JWT. `service_role` exists **only** in workers, on explicitly scoped
> paths, and never behind a user-facing route.

Rationale: application-layer isolation fails open on the first forgotten `WHERE` clause. Engine-
layer isolation fails closed. In a multi-product portfolio sharing one platform, a single leak
is an extinction event across the whole brand — not one product.

---

## 2. Platform / Product Boundary

This boundary *is* the business model (see BUSINESS_MODEL_CANVAS §0). It must be defended.

```
┌─ PLATFORM (packages/) ───────── built once, inherited by every product ─┐
│ tenancy · RBAC · audit · connectors · ingestion · agent orchestration    │
│ human-in-the-loop escalation · evaluation harness · billing · tokens · UI│
└─────────────────────────────────────────────────────────────────────────┘
┌─ PRODUCT (apps/<product>/) ──── the only part that is domain-specific ──┐
│ domain schema · agent definitions + prompts · golden set · domain UI     │
│ theme token overrides · product routes                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Governance rule:** if a product needs something from the platform, it is added to the
platform — never forked into the product. A CODEOWNERS gate on `packages/` enforces TL review.
Reuse percentage is instrumented per product and reported to the Blackboard (validates
assumption A1).

---

## 3. Repository Structure

**Monorepo.** pnpm workspaces + uv workspace. One repo, shared platform, N products.

```
bai/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint · typecheck · test · token-validate
│   │   ├── deploy-web.yml          # Vercel, on main
│   │   ├── deploy-api.yml          # Fly.io LHR, on main
│   │   ├── db-migrate.yml          # Supabase migrations, manual approval gate
│   │   ├── eval-harness.yml        # agent accuracy regression gate — BLOCKING
│   │   ├── platform-reuse.yml      # reports product substrate-reuse %
│   │   └── security.yml            # CodeQL · gitleaks · pip-audit · pnpm audit
│   ├── CODEOWNERS                  # packages/** requires TL review
│   └── pull_request_template.md
│
├── packages/                       # ══ THE PLATFORM ══
│   ├── tokens/                     # bai-core + per-product themes
│   │   ├── src/{bai-core.tokens.json,<product>.theme.json}
│   │   ├── build.ts                # → css vars · tailwind preset · ts consts
│   │   └── dist/
│   ├── ui/                         # cross-product React primitives
│   │   └── src/{primitives,evidence,confidence,escalation,rbac}/
│   ├── platform-py/                # shared Python substrate
│   │   └── src/bai_platform/
│   │       ├── tenancy/            # org context, JWT claims, RLS helpers
│   │       ├── rbac/               # permission matrix, decorators
│   │       ├── audit/              # append-only trail writer
│   │       ├── connectors/         # base protocol + certified integrations
│   │       ├── ingestion/          # parse · chunk · embed · dedupe by hash
│   │       ├── agents/             # orchestration, tool registry, run state
│   │       │   ├── runner.py       # durable multi-step agent execution
│   │       │   ├── escalation.py   # human-in-the-loop boundary
│   │       │   ├── provenance.py   # source + span + confidence on every fact
│   │       │   └── budget.py       # per-tenant inference spend guard
│   │       ├── llm/                # Anthropic client, routing, prompt caching
│   │       └── evals/              # golden-set runner, regression gates
│   ├── types/                      # generated DB + OpenAPI types
│   └── config/                     # shared eslint · tsconfig · ruff · prettier
│
├── apps/
│   ├── web/                        # shell: auth, org switcher, settings, product mount
│   │   └── src/{routes,components,lib,hooks,styles}/
│   ├── api/                        # FastAPI — thin, typed, RLS-respecting
│   │   └── src/bai_api/{routers,schemas,services,middleware,core}/
│   ├── workers/                    # Celery — agent execution
│   │   └── src/bai_workers/{tasks,beat}/
│   └── _product-template/          # scaffold for product N
│       ├── schema/                 # domain migrations
│       ├── agents/                 # definitions + versioned prompts
│       ├── evals/golden/           # annotated corpus — REQUIRED to ship
│       ├── ui/
│       └── theme.json
│
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   │   ├── 20260101000000_extensions.sql        # pgvector, pgcrypto, pg_cron
│   │   ├── 20260101000100_orgs_and_rbac.sql
│   │   ├── 20260101000200_records.sql           # generic tenant record spine
│   │   ├── 20260101000300_documents.sql
│   │   ├── 20260101000400_agent_runs.sql
│   │   ├── 20260101000500_escalations.sql
│   │   ├── 20260101000600_vectors.sql
│   │   ├── 20260101000700_audit.sql             # append-only, no UPDATE/DELETE grant
│   │   └── 20260101000800_rls_policies.sql
│   └── seed.sql
│
├── scripts/{bootstrap.sh,validate-tokens.py,gen-types.sh,eval/run_golden_set.py}
├── docs/{ARCHITECTURE.md,RBAC.md,DATA_RETENTION.md,RUNBOOK.md,ADR/}
├── .env.example · pnpm-workspace.yaml · package.json · pyproject.toml · README.md
```

---

## 4. RBAC Model — the compliance backbone

**Five roles, defined at platform level. Products may add permissions, never roles.**

| Role | Records | Documents | Agent runs | Escalations | Members | Billing | Audit |
|---|---|---|---|---|---|---|---|
| `owner` | all · CRUD | CRUD | run/cancel | resolve | manage | manage | read |
| `admin` | all · CRUD | CRUD | run/cancel | resolve | manage | — | read |
| `manager` | assigned · CRU | CRU | run | resolve | — | — | — |
| `operator` | assigned · read | read | run | **resolve** | — | — | — |
| `viewer` | assigned · read | read | read | read | — | — | — |

`operator` is the load-bearing role: it can clear the exception queue without being able to
change the record. That separation is what makes the escalation queue delegable — and
delegability is what makes the product economically worthwhile.

**`restricted_record`** — per-record ACL for commercially sensitive items. Even `owner` is
excluded unless explicitly granted, and grants are themselves audited. *(Generalised from the
voided v1.0 `restricted_contract`.)* This is the control that survives enterprise security review.

**JWT claim shape** (set by a Supabase Auth hook):
```json
{ "sub": "<user_uuid>", "org_id": "<uuid>", "role": "operator", "tier": "enterprise" }
```

**Canonical RLS pattern** — every tenant table follows it:
```sql
create policy "tenant_isolation_select" on public.records
for select to authenticated
using (
  org_id = (auth.jwt() ->> 'org_id')::uuid
  and (
    (auth.jwt() ->> 'role') in ('owner','admin')
    or exists (
      select 1 from public.record_assignments ra
      where ra.record_id = records.id and ra.user_id = auth.uid()
    )
  )
  and (
    not exists (select 1 from public.record_restrictions rr where rr.record_id = records.id)
    or exists (
      select 1 from public.record_restriction_grants g
      where g.record_id = records.id and g.user_id = auth.uid()
    )
  )
);
```
*(Full policy set — every table, every verb — is a Phase 3 deliverable.)*

---

## 5. Agent Execution Model

```
trigger → plan → [ act ⇄ observe ]* → verify → { commit | escalate } → audit
```

**Five platform-level invariants, binding on every product:**

1. **Durable runs.** Each step persists to `agent_runs` with input hash, output, tokens, cost
   and latency. A crash resumes; it never silently restarts or double-acts.
2. **Provenance on every fact.** `{source_id, locator, char_span, confidence}`. Facts below the
   confidence floor render as `unknown` — never as success. *(Retained UR finding.)*
3. **Escalation is a first-class outcome, not an error.** Consequential actions — financial,
   legal, contractual, or irreversible — require human approval by default. Autonomy is granted
   per action type, per tenant, and only on evidenced accuracy.
4. **Every write is reversible or approved.** No agent performs an unlogged, unapproved,
   irreversible action against a customer system. Connectors declare reversibility; the runner
   enforces it.
5. **Budget guard.** Hard per-tenant monthly inference ceiling with alerting at 70/90/100%.

**Cost engineering:** prompt-cache the domain rubric (largest single saving), route extraction
to a cheaper model and reasoning to the frontier model, dedupe by SHA-256 content hash.

---

## 6. Environments & Secrets

| Env | Supabase | API | Web | Data |
|---|---|---|---|---|
| local | CLI (Docker) | uvicorn :8000 | vite :5173 | seeded synthetic |
| preview | branch DB | Fly preview | Vercel preview | **synthetic only — never production data** |
| staging | staging project (LHR) | `bai-api-staging` | Vercel staging | anonymised |
| production | prod project (LHR) | `bai-api` | Vercel prod | live, PII |

Secrets via GitHub OIDC → Fly/Vercel; no long-lived cloud keys in Actions.
`SUPABASE_SERVICE_ROLE_KEY` exists **only** in the workers environment. `gitleaks` on every PR.

---

## 7. Quality Gates (CI must pass to merge)

1. `eslint` + `tsc --noEmit` (strict) · `ruff` + `mypy --strict`
2. `pytest` ≥80% on `bai_platform/` and `tasks/`; `vitest` on `lib/` and `components/`
3. `validate-tokens.py` — fails if a product theme overrides a `$locked` path
4. **Agent eval gate — BLOCKING.** Per-product golden set; merge blocked if accuracy on the
   product's declared output fields regresses >2%. *No product ships without a golden set.*
   *(Retained from v1.0 — Data's finding generalises: we sell correctness, so we measure it.)*
5. **RLS test suite** — every tenant table asserted unreadable cross-org by an authenticated user.
   A new table without an RLS test fails the build.
6. **Escalation-boundary test** — every action typed `consequential` asserted to require approval.
7. `CodeQL` · `gitleaks` · `pip-audit` · `pnpm audit`
