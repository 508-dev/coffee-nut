# Deployment

coffee-nut runs on 508.dev's Coolify at **https://coffee.508.dev**, as one
Docker Compose stack built from this repository.

## Decision record

- **Target platform:** Coolify (`coolify.508.dev`), server `Prod1`, project
  `coffee-nut`, environment `production`.
- **Services deployed:** one compose stack, `compose.prod.yml`: `web` (nginx),
  `api` (Django under gunicorn), `postgres`, `redis`.
- **Database and backups:** PostgreSQL 17 inside the stack, on a named volume.
  **No backups yet.** Coolify's scheduled backups cover its standalone database
  resources, not a database inside a compose application.
- **Secrets management:** Coolify environment variables on the application.
  Nothing secret is in the repository.
- **Preview environments:** off.
- **Rollback strategy:** redeploy an earlier commit from Coolify, or revert and
  push. Migrations run forward only, so a rollback across a migration needs a
  manual `migrate <app> <previous>` first.

## Shape

```text
            Traefik (Coolify, TLS, coffee.508.dev)
                         |
                       web :80   nginx
          /, /s/...  -> static SPA, index.html fallback
          /static/   -> Django collected static (admin, API docs)
 /api/ /admin/ /health/ -> api :8000
                         |
                       api       gunicorn + Django
                      /    \
               postgres    redis
```

Everything is one origin, which is what makes the auth design simple: the SPA
calls `/api/v1` by relative path, CORS never applies, and the `HttpOnly`
refresh cookie needs no shared parent domain.

The two images come from the root `Dockerfile`:

- `api` installs the locked dependencies with uv, runs `collectstatic`, and
  starts with `deploy/api-start.sh`, which runs `migrate` and `seed_catalog`
  (both idempotent) before `exec gunicorn`.
- `web` is nginx with `deploy/nginx.conf`, the SPA build, and the API's
  collected static files.

nginx trusts the last address in `X-Forwarded-For`, the one Traefik appends,
and passes only that to Django. That keeps DRF's throttling keyed on the real
client: forwarding the header as-is would let a client choose its own throttle
identity, and dropping it would throttle every user as one.

## Configuration

Set on the Coolify application. `compose.prod.yml` derives everything else.

| Variable | Required | Notes |
| --- | --- | --- |
| `PUBLIC_HOST` | yes | `coffee.508.dev`. Drives allowed hosts, CORS, and email and share links. |
| `DJANGO_SECRET_KEY` | yes | Random, at least 32 bytes. |
| `JWT_SIGNING_KEY` | yes | Random, distinct from the secret key. |
| `POSTGRES_PASSWORD` | yes | Random and URL-safe; it is embedded in `DATABASE_URL`. |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | no | Defaults to the console backend; see below. |
| `GUNICORN_WORKERS`, `LOG_LEVEL` | no | 3 and `INFO`. |

Optional variables default to a working value rather than to empty, because
django-environ reads a present-but-blank variable as `""` (see
[`secrets.md`](secrets.md)).

**Email is not delivered yet.** Until a provider is chosen
([`architecture.md` §11](architecture.md)), verification and password-reset
emails are written to the `api` container's log. Sign-up works; password reset
does not reach the user. To switch, set `EMAIL_BACKEND` to
`django.core.mail.backends.smtp.EmailBackend` and fill in `EMAIL_HOST`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`.

## Auto-deploy

Pushing to the deployed branch redeploys. A GitHub webhook on the repository
sends `push` events to Coolify's manual-webhook endpoint
(`/webhooks/source/github/events/manual`), signed with the secret stored on the
application as `manual_webhook_secret_github`. Coolify matches the repository
and branch and queues a deployment.

The deployed branch is currently **`feat/scaffold-foundation`**, because that is
where the application lives; `main` holds only the initial commit. Once the
branch merges, point the application at `main`.

Deploys are not gated on CI: CI validates `compose.prod.yml`, but a commit that
fails its tests still deploys. If deploys should wait for CI, replace the
webhook with a CI job that calls Coolify's `POST /api/v1/deploy` using a token
limited to the deploy ability.

## Operating

From the Coolify UI, the application is under *Projects → coffee-nut →
production*. Logs, a terminal per container, and redeploy are all there.

```bash
# After any deploy: walk the product story against the live site.
# Creates a throwaway smoke+<random>@example.com account each run.
./scripts/smoke-deploy.py https://coffee.508.dev
```

Create an admin user from the `api` container's terminal in Coolify:

```bash
python apps/api/manage.py createsuperuser
```

Run the production stack locally to test a change to the images or the
compose file. Nothing publishes a port, so add one with an override file:

```bash
cat > /tmp/ports.yml <<'EOF'
services:
  web:
    ports: ["127.0.0.1:18080:80"]
