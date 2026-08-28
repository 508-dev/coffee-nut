"""The ownership chokepoint.

Everything in the product relies on ``visible_to`` being right, so it is tested
directly rather than only through the endpoints that happen to use it.
"""

import uuid

import pytest
from django.contrib.auth.models import AnonymousUser

from coffeenut.common.models import Visibility
from tests.testapp.models import OwnedThing

pytestmark = pytest.mark.django_db


def test_visible_to_returns_only_own_rows(alice, bob):
    mine = OwnedThing.objects.create(owner=alice, label="mine")
    OwnedThing.objects.create(owner=bob, label="theirs")

    assert list(OwnedThing.objects.visible_to(alice)) == [mine]


def test_visible_to_anonymous_returns_nothing(alice):
    OwnedThing.objects.create(owner=alice)

    assert OwnedThing.objects.visible_to(AnonymousUser()).count() == 0
    assert OwnedThing.objects.visible_to(None).count() == 0


def test_new_rows_are_private_and_unshared(alice):
    thing = OwnedThing.objects.create(owner=alice)

    assert thing.visibility == Visibility.PRIVATE
    assert thing.share_token is None
    assert thing.is_shared is False


def test_enable_sharing_issues_a_token(alice):
    thing = OwnedThing.objects.create(owner=alice)

    token = thing.enable_sharing()

    thing.refresh_from_db()
    assert thing.visibility == Visibility.UNLISTED
    assert thing.share_token == token
    assert thing.is_shared is True


def test_enable_sharing_is_idempotent_without_rotate(alice):
    thing = OwnedThing.objects.create(owner=alice)

    first = thing.enable_sharing()
    second = thing.enable_sharing()

    assert first == second, "re-sharing must not silently break existing links"


def test_rotating_invalidates_the_previous_link(alice):
    thing = OwnedThing.objects.create(owner=alice)
    original = thing.enable_sharing()

    rotated = thing.enable_sharing(rotate=True)

    assert rotated != original
    assert OwnedThing.objects.shared_by_token(original).count() == 0
    assert OwnedThing.objects.shared_by_token(rotated).count() == 1


def test_disable_sharing_revokes_immediately(alice):
    thing = OwnedThing.objects.create(owner=alice)
    token = thing.enable_sharing()

    thing.disable_sharing()

    assert OwnedThing.objects.shared_by_token(token).count() == 0
    thing.refresh_from_db()
    assert thing.visibility == Visibility.PRIVATE
    assert thing.share_token is None


def test_shared_by_token_ignores_private_rows(alice):
    """A token alone is not enough; visibility must agree."""
    thing = OwnedThing.objects.create(owner=alice, share_token=uuid.uuid4())

    assert OwnedThing.objects.shared_by_token(thing.share_token).count() == 0


@pytest.mark.parametrize("token", ["", None, "not-a-uuid", "12345"])
def test_shared_by_token_rejects_junk(token):
    """Malformed tokens must return empty, not raise a 500."""
    assert OwnedThing.objects.shared_by_token(token).count() == 0


def test_many_unshared_rows_coexist(alice):
    """share_token is unique, but NULLs must not contend under that index."""
    OwnedThing.objects.create(owner=alice)
    OwnedThing.objects.create(owner=alice)

    assert OwnedThing.objects.filter(share_token__isnull=True).count() == 2
