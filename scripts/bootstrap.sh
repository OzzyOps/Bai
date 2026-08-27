#!/usr/bin/env bash
# BAi — Phase 0 Genesis bootstrap
# Creates the monorepo skeleton exactly as specified in architecture/TECH_ARCHITECTURE.md
# Idempotent-ish: run once in an empty parent directory.
set -euo pipefail

ROOT="${1:-bai}"
echo "▶ Bootstrapping BAi monorepo at ./${ROOT}"

# ── 0. Prerequisites ────────────────────────────────────────────────────────
command -v node    >/dev/null || { echo "✖ Node 20+ required"; exit 1; }
command -v pnpm    >/dev/null || npm install -g pnpm@9
command -v uv      >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v supabase>/dev/null || npm install -g supabase
command -v gh      >/dev/null || echo "⚠ gh CLI not found — repo creation will be manual"

mkdir -p "${ROOT}" && cd "${ROOT}"
git init -b main

# ── 1. Workspace roots ──────────────────────────────────────────────────────
cat > pnpm-workspace.yaml <<'YAML'
packages:
  - 'apps/web'
  - 'packages/*'
YAML

cat > package.json <<'JSON'
{
  "name": "bai",
  "private": true,
  "packageManager": "pnpm@9.12.0",
  "engines": { "node": ">=20" },
  "scripts": {
    "dev": "pnpm --filter @bai/web dev",
    "build": "pnpm --filter @bai/tokens build && pnpm --filter @bai/web build",
    "lint": "eslint . --max-warnings=0",
    "typecheck": "tsc -b --noEmit",
    "test": "vitest run",
    "tokens:build": "pnpm --filter @bai/tokens build",
    "tokens:validate": "python scripts/validate-tokens.py",
    "gen:types": "bash scripts/gen-types.sh"
  }
}
JSON

cat > pyproject.toml <<'TOML'
[tool.uv.workspace]
members = ["apps/api", "apps/workers"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
TOML

# ── 2. Directory skeleton ───────────────────────────────────────────────────
mkdir -p .github/workflows apps packages/{tokens/src,ui/src,types,config} \
         packages/platform-py/src/bai_platform/{tenancy,rbac,audit,connectors,ingestion,agents,llm,evals} \
         apps/_product-template/{schema,agents,evals/golden,ui} \
         supabase/{migrations,functions} scripts/eval docs/ADR

# ── 3. Frontend — React 19 + TS + Vite ──────────────────────────────────────
pnpm create vite@latest apps/web --template react-ts
cd apps/web
pnpm install
pnpm add react-router-dom @tanstack/react-query zustand @supabase/supabase-js \
        clsx tailwind-merge lucide-react date-fns zod react-hook-form @hookform/resolvers
pnpm add -D tailwindcss @tailwindcss/vite autoprefixer vitest @testing-library/react \
        @testing-library/jest-dom jsdom eslint-plugin-jsx-a11y openapi-typescript
npx shadcn@latest init -d
cd ../..

# ── 4. Backend — FastAPI ────────────────────────────────────────────────────
mkdir -p apps/api/src/bai_api/{routers,schemas,services,core,middleware} apps/api/tests
cat > apps/api/pyproject.toml <<'TOML'
[project]
name = "bai-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "supabase>=2.10",
  "python-jose[cryptography]>=3.3",
  "httpx>=0.27",
  "structlog>=24.4",
  "sentry-sdk[fastapi]>=2.18",
  "slowapi>=0.1.9",
]
[dependency-groups]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "mypy>=1.13", "ruff>=0.7", "pip-audit>=2.7"]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
TOML

# ── 5. Workers — Celery + Anthropic ─────────────────────────────────────────
mkdir -p apps/workers/src/bai_workers/{tasks,parsers,llm/prompts}
cat > apps/workers/pyproject.toml <<'TOML'
[project]
name = "bai-workers"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "celery[redis]>=5.4",
  "anthropic>=0.40",
  "supabase>=2.10",
  "pydantic>=2.9",
  "pypdf>=5.1",
  "pdfplumber>=0.11",
  "python-docx>=1.1",
  "openpyxl>=3.1",
  "tiktoken>=0.8",
  "structlog>=24.4",
  "tenacity>=9.0",
]
[dependency-groups]
dev = ["pytest>=8.3", "mypy>=1.13", "ruff>=0.7"]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
TOML

uv sync

# ── 6. Supabase ─────────────────────────────────────────────────────────────
supabase init
supabase start          # local Postgres + Auth + Storage on Docker
# Link to the EU-West (London) hosted project once created:
#   supabase link --project-ref <PROJECT_REF>
#   supabase db push

# ── 7. Design tokens package ────────────────────────────────────────────────
cat > packages/tokens/package.json <<'JSON'
{
  "name": "@bai/tokens",
  "version": "1.0.0",
  "main": "dist/index.js",
  "scripts": { "build": "tsx build.ts" },
  "devDependencies": { "tsx": "^4.19.0", "typescript": "^5.6.0" }
}
JSON
# Copy the Phase 0 token files in:
#   cp ~/Desktop/BAi/tokens/bai-core.tokens.json packages/tokens/src/
#   cp ~/Desktop/BAi/tokens/_product.theme.template.json packages/tokens/src/

# ── 8. Environment template ─────────────────────────────────────────────────
cat > .env.example <<'ENVEOF'
# ── Supabase ──
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=      # workers ONLY — never in web or api env
SUPABASE_DB_URL=
SUPABASE_REGION=eu-west-2

# ── Anthropic ──
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL_ANALYSIS=claude-opus-5
ANTHROPIC_MODEL_EXTRACT=claude-sonnet-5
ANTHROPIC_MAX_MONTHLY_SPEND_GBP=2500

# ── Infra ──
REDIS_URL=redis://localhost:6379/0
API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=

# ── Telemetry (EU-resident) ──
SENTRY_DSN=
POSTHOG_KEY=
POSTHOG_HOST=https://eu.i.posthog.com

# ── Compliance ──
DATA_RESIDENCY=eu
DEFAULT_RETENTION_DAYS=2555        # 7 years, contract-record default
ENVEOF

cat > .gitignore <<'GITEOF'
node_modules/
dist/
.env
.env.local
__pycache__/
.venv/
.pytest_cache/
.mypy_cache/
.DS_Store
supabase/.branches/
supabase/.temp/
GITEOF

# ── 9. First commit ─────────────────────────────────────────────────────────
git add -A
git commit -m "chore: BAi Phase 0 genesis — platform monorepo skeleton"
# gh repo create <org>/bai --private --source=. --push

echo ""
echo "✅ BAi monorepo bootstrapped."
echo "   Next: pnpm dev (web :5173) · uv run uvicorn bai_api.main:app --reload (api :8000)"
echo "   Then: supabase link --project-ref <ref> && supabase db push"