EOF
DJANGO_SECRET_KEY=local-only-0123456789abcdef0123456789abcdef \
JWT_SIGNING_KEY=local-only-fedcba9876543210fedcba9876543210 \
PUBLIC_HOST=coffee.localtest POSTGRES_PASSWORD=local \
  docker compose -p coffeenut-prodtest -f compose.prod.yml -f /tmp/ports.yml up -d --build --wait

./scripts/smoke-deploy.py http://127.0.0.1:18080 --host coffee.localtest
docker compose -p coffeenut-prodtest -f compose.prod.yml down -v
```

## Driving Coolify from its API

This deployment was set up entirely through Coolify's REST API, which is also
how a coding agent can operate it. Keep the credentials in the gitignored
`.env` (placeholders are in `.env.example`):

```bash
COOLIFY_URL=https://coolify.508.dev
COOLIFY_API_TOKEN=...      # Coolify: Keys & Tokens -> API tokens
COOLIFY_APP_UUID=eqccpwotqp4hwhwwzbnn1pul   # this application; not a secret
```

Load just those, quoted, since `.env` as a whole is not valid shell
(`DEFAULT_FROM_EMAIL` contains `<...>`, and Coolify tokens contain `|`):

```bash
eval "$(grep -E '^COOLIFY_' .env | sed 's/^/export /; s/=\(.*\)$/="\1"/')"
api() { curl -sS -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H 'Content-Type: application/json' "$COOLIFY_URL/api/v1$@"; }

api "/applications/$COOLIFY_APP_UUID" | jq '{status, git_branch}'
api "/deploy?uuid=$COOLIFY_APP_UUID" -X POST            # redeploy
api "/deployments/applications/$COOLIFY_APP_UUID"       # history
api "/deployments/<deployment_uuid>" | jq -r .status    # one deploy
api "/applications/$COOLIFY_APP_UUID/envs/bulk" -X PATCH \
  -d '{"data":[{"key":"LOG_LEVEL","value":"DEBUG"}]}'   # then redeploy
```

Things learned setting it up:

- Cloudflare fronts `coolify.508.dev` and rejects some default client user
  agents, Python's `urllib` among them. curl is fine; scripts should send their
  own descriptive `User-Agent`.
- `*.508.dev` already resolves to `Prod1`, so a new subdomain needs no DNS
  change; Traefik issues the certificate on first request.
- The server runs Docker 24 and Compose 2.18. Keep `compose.prod.yml` to syntax
  that version understands, and the `Dockerfile` buildable by the classic
  builder.
- Only the `web` service gets a domain (`docker_compose_domains`). Nothing
  publishes a host port; the stack talks over its own network.
- The application's API reference is published by Coolify as `openapi.json` in
  the `coollabsio/coolify` repository.

## Health

`/health/` returns `{"status": "ok"}` and requires no authentication. It does
not check the database, which is deliberate: it answers "is this process
up?", not "is the system healthy?". The compose healthchecks gate start-up
order (postgres and redis, then api, then web) and feed Coolify's status.

## Not yet decided

- Backups for the in-stack PostgreSQL. Options: a Coolify scheduled task running
  `pg_dump` to S3, or moving to a Coolify-managed database resource, which has
  backups built in.
- Transactional email provider.
- Object storage, which arrives with photo support.
