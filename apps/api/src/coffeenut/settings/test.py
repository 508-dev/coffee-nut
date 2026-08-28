"""Test settings.

Tests run against real Postgres, never SQLite: the schema relies on CHECK
constraints and partial unique indexes that SQLite models differently.
"""

from typing import cast

from .base import *
from .base import DATABASES, INSTALLED_APPS, REST_FRAMEWORK, SIMPLE_JWT

DEBUG = False
# At least 32 bytes: HS256 warns below that (RFC 7518 §3.2).
SECRET_KEY = "test-only-key-not-used-outside-the-test-suite"

# SIMPLE_JWT is built in base.py from base's SECRET_KEY, so overriding
# SECRET_KEY above does not reach it. Keep them in step explicitly.
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}

# Concrete models for exercising the abstract bases in coffeenut.common.
# Has no migrations, so the test runner creates its tables via run_syncdb.
INSTALLED_APPS = [*INSTALLED_APPS, "tests.testapp"]

# Fast, deterministic hashing. Never use outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ATOMIC_REQUESTS interacts badly with pytest-django's transactional fixtures.
DATABASES = {**DATABASES}
DATABASES["default"] = {**DATABASES["default"], "ATOMIC_REQUESTS": False}

# Rates become None (unlimited) rather than being removed: ScopedRateThrottle
# raises ImproperlyConfigured for a declared scope with no entry, so dropping
# the keys would break every throttled view. Tests that assert throttling
# override this with a real rate.
# Derived rather than restated, so a scope added in base.py cannot be missed
# here and blow up at request time.
_throttle_scopes = cast(dict[str, str], REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": dict.fromkeys(_throttle_scopes)}
