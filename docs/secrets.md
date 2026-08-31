# Secrets

Environment variables and CI secrets. Nothing encrypted is committed to this
repository, and nothing needs to be.

`.env.example` is the contract. Every value in it is safe to be public — it
exists to document shape and provide local-safe defaults. Copy it to `.env`,
which is gitignored.

## What must change before deploying

| Variable | Local default | Production requirement |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | an obvious placeholder | Real, ≥ 32 bytes. `production.py` has no default and will fail loudly if unset. |
| `JWT_SIGNING_KEY` | blank, falls back to the secret key | Set separately, so rotating one does not invalidate the other. |
| `DJANGO_DEBUG` | `true` | `false`. |
| `DJANGO_ALLOWED_HOSTS` | localhost | The real hostnames. |
| `CORS_ALLOWED_ORIGINS` | the local SPA | The real SPA origin. Credentials are sent, so `*` is not valid. |
| `JWT_REFRESH_COOKIE_SECURE` | `false` | `true`. |
| `EMAIL_*` | console backend | A real provider. |

Generate a secret key with:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

A blank value is not the same as an unset one. `JWT_SIGNING_KEY=` in `.env` is
*present and empty*, which is why the setting falls back with `or SECRET_KEY`
rather than relying on a default — an empty HMAC key would otherwise reach the
JWT library.

## Scanning

GitHub's native secret scanning and push protection are the first choice, if
the hosting organisation provides them. CI-based scanning is not enabled;
it needs a baseline and someone willing to triage historical findings.

If a real secret is ever committed: **rotate it**. Removing it from git history
is not sufficient, because it may already have been cloned or indexed.
