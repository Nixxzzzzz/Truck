#!/bin/sh
set -eu

python -m alembic upgrade head

if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_NAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
  python -m app.cli init-admin
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"