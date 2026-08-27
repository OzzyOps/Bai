# BAi — Brand Identity Document
**Version:** 2.0 (v1.0 void — see VOID_LOG.md) · **Phase 0 Genesis** · **Owner:** Brand Pod
**Entity model:** BAi is the holding brand. Products ship under their own names, endorsed "by BAi".
**Evidence base:** Raz's vision and industry statement. No product exists yet. Nothing here is
derived from any pre-existing asset.

---

## 1. Mission

**We remove the work that shouldn't need a human.**

BAi builds agentic software that absorbs the heavy, repetitive, high-volume operational work
inside businesses — so the people we serve spend their hours on judgement, not on process.

## 2. Vision

Human capital is never again spent on a task a machine should have finished.

## 3. Positioning Thesis

*Re-derived from the vision statement. This replaces the voided v1.0 thesis entirely.*

Operational friction is not a tooling shortage. Most enterprises already own systems for every
function they run. The friction lives in the **seams between them** — the reconciliations, the
approvals, the chasing, the re-keying, the checking of one system's truth against another's.
That work is too variable for RPA, too dull for good people, and too consequential to skip.

BAi's thesis: **the seam is the product.** Agentic systems can now hold enough context to work
across boundaries that deterministic automation could never span — reading unstructured input,
reasoning about exceptions, and escalating the small fraction that genuinely needs a person.

**Category we intend to own:** *Operational Intelligence* — software that does the operational
work, shows its reasoning, and asks a human only when the decision is genuinely theirs.

**What separates us from the RPA incumbents:** they automate the happy path and hand you the
exceptions. We work the exceptions and hand you the decisions.

## 4. Core Values

| Value | In practice | Forbids |
|---|---|---|
| **Show the receipt** | Every output cites its source — record, field, timestamp, and the reasoning that produced it. | Unattributed assertions. Confidence without provenance. |
| **Earn the automation** | A step runs unsupervised only once we can evidence it is right. Humans approve consequence. | Silent autonomous action with financial, legal or contractual effect. |
| **Own the miss** | When the system is unsure it says unsure — visibly, in its own colour, never as a quiet default. | Presenting a guess as a finding. Rendering low confidence as neutral. |
| **Plain over clever** | Output is written for the accountable person, not the specialist who built it. | Shipping a screen that needs a training session. |
| **Ship the boring parts** | RBAC, audit trails, retention, export, residency. Enterprise trust is a feature. | "We'll add permissions later." |
| **Small form, large lift** | We ask only for what the customer alone knows. Everything else we discover. | Onboarding that asks for what our systems can already reach. |

## 5. Tone of Voice

**Derivation:** the mission is *we remove work*. A brand that removes work may not create any.
Every voice rule below follows from that single constraint.

**Register:** British English. An unusually clear senior colleague — the one who tells you the
answer first and the reasoning second.

**Four rules**

1. **Answer, then explain.** Lead with the finding, never the process. "Three invoices don't
   match the PO." Not "Our reconciliation engine has surfaced potential discrepancies."
2. **Concrete over abstract.** Money, counts, dates, names. "£84,000 a year" beats "significant
   savings potential." If a claim can't be quantified, question whether it's a claim.
3. **No AI theatre.** We never sell the model. We describe the outcome. The intelligence should
   be self-evident from the work, never asserted in the copy.
4. **Calm under consequence.** Risk and error copy is factual and actionable, never alarmist and
   never apologetic. State what happened, what it means, what to do.

**Voice sliders**
```
Formal    |------●-------| Casual     professional, not stiff
Technical |--●-----------| Plain      aggressively plain
Reserved  |-----●--------| Bold       confident, never hyped
Serious   |----●---------| Playful    dry wit permitted; never in risk or error UI
```

**Do / Don't**

| Don't | Do |
|---|---|
| "Leverage AI-powered automation to optimise your workflows." | "It does the reconciliation. You approve the exceptions." |
| "Robust enterprise-grade security architecture." | "Your data stays in your workspace. Only your team can see it." |
| "An anomaly has been detected in the dataset." | "Row 214 doesn't match. The supplier ID is on the invoice but not in the ledger." |
| "An error occurred." | "We couldn't reach the ledger — it returned a timeout. Nothing was changed. Retry?" |

## 6. Brand Architecture

```
BAi  — holding brand · trust, engineering credibility, enterprise assurance
 │
 ├── <Product 1> by BAi   — UNDEFINED, awaiting Phase 1
 ├── <Product 2> by BAi   — reserved
 └── <Agentic tool> by BAi — reserved
```

**Rules of endorsement**
- Product name is always primary. `by BAi` sets at 55% of the wordmark's optical size in `text.muted`.
- BAi appears **once** on a product surface — footer or account menu — plus in full on trust
  surfaces: security page, DPA, sub-processor register, contract, invoice.
- Every product inherits the **BAi core token layer** and may override only the **theme layer**
  (accent hue). Neutrals, type scale, spacing, radii, motion and semantic status colours are
  fixed ecosystem-wide. This is what makes the family recognisable as a family.

## 7. Visual Identity Direction

*Proposed, not executed. This is the artefact most in need of Raz's steer.*

**Rationale.** Enterprise AI branding has converged on indigo-to-violet gradients and cold slate
greys; a new holding brand entering operational and financial technology gains more from
looking calm and precise than from looking futuristic. The direction below is deliberately
counter-positioned.

- **Ink `#0A0E13`** — near-black with a cool undertone. The holding-brand colour. Authority.
- **Meridian `#0E6E62`** — deep teal-green primary. Precision and money without the fintech
  cliché of navy; distinctly uncrowded in this category.
- **Flux `#1FD1B2`** — bright teal accent, reserved for BAi corporate surfaces and for
  indicating *automated action taken*. The visual signature of work being removed.
- **Warm neutrals** (`#F8F7F5` canvas, warm greys) rather than cold slate — softens enterprise
  density and separates us from every competitor's cool-grey UI.

**Typeface direction:** a geometric-humanist sans with a true tabular figure set — BAi products
are figure-dense by nature. `Inter Tight` for UI, `Inter` for prose, both variable, both
self-hostable for residency compliance. Proposed, not fixed.

**Wordmark brief:** lowercase `bai`, the dot of the `i` replaced by a small filled square in
Flux — a completed checkbox, the mark of work finished without you. Must hold at 16px favicon.
Wordmark only; no icon-only mark until recall exists.

**Two alternates if this direction is wrong:** (a) Ink + warm amber — operational, industrial,
human; (b) Ink + a single desaturated cobalt — conservative, closest to buyer expectation in
financial services.

## 8. The Promise We Are Held To

> Give it the work. Get back the decisions.

If a product carrying "by BAi" cannot meet that sentence, it does not ship under the name.
