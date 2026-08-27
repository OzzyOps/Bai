# BAi — Business Model Canvas (Holding Level)
**Version:** 2.0 (v1.0 void) · **Phase 0 Genesis** · **Owner:** PM Pod
**Scope note:** No product is defined yet. This is the *holding company's* model — the engine
that makes shipping product N+1 cheaper than product N. Product-level canvases are Phase 1
deliverables and will inherit from this one.
**Market:** UK/EU primary · GBP · en-GB

---

## 0. The Economic Engine (read this first)

BAi is not a company that happens to make several products. It is a company whose **business
model is the shared substrate**.

Every operational-automation product needs the same expensive, unglamorous foundation:
multi-tenancy with real isolation, RBAC, audit trails, connector plumbing into enterprise
systems, agent orchestration, human-in-the-loop escalation, evaluation harnesses, and the
compliance estate (SOC 2, ISO 27001, DPAs, residency) that unlocks enterprise budget.

That foundation is **60–70% of the cost of any one product and ~0% of its differentiation.**

> **The BAi thesis: build the substrate once, amortise it across a portfolio.**
> Product 1 pays for the platform. Product 2 ships at roughly 35% of the cost.
> Product 3 ships at roughly 25%. Compliance is bought once and inherited by all.

Everything in the nine blocks below serves that engine. **If a product cannot be built on the
shared substrate, it is a signal the product is wrong — not that the substrate is.**

---

## 1. Customer Segments

**Primary buyer — "The Accountable Operator."** Owns an operational outcome, is measured on
cost and cycle time, has headcount doing work they cannot defend at board level.

| Segment | Org size | Economic buyer | Trigger to buy |
|---|---|---|---|
| **Beachhead: Mid-market Operations** | 200–2,000 FTE | COO / Head of Operations | Volume grew, headcount can't; process is manual and error-prone |
| **Finance Operations** | 200–5,000 FTE | CFO / Finance Director | Reconciliation, exception handling and controls eat the team |
| **Shared Services / GBS** | 1,000+ FTE | GBS Director | Chartered to cut cost-to-serve; already measures it |
| **Regulated Financial Services** | 500+ | COO / Head of Ops Risk | Manual controls fail audit; needs an evidenced trail |
| **Channel: Advisory & BPO** | — | Practice / Delivery Lead | Margin pressure on people-heavy delivery |

**Deliberately NOT our segment at Phase 0:** sub-100-FTE businesses (enterprise compliance cost
cannot be recovered), and greenfield digital natives (no legacy seams — our thesis is the seam).

**The segment decision that matters:** BAi sells to whoever owns the *cost of the process*,
not whoever owns the *system the process runs in*. IT is an approver, never the buyer.

## 2. Value Propositions

**Holding:** *We remove the work that shouldn't need a human.*
**Promise:** *Give it the work. Get back the decisions.*

| Level | Proposition |
|---|---|
| **To the operator** | The volume gets handled. You see only what genuinely needed you. |
| **To the CFO** | Cost-to-serve falls without a redundancy programme; the saving is measurable per process. |
| **To Risk & Audit** | Every action carries provenance and an immutable trail. Controls become evidenced, not asserted. |
| **To IT** | One vendor, one security review, one DPA — across a portfolio, not per tool. |

**Counter-positioning vs. the incumbents**

| Incumbent class | Their model | Where we win |
|---|---|---|
| RPA (UiPath, Blue Prism) | Automate the happy path; brittle, breaks on change | We work the exceptions; adapt without re-scripting |
| Horizontal AI platforms | Sell capability, customer builds the product | We ship the finished process, not a toolkit |
| BPO / offshore | Buy cheaper hours | We remove the hours |
| Internal build | Full control | We carry the compliance estate they'd build alone |

**The BAi advantage that compounds:** every product inherits the trust estate. The fifth
enterprise product sells into an account that already ran the security review.

## 3. Channels

