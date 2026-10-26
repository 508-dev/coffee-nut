# coffee-nut

A brewing journal for coffee enthusiasts. Record the bags you buy, log every
brew you make with them, and share a single brew with anyone by link.

- **API** — Django 5.2 LTS + Django REST Framework on PostgreSQL 17.
- **Web** — SvelteKit as a static SPA, no server runtime to deploy.
- **Also** — the REST API is the only interface. Native Android and iOS clients
  are planned, and the web app gets no privileged access.

See [`docs/architecture.md`](docs/architecture.md) for the data model, API
surface, and the reasoning behind both.

## What it does

- **Coffees and bags.** A *coffee* is the product a roaster sells; a *bag* is
  one purchase of it. Buy the same lot twice and you get one coffee with two
  bags, so you can compare across purchases.
- **Brews.** Log dose, water, temperature, grind, and timings against a bag.
  The form adapts to the method — espresso asks for a yield, pour over asks
  about the bloom — driven by data rather than hard-coded forms.
- **Autofill.** Countries, regions, farms, roasters, varietals, processes, brew
  methods, and tasting notes come pre-seeded. Anything missing you can add, and
  it stays private to you.
- **Sharing.** Tick one box on a brew to get an unguessable link that anyone can
  open without an account. Untick it and the link dies immediately.

## Requirements

