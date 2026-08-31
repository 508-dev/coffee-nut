# GitHub workflows

One workflow, `.github/workflows/ci.yml`, with three component jobs behind a
path filter and a summary gate.

## Jobs

| Job | Runs when | Does |
| --- | --- | --- |
| `changes` | always | Path filter deciding which component jobs run. |
| `api` | `apps/api/**`, `pyproject.toml`, `uv.lock`, `.python-version`, `scripts/*.sh`, the generated schema types | ruff, mypy, Django checks, missing-migration gate, pytest, and the API type drift check. |
| `web` | `apps/web/**`, `package.json`, `bun.lock`, `biome.json`, `scripts/*.sh` | biome, svelte-check, vitest, static build. |
| `compose` | `compose.yml`, `.env.example` | Validates the Compose file parses against the example env. |
| `ci-passed` | always | The required check. |

`ci-passed` exists because the component jobs are skipped by the path filter,
and a skipped job cannot be a required check on its own. It treats `success`
and `skipped` as passes, but only after confirming `changes` itself succeeded —
otherwise a broken path filter would let everything skip silently.

**These four move together.** Adding a job means updating the filter, the job
list in `ci-passed`'s `needs`, and its result check. Editing one alone
degrades the merge gate without failing anything.

## The api job

It runs a real PostgreSQL 17 service container. The schema uses `CHECK`
constraints and partial unique indexes that SQLite models differently, so
SQLite would pass things production rejects.

Two gates there are easy to overlook and worth keeping:

- **`makemigrations --check --dry-run`.** A model change without a migration is
  the most common way this repository breaks for everyone else. Cheap to check,
  expensive to discover after merge.
- **`generate-api-types.sh --check`.** If the committed types drift from the
  schema, the frontend typechecks against an API that no longer exists.

## Hardening

- `permissions: contents: read` at the workflow level.
- Actions pinned by commit SHA.
- `persist-credentials: false` on checkout.
- `harden-runner` in audit mode.
- `paths-filter` runs with an empty token, forcing local git comparison rather
  than needing `pull-requests: read`.
- Tool versions pinned via `UV_VERSION` and `BUN_VERSION`.

## Templates

`.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md` are generic
and need no project-specific configuration.

## Not enabled

- **Secret scanning in CI.** GitHub's native scanning and push protection are
  the better first step. A CI scanner needs a baseline and someone to triage
  historical findings.
- **Dependency review.** Depends on GitHub's dependency graph being enabled,
  and reports vulnerabilities and licences rather than detecting active
  supply-chain attacks. Renovate cooldowns and locked installs do more here.
- **Deploy workflows.** No platform chosen; see [`deployment.md`](deployment.md).