| Stage | Channel |
|---|---|
| Awareness | Founder-led thought leadership on operational cost; the "seam" narrative; SEO on process-specific pain |
| Consideration | **Sandbox environment** — synthetic data, no signup, no sales contact. Product-led proof of the substrate. |
| Trial | **Paid Process Audit** — a fixed-fee diagnostic on one real process, returning a quantified before/after. The report is the sales asset. |
| Purchase | PLG below ~£15k ACV; sales-assist above. Annual invoice + PO — enterprise ops buyers do not pay by card. |
| Land & expand | Land one process → adjacent processes → additional BAi products in the same account |
| Partner | Advisory firms and BPOs as channel; they resell margin recovery |

**Structural advantage:** the second product enters through an existing account with security
review, DPA and procurement already cleared. **Portfolio CAC declines with portfolio size.**

## 4. Customer Relationships

- **Self-serve** at the low tier: sandbox, docs, in-product guidance, no CSM.
- **Guided implementation** at enterprise: connecting to real systems is where deals die.
  Time-to-first-automated-action is the activation metric across every product.
- **Proactive by design:** the product's default relationship is *it did the work and told you*.
  Retention is earned by the exception it caught, not by the login.
- **Evidence relationship:** a quarterly, per-process savings and accuracy statement. In
  regulated accounts this is what justifies the renewal internally.

## 5. Revenue Streams

*Rates are holding-level defaults; product canvases may refine within these bands.*

| # | Stream | Model | Band (GBP) | Target % of Yr-3 rev |
|---|---|---|---|---|
| 1 | **Product subscription** | Annual SaaS, tiered by process volume + seats | £8k–£120k/yr | **62%** |
| 2 | **Volume overage** | Usage beyond tier allowance | per-unit, ~85–92% GM | 11% |
| 3 | **Platform licence (multi-product)** | Discounted bundle across ≥2 BAi products | 20–30% off list | 9% |
| 4 | **Process Audit** | Fixed-fee diagnostic, credited to year-1 licence | £4.5k–£15k | 7% |
| 5 | **Implementation & integration** | One-off professional services | £6k–£40k | 6% |
| 6 | **Partner / white-label** | Rev-share with advisories and BPOs | 25–35% share | 5% |

**Two pricing principles, locked at holding level:**
1. **Price on work removed, not seats.** Seat pricing punishes exactly the adoption we need.
   The unit is the process instance handled.
2. **Never meter the exception queue.** Escalations to a human are where trust is built; charging
   for them would incentivise us to escalate less. Structurally corrosive.

## 6. Key Resources

| Class | Asset | Compounding? |
|---|---|---|
| **Platform** | The shared agentic substrate — tenancy, RBAC, audit, connectors, orchestration, HITL escalation | ✅ Core |
| **Proprietary** | Per-domain evaluation corpora — annotated golden sets defining "correct" for each process | ✅ Strongest moat |
| **Trust estate** | SOC 2 Type II, ISO 27001, DPA + sub-processor register, UK/EU residency | ✅ Bought once, inherited by all |
| **Connector library** | Certified integrations into ERP, finance, ITSM, document systems | ✅ |
| **Model access** | Anthropic Claude — enterprise terms, zero-retention routing | ❌ Not exclusive |
| **Human** | Domain-embedded product pods; ops-risk advisor on retainer | Partial |

**Blunt assessment of the moat:** model access is not one. The connector library and the
evaluation corpora are. **Whoever can prove their agent is right, in a given domain, wins that
domain.** Everything else is commodity within 24 months.

## 7. Key Activities

1. **Build and defend the substrate.** Platform work is the highest-leverage engineering in
   the company. It is never "overhead against the roadmap."
2. **Evaluation engineering.** Golden sets, regression gates in CI, per-process accuracy
   reporting. *(Retained from v1.0 — Data's finding generalises: we sell correctness, so
   correctness must be measured or the claim is unfounded.)*
3. **Human-in-the-loop design.** Getting the escalation boundary right is the product craft.
   Too eager destroys the value; too confident destroys the trust.
4. **Connector engineering.** Unglamorous, and the actual barrier to entry.
5. **Compliance programme.** SOC 2 → ISO 27001 → residency. Revenue-unlocking, not overhead.
6. **Portfolio selection.** Choosing which process to attack next is the CPO's highest-stakes
   recurring decision. Criteria in §10.

## 8. Key Partnerships

