# coffee-nut Decisions

Standing decisions and why they were made. `docs/architecture.md` describes
*what* the system is; this file records *why* it is that way, so a future change
can disagree deliberately rather than by accident.

Each entry says when deviating is reasonable. None of them are sacred, but the
tenancy ones are close.

---

## Django REST Framework, not django-ninja

**Decision:** DRF for the API layer.

**Why:** mature permission and serializer primitives, and the largest body of
documentation and prior art. Three clients will consume this API over its life;
the boring choice is the right one. OpenAPI comes from drf-spectacular.

**Deviate when:** never casually. Mixing frameworks in one project costs more
than either choice saves.

## Django 5.2 LTS, not the latest release

**Decision:** pin to the 5.2 LTS line.

**Why:** security support into 2028, and the whole surrounding ecosystem —
DRF, simplejwt, drf-spectacular, and the type stubs — is proven against it.
Stub packages in particular lag new Django majors.

**Deviate when:** a needed feature only exists in a newer release, and the
dependency set resolves cleanly against it.

## One tenancy chokepoint

**Decision:** all user-owned rows are reached through
`OwnedQuerySet.visible_to(user)` for reads and `owned_by(user)` for writes.
Nothing else in the codebase filters on `owner`.

**Why:** this is the single most important structural decision in the schema.
It is what makes "add social features later" a change to one method instead of
an audit of every endpoint, and it means tenancy correctness is reviewable in
one place rather than distributed across every viewset.

`tests/test_tenancy.py` walks the router registry rather than a hand-maintained
list, so a new endpoint that forgets scoping fails CI without anyone
remembering to add it.

**Deviate when:** you have a genuinely different access model. Then change
`visible_to`, not its callers.

## 404, never 403, for another user's row

**Decision:** unauthorised access to an existing row returns 404. A
client-supplied `owner` is ignored rather than rejected.

**Why:** a 403 confirms the id exists, and a rejection confirms a user id is
real. Both are enumeration oracles. Absence leaks nothing.

**Deviate when:** never, on user-owned resources.

## Public sharing uses an allowlist serializer

**Decision:** the anonymous share view has its own serializer listing exactly
what is public — not the authenticated serializer with fields excluded.

**Why:** someone will add a field to the private serializer one day. With an
allowlist that field cannot leak by default; with exclusions it leaks until
someone notices. The cost is remembering to add genuinely public fields, which
is the safer direction to fail in.

**Deviate when:** never. `tests/test_sharing.py::TestNoLeaks` enforces it.

## JWT, with delivery that differs by client

**Decision:** one JWT model for all clients. Browsers get the refresh token as
an `HttpOnly` cookie and never see it in a response body; native clients opt in
with `X-Client: native` and receive it in the body for the platform keystore.
Cookie delivery is the default.

**Why:** a browser has no safe place to store a long-lived token, and anything
script can read an XSS can steal. A native app does have one. Defaulting to
cookies means a client that forgets the header gets the safer behaviour, not
the weaker one.

**Deviate when:** a client genuinely cannot handle cookies. That is what the
header is for.

## Coffee and Bag are separate

**Decision:** a `Coffee` is the product; a `Bag` is one purchase of it.

**Why:** buying the same lot twice should reuse one product identity, so
"how did this year's harvest compare?" is a query rather than a guess.
`roast_date` lives on `Bag` because freshness is a property of the physical bag
and is the field most likely to differ between two purchases.

**Deviate when:** never — collapsing them loses information that cannot be
recovered.

## Brew parameters are columns, not a JSON blob

**Decision:** method-specific brew parameters are real, nullable columns.
`BrewMethod.parameter_schema` declares which apply and which are required.

**Why:** three clients consume this API. A JSON blob is invisible to OpenAPI,
unvalidatable at the database layer, and awkward to filter or aggregate on.
Nearly every field applies to two or more methods, so the table is narrower
than it first looks. The schema keeps the form method-aware while the contract
stays typed, and adding a brew method remains a fixture change.

**Deviate when:** a parameter is genuinely one-off or experimental. That is
what the `extras` JSON field is for.

## Reference data is one table with a nullable owner

**Decision:** canonical rows (`owner IS NULL`) and users' private additions
share a table, with `merged_into` as the promotion path.

**Why:** foreign keys stay uniform — a `Coffee` points at a `Roaster` without
caring which kind it is. Promoting a popular custom entry becomes a data change
rather than a migration, and existing foreign keys keep resolving.

**Deviate when:** an entity is genuinely canonical-only, like `Country`. Then
make it read-only at the API rather than splitting the table.

## Roasters and producers ship empty

**Decision:** seed countries, regions, varietals, processes, brew methods, and
tasting notes. Seed no roasters or producers.

**Why:** a half-complete canonical list is worse than none. People trust it,
fail to find their roaster, and create a duplicate anyway. Until we have done
the sourcing, every roaster is a user row, and `merged_into` promotes them once
we can see which names recur.

**Deviate when:** we have a real, reasonably complete source.

## No copyrighted tasting vocabulary

