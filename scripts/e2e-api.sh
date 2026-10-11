#!/usr/bin/env bash
# Starts the FastAPI service for browser tests against a dedicated, freshly created PostgreSQL
# database (geevi_e2e) on the Geevi development cluster. Never touches any other database.
set -euo pipefail
export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT_DB="${GEEVI_PGPORT:-5433}"
DB="${GEEVI_E2E_DB:-geevi_e2e}"
API_PORT="${GEEVI_E2E_API_PORT:-8010}"
WEB_ORIGIN="${GEEVI_E2E_WEB_ORIGIN:-http://127.0.0.1:3010}"

if [ -z "${GEEVI_E2E_DATABASE_URL:-}" ]; then
  "$ROOT/scripts/dev-db.sh" start >/dev/null
  dropdb -h 127.0.0.1 -p "$PORT_DB" -U geevi --if-exists --force "$DB"
  createdb -h 127.0.0.1 -p "$PORT_DB" -U geevi "$DB"
  export GEEVI_DATABASE_URL="postgresql+psycopg://geevi@127.0.0.1:$PORT_DB/$DB"
  rm -f "$ROOT/apps/api/.e2e-credentials.json"  # fresh database: fresh fictional passwords
else
  export GEEVI_DATABASE_URL="$GEEVI_E2E_DATABASE_URL"
fi
export GEEVI_DEV_MODE=true
export GEEVI_ALLOWED_ORIGINS="[\"$WEB_ORIGIN\"]"
export GEEVI_CREDENTIALS_FILE="$ROOT/apps/api/.e2e-credentials.json"
cd "$ROOT/apps/api"
uv run alembic upgrade head
uv run python scripts/seed_demo.py --name "E2E base workspace (fictional)"
# Supervise the API so a test can kill the server process and prove that a restarted process
# serves the same durable state (sessions included) from PostgreSQL.
child=""
stop() { [ -n "$child" ] && kill "$child" 2>/dev/null; pkill -P $$ 2>/dev/null; exit 0; }
trap stop TERM INT HUP
while true; do
  uv run uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --log-level warning &
  child=$!
  wait "$child" || true
  echo "geevi e2e API process exited; restarting against the same database" >&2
  sleep 0.3
done
