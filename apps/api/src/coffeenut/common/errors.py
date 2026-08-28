"""Uniform error envelope.

Native clients need to branch on a machine-readable code rather than parse
English, and DRF's default shape varies by exception type. Everything is
flattened to::

    {"type": ..., "detail": ..., "errors": [{"field", "code", "message"}]}
"""

from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

NON_FIELD = "non_field_errors"


def _flatten(detail: Any, prefix: str = "") -> list[dict[str, Any]]:
    """Walk DRF's nested error structures into a flat list.

    Nested serializers produce dicts of lists of dicts, so the field path is
    built up as ``bag.coffee.roaster`` to stay useful to a form.
    """
    if isinstance(detail, dict):
        errors: list[dict[str, Any]] = []
        for key, value in detail.items():
            field = str(key)
            path = field if not prefix else f"{prefix}.{field}"
            errors.extend(_flatten(value, "" if field == NON_FIELD else path))
        return errors

    if isinstance(detail, list):
        errors = []
        for item in detail:
            errors.extend(_flatten(item, prefix))
        return errors

    return [
        {
            "field": prefix or None,
            "code": str(getattr(detail, "code", "error")),
            "message": str(detail),
        }
    ]


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled exception. Let Django's handler produce a 500 rather than
        # dressing up an internal error as a structured client error.
        return None

    errors = _flatten(response.data)

    if isinstance(exc, ValidationError):
        error_type = "validation_error"
        summary = "Invalid input."
    else:
        error_type = str(getattr(exc, "default_code", "error"))
        detail = getattr(exc, "detail", None)
        summary = str(detail) if isinstance(detail, str) else "Request failed."

    response.data = {"type": error_type, "detail": summary, "errors": errors}
    return response
