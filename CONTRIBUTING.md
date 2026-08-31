# Contributing

## Getting set up

See the [README](README.md) for requirements and the quick start. In short:

```bash
uv sync && bun install
./scripts/dev.sh
```

## Before you open a PR

Run the narrowest relevant checks while iterating:

```bash
./scripts/lint.sh
./scripts/typecheck.sh
./scripts/test.sh
```

Then run the full gate, which is what CI runs:

```bash
./scripts/check-all.sh
```

## Expectations

- **Read `docs/architecture.md` before structural changes.** It is the design
  authority, and several of its rules exist to stop user data leaking between
  accounts. `AGENTS.md` lists them.
- **Model changes need a migration in the same commit.** CI runs
  `makemigrations --check` and will fail otherwise.
- **API changes need regenerated types.** Run
  `./scripts/generate-api-types.sh` and commit the result, or CI will fail on
  drift.
- **Add or update tests when behaviour changes.** New endpoints that own user
  data are picked up automatically by the tenancy sweep, but their own
  behaviour still needs covering.
- **Update `.env.example` when adding configuration**, and the docs when
  changing a workflow.
- Keep edits surgical, and do not reformat unrelated files.

## Verifying real behaviour

Passing tests are necessary but not sufficient. Several bugs in this codebase
were invisible to a fully green suite and only appeared when the app was
actually run — a missing production dependency masked by a test-only cache
backend, and a form handler that threw before reaching the network. If you
change a user-facing flow, exercise it against `./scripts/dev.sh` too.

## What not to commit

Local state: `.venv`, `node_modules`, `.svelte-kit`, caches, logs, `.env`, and
`.context/`. The `.gitignore` covers these, but check `git status` before
staging broadly.
