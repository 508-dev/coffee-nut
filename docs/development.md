# Local development

The [README](../README.md) covers requirements and the quick start. This is the
detail: what the scripts actually do, and what to do when something misbehaves.

## The shape of it

Application processes run on your host; only PostgreSQL and Redis run in
containers. Host processes reload faster and give readable stack traces, while
Compose keeps the datastores reproducible.

`./scripts/dev.sh` does the whole sequence:

1. Copies `.env.example` to `.env` if you have no `.env`.
2. Computes this worktree's ports and exports them, overriding `.env`.
3. Starts Postgres and Redis, then waits for Postgres to accept connections.
4. Applies migrations.
5. Seeds the reference catalog (idempotent).
6. Starts Django and Vite, and exits if either one dies.

Ctrl-C stops both.

## Ports

Ports are derived from a hash of the worktree's absolute path, so two checkouts
can run simultaneously without editing anything:

```bash
./scripts/worktree-ports.sh env
```

`dev.sh` also derives `PUBLIC_WEB_BASE_URL`, `PUBLIC_SHARE_BASE_URL`,
`PUBLIC_API_BASE_URL`, and `CORS_ALLOWED_ORIGINS` from those ports. Without
that, share links and verification emails in one worktree point at another
worktree's port.

Exported shell variables win over `.env`, because `django-environ`'s
`read_env` uses `setdefault`. That is what keeps worktrees isolated.

If a previous run left a port held:

```bash
./scripts/dev.sh --reclaim-ports
```

That is deliberately narrow. It inspects the listener with `lsof` and refuses
to kill anything that does not look like this worktree's own dev process.

## Running the pieces separately

```bash
./scripts/docker-compose.sh up -d postgres redis
uv run python apps/api/manage.py runserver 127.0.0.1:$API_PORT
bun run --cwd apps/web dev
```

Use `./scripts/docker-compose.sh` rather than `docker compose` directly; it
injects the worktree-specific ports and project name.

## Django management commands

```bash
uv run python apps/api/manage.py <command>
```

Worth knowing:

- `createsuperuser` — for `/admin/`.
- `seed_catalog` — reloads canonical reference data. Idempotent: it matches on
  slug and updates in place, so it never duplicates and never orphans a foreign
  key your data already holds.
- `makemigrations --check --dry-run` — what CI runs. Non-zero means you changed
  a model without a migration.
- `spectacular --file schema.yaml` — dump the OpenAPI schema.
- `check --deploy` — production security checklist.

Settings default to `coffeenut.settings.local`. Tests use
`coffeenut.settings.test`, which points at real Postgres, swaps in a local-memory
cache, and disables throttle rates.

## Tests

```bash
./scripts/test.sh                                   # pytest + vitest
uv run pytest apps/api/tests/test_brewing.py -q     # one file
uv run pytest -k tenancy                            # by name
uv run pytest -x --lf                               # stop at first, rerun last failures
bun run --cwd apps/web test
```

Tests need Postgres running; `test.sh` starts it. They will not fall back to
SQLite — the schema uses `CHECK` constraints and partial unique indexes that
SQLite models differently, so a SQLite pass would be misleading.

`tests/testapp/` holds concrete models that exist only to exercise the abstract
bases in `coffeenut.common`. It is installed by the test settings and has real
migrations, because its foreign key to the custom user model means `run_syncdb`
would create its tables before `accounts` exists.

## The full gate

```bash
./scripts/check-all.sh
```

Runs, in order: ruff (lint + format), biome, mypy, svelte-check, the
missing-migration check, the API type drift check, pytest, vitest, and the web
build. This is exactly what CI runs.

## API types

The SPA's types come from the OpenAPI schema and are committed:

```bash
./scripts/generate-api-types.sh            # regenerate
./scripts/generate-api-types.sh --check    # verify in sync
```

It reads the schema from Django directly, so it needs no running server.

`apps/web/src/lib/api/schema.d.ts` is excluded from Biome. Formatting it would
permanently fail the drift check, because regeneration produces unformatted
output.

## Troubleshooting

**429 on register or login.** You hit the real throttle — 5 registrations an
hour, 10 auth attempts a minute. Common when running automated UI tests. Clear
the counters:

```bash
./scripts/docker-compose.sh exec -T redis redis-cli FLUSHDB
```

**A share link or verification email points at the wrong port.** You started
Django directly instead of through `dev.sh`, so the `PUBLIC_*` variables fell
back to `.env`.

**`svelte-check` reports errors that make no sense.** Run
`bun run --cwd apps/web typecheck`, which runs `svelte-kit sync` first to
regenerate `.svelte-kit/`. Deleting that directory and re-running is safe.

**Session lost after a restart, or a saved browser session stops working.**
Refresh tokens rotate and the previous one is blacklisted. An old cookie is
genuinely dead; sign in again. For multi-step browser automation, do the whole
flow in one session rather than reusing saved state.

**uv refuses to run.** `required-version = ">=0.9.17"` in `pyproject.toml`
means an older uv fails deliberately rather than silently ignoring the
dependency cooldown. Upgrade with `uv self update`.

**Postgres will not start.** Check the port is free with
`./scripts/worktree-ports.sh env` and `lsof -i :<port>`. To start clean:

```bash
./scripts/docker-compose.sh down -v    # destroys local data
```

## Agent scratch

`.context/` is gitignored, workspace-local scratch. Do not commit it. Durable
knowledge belongs in `docs/`, `DECISIONS.md`, or the README.
