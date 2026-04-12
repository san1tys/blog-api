#!/usr/bin/env bash
set -Eeuo pipefail

REDIS_URL="${BLOG_REDIS_URL:-redis://localhost:6379/1}"
SEED="${BLOG_SEED_DB:-0}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { echo "[entrypoint] $*"; }

wait_for_redis() {
    local host port

    # Parse host:port from redis://host:port/db
    host=$(echo "$REDIS_URL" | sed -E 's|redis://([^:/]+).*|\1|')
    port=$(echo "$REDIS_URL" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|')
    port="${port:-6379}"

    log "Waiting for Redis at $host:$port ..."
    local retries=30
    until python - <<PY 2>/dev/null
import socket, sys
s = socket.create_connection(("$host", $port), timeout=2)
s.close()
PY
    do
        retries=$((retries - 1))
        if [[ $retries -eq 0 ]]; then
            echo "[entrypoint] ERROR: Redis not reachable after 30 attempts" >&2
            exit 1
        fi
        sleep 1
    done
    log "Redis is up."
}

# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

wait_for_redis

log "Running migrations..."
python manage.py migrate --noinput

log "Collecting static files..."
python manage.py collectstatic --noinput

log "Compiling translation messages..."
python manage.py compilemessages

if [[ "$SEED" == "1" ]]; then
    log "Seeding demo data..."
    python manage.py seed
fi

log "Starting server..."
exec "$@"
