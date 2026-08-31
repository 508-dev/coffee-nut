# Tooling

Two toolchains, one entrypoint each.

| Concern | Python | JavaScript |
| --- | --- | --- |
| Package manager | `uv` | `bun` |
| Lint | `ruff check` | `biome check` |
| Format | `ruff format` | `biome format` |
| Types | `mypy` (+ django-stubs, drf-stubs) | `svelte-check` |
| Tests | `pytest` (+ pytest-django) | `vitest` |

Prefer `uv run …` and `bun run …` over raw interpreters, so everyone runs the
same resolved versions.

## Scripts are the interface

`scripts/` holds the entrypoints humans, agents, and CI all use. Keeping one
command per concern means a tool change is one edit, and that a local pass means
the same thing as a CI pass.

```bash
./scripts/dev.sh          ./scripts/lint.sh
./scripts/test.sh         ./scripts/typecheck.sh
./scripts/format.sh       ./scripts/check-all.sh
```

`dev.sh` is `bash`, not `sh`: it uses `wait -n` to exit as soon as either
service dies, which is not POSIX and is unsupported by dash. The others are
POSIX `sh`.

## Version pins

| Thing | Pinned in | Value |
| --- | --- | --- |
| Python | `.python-version` | 3.13 |
| uv | `pyproject.toml` (`required-version`), `ci.yml` (`UV_VERSION`) | ≥ 0.9.17 / 0.12.6 |
| Bun | `package.json` (`packageManager`), `ci.yml` (`BUN_VERSION`) | 1.4.0 |
| Django | `apps/api/pyproject.toml` | 5.2 LTS line |

CI pins the tools themselves, not just the dependencies. `setup-uv` was
previously unpinned, which silently hid a local/CI version skew.

## Known sharp edges

Each of these cost time once and is now configured away. They are here so the
configuration does not look arbitrary.

- **ruff formats Python inside Markdown.** `docs/**` is excluded from ruff, so
  illustrative code samples in prose stay as written.
- **Biome does not parse Svelte templates.** It reads the `<script>` block only,
  so an import used solely in markup looks unused. `noUnusedImports` and
  `noUnusedVariables` are off for `*.svelte`.
- **Generated and curated files are excluded from Biome.**
  `apps/web/src/lib/api/schema.d.ts` because formatting it would permanently
  fail the drift check, and `apps/api/**/fixtures/` because those are curated
  data grouped with blank lines for review.
- **`svelte-kit sync` reads `svelte.config.js`, not `vite.config.ts`.** The
  shared root `.env` needs `kit.env.dir`, not Vite's `envDir`, or
  `$env/static/public` comes back untyped.
- **django-stubs runs `django.setup()`.** So `mypy_path` needs `apps/api` as
  well as `apps/api/src`, or the plugin cannot import the test app named in
  `INSTALLED_APPS`.
- **DRF binds `THROTTLE_RATES` at import time.** `override_settings` cannot
  change a rate; tests monkeypatch the dict. Test settings set rates to `None`
  rather than removing them, because `ScopedRateThrottle` raises for a declared
  scope with no entry.

## Adding a dependency

```bash
uv add <package>                    # API
bun add --cwd apps/web <package>    # web
```

Commit the lockfile. Both managers apply a release-age cooldown, so a version
published in the last seven days will not resolve — see
[`supply-chain.md`](supply-chain.md).
