# Security Policy

## Reporting vulnerabilities

Do not open public issues for vulnerabilities or leaked secrets. Report them
privately to the maintainers.

> **TODO:** replace this with the real reporting address before the repository
> is made public.

## Handling user data

coffee-nut is multi-tenant: every coffee, bag, and brew belongs to exactly one
user, and one account must never see another's data. Several conventions exist
solely to enforce that, and they are not optional:

- All reads go through `Model.objects.visible_to(user)` and writes through
  `owned_by(user)`. Nothing else may filter on `owner`.
- Owned viewsets extend `OwnedModelViewSet` and register on
  `coffeenut.api_router`. `tests/test_tenancy.py` walks that registry, so a new
  endpoint without owner scoping fails CI.
- Foreign keys to user-owned rows use `OwnedPrimaryKeyRelatedField`. A plain
  `PrimaryKeyRelatedField` accepts another user's row.
- Unauthorised access returns 404, not 403. A 403 confirms the id exists.
- The public share endpoint uses its own allowlist serializer, never the
  authenticated one with fields excluded, so a newly added field cannot leak by
  default. `tests/test_sharing.py::TestNoLeaks` pins the published field set.

Password reset never reveals whether an address is registered, and a bad token
and a bad uid return the same error, so neither can be used to enumerate
accounts.

## Secret handling

- Keep secrets in environment variables. Never commit real `.env` files,
  tokens, keys, or production data.
- `.env.example` is documentation; every value in it is safe to be public.
- `DJANGO_SECRET_KEY` must be at least 32 bytes — JWT signing warns below that.
  Generate one with:

  ```bash
  uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

- Set `JWT_SIGNING_KEY` separately from `DJANGO_SECRET_KEY` in production so
  rotating one does not invalidate the other.

## Authentication

Access tokens are short-lived and held in memory by the SPA, never in
`localStorage`. Refresh tokens reach browsers as `HttpOnly` cookies scoped to
the auth endpoints, and native clients receive them in the response body for
the platform keystore. Refresh tokens rotate and the previous one is
blacklisted. Changing or resetting a password revokes every outstanding session.

## Dependency policy

Cooldowns and locked installs, so a freshly published malicious version is not
picked up immediately:

- Bun: `minimumReleaseAge = 604800` in `bunfig.toml`.
- uv: `exclude-newer = "P7D"` in `pyproject.toml`, with
  `required-version = ">=0.9.17"` so an older client fails loudly rather than
  silently ignoring it.
- Renovate: `minimumReleaseAge = "7 days"`.
- CI uses `uv sync --locked` and `bun install --frozen-lockfile`, with the tool
  versions themselves pinned.

## GitHub Actions

Workflows use least-privilege permissions, pinned action SHAs,
`persist-credentials: false`, and `harden-runner` in audit mode.

Secret scanning is not currently enabled in CI. GitHub's native secret scanning
and push protection are the better first step if the repository moves to an
organisation that provides them.
