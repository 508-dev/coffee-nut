# Observability

Nothing is wired up yet. The environment names exist so that adding a
destination later is configuration rather than a code change.

Available in `.env.example`:

- `LOG_LEVEL` — used now; drives Django's root logger.
- `SENTRY_DSN` — unused.
- `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` — unused.

Django logs to the console via the `LOGGING` block in
`apps/api/src/coffeenut/settings/base.py`.

## When to add an SDK

Add Sentry once there is a real error-reporting destination and a release and
environment naming convention. It is the higher-value of the two: a
multi-tenant app wants to know about a 500 before a user reports it.

Add OpenTelemetry once there is a collector, a sampling policy, and a service
naming convention. Until then it is a dependency with nowhere to send data.

Do not add either just because the variables exist.

## Worth instrumenting first

When error reporting does arrive, these are the signals that matter for this
app specifically:

- **Tenancy failures.** `OwnedModelViewSet` raises `ImproperlyConfigured` when
  a viewset's queryset is not an `OwnedQuerySet`. That should page someone.
- **Public share traffic.** The one unauthenticated endpoint, and the one most
  likely to be scraped or abused.
- **Auth throttling.** Sustained 429s on `/auth/token/` are a credential
  stuffing signal, not a capacity problem.
- **Migration state.** A deploy that starts serving before migrations finish
  produces a specific, recognisable class of error.