| Partner | Type | Why |
|---|---|---|
| **Anthropic** | Core model provider | Claude for reasoning and extraction; enterprise data terms; zero-retention routing |
| **Supabase** | Data + auth platform | Postgres, RLS, Auth, Storage; EU region for residency |
| **Vercel / Fly.io** | Hosting | Frontend + Python services, EU regions |
| **ERP & finance vendors** | Integration | Connectors are the barrier to entry; certification is the durable version |
| **Advisory firms & BPOs** | Channel | Distribution into mid-market without a large sales team |
| **Ops-risk / controls counsel** | Advisory | Underwrites the "evidenced control" claim in regulated accounts |
| **SOC 2 / ISO auditor** | Compliance | Unlocks enterprise tiers across the whole portfolio |

## 9. Cost Structure

**Shape:** platform-heavy in year 1, margin-expanding thereafter as substrate cost amortises
across products. Inference is the one line that scales with revenue and must be engineered.

**Year-1 operating cost (6 FTE, platform-building year):**

| Category | £/yr | Note |
|---|---|---|
| People (2 platform eng, 1 product eng, 1 product/design, 1 GTM, founder) | 510,000 | ~68% |
| LLM inference | 28,000 | Low in yr 1 — few tenants |
| Infrastructure | 16,000 | Supabase, Vercel, Fly, storage, egress |
| Compliance (SOC 2 readiness, ISO prep, legal, DPA, insurance) | 52,000 | Front-loaded; unlocks the portfolio |
| Tooling | 14,000 | GitHub, Sentry, PostHog, Linear, CI |
| Sales & marketing | 60,000 | |
| Contingency (10%) | 68,000 | |
| **Total** | **£748,000** | |

**Platform amortisation — the number that defines the company:**

| | Product 1 | Product 2 | Product 3 |
|---|---|---|---|
| Substrate cost | 100% (built) | inherited | inherited |
| Compliance cost | 100% (bought) | inherited | inherited |
| Net build cost vs. P1 | **100%** | **~35%** | **~25%** |
| Time to first revenue | ~9 months | ~4 months | ~3 months |

**Gross margin target:** 88–93% at scale. Inference is engineered down via prompt caching of
the domain rubric, tiered model routing (cheaper model for extraction, frontier for reasoning
and synthesis), deduplication by content hash, and a hard per-tenant monthly inference budget
with alerting.

**Break-even:** ~£748k ÷ ~90% GM ⇒ **~£830k ARR**. Reachable on a single product with a
mixed book of roughly 12 enterprise + 20 mid-market accounts — *or* considerably faster on two
products sharing a substrate, which is the entire argument for the model.

---

## 10. Portfolio Selection Criteria *(the CPO's recurring decision)*

A candidate process qualifies for a BAi product only if it scores on all five:

1. **High volume, high variability** — too varied for RPA, too dull for good people.
2. **Quantifiable cost of the status quo** — we can state the saving in £ before we build.
3. **Evidenced correctness is possible** — a golden set can be constructed. If we cannot
   measure right, we cannot sell it. **Hard gate.**
4. **Substrate fit ≥ 70%** — reuses tenancy, RBAC, audit, connectors, orchestration.
5. **A named accountable buyer** — someone whose objectives improve measurably. Processes
   nobody owns do not get funded.

---

## 11. Assumptions Register *(explicit, to be validated in Phase 1)*

| # | Assumption | Risk if wrong | Validation |
|---|---|---|---|
| A1 | Substrate reuse genuinely hits ~65% for product 2 | The whole economic engine collapses to a normal multi-product company | Instrument reuse at the module level from day one |
| A2 | Enterprise buyers will let agents act, not just recommend | Value proposition halves; we become a reporting tool | Test escalation thresholds in the first Process Audits |
| A3 | Evaluation corpora are defensible, not commoditised | Moat is temporary | Track whether competitors publish accuracy; ours must be verifiable |
| A4 | Buyer is Operations, not IT | Sales motion and pricing are wrong | 15 discovery interviews before Phase 1 close |
| A5 | Compliance estate is inheritable across products without re-audit | Cost model understates by ~£40k/product | Confirm scope boundaries with auditor early |
| A6 | Inference cost stays engineerable within GM target | Margin compression | Per-tenant cost telemetry from first tenant |
