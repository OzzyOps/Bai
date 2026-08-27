# THE SHARED BLACKBOARD
**Single source of approved truth. Agents read only from here.**
Written by: The Overlord · **Phase 0 COMPLETE — company operational**
v1.0 retracted in full — see `VOID_LOG.md`

---

## COMPANY STATE
| Key | Value | Status |
|---|---|---|
| `entity.name` | BAi | **CONFIRMED BY CEO** |
| `entity.model` | Holding brand; products endorsed "by BAi" | **CONFIRMED BY CEO** |
| `entity.domain` | B2B SaaS · operational technology + fintech + AI workflow automation | **CONFIRMED BY CEO** |
| `entity.compliance_posture` | **Global**, multi-region, multi-currency | **CONFIRMED BY CEO** |
| `entity.visual_direction` | Ink `#0A0E13` · Meridian `#0E6E62` · Flux `#1FD1B2` · warm neutrals | **APPROVED BY CEO** |
| `entity.mission` | We remove the work that shouldn't need a human. | PROPOSED |
| `entity.category` | Operational Intelligence | PROPOSED |
| `entity.thesis` | The seam between systems is the product | PROPOSED |
| `entity.regions` | eu · uk · us · apac · jp · br (physically isolated) | PROPOSED |
| `entity.deferred_market` | Mainland China / PIPL — distinct programme, not a region toggle | PROPOSED |

## PRODUCT REGISTRY
| Product | Status |
|---|---|
| — | **NONE DEFINED.** Phase 1 input required from the CEO. |

## EXPLICITLY OUT OF SCOPE
| Item | Ruling |
|---|---|
| **ContractIQ** and all assets under `~/Desktop/ContractIQ` | **Constitutes no part of this project.** Confirmed by the CEO. Not a reference, not a precedent, not a Phase 1 candidate. |

## AGENT ROSTER — OPERATIONAL
`.claude/agents/` · 12 agents · invoke by name, the Overlord routes

| Pod | Agents | Model |
|---|---|---|
| Supervisor | `overlord` | opus |
| Generators | `product-manager` · `tech-lead` · `product-designer` · `brand` | opus |
| Generators | `content-designer` | sonnet |
| Evaluators | `user-researcher` · `secops` · `data-analyst` | opus |
| Synthesizers | `service-designer` · `product-marketing` | opus |
| Synthesizers | `implementation-ops` | sonnet |

## LOCKED DECISIONS — only the Overlord may reopen, in writing, with a reason
1. Tenant isolation lives in Postgres RLS, never in application code.
2. The platform/product boundary is defended: a product need becomes a platform feature, never a fork.
3. Semantic and confidence colours, type scale, spacing, motion and a11y floors are fixed ecosystem-wide.
4. Price on work removed, not seats. The exception queue is never metered.
5. Every agent-produced fact carries source, locator, span and confidence.
6. Consequential actions require human approval by default; autonomy is earned per action type, per tenant, on evidenced accuracy.
7. No product ships without a golden-set eval and a CI regression gate.
8. **Jurisdiction is a tenant attribute, never a global constant.**

## BUILT AND VERIFIED
| Component | Path | Verification |
|---|---|---|
| Agent roster | `.claude/agents/*.md` | 12 definitions, routing table consistent |
| Design tokens | `packages/tokens/src/` | 142 tokens · validator passes · 0 violations |
| Money (multi-currency) | `.../bai_platform/money/` | **16/16 logic checks** — JPY 0dp, KWD 3dp, float rejected, cross-currency rejected, allocation exact |
| i18n / regions | `.../bai_platform/i18n/` | currency resolves independently of locale and region |
| RBAC matrix | `.../bai_platform/rbac/` | **17/17 checks** — monotonic ladder, operator separation, fail-closed |
| Agent substrate | `.../bai_platform/agents/` | **16/16 checks** — all five invariants enforced |
| RLS policies | `supabase/migrations/` | 14 policies · self-grant and self-escalation blocked |
| CI gates | `.github/workflows/` | 7 gates incl. eval harness and service_role leak scan |
| Test suites | `packages/platform-py/tests/` | money · rbac · agents |

