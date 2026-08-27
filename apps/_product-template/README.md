# `<product>` by BAi

Scaffold for a new BAi product. Copy to `products/<name>/` and fill in.

A product is a **domain layer** over the platform. If you need something the
platform does not offer, add it to `packages/` — never fork it in here. That
boundary is the company's economic thesis (see `company/BUSINESS_MODEL_CANVAS.md` §0)
and CODEOWNERS enforces review on it.

## Required before this product can ship

| Item | Path | Gate |
|---|---|---|
| Golden set | `evals/golden/*.json` | **Blocking.** No golden set, no ship. |
| Eval runner | `evals/runner.py` | Must expose `predict(cases) -> list[Prediction]` |
| Baseline | `evals/baseline.json` | Written on first run; regression gate compares against it |
| Domain schema | `schema/*.sql` | Every table needs `org_id`, an RLS policy and a cross-org test |
| Theme | `theme.json` | May override the theme layer only; `$locked` paths are fixed |
| Agent definitions | `agents/*.py` | Each declares consequence and reversibility per action |

## Portfolio criteria

Before building, confirm the process clears all five criteria in
`company/BUSINESS_MODEL_CANVAS.md` §10. Criterion 3 is a hard gate: if a golden
set cannot be constructed, correctness cannot be measured, and BAi cannot sell
automation of it.
