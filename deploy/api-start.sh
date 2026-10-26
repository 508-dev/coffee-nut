#!/bin/sh
# Entrypoint for the api container. Both setup steps are idempotent, so every
# deploy and every restart runs them rather than relying on a one-off job.
set -eu

cd /app
python apps/api/manage.py migrate --noinput
python apps/api/manage.py seed_catalog

exec gunicorn coffeenut.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --access-logfile - \
  --forwarded-allow-ips '*'