**Superseded by the verification pass below.** The table above recorded what was written. It is
now also a record of what was *executed*, which is not the same thing and had not been done.

## VERIFICATION PASS — executed, not asserted
Every claim above was re-tested against a live Postgres 16 and a real build. Six defects were
found, all of which would have surfaced in front of a customer or a candidate.

| # | Defect | Severity | Status |
|---|---|---|---|
| V1 | **RLS policy recursion.** `record_visible()` read `record_restrictions`, whose policy read `records`, whose policy called `record_visible()`. With one restriction row present, `select count(*) from records` failed with `54001 statement_too_complex`. The core table was unreadable for the whole org from the moment the first sensitive record was restricted. | **CRITICAL** | Fixed — `20260101001000_fix_policy_recursion.sql`, helpers now `security definer` with pinned `search_path`; regression test added |
| V2 | **The isolation tests proved nothing.** `seed.sql` created orgs `e1/e2/e3`; `test_rls.py` asserted against orgs `a1/b1`. "0 rows leaked" was trivially true of tables with no rows to leak. The append-only test likewise ran against an empty `audit_log`, where a per-row trigger never fires. | **CRITICAL** | Fixed — isolation fixture added to `seed.sql`; a test now fails if the fixture is empty |
| V3 | **CI's tenancy gate never ran.** The `rls` job called pytest without `SUPABASE_DB_URL`, so every isolation test SKIPPED and the job went green. It also used `uv` without installing it. | **CRITICAL** | Fixed — Postgres service container, and the job now fails if any isolation test is skipped |
| V4 | **The web app did not build.** Seven TypeScript errors, then a Rollup parse failure: `packages/tokens/build.ts` emitted TypeScript syntax into `dist/index.js`. Nothing compiled that file, so it typechecked and failed only at bundle time. CI never ran `pnpm build`. | **BLOCKING** | Fixed — emitter corrected, types moved to `index.d.ts`, `pnpm build` added as a CI gate |
| V5 | **`pnpm lint`, `typecheck` and `test` all failed at the root** ("eslint/tsc/vitest: not found"), there was no `eslint.config.js` anywhere a linter would look, and there were no front-end tests at all. | **BLOCKING** | Fixed — scripts delegate to the workspace, ESLint wired to `@bai/config`, 15 tests added covering money, confidence and the escalation surface |
| V6 | **The `service_role` gate failed on its own guard.** The scan flagged `assert_no_service_role` — the function that *prevents* the leak — so the gate failed on every run. | MATERIAL | Fixed — guard marked and exempted; a second check asserts the guard still exists |

### Second pass — the agent company itself
The verification above covered the platform. The company that builds on it — twelve agents, a
routing table, a phase ladder — had never been checked at all.

| # | Defect | Severity | Status |
|---|---|---|---|
| V7 | **The phase ladder did not exist.** "Phase 1" was referenced eleven times across the repo and defined nowhere: no phase list, no stages, no order, no statement of what a gate consists of. The Overlord was instructed not to begin phase N+1 before phase N was approved, with N undefined. | **BLOCKING** | Fixed — `company/ORCHESTRATION.yaml`, ten phases, each with stages, roles and a gate |
| V8 | **Nothing routed by brief type.** The routing table mapped *needs* to agents. A GTM request and a greenfield product took the same undefined path, and a compliance question would have been answered by whoever was asked first. | **BLOCKING** | Fixed — eight brief types, each with an ordered phase list and a named entry agent |
| V9 | **The routing rules disagreed with themselves in three places.** `overlord.md` said tech-lead was evaluated by SecOps *and* Data; tech-lead's own description promised SecOps only. Same for product-designer (SecOps missing) and service-designer (no evaluator declared at all). Claude Code routes on the `description` field, so in each case the second evaluator never ran and the prose table was decorative. | **CRITICAL** | Fixed — one spec, descriptions aligned to it, CI fails if they drift again |
| V10 | **Two evaluators had no evaluator.** UR's discovery studies and Data's golden sets are artefacts like any other, and both were unchecked — an unchecked golden set is how a product comes to measure the wrong thing very precisely. | MATERIAL | Fixed — both now checked by the PM, who is accountable for what is sold |
| V11 | Tech-lead was instructed to emit a `vercel.json`. The company runs on Fly and GitHub Pages. | ADVISORY | Fixed |

