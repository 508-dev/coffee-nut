"""Signed, stateless tokens for email flows.

Both generators derive their hash from mutable user state, so a token stops
working once the thing it authorises has happened. No token table required.
"""

from typing import Any

from django.contrib.auth.tokens import PasswordResetTokenGenerator

from .models import User


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user: User, timestamp: int) -> str:
        # email_verified_at makes the token single-use: once verification lands,
        # the hash changes and the emailed link stops working. Including email
        # invalidates it if the address changes before the link is opened.
        return f"{user.pk}{timestamp}{user.email}{user.email_verified_at}"


email_verification_token = EmailVerificationTokenGenerator()

# Django's default reset generator already folds in the password hash and
# last_login, so a reset link dies as soon as it is used. Aliased here so both
# flows are found in one place.
password_reset_token: Any = PasswordResetTokenGenerator()
