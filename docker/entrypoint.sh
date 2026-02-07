#!/usr/bin/env sh
set -eu

python manage.py migrate --noinput

exec gunicorn skills_runtime_service.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-30}"