**Verified about the roster, not assumed:** all twelve agent files parse; every `name` matches
its filename (a mismatch makes an agent unreachable however good the prompt); every model is a
real alias; only the Overlord holds the `Agent` tool, so no generator can commission its own
evaluation; every producing agent has an assigned evaluator; no phase opens with an evaluation;
no phase lacks a gate; every brief's entry agent is the one that actually runs first; and no
agent is on the roster that no brief could ever reach.

`scripts/validate_orchestration.py` enforces all of it, and 26 tests enforce the validator —
eighteen of them corrupt a copy of the repo in a specific way and fail if the validator does not
notice. A gate nobody has watched fail is decoration; that lesson was learned twice this week.

**Now measured, not claimed:**
- 168 Python tests pass against a live database, 0 skipped; coverage **97%** (gate is 80%).
- The orchestration spec validates: 12 agents, 4 pods, 10 phases, 33 stages, 8 brief routes.
- 15 front-end tests pass; `pnpm lint`, `typecheck`, `test` and `build` all clean.
- `ruff` clean; `mypy --strict` clean across 36 files.
- All 9 migrations apply from empty; RLS coverage gate passes; tenant isolation verified with
  rows present in both orgs.
- Ruff's rule set is now pinned in `pyproject.toml`: an unpinned `ruff>=0.7` meant the lint gate
  could start failing on a commit that changed nothing.

## OPEN RISKS
| ID | Risk | Owner | Gate |
|---|---|---|---|
| R1 | No product defined — the foundation is unfalsifiable until one exists | Overlord | Phase 1 |
| R2 | Substrate reuse (~65% for product 2) is the economic thesis and is unvalidated | TL / PM | Phase 2 |
| R3 | Buyer identity (Operations vs IT) unvalidated | UR | Phase 1 |
| R4 | Compliance-scope inheritance across products unconfirmed with auditor (BMC A5) | SecOps | Phase 2 |
| R5 | Six-region isolation multiplies infra cost and operational burden from day one | TL / Ops | Phase 1 — **may warrant launching with 2 regions** |
| R6 | ~~Platform modules unexecuted on target runtime~~ — **CLOSED.** Executed on 3.11 against a live Postgres 16: 142 tests, 0 skipped. Target remains 3.12; nothing in the code is version-sensitive. | TL | Closed |
| R7 | The `claude-proxy` Edge Function defaulted to `ALLOWED_ORIGINS="*"` — an open proxy to a paid Anthropic account for anyone who found the URL. Now fails closed. Still has no rate limit: a permitted origin can still spend. | SecOps | Before public launch |

## METHOD CORRECTION (standing)
The Overlord may not promote an environmental observation to a Blackboard fact.
Observations enter as `UNVERIFIED` and require the CEO's explicit confirmation.

## PHASE GATE
`PHASE 0 — COMPLETE AND VERIFIED. Company operational, agents ready, substrate proven to run.`
→ next: `PHASE 1 STRATEGIC CONTEXT`

**Phase 1 requires one input from the CEO: the first product.** Everything else is built. The
foundation now runs, and — more usefully — it now fails when it is broken, which it did not
before: three of the six defects above were gates that passed while proving nothing.
