# Supply chain

Two rules: wait before adopting a new release, and install exactly what the
lockfile says.

## Cooldowns

A newly published package version is the risk window — compromised releases are
usually caught and yanked within days. Every manager here waits seven days.

| Manager | Setting | Where |
| --- | --- | --- |
| Bun | `minimumReleaseAge = 604800` | `bunfig.toml` |
| uv | `exclude-newer = "P7D"` | `pyproject.toml` |
| Renovate | `minimumReleaseAge: "7 days"` | `renovate.json` |

The uv setting has a prerequisite. Relative durations need uv ≥ 0.9.17, and
older clients fail during settings discovery with an opaque error. So
`required-version = ">=0.9.17"` sits next to it, and uv states the requirement
itself instead of leaving it to be discovered.

You will notice the cooldown in practice: a fresh `uv sync` may resolve a
slightly older patch release than the one on PyPI today. That is the mechanism
working.

## Locked installs

`uv.lock` and `bun.lock` are committed. CI installs with `uv sync --locked` and
`bun install --frozen-lockfile`, so a resolution that differs from the lockfile
fails the build rather than silently drifting.

## Pinned tooling

`ci.yml` pins `UV_VERSION` and `BUN_VERSION`. Without that, an upstream release
changes what the merge gate runs with no review — and can diverge from what
developers run locally without anyone noticing.

Keep them in step with `.python-version` and `package.json`'s `packageManager`.

## Pinned actions

Workflow steps reference actions by commit SHA, not tag, with the version in a
trailing comment. A tag can be moved; a SHA cannot.

## Deviating

A security fix that needs immediate adoption is a legitimate reason to bypass a
cooldown. Note the exception in the pull request so it is visible in review.
