"""User and profile behaviour."""

import pytest
from django.db import IntegrityError, transaction

from coffeenut.accounts.models import Profile, Units, User

pytestmark = pytest.mark.django_db


def test_email_is_the_username_field():
    assert User.USERNAME_FIELD == "email"
    assert "username" not in [f.name for f in User._meta.get_fields()]


def test_email_is_normalised_to_lowercase():
    user = User.objects.create_user(email="  Alice@Example.COM ", password="pw-pw-pw-pw")

    assert user.email == "alice@example.com"


def test_duplicate_email_is_rejected_case_insensitively():
    User.objects.create_user(email="alice@example.com", password="pw-pw-pw-pw")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="ALICE@example.com", password="pw-pw-pw-pw")


def test_creating_a_user_requires_an_email():
    with pytest.raises(ValueError, match="email"):
        User.objects.create_user(email="", password="pw-pw-pw-pw")


def test_password_is_hashed_not_stored():
    user = User.objects.create_user(email="a@example.com", password="correct-horse")

    assert user.password != "correct-horse"
    assert user.check_password("correct-horse")


def test_superuser_has_staff_and_superuser_flags():
    user = User.objects.create_superuser(email="root@example.com", password="pw-pw-pw-pw")

    assert user.is_staff and user.is_superuser


def test_superuser_rejects_contradictory_flags():
    with pytest.raises(ValueError, match="is_staff"):
        User.objects.create_superuser(
            email="root@example.com", password="pw-pw-pw-pw", is_staff=False
        )


def test_primary_key_is_a_uuid(alice):
    """Exposed in URLs and generatable offline by mobile clients."""
    import uuid

    assert isinstance(alice.pk, uuid.UUID)


def test_every_user_gets_a_profile(alice):
    assert Profile.objects.filter(user=alice).exists()
    assert alice.profile.preferred_units == Units.METRIC


def test_profile_is_created_for_superusers_too():
    """Covers createsuperuser, which bypasses the API entirely."""
    user = User.objects.create_superuser(email="root@example.com", password="pw-pw-pw-pw")

    assert Profile.objects.filter(user=user).exists()


def test_email_verification_starts_unset(alice):
    assert alice.is_email_verified is False

    alice.mark_email_verified()

    alice.refresh_from_db()
    assert alice.is_email_verified is True
