# Devkit Selection Report

Required by `MANIFEST.md` before product feature work. One row per top-level
path in this repo, with an adopt / adapt / skip / delete / defer decision.

Target project: **coffee-nut** — Django + DRF REST API on Postgres, consumed by
a SvelteKit SPA and (later) native Android and iOS clients.

Because this repo *is* the devkit-generated repo, "target repo" rows and
"devkit" rows are the same set of paths. Decisions below are what the first
implementation PR should do.

## Decision Summary

| Decision | Count | Meaning |
| --- | --- | --- |
| adopt | 14 | Keep as-is. |
| adapt | 16 | Keep, but rewrite for Django/SvelteKit. |
| delete | 12 | Remove; devkit-only or wrong stack. |
| defer | 3 | Revisit when the need is real. |

## Top-Level Inventory

| Path | Decision | Reason |
| --- | --- | --- |
| `.cursor/rules/` | adopt | Points at `AGENTS.md`; still correct after the rewrite. |
| `.dockerignore` | adapt | Add `apps/api/staticfiles`, `apps/api/media`, `apps/web/.svelte-kit`, `.venv`. |
| `.editorconfig` | adapt | Add a Python section (4-space indent) alongside the existing JS defaults. |
| `.env.example` | adapt | Rewrite: drop `OPENAI_*`, add Django secret/debug/hosts, CORS, JWT lifetimes, email, and share-link base URL. Keep the worktree port block verbatim. |
| `.github/ISSUE_TEMPLATE/` | adopt | Generic and useful; no stack coupling. |
| `.github/PULL_REQUEST_TEMPLATE.md` | adopt | Generic. |
| `.github/FUNDING.yml` | defer | Co-op policy call, not an architecture call. |
| `.github/workflows/ci.yml` | adapt | Replace the `typescript` and `python` jobs with `api` and `web`; add a Postgres service container and a missing-migrations gate. See "CI" below. |
| `.gitignore` | adapt | Add `.svelte-kit/`, `staticfiles/`, `media/`, `*.sqlite3`. |
| `.pre-commit-config.yaml` | defer | `scripts/check-all.sh` already covers the gates; revisit if drift appears. |
| `.sops.yaml.example` | defer | No tracked encrypted files yet. Revisit at first deploy. |
| `.worktreeinclude` | adopt | Correct allowlist already. |
| `AGENTS.md` | adapt | Replace framework-neutral guidance with Django/SvelteKit specifics; keep supply-chain, `.context/`, and editing rules unchanged. |
| `CLAUDE.md` | adopt | Thin pointer to `AGENTS.md`; stays valid. |
| `CONTRIBUTING.md` | adapt | Update the quickstart to the real two-service dev loop. |
| `DECISIONS.md` | adapt | Rewrite from devkit constitution into coffee-nut product decisions. `MANIFEST.md` explicitly calls for this. |
| `LICENSE` | adopt | Unchanged unless the co-op wants a different license for a product repo. |
| `MANIFEST.md` | adapt | Reduce to a coffee-nut inventory; the devkit selection checklist has served its purpose once this report lands. |
| `README.md` | adapt | Rewrite as the coffee-nut overview and quickstart. |
| `SECURITY.md` | adopt | Reporting policy is project-independent. |
| `biome.json` | adapt | Retarget from `stacks/typescript` to `apps/web`; add Svelte file handling. |
| `bun.lock` | adapt | Regenerates when workspaces change to `apps/web`. |
| `bunfig.toml` | adopt | `minimumReleaseAge = 604800` is already the required policy. |
| `compose.yml` | adopt | Postgres 17 and Redis 7 on worktree-hashed ports are exactly what we need. Redis earns its place as the DRF throttle and cache backend. |
| `docker-compose.yml` | adopt | Compatibility wrapper; harmless. |
| `llms.txt` | adapt | Reindex against the new docs set. |
| `package.json` | adapt | `workspaces` becomes `["apps/web"]`; `db:*` scripts proxy Django `manage.py` instead of Drizzle. |
| `pnpm-workspace.example.yaml` | delete | We are committing to Bun. The pnpm path stays available upstream in the devkit. |
| `renovate.json` | adopt | Cooldown-aware policy applies to the Python and JS graphs alike. |
| `scripts/check-all.sh` | adapt | Fan out to both API and web gates. |
| `scripts/dev.sh` | adapt | Substantial rework: today it starts only the JS watcher. It must start Compose infra, Django on `API_PORT`, and Vite on `WEB_PORT`, with clean teardown. Its `is_expected_web_dev_command` already matches `vite`. |
| `scripts/docker-compose.sh` | adopt | Worktree-safe Compose wrapper; no changes needed. |
| `scripts/format.sh` | adapt | Add `ruff format` beside Biome. |
| `scripts/lint.sh` | adapt | Add `ruff check` beside Biome. |
| `scripts/test.sh` | adapt | Add `pytest` beside Vitest. |
| `scripts/typecheck.sh` | adapt | Add `mypy` and `svelte-check`. |
| `scripts/worktree-ports.sh` | adopt | Already emits `API_PORT`, `WEB_PORT`, `POSTGRES_HOST_PORT`, `DATABASE_URL`. Verified working: this worktree resolves to API 9620 / web 9630 / Postgres 9640. |
| `skills/508-devkit/` | delete | Devkit interface content, not product content. |
| `skills/add-migration/` | adapt | Genuinely useful, but rewrite for `manage.py makemigrations` instead of Alembic. |
| `skills/add-service/` | delete | Assumes the devkit's multi-service topology. |
| `skills/promote-context/` | adopt | `.context/` promotion workflow is stack-independent. |
| `skills/triage-ci-failure/` | adapt | Update for the new `api` and `web` job names. |
| `stacks/python/` | delete | FastAPI + Pydantic-settings + Alembic. Django supplies its own ORM, migrations, and settings layer. Ruff/MyPy/Pytest config is ported into the root `pyproject.toml` first. |
| `stacks/ruby/` | delete | No Ruby in this project. |
| `stacks/typescript/` | delete | Framework-neutral placeholder plus Drizzle, which Django's ORM replaces. Biome, tsconfig, and Vitest conventions are ported into `apps/web` first. |
| `extras/dev-scripts/` | delete | JS variants of scripts we are rewriting for a two-language repo. |
| `extras/devcontainer/` | skip | Leave unused; `DECISIONS.md` commits to host-run apps. |
| `extras/dockerfiles/` | adapt | `Dockerfile.api.example` needs a Django/Gunicorn rewrite; `Dockerfile.web-typescript.example` becomes a static-asset build. Both stay examples until deploy target is chosen. |
| `extras/github/` | adopt | Promote `CODEOWNERS.example` and `gitleaks.yml.example` into `.github/`. A public-share app warrants secret scanning. |
| `extras/object-storage/` | defer | Needed only when we add bag or brew photos. Likely, but not v1. |
| `extras/todo-to-issue/` | skip | Noisy for a small team. |
| `docs/agent-walkthrough.md` | delete | Devkit-only. |
| `docs/deployment.md` | adapt | Fill in once a deploy target exists. |
| `docs/development.md` | adapt | Rewrite the runbook for the Django + SvelteKit loop. |
| `docs/frontend.md` | adapt | Replace framework-neutral policy with the SvelteKit SPA decision and its `PUBLIC_API_BASE_URL` mapping. |
| `docs/github-template.md` | delete | Devkit-only cleanup checklist; this report supersedes it. |
| `docs/github-workflows.md` | adapt | Update for the new job matrix. |
| `docs/interfaces.md` | adapt | Becomes the REST API contract doc: versioning, pagination, errors, units. |
| `docs/observability.md` | adopt | Guidance is stack-independent; wire Sentry at deploy time. |
| `docs/pattern-report.md` | delete | Devkit design history. |
| `docs/secrets.md` | adopt | Applies directly to `DJANGO_SECRET_KEY` and JWT signing keys. |
| `docs/supply-chain.md` | adapt | Add the uv cooldown constraint recorded below. |
| `docs/template-proposal.md` | delete | Devkit design history. |
| `docs/tooling.md` | adapt | Rewrite for uv + Bun as the two toolchains. |

