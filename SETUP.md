# Connecting BAi together

Everything below is ordered so each step is verifiable before the next one depends on it.
Nothing here needs an Anthropic API key until step 5.

**Prerequisites:** Node 20+, Python 3.12+, [uv](https://docs.astral.sh/uv/), pnpm 9,
[Supabase CLI](https://supabase.com/docs/guides/cli), Docker (for local Supabase),
and `gh` if you want the GitHub steps automated.

Check what you have:

```bash
node -v && python3 --version && uv --version && pnpm -v && supabase --version && docker info >/dev/null && echo "docker ok"
```

macOS installs for anything missing:

```bash
brew install node python@3.12 pnpm supabase/tap/supabase && curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 1 · Install dependencies

```bash
cd ~/Desktop/BAi
pnpm install
uv sync --all-extras
```

**Verify:** `uv run python -c "import bai_platform; print('platform ok')"`

## 2 · Run the test suite

This is the first real proof the code works.

```bash
uv run pytest -v
uv run ruff check .
uv run mypy --strict packages/platform-py/src apps/api/src apps/workers/src
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

**Expect:** 118 Python tests passing with the isolation suite skipped (it needs the database
from step 3, after which it is 142), ruff clean, mypy clean across 36 files, and 15 front-end
tests passing.

If anything fails here, fix it before going further; everything downstream assumes the
substrate is sound.

## 3 · Local database

```bash
supabase start          # first run pulls Docker images, takes a few minutes
supabase db reset       # applies all 9 migrations, then seed.sql
```

**Without Docker,** point psql at any Postgres 16 with pgvector and run:

```bash
./scripts/db_local_reset.sh
```

It applies `supabase/local/auth_shim.sql` (which recreates just the parts of Supabase's `auth`
schema the migrations use), then every migration, then the seed, then the RLS coverage gate.
Local and CI only — hosted Supabase provides the real `auth` schema itself.

`supabase start` prints your local API URL, anon key and service-role key. Keep the terminal.

**Verify tenant isolation actually holds:**

```bash
supabase db execute --file scripts/assert_rls_coverage.sql
export SUPABASE_DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest packages/platform-py/tests/test_rls.py -v
```

The coverage script fails loudly if any table is missing RLS, a policy, or `org_id`.

## 4 · Environment

```bash
cp .env.example .env
```

Fill in from the `supabase start` output. For local work you only need the `EU` block:

```bash
SUPABASE_EU_URL=http://127.0.0.1:54321
SUPABASE_EU_ANON_KEY=<anon key>
SUPABASE_EU_SERVICE_KEY=<service_role key>
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=<anon key>
```

> **The service-role key goes in the workers environment only.** The API refuses to start if it
> finds one — that check is `assert_no_service_role` in `apps/api/src/bai_api/config.py`, and it
> exists because a service-role key behind a user-facing route bypasses RLS entirely.

## 5 · Anthropic API key

Get one at [console.anthropic.com](https://console.anthropic.com). This is **separate billing
from your Claude subscription** — Pro/Max covers claude.ai and Claude Code, not a hosted app.

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Set a monthly spend cap in the Anthropic Console before anything is publicly reachable.**
The platform's per-tenant ceiling limits one tenant; the Console cap limits your whole account.
Use the **BAi workspace** in the Console so this spend is separated from anything else you run,
and give that workspace its own limit.

## 6 · Run it

Four terminals:

```bash
pnpm tokens:build && pnpm dev                              # web  → :5173
uv run uvicorn bai_api.main:app --reload --port 8000       # api  → :8000
uv run celery -A bai_workers.celery_app worker -l info     # workers
node apps/console/server.mjs                               # console → :8477
```

Celery needs Redis: `docker run -d -p 6379:6379 redis:7-alpine`

**Verify:** `curl localhost:8000/health/ready` lists your configured regions.

## 7 · GitHub

```bash
gh repo create <org>/bai --private --source=. --push
```

Then **Settings → Pages → Source: GitHub Actions** to publish the console.

Add repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Used by |
|---|---|
| `ANTHROPIC_API_KEY` | `eval-harness.yml` |
| `FLY_API_TOKEN` | API and worker deploys |
| `SUPABASE_ACCESS_TOKEN` | migration workflow |

Four workflows run on push: `ci`, `security`, `eval-harness`, `deploy-console`.

## 8 · Hosted Supabase

One project **per region** — customer data never crosses a region boundary.

```bash
supabase link --project-ref <ref>
supabase db push
```

Deploy the console's Claude proxy so the key stays server-side:

```bash
supabase functions deploy claude-proxy
supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
supabase secrets set ALLOWED_ORIGINS=https://<user>.github.io
```

`ALLOWED_ORIGINS` is **not optional**. The proxy fails closed without it and answers 403 —
deliberately, because an unset value used to mean "any origin", which is an open door to a
paid Anthropic account for anyone who finds the URL. No path, no trailing slash. For local
work only, `ALLOW_ANY_ORIGIN=true` opts out explicitly.

Then open the console → **Settings** → **Supabase proxy** and paste the project URL and **anon**
key. The anon key is safe in a browser; that is what it is for.

## 9 · Deploy services

```bash
fly launch --config apps/api/fly.toml --name bai-api-eu --region fra --no-deploy
fly secrets set --app bai-api-eu SUPABASE_EU_URL=... SUPABASE_EU_ANON_KEY=...
fly deploy --config apps/api/fly.toml
```

One app per region. `primary_region` in `fly.toml` is pinned per deployment, not multi-region —
a multi-region product means several single-region apps.

## 10 · Regenerate types after any schema change

```bash
./scripts/gen-types.sh
```

Writes `packages/types/src/database.d.ts` and `api.d.ts`. Both are generated — never hand-edit.

---

## Where to go next

The platform is a substrate with **no product on it**. To build the first one:

```bash
cp -r apps/_product-template products/<name>
```

Then invoke `overlord` and tell it what you want. It classifies the brief, states which type it
chose and why it is not the neighbouring one, and runs the phases that type calls for — stopping
at each gate for you.

To see the order before you start:

```bash
python3 scripts/validate_orchestration.py --plan new-product
```

`company/ORCHESTRATION.yaml` holds the eight brief types and the ten phases. A `new-product`
brief runs all seven build phases; `gtm-launch` runs one; `compliance-review` has a phase of its
own so that SecOps leads it rather than the tech lead. Edit that file to change any of it —
`scripts/validate_orchestration.py` will tell you what else needs to change, and CI fails if the
spec and the agent files disagree.

**A product cannot ship without a golden set** (`evals/golden/*.json`) and a passing regression
gate. That is locked decision #7, and `eval-harness.yml` enforces it rather than trusting anyone
to remember.

## Reading order for the docs

| File | What it answers |
|---|---|
| `CLAUDE.md` | How the company operates. Read first. |
| `BLACKBOARD.md` | Current approved state and open risks |
| `docs/RBAC.md` | Who can do what, and where it is actually enforced |
| `docs/RUNBOOK.md` | What to do at 3am |
| `docs/DATA_RETENTION.md` | Erasure order, and why embeddings go first |
| `docs/ADR/` | Why RLS, and why jurisdiction is a tenant attribute |
| `company/` | Brand, business model, architecture, compliance |