**Decision:** the seeded `TastingNote` tree is independently worded. The
SCA / World Coffee Research Flavor Wheel and its lexicon are excluded.

**Why:** they are copyrighted works. Using them needs permission or a licence.

**Deviate when:** a licence or partnership is in place. The schema absorbs one
cleanly: `TastingNote` is a reference model with `source`/`external_id`
columns, so an imported taxonomy lands as canonical rows.

## SvelteKit as a static SPA

**Decision:** `adapter-static`, `ssr = false`, one HTML fallback. Hand-rolled
CSS, no component library, no CSS framework.

**Why:** the product does not need SSR, and a static bundle has no server
runtime to deploy or secure. File-based routing and per-route code splitting
are worth the framework; a component library is not, against a bundle budget.

**Deviate when:** SEO on the public share pages becomes a real requirement.
That is the one surface where rendering on the server would pay.

## The API is the only interface

**Decision:** the web app gets no privileged access. Every capability is a
documented REST endpoint.

**Why:** native clients are planned. Anything the SPA can do through a private
path is something a mobile app will later need reimplemented.

**Deviate when:** never, while mobile clients remain on the roadmap.

## Client-generatable UUIDs, `updated_since`, cursor pagination

**Decision:** UUID primary keys that clients may supply on create, an
`?updated_since=` filter on every list endpoint, and cursor pagination.

**Why:** all three are cheap now and expensive to retrofit. They are what make
offline creation and incremental sync possible for a mobile client without
reshaping the API or backfilling indexes on a live table.

**Deviate when:** never — the cost today is close to zero.

## Tests run against real PostgreSQL

**Decision:** never SQLite, not even for speed.

**Why:** the schema relies on `CHECK` constraints and partial unique indexes
that SQLite models differently. SQLite would pass things production rejects.

**Deviate when:** never.

## Verify against a running app, not only tests

**Decision:** a feature is not done until it has been exercised against
`./scripts/dev.sh`.

**Why:** this is not a platitude here. Test settings substitute local backends,
which hides whole classes of defect. Bugs that a fully green suite missed
include a missing production dependency, a blank signing key, a wrong error
field, a 500 where a 400 belonged, and a form handler that threw before
reaching the network. `tests/test_settings_contract.py` now covers some of
these, but it cannot cover all of them.

**Deviate when:** the change genuinely cannot affect runtime behaviour.

## Host applications, Compose infrastructure

**Decision:** PostgreSQL and Redis run in Docker Compose; Django and Vite run
on the host.

**Why:** host processes reload faster and produce readable stack traces, while
Compose keeps the datastores reproducible.

**Deviate when:** deployment parity or a binary dependency requires full
containerisation. Put that in `docs/development.md` explicitly.

## Ports derived from the worktree path

**Decision:** `scripts/worktree-ports.sh` hashes the absolute worktree path
into a port block.

**Why:** several checkouts can run at once without hand-editing `.env`.

**Deviate when:** a platform assigns ports dynamically. Map its reservation to
`WORKTREE_PRIMARY_PORT` or `WORKTREE_PORT_BLOCK_START` rather than editing the
helper.

## Dependency cooldowns, locked installs, pinned CI tools

**Decision:** `minimumReleaseAge` for Bun, `exclude-newer = "P7D"` for uv,
`minimumReleaseAge` for Renovate, locked installs in CI, and explicit
`UV_VERSION` and `BUN_VERSION` pins.

**Why:** a newly published version is the supply-chain risk window. The tool
pins matter too: `setup-uv` was previously unpinned, which silently hid a
local/CI version skew.

`required-version` accompanies the uv cooldown so an older client fails with a
clear message instead of an opaque settings-discovery error.

**Deviate when:** a security fix needs immediate adoption. Note the exception
in the PR.

## Generated API types are committed and gated

**Decision:** `apps/web/src/lib/api/schema.d.ts` is generated from the OpenAPI
schema, committed, and verified by `--check` in CI.

**Why:** if the types drift, the frontend typechecks against an API that no
longer exists — the worst kind of green build. Generating from Django directly
rather than a running server keeps it working offline and in CI.

**Deviate when:** never. Regenerate and commit.

## `.context/` stays gitignored

**Decision:** workspace-local agent scratch only.

**Why:** durable knowledge belongs in tracked docs where humans will find it.

**Deviate when:** the information is durable — then it goes in `docs/`,
`README.md`, or here.

## Pruned from the 508 devkit

**Decision:** this repository started from the 508.dev devkit template. The
Ruby, Python (FastAPI/Alembic), and TypeScript (Drizzle) convention packs were
deleted rather than adapted, along with the template's own inventory,
selection, and design-history documents.

**Why:** FastAPI, Alembic, and Drizzle all conflict with Django owning the
schema, and a template's scaffolding is noise in a product repo. The
conventions worth keeping — supply-chain policy, worktree ports, host-apps
topology, `.context/`, GitHub hygiene — were kept and are recorded above.

**Deviate when:** never; the devkit still exists upstream if it is needed.
