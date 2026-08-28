#!/usr/bin/env sh
# Regenerate the SPA's API types from the Django schema.
#
# Reads the schema straight from Django rather than a running server, so this
# works in CI and offline. The output is committed; --check verifies it has not
# drifted from the backend.
set -eu

cd "$(dirname "$0")/.."

TARGET="apps/web/src/lib/api/schema.d.ts"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

SCHEMA="$(mktemp -t coffeenut-schema.XXXXXX.yaml)"
OUT="$(mktemp -t coffeenut-types.XXXXXX.d.ts)"
trap 'rm -f "$SCHEMA" "$OUT"' EXIT

DJANGO_SETTINGS_MODULE=coffeenut.settings.local \
  uv run python apps/api/manage.py spectacular --file "$SCHEMA"

bun x openapi-typescript "$SCHEMA" -o "$OUT" >/dev/null

if [ "$CHECK" = "1" ]; then
  if ! diff -q "$TARGET" "$OUT" >/dev/null 2>&1; then
    echo "API types are stale. Run ./scripts/generate-api-types.sh and commit." >&2
    diff -u "$TARGET" "$OUT" | head -40 >&2
    exit 1
  fi
  echo "API types match the backend schema."
  exit 0
fi

cp "$OUT" "$TARGET"
echo "Wrote $TARGET"
