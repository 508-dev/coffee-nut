"""Test settings.

Tests run against real Postgres, never SQLite: the schema relies on CHECK
constraints and partial unique indexes that SQLite models differently.
"""

from .base import *
from .base import DATABASES, INSTALLED_APPS, REST_FRAMEWORK

DEBUG = False
SECRET_KEY = "test-only-key"

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

# Throttling is asserted explicitly where it matters; leaving it on globally
# makes unrelated tests flaky once they exceed a rate inside one test run.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {}}
