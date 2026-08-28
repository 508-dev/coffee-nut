"""Canonical-plus-custom reference data."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction

from tests.testapp.models import ReferenceThing

pytestmark = pytest.mark.django_db


def test_available_to_returns_canonical_plus_own(alice, bob):
    canonical = ReferenceThing.objects.create(name="Ethiopia")
    mine = ReferenceThing.objects.create(name="My Local Cafe", owner=alice)
    ReferenceThing.objects.create(name="Their Cafe", owner=bob)

    available = set(ReferenceThing.objects.available_to(alice))

    assert available == {canonical, mine}


def test_available_to_anonymous_returns_canonical_only(alice):
    canonical = ReferenceThing.objects.create(name="Ethiopia")
    ReferenceThing.objects.create(name="Private", owner=alice)

    assert list(ReferenceThing.objects.available_to(AnonymousUser())) == [canonical]


def test_is_canonical_tracks_owner(alice):
    assert ReferenceThing.objects.create(name="Seeded").is_canonical is True
    assert ReferenceThing.objects.create(name="Custom", owner=alice).is_canonical is False


def test_slug_is_derived_from_name():
    assert ReferenceThing.objects.create(name="Onyx Coffee Lab").slug == "onyx-coffee-lab"


def test_canonical_slugs_are_unique():
    ReferenceThing.objects.create(name="Ethiopia")

    with pytest.raises(IntegrityError), transaction.atomic():
        ReferenceThing.objects.create(name="Ethiopia")


def test_two_users_may_reuse_the_same_slug(alice, bob):
    """A custom name must not be reserved globally by whoever typed it first."""
    ReferenceThing.objects.create(name="Corner Cafe", owner=alice)
    ReferenceThing.objects.create(name="Corner Cafe", owner=bob)

    assert ReferenceThing.objects.filter(slug="corner-cafe").count() == 2


def test_a_user_may_not_duplicate_their_own_slug(alice):
    ReferenceThing.objects.create(name="Corner Cafe", owner=alice)

    with pytest.raises(IntegrityError), transaction.atomic():
        ReferenceThing.objects.create(name="Corner Cafe", owner=alice)


def test_a_custom_row_may_reuse_a_canonical_slug(alice):
    """Canonical and custom namespaces are separate by design."""
    ReferenceThing.objects.create(name="Ethiopia")
    ReferenceThing.objects.create(name="Ethiopia", owner=alice)

    assert ReferenceThing.objects.filter(slug="ethiopia").count() == 2


def test_merging_preserves_the_custom_row(alice):
    """Promotion must not break foreign keys that already point at the custom row."""
    canonical = ReferenceThing.objects.create(name="Onyx Coffee Lab")
    custom = ReferenceThing.objects.create(name="Onyx Coffee Lab", owner=alice)

    custom.merged_into = canonical
    custom.save()

    assert list(ReferenceThing.objects.unmerged().filter(slug="onyx-coffee-lab")) == [canonical]
    custom.refresh_from_db()
    assert custom.pk is not None
