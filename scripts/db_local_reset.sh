#!/usr/bin/env bash
# Rebuild a local database from the migrations, WITHOUT Docker or the Supabase CLI.
#
# `supabase db reset` is the normal path and stays the normal path (see SETUP.md
# step 3). This script exists for the two places that cannot run Docker: CI
# containers and a plain Postgres 16 on a dev box. It applies the local auth shim,
# then every migration in order, then the seed.
#
#   ./scripts/db_local_reset.sh
#   SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:5432/bai pytest packages/platform-py/tests/test_rls.py
#
# Requires: psql on PATH, a running Postgres 16 with pgvector, superuser access.

set -euo pipefail

DB_NAME="${DB_NAME:-bai}"
PSQL="${PSQL:-psql}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "→ recreating database ${DB_NAME}"
$PSQL -q -d postgres -v ON_ERROR_STOP=1 \
  -c "drop database if exists ${DB_NAME} with (force);" \
  -c "create database ${DB_NAME};"

echo "→ local auth shim"
$PSQL -q -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "${ROOT}/supabase/local/auth_shim.sql"

for f in "${ROOT}"/supabase/migrations/*.sql; do
  echo "→ $(basename "$f")"
  $PSQL -q -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "$f"
done

echo "→ seed"
$PSQL -q -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "${ROOT}/supabase/seed.sql"

echo "→ RLS coverage gate"
$PSQL -q -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "${ROOT}/scripts/assert_rls_coverage.sql"

echo "✓ ${DB_NAME} rebuilt"