## New Paths This Project Adds

| Path | Purpose |
| --- | --- |
| `pyproject.toml` | uv workspace root; Ruff, MyPy, pytest, coverage config ported from `stacks/python`. |
| `.python-version` | Pins the interpreter for `uv` and CI. |
| `uv.lock` | Committed lockfile, per `DECISIONS.md`. |
| `apps/api/` | Django project and apps. |
| `apps/web/` | SvelteKit SPA. |
| `docs/architecture.md` | This pass's companion document. |
| `docs/selection-report.md` | This file. |

## CI

The current `changes` job filters on `stacks/typescript/**` and
`stacks/python/**`, and `ci-passed` hard-codes the `typescript`, `python`, and
`compose` job names. All three must change together or the merge gate silently
passes on skipped jobs.

Target matrix:

- `api` — `uv sync --locked`, `ruff check`, `mypy`, `manage.py check --deploy`,
  `manage.py makemigrations --check --dry-run`, `pytest` against a Postgres
  service container.
- `web` — `bun install --frozen-lockfile`, `biome check`, `svelte-check`,
  `vitest`, `vite build`.
- `compose` — unchanged.
- `ci-passed` — update the job-name list.

The missing-migrations gate is the highest-value addition: a model edit without
a migration is the most common way a Django repo breaks for everyone else.

## Toolchain Constraints

**uv cooldown — resolved.** `AGENTS.md` requires `exclude-newer = "P7D"` only
when `uv >= 0.9.17`. The machine was on uv 0.9.5 (a standalone user-level
install from October 2025) and has been upgraded to **0.12.6**. Both
`exclude-newer = "P7D"` and `required-version` were verified to parse and
resolve on 0.12.6 before being adopted here. The scaffold therefore writes:

```toml
[tool.uv]
required-version = ">=0.9.17"
exclude-newer = "P7D"
```

`required-version` is the important half. Without it, the cooldown is a silent
trap: a contributor on an older uv gets a settings-discovery failure with no
indication why. With it, uv states the requirement itself.

**Pin uv in CI.** `.github/workflows/ci.yml` currently uses
`astral-sh/setup-uv@v7.6.0` with no `version:` input, so CI installs whatever
is latest. That produced a silent local/CI skew (0.9.5 against ~0.12.6). Pin an
explicit `version:` so the two agree and upgrades are a reviewed change.

**Python version.** The host runs 3.14.6; CI currently installs 3.12. Django
5.2 LTS supports 3.10–3.13. Pin **3.13** in `.python-version` and CI — uv
resolves CPython 3.13.5 on this machine already. Exact Django and package
versions must be verified at scaffold time per the Currency decision in
`DECISIONS.md`.
