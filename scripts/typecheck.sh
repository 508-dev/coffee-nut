#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

echo "==> mypy"
uv run mypy

echo "==> svelte-check"
bun run typecheck
