#!/usr/bin/env sh
set -eu

if [ "${RUN_DB_MIGRATIONS:-true}" = "true" ]; then
  alembic -c /app/apps/compras_divididas/alembic.ini upgrade head
fi

exec uvicorn compras_divididas.api.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${API_WORKERS:-2}" \
  --log-level "${API_LOG_LEVEL:-info}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
