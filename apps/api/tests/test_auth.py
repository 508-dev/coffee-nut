"""Authentication endpoints.

Covers the two token-delivery modes, session revocation, and the
non-enumeration promises, since those are the parts that fail quietly.
"""

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from coffeenut.accounts.models import User
from coffeenut.accounts.tokens import email_verification_token, password_reset_token

pytestmark = pytest.mark.django_db

COOKIE = settings.JWT_REFRESH_COOKIE_NAME
GOOD_PASSWORD = "quiet-kettle-9-brews"
NATIVE = {"HTTP_X_CLIENT": "native"}


def register_payload(**overrides):
    return {"email": "new@example.com", "password": GOOD_PASSWORD, **overrides}


class TestRegistration:
    def test_creates_an_account_and_signs_in(self, api_client):
        response = api_client.post(reverse("accounts:register"), register_payload())

        assert response.status_code == 201
        assert "access" in response.data
        assert User.objects.filter(email="new@example.com").exists()

    def test_sends_a_verification_email(self, api_client):
        api_client.post(reverse("accounts:register"), register_payload())

        assert len(mail.outbox) == 1
        assert "new@example.com" in mail.outbox[0].to

    def test_new_accounts_start_unverified(self, api_client):
        api_client.post(reverse("accounts:register"), register_payload())

        assert User.objects.get(email="new@example.com").is_email_verified is False

    def test_browsers_get_the_refresh_token_only_as_a_cookie(self, api_client):
        response = api_client.post(reverse("accounts:register"), register_payload())

        assert "refresh" not in response.data, "refresh must not be readable by script"
        assert response.cookies[COOKIE]["httponly"] is True

    def test_native_clients_get_the_refresh_token_in_the_body(self, api_client):
        response = api_client.post(reverse("accounts:register"), register_payload(), **NATIVE)

        assert "refresh" in response.data
        assert COOKIE not in response.cookies

    def test_email_is_normalised(self, api_client):
        api_client.post(reverse("accounts:register"), register_payload(email="New@Example.COM "))

        assert User.objects.filter(email="new@example.com").exists()

    def test_weak_passwords_are_rejected(self, api_client):
        response = api_client.post(reverse("accounts:register"), register_payload(password="pass"))

        assert response.status_code == 400
        assert any(e["field"] == "password" for e in response.data["errors"])

    def test_password_similar_to_email_is_rejected(self, api_client):
        response = api_client.post(
            reverse("accounts:register"),
            register_payload(email="brewmaster@example.com", password="brewmaster"),
        )

        assert response.status_code == 400

    def test_duplicate_email_is_rejected(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:register"), register_payload(email=alice.email)
        )

        assert response.status_code == 400
        assert User.objects.filter(email=alice.email).count() == 1


