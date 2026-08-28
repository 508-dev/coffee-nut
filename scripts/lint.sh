#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

echo "==> ruff"
uv run ruff check .
uv run ruff format --check .

echo "==> biome"
bun run lint
