# BAi

**We remove the work that shouldn't need a human.**

BAi builds agentic software that absorbs heavy, repetitive, high-volume operational work — so
teams spend their hours on judgement, not process. Products ship under their own names,
endorsed *by BAi*.

- **Category:** Operational Intelligence
- **Thesis:** the seam between systems is the product
- **Model:** one shared agentic substrate, amortised across a portfolio

## Start here

| Document | What it is |
|---|---|
| [CLAUDE.md](CLAUDE.md) | How the company operates. Read first. |
| [BLACKBOARD.md](BLACKBOARD.md) | Single source of approved truth |
| [company/BRAND_IDENTITY.md](company/BRAND_IDENTITY.md) | Mission, tone of voice, visual system |
| [company/BUSINESS_MODEL_CANVAS.md](company/BUSINESS_MODEL_CANVAS.md) | The economic engine |
| [company/TECH_ARCHITECTURE.md](company/TECH_ARCHITECTURE.md) | Platform substrate |
| [company/COMPLIANCE.md](company/COMPLIANCE.md) | Global regions, regimes, multi-currency |

## Stack

React 19 + TypeScript + Vite · Python 3.12 + FastAPI + Celery · Supabase Postgres 16 with RLS ·
Anthropic Claude · GitHub Actions · Vercel + Fly.io, six regions.

## Setup

```bash
pnpm install && uv sync
cp .env.example .env
supabase start && supabase db reset
pnpm dev
```

Requires Node 20+, Python 3.12+, pnpm 9, uv, Supabase CLI, Docker.