class TestLogin:
    def test_valid_credentials_return_an_access_token(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:token"),
            {"email": alice.email, "password": "correct-horse-battery"},
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" not in response.data

    def test_wrong_password_is_rejected(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:token"), {"email": alice.email, "password": "wrong"}
        )

        assert response.status_code == 401

    def test_unknown_account_is_rejected(self, api_client):
        response = api_client.post(
            reverse("accounts:token"), {"email": "nobody@example.com", "password": "whatever"}
        )

        assert response.status_code == 401


class TestRefresh:
    def test_refreshes_from_the_cookie_with_no_body(self, api_client, alice):
        api_client.post(
            reverse("accounts:token"),
            {"email": alice.email, "password": "correct-horse-battery"},
        )

        response = api_client.post(reverse("accounts:token-refresh"))

        assert response.status_code == 200
        assert "access" in response.data

    def test_refreshes_from_the_body_for_native_clients(self, api_client, alice):
        token = str(RefreshToken.for_user(alice))

        response = api_client.post(reverse("accounts:token-refresh"), {"refresh": token}, **NATIVE)

        assert response.status_code == 200
        assert "refresh" in response.data

    def test_missing_token_is_rejected(self, api_client):
        assert api_client.post(reverse("accounts:token-refresh")).status_code == 401

    def test_rotated_tokens_cannot_be_reused(self, api_client, alice):
        token = str(RefreshToken.for_user(alice))
        api_client.post(reverse("accounts:token-refresh"), {"refresh": token}, **NATIVE)

        replay = api_client.post(reverse("accounts:token-refresh"), {"refresh": token}, **NATIVE)

        assert replay.status_code == 401, "a rotated refresh token must be blacklisted"


class TestLogout:
    def test_blacklists_the_token_and_clears_the_cookie(self, api_client, alice):
        token = str(RefreshToken.for_user(alice))

        response = api_client.post(reverse("accounts:logout"), {"refresh": token}, **NATIVE)

        assert response.status_code == 204
        assert response.cookies[COOKIE].value == ""
        replay = api_client.post(reverse("accounts:token-refresh"), {"refresh": token}, **NATIVE)
        assert replay.status_code == 401

    def test_works_without_a_valid_access_token(self, api_client):
        """Signing out is most needed exactly when the access token has expired."""
        assert api_client.post(reverse("accounts:logout")).status_code == 204

    def test_is_idempotent(self, api_client, alice):
        token = str(RefreshToken.for_user(alice))
        api_client.post(reverse("accounts:logout"), {"refresh": token}, **NATIVE)

        assert (
            api_client.post(reverse("accounts:logout"), {"refresh": token}, **NATIVE).status_code
            == 204
        )


class TestMe:
    def test_returns_the_signed_in_user(self, as_user, alice):
        response = as_user(alice).get(reverse("accounts:me"))

        assert response.status_code == 200
        assert response.data["email"] == alice.email
        assert response.data["profile"]["preferred_units"] == "metric"

    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("accounts:me")).status_code == 401

    def test_updates_display_name_and_profile(self, as_user, alice):
        response = as_user(alice).patch(
            reverse("accounts:me"),
            {"display_name": "Al", "profile": {"preferred_units": "imperial"}},
        )

        assert response.status_code == 200
        alice.refresh_from_db()
        assert alice.display_name == "Al"
        assert alice.profile.preferred_units == "imperial"

    def test_email_is_read_only(self, as_user, alice):
        as_user(alice).patch(reverse("accounts:me"), {"email": "hijack@example.com"})

        alice.refresh_from_db()
        assert alice.email == "alice@example.com"


class TestPasswordChange:
    def test_changes_the_password(self, as_user, alice):
        response = as_user(alice).post(
            reverse("accounts:password-change"),
            {"current_password": "correct-horse-battery", "new_password": GOOD_PASSWORD},
        )

        assert response.status_code == 200
        alice.refresh_from_db()
        assert alice.check_password(GOOD_PASSWORD)

    def test_wrong_current_password_is_rejected(self, as_user, alice):
        response = as_user(alice).post(
            reverse("accounts:password-change"),
            {"current_password": "nope", "new_password": GOOD_PASSWORD},
        )

        assert response.status_code == 400
        alice.refresh_from_db()
        assert alice.check_password("correct-horse-battery")

    def test_other_sessions_are_revoked(self, api_client, as_user, alice):
        """A compromised password means live sessions must not survive."""
        stolen = str(RefreshToken.for_user(alice))

        as_user(alice).post(
            reverse("accounts:password-change"),
            {"current_password": "correct-horse-battery", "new_password": GOOD_PASSWORD},
        )

        replay = api_client.post(reverse("accounts:token-refresh"), {"refresh": stolen}, **NATIVE)
        assert replay.status_code == 401


