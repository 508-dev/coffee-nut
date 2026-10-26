# Production images. Two runtime targets, both built by compose.prod.yml:
#
#   api  Django under gunicorn. Runs migrations and seeds the catalog on start.
#   web  nginx serving the static SPA and Django's collected static files, and
#        proxying /api/, /admin/ and /health/ to the api service.
#
# Serving both from one origin is what docs/deployment.md recommends: no CORS,
# and the refresh cookie needs no shared parent domain.
#
# Not used for local development; that is ./scripts/dev.sh.

# --- SPA --------------------------------------------------------------------

FROM oven/bun:1.4.0 AS web-build
WORKDIR /app

COPY package.json bun.lock bunfig.toml ./
COPY apps/web/package.json apps/web/
RUN bun install --frozen-lockfile

COPY apps/web apps/web
# Baked into the bundle by $env/static/public. A path rather than a URL because
# the SPA and the API share an origin.
ARG PUBLIC_API_BASE_URL=/api/v1
ENV PUBLIC_API_BASE_URL=${PUBLIC_API_BASE_URL}
RUN bun run --cwd apps/web build

# --- API --------------------------------------------------------------------

FROM python:3.13-slim AS api

# Same uv as CI's UV_VERSION, so the lockfile is read the same way.
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=coffeenut.settings.production

WORKDIR /app

# Dependencies first, so a source-only change reuses this layer.
COPY pyproject.toml uv.lock .python-version ./
COPY apps/api/pyproject.toml apps/api/
RUN uv sync --locked --no-dev --no-install-workspace

COPY apps/api apps/api
RUN uv sync --locked --no-dev

# production.py refuses to import without these. Neither value outlives this
# step; the real ones come from the runtime environment.
RUN DJANGO_SECRET_KEY=collectstatic-only DJANGO_ALLOWED_HOSTS=localhost \
    python apps/api/manage.py collectstatic --noinput

COPY deploy/api-start.sh /usr/local/bin/api-start

RUN useradd --system --uid 10001 --no-create-home coffeenut
USER coffeenut

EXPOSE 8000
CMD ["api-start"]

# --- Web --------------------------------------------------------------------

FROM nginx:1.30-alpine AS web

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /app/apps/web/build /usr/share/nginx/html
# STATIC_ROOT in settings/base.py.
COPY --from=api /app/apps/api/src/staticfiles /usr/share/nginx/static

EXPOSE 80
