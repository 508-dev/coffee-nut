# Deployment

**Nothing is deployed yet, and no platform has been chosen.** This document
records what a deployment will need, so the decision can be made with the
constraints visible.

## Decision record

Fill this in when the platform is chosen. Leaving it blank is better than
guessing.

- Target platform:
- Services deployed:
- Database and backups:
- Secrets management:
- Preview environments:
- Rollback strategy:

## What has to be deployed

Two artefacts, and they are unusually independent:

1. **The API** — a Django WSGI/ASGI application needing PostgreSQL 17 and
   Redis. `apps/api/src/coffeenut/wsgi.py` is the entrypoint, and
   `coffeenut.settings.production` the settings module.
2. **The web app** — a directory of static files from `bun run build`. There is
   no server runtime; any static host or CDN will do.

Because the SPA is static and talks to the API purely over HTTPS, the two can
be hosted separately. That also means CORS and the refresh-cookie domain need
deliberate configuration — see below.

## Before the first deploy

1. **Set the real environment.** See [`secrets.md`](secrets.md) for the
   variables that must change. `production.py` deliberately has no default for
   `DJANGO_SECRET_KEY`, so a missing one fails at startup rather than silently
   running insecurely.
2. **Decide the cookie domain.** The refresh token is an `HttpOnly` cookie
   scoped to `/api/v1/auth/`. If the SPA and API are on different hosts, set
   `JWT_REFRESH_COOKIE_DOMAIN` to a shared parent domain, and confirm
   `SameSite` still permits the request. Serving both from one domain avoids
   the problem entirely and is the simpler choice.
3. **Choose an email provider.** Registration verification and password reset
   need real delivery. Local development uses the console backend.
4. **Run `migrate` before serving.** And `collectstatic`, for the admin.
5. **Seed the catalog.** `manage.py seed_catalog` is idempotent, so it is safe
   to run on every deploy.
6. **Check `manage.py check --deploy`.** It flags the security settings that
   production mode should have on.

## Health

`/health/` returns `{"status": "ok"}` and requires no authentication. It does
not currently check the database, which is deliberate — it answers "is this
process up?", not "is the system healthy?". A deeper check should be a separate
endpoint if a platform needs one.

## Not yet decided

- Whether to containerise the API or run it on a platform buildpack. Compose
  here is for local infrastructure only, not a deployment artefact.
- Backup and restore policy for PostgreSQL.
- Object storage, which arrives with photo support.
