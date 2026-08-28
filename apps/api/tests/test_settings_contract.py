"""Settings that only bite outside the test suite.

Test settings deliberately swap the cache and email backends for fast local
ones, which means a missing production dependency passes every other test and
then 500s on the first real request. These assertions cover that gap.
"""

import importlib
from typing import cast

from django.conf import settings
from django.utils.module_loading import import_string


def test_configured_cache_backend_is_importable():
    """base.py configures Django's RedisCache, which needs redis-py.

    Django ships the backend but not a client, so a missing dependency only
    surfaces when something touches the cache — such as any throttled endpoint.
    """
    from coffeenut.settings import base

    backend = cast(str, base.CACHES["default"]["BACKEND"])
    import_string(backend)

    if "redis" in backend:
        importlib.import_module("redis")


def test_every_throttle_scope_has_an_entry():
    """ScopedRateThrottle raises ImproperlyConfigured for an unlisted scope."""
    from coffeenut.settings import base

    # REST_FRAMEWORK is a dict[str, object] as far as the checker knows.
    rates = cast(dict[str, str], base.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
    for scope in ("auth", "register", "password_reset", "public_share"):
        assert scope in rates, f"throttle scope {scope!r} has no configured rate"


def test_signing_key_is_never_empty():
    """`JWT_SIGNING_KEY=` in .env is present-but-blank, which would otherwise
    hand PyJWT an empty HMAC key."""
    assert settings.SIMPLE_JWT["SIGNING_KEY"]
    assert len(settings.SIMPLE_JWT["SIGNING_KEY"]) >= 32, "HS256 wants >= 32 bytes"


def test_refresh_cookie_is_scoped_to_the_auth_endpoints():
    assert settings.JWT_REFRESH_COOKIE_PATH == "/api/v1/auth/"


def test_tests_run_against_postgres():
    """The schema uses CHECK constraints and partial unique indexes that SQLite
    models differently, so a SQLite fallback would pass tests production fails."""
    assert "postgresql" in settings.DATABASES["default"]["ENGINE"]
