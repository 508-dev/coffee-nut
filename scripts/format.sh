#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

echo "==> ruff"
uv run ruff format .
uv run ruff check --fix .

echo "==> biome"
bun run format
