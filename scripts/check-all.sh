#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

./scripts/lint.sh
./scripts/typecheck.sh

# A model edit without a migration is the most common way this repo breaks for
# everyone else, so it is checked before the tests rather than after.
echo "==> missing migrations"
PYTHONPATH=apps/api:apps/api/src \
DJANGO_SETTINGS_MODULE=coffeenut.settings.test \
  uv run python apps/api/manage.py makemigrations --check --dry-run

./scripts/test.sh

echo "==> web build"
bun run build
