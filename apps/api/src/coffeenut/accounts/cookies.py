"""Refresh-token delivery.

Two client shapes share one auth model (docs/architecture.md §6):

* **Browsers** must never hold a long-lived token where script can read it, so
  the refresh token goes into an ``HttpOnly`` cookie and never appears in a
  response body.
* **Native clients** have a real secure store, so they take the refresh token in
  the body and keep it in the platform keystore.

Cookie delivery is the default. A native client opts out explicitly with
``X-Client: native``; defaulting the other way would mean any client that forgot
the header silently got the less safe behaviour.
"""

from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response

NATIVE_CLIENT_HEADER = "X-Client"
NATIVE_CLIENT_VALUE = "native"


def wants_token_in_body(request: Request) -> bool:
    return request.headers.get(NATIVE_CLIENT_HEADER, "").strip().lower() == NATIVE_CLIENT_VALUE


def read_refresh_token(request: Request) -> str | None:
    """Body first, then cookie, so a native client is never ambiguous."""
    token = request.data.get("refresh") if hasattr(request.data, "get") else None
    return token or request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)


def deliver_tokens(request: Request, response: Response) -> Response:
    """Move ``refresh`` out of the body and into a cookie, unless native."""
    if not isinstance(response.data, dict) or "refresh" not in response.data:
        return response

    if wants_token_in_body(request):
        return response

    refresh = response.data.pop("refresh")
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh,
        httponly=True,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN,
        # Scoped to the auth endpoints: no other request needs to carry it.
        path=settings.JWT_REFRESH_COOKIE_PATH,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )
    return response


def clear_refresh_cookie(response: Response) -> Response:
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )
    return response
