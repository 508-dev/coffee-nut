#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

# Tests need real Postgres; the schema uses CHECK constraints and partial
# unique indexes that SQLite models differently.
eval "$(./scripts/worktree-ports.sh export)"
./scripts/docker-compose.sh up -d postgres >/dev/null

echo "==> pytest"
uv run pytest "$@"

echo "==> vitest"
bun run test
