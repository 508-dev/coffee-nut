from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

from coffeenut.accounts.models import User


@pytest.fixture
def make_user(db: Any) -> Callable[..., User]:
    def _make(email: str = "user@example.com", **extra: Any) -> User:
        return User.objects.create_user(email=email, password="correct-horse-battery", **extra)

    return _make


@pytest.fixture
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice@example.com", display_name="Alice")


@pytest.fixture
def bob(make_user: Callable[..., User]) -> User:
    return make_user("bob@example.com", display_name="Bob")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def as_user() -> Callable[[User], APIClient]:
    def _as(user: User) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _as
