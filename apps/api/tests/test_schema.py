"""The OpenAPI schema is a shipped artefact.

Three clients are generated from it, so a schema that fails to build — or
silently loses an endpoint — is a real defect, not a docs nicety.
"""

import pytest
from drf_spectacular.generators import SchemaGenerator

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def test_schema_generates(schema):
    assert schema["info"]["title"] == "coffee-nut API"
    assert schema["openapi"].startswith("3.")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/register/",
        "/api/v1/auth/token/",
        "/api/v1/auth/token/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/me/",
        "/api/v1/auth/password/change/",
        "/api/v1/auth/password/reset/",
        "/api/v1/auth/password/reset/confirm/",
        "/api/v1/auth/email/verify/",
    ],
)
def test_auth_endpoints_are_documented(schema, path):
    assert path in schema["paths"], f"{path} is missing from the OpenAPI schema"


def test_no_response_schema_exposes_a_password(schema):
    """Password fields must be write-only.

    COMPONENT_SPLIT_REQUEST means request bodies are the `*Request` components,
    where a write-only password belongs. Everything else is a response shape,
    and a password appearing there would mean it is being serialised back out.
    """
    for name, component in schema["components"]["schemas"].items():
        if name.endswith("Request"):
            continue
        for field in component.get("properties", {}):
            assert "password" not in field.lower(), f"{name}.{field} appears in a response schema"
