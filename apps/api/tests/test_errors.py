"""The error envelope native clients branch on."""

import pytest
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from coffeenut.common.errors import exception_handler


def _handle(exc):
    response = exception_handler(exc, {})
    assert response is not None
    return response.data


def test_validation_errors_are_flattened_per_field():
    data = _handle(ValidationError({"dose_grams": ["Must be greater than 0."]}))

    assert data["type"] == "validation_error"
    assert data["errors"] == [
        {"field": "dose_grams", "code": "invalid", "message": "Must be greater than 0."}
    ]


def test_nested_serializer_errors_keep_a_field_path():
    data = _handle(ValidationError({"bag": {"coffee": ["This field is required."]}}))

    assert data["errors"][0]["field"] == "bag.coffee"


def test_non_field_errors_have_no_field():
    data = _handle(ValidationError({"non_field_errors": ["Dose must not exceed water."]}))

    assert data["errors"][0]["field"] is None


def test_multiple_fields_each_produce_an_entry():
    data = _handle(ValidationError({"dose_grams": ["Required."], "water_grams": ["Required."]}))

    assert {e["field"] for e in data["errors"]} == {"dose_grams", "water_grams"}


@pytest.mark.parametrize(
    ("exc", "expected_type"),
    [(NotFound(), "not_found"), (PermissionDenied(), "permission_denied")],
)
def test_api_exceptions_expose_their_code(exc, expected_type):
    data = _handle(exc)

    assert data["type"] == expected_type
    assert data["errors"][0]["code"] == expected_type


def test_envelope_shape_is_stable():
    data = _handle(NotFound())

    assert set(data) == {"type", "detail", "errors"}
    assert set(data["errors"][0]) == {"field", "code", "message"}


def test_unhandled_exceptions_are_not_swallowed():
    """A programming error must become a 500, not a tidy client error."""
    assert exception_handler(RuntimeError("boom"), {}) is None
