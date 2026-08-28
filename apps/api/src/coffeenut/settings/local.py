"""Local development settings. Host-run Django against Compose infrastructure."""

from .base import *
from .base import REST_FRAMEWORK, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serving over plain HTTP locally, so a Secure cookie would never be stored.
JWT_REFRESH_COOKIE_SECURE = False

# The browsable API is a genuine convenience when hand-testing endpoints.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
