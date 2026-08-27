#!/usr/bin/env bash
# Regenerate TypeScript types from the database and the API's OpenAPI spec.
# Both outputs are generated — never hand-edit them.
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="packages/types/src"

echo "▶ database types"
if [[ -n "${SUPABASE_PROJECT_REF:-}" ]]; then
  supabase gen types typescript --project-id "$SUPABASE_PROJECT_REF" --schema public \
    > "$OUT/database.d.ts"
else
  supabase gen types typescript --local --schema public > "$OUT/database.d.ts"
fi

echo "▶ API types"
API_URL="${API_BASE_URL:-http://localhost:8000}"
if ! curl -fsS "$API_URL/health" >/dev/null 2>&1; then
  echo "✖ API is not reachable at $API_URL" >&2
  echo "  Start it first: uv run uvicorn bai_api.main:app --reload" >&2
  exit 1
fi
npx openapi-typescript "$API_URL/openapi.json" -o "$OUT/api.d.ts"

echo "✓ types regenerated into $OUT"