| Tool | Version | Why |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.9.17 | Python toolchain. The dependency cooldown syntax needs it. |
| [Bun](https://bun.sh/) | 1.4.0 | JavaScript toolchain. |
| Docker + Compose | any recent | Runs PostgreSQL and Redis locally. |
| Python | 3.13 | Installed automatically by uv; see `.python-version`. |

Application processes run on your host, and only the databases run in
containers. That keeps reloads fast and stack traces readable.

## Quick start

```bash
git clone <this repo> && cd coffee-nut

cp .env.example .env          # dev.sh does this for you if you forget
uv sync                       # Python dependencies
bun install                   # JavaScript dependencies

./scripts/dev.sh
```

`dev.sh` brings up Postgres and Redis, applies migrations, seeds the reference
data, then starts Django and Vite together. It prints the URLs it chose:

```
  API       http://127.0.0.1:8720  (schema at /api/docs/)
  Web       http://127.0.0.1:8730
  Postgres  127.0.0.1:8740
  Redis     127.0.0.1:8750
```

Your ports will differ. They are derived from the worktree's path so that
several checkouts of this repo can run at once without colliding. Run
`./scripts/worktree-ports.sh env` to print the ones assigned to you.

Open the web URL, register an account, and add your first coffee. Verification
and password-reset emails print to the terminal running `dev.sh`; there is no
mail provider configured for local development.

To create an admin user for `/admin/`:

```bash
uv run python apps/api/manage.py createsuperuser
```

## Everyday commands

```bash
./scripts/dev.sh              # the whole stack
./scripts/dev.sh --help       # options, including --reclaim-ports

./scripts/lint.sh             # ruff + biome
./scripts/typecheck.sh        # mypy + svelte-check
./scripts/test.sh             # pytest + vitest
./scripts/format.sh           # apply formatting

./scripts/check-all.sh        # everything CI runs, in the same order
```

`check-all.sh` is the one that matters before pushing. It also catches the two
things easiest to forget: a model change without a migration, and API types
that have drifted from the schema.

Narrower loops:

```bash
uv run pytest apps/api/tests/test_brewing.py -q     # one test file
uv run pytest -k tenancy                            # by name
bun run --cwd apps/web test                         # web tests only
```

### Database and reference data

```bash
uv run python apps/api/manage.py makemigrations
uv run python apps/api/manage.py migrate
uv run python apps/api/manage.py seed_catalog       # idempotent
```

`seed_catalog` loads ~400 canonical rows: every ISO country, major growing
regions, varietals, processes, brew methods, and tasting notes. It matches
existing rows on their slug and updates in place, so re-running it never
duplicates anything and never breaks a foreign key your data already holds.
`dev.sh` runs it on every start.

Roasters and producers ship deliberately empty. A half-complete canonical list
is worse than none — people trust it, fail to find their roaster, and create a
duplicate anyway. Add your own; promotion to canonical happens later, once we
can see which names actually recur.

### API schema and generated types

The SPA's types are generated from the OpenAPI schema and committed:

```bash
./scripts/generate-api-types.sh              # regenerate after an API change
./scripts/generate-api-types.sh --check      # verify they are in sync
```

`check-all.sh` and CI run `--check`. If it fails, the frontend is typechecking
against an API that no longer exists.

Browse the API at `/api/docs/` while `dev.sh` is running, or fetch the raw
schema from `/api/schema/`.

## Layout

```text
apps/api/                 Django project
  manage.py
  src/coffeenut/
    settings/             base, local, test, production
    common/               abstract models, tenancy, errors, pagination, expand
    accounts/             custom User, Profile, auth endpoints
    catalog/              reference data + seed fixtures
    coffee/               Coffee, Bag
    brewing/              Brew
    sharing/              public read-only share views
  tests/

apps/web/                 SvelteKit SPA (static)
  src/routes/             file-based routes, incl. the public /s/[token] page
  src/lib/api/            generated types + fetch wrapper
  src/lib/components/     reference picker, method-aware brew fields

scripts/                  dev, lint, typecheck, test, format, check-all
docs/                     architecture and runbooks
compose.yml               Postgres + Redis
```

## Things worth knowing before you change code

A few rules are load-bearing, and breaking them is how user data leaks.
[`AGENTS.md`](AGENTS.md) has the full list; the short version:

- **Never filter on `owner` yourself.** Read through
  `Model.objects.visible_to(user)` and write through `owned_by(user)`. That
  single chokepoint is where tenancy is decided.
- **Owned viewsets extend `OwnedModelViewSet`** and register on
  `coffeenut.api_router`. A test walks that registry and fails if a new endpoint
  is missing owner scoping, so you do not have to remember to add it to a list.
- **Foreign keys use the scoped relation fields.** A plain
  `PrimaryKeyRelatedField` will happily accept another user's row.
- **Unauthorised access returns 404, not 403.** A 403 confirms the id exists.
- **The public share view has its own serializer**, an explicit allowlist. Never
  the authenticated one with fields excluded.
- **Model changes need a migration in the same commit.**

## Testing

Tests run against real PostgreSQL, never SQLite. The schema uses `CHECK`
constraints and partial unique indexes that SQLite models differently, so
SQLite would pass things production rejects. `./scripts/test.sh` starts the
container for you.

Worth knowing about the suite:

- `tests/test_tenancy.py` walks the API router and asserts every owned resource
  hides other users' rows.
- `tests/test_sharing.py::TestNoLeaks` asserts the *absence* of private fields
  from public payloads and pins the published field set.
- `tests/test_brewing.py::TestBriefWalkthrough` runs the whole product story end
  to end: buy a bag, brew it, list the bag's brews, share it.
- `tests/test_settings_contract.py` covers things only true outside the test
  suite, such as the production cache backend being importable.

## Configuration

`.env.example` is the contract; copy it to `.env`. Every value has a
local-safe default, so an unedited copy works.

Ports left commented out are derived from the worktree path. Set them only if
you need fixed values.

Before deploying anywhere, generate a real secret:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Documentation

| Document | What it covers |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Data model, API surface, auth, permissions, frontend. Start here. |
| [`docs/development.md`](docs/development.md) | Local development runbook and troubleshooting. |
| [`DECISIONS.md`](DECISIONS.md) | Standing decisions and why they were made. |
| [`AGENTS.md`](AGENTS.md) | Operating instructions for coding agents. |
| [`docs/deployment.md`](docs/deployment.md) | Production on Coolify: shape, configuration, auto-deploy, runbook. |

## Status

Feature-complete against the original brief, fully tested, and deployed at
<https://coffee.508.dev> (see [`docs/deployment.md`](docs/deployment.md)).
Open questions are tracked in [`docs/architecture.md` §11](docs/architecture.md):
transactional email provider, photo storage, and multi-currency handling.

## License

See [`LICENSE`](LICENSE).