class TestPasswordReset:
    def test_sends_a_reset_email(self, api_client, alice):
        response = api_client.post(reverse("accounts:password-reset"), {"email": alice.email})

        assert response.status_code == 204
        assert len(mail.outbox) == 1

    def test_unknown_address_looks_identical(self, api_client):
        """No account-existence oracle: same status, and no email sent."""
        response = api_client.post(
            reverse("accounts:password-reset"), {"email": "nobody@example.com"}
        )

        assert response.status_code == 204
        assert len(mail.outbox) == 0

    def test_confirm_sets_the_new_password(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:password-reset-confirm"),
            {
                "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
                "token": password_reset_token.make_token(alice),
                "new_password": GOOD_PASSWORD,
            },
        )

        assert response.status_code == 204
        alice.refresh_from_db()
        assert alice.check_password(GOOD_PASSWORD)

    def test_reset_token_cannot_be_reused(self, api_client, alice):
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
            "token": password_reset_token.make_token(alice),
            "new_password": GOOD_PASSWORD,
        }
        api_client.post(reverse("accounts:password-reset-confirm"), payload)

        second = api_client.post(reverse("accounts:password-reset-confirm"), payload)

        assert second.status_code == 400

    def test_bad_token_is_rejected(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:password-reset-confirm"),
            {
                "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
                "token": "not-a-real-token",
                "new_password": GOOD_PASSWORD,
            },
        )

        assert response.status_code == 400

    def test_bad_uid_gives_the_same_error_as_a_bad_token(self, api_client):
        response = api_client.post(
            reverse("accounts:password-reset-confirm"),
            {"uid": "garbage", "token": "garbage", "new_password": GOOD_PASSWORD},
        )

        assert response.status_code == 400
        assert response.data["errors"][0]["message"] == "Invalid or expired link."


class TestEmailVerification:
    def test_confirms_the_address(self, api_client, alice):
        response = api_client.post(
            reverse("accounts:email-verify"),
            {
                "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
                "token": email_verification_token.make_token(alice),
            },
        )

        assert response.status_code == 204
        alice.refresh_from_db()
        assert alice.is_email_verified is True

    def test_link_is_single_use(self, api_client, alice):
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
            "token": email_verification_token.make_token(alice),
        }
        api_client.post(reverse("accounts:email-verify"), payload)

        second = api_client.post(reverse("accounts:email-verify"), payload)

        assert second.status_code == 400, "verifying stamps the user, invalidating the token"

    def test_a_reset_token_cannot_verify_an_address(self, api_client, alice):
        """The two generators must not be interchangeable."""
        response = api_client.post(
            reverse("accounts:email-verify"),
            {
                "uid": urlsafe_base64_encode(force_bytes(alice.pk)),
                "token": password_reset_token.make_token(alice),
            },
        )

        assert response.status_code == 400


class TestThrottling:
    """The rates are disabled globally in test settings, so assert them here."""

    @pytest.fixture(autouse=True)
    def _clear_throttle_history(self):
        # Throttle counters live in the cache and would otherwise leak between
        # tests, making failures depend on execution order.
        cache.clear()
        yield
        cache.clear()

    def _with_rate(self, monkeypatch, scope, rate):
        # SimpleRateThrottle binds THROTTLE_RATES to api_settings at class
        # definition time, so override_settings cannot reach it. Patch the dict.
        monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, scope, rate)

    def test_login_attempts_are_rate_limited(self, api_client, alice, monkeypatch):
        """Brute-forcing a password must hit a wall."""
        self._with_rate(monkeypatch, "auth", "3/min")
        url = reverse("accounts:token")

        statuses = [
            api_client.post(url, {"email": alice.email, "password": "wrong"}).status_code
            for _ in range(5)
        ]

        assert 429 in statuses

    def test_registration_is_rate_limited(self, api_client, monkeypatch):
        self._with_rate(monkeypatch, "register", "2/hour")
        url = reverse("accounts:register")

        statuses = [
            api_client.post(url, register_payload(email=f"user{i}@example.com")).status_code
            for i in range(4)
        ]

        assert 429 in statuses

    def test_password_reset_is_rate_limited(self, api_client, alice, monkeypatch):
        """Otherwise this endpoint is a free mail cannon aimed at any address."""
        self._with_rate(monkeypatch, "password_reset", "2/hour")
        url = reverse("accounts:password-reset")

        statuses = [api_client.post(url, {"email": alice.email}).status_code for _ in range(4)]

        assert 429 in statuses
