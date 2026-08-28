"""Transactional email.

Links point at the SPA, not the API: the user lands on a page that collects the
new password and then calls the API. No provider is chosen yet, so local
development uses the console backend (docs/architecture.md §11).
"""

from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User
from .tokens import email_verification_token, password_reset_token


def _uid(user: User) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def send_email_verification(user: User) -> None:
    link = (
        f"{settings.PUBLIC_WEB_BASE_URL}/verify-email"
        f"?uid={_uid(user)}&token={email_verification_token.make_token(user)}"
    )
    send_mail(
        subject="Confirm your coffee-nut address",
        message=(
            "Welcome to coffee-nut.\n\n"
            f"Confirm your email address:\n{link}\n\n"
            "If you did not create this account, ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset(user: User) -> None:
    link = (
        f"{settings.PUBLIC_WEB_BASE_URL}/reset-password"
        f"?uid={_uid(user)}&token={password_reset_token.make_token(user)}"
    )
    send_mail(
        subject="Reset your coffee-nut password",
        message=(
            f"Reset your password:\n{link}\n\n"
            "The link expires shortly and can be used once. If you did not "
            "request this, ignore this message; your password is unchanged."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
