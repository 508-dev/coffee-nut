from contextlib import suppress
from typing import Any, cast

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .cookies import clear_refresh_cookie, deliver_tokens, read_refresh_token
from .emails import send_email_verification, send_password_reset
from .models import User
from .serializers import (
    AccessTokenSerializer,
    EmailVerifySerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _issue_tokens(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def _revoke_all_sessions(user: User) -> None:
    """Blacklist every outstanding refresh token for a user.

    Called on password change and reset: if a password was compromised, leaving
    old sessions alive defeats the point of changing it.
    """
    for outstanding in OutstandingToken.objects.filter(user=user):
        # The stubs type RefreshToken() as taking Token | None, but it accepts
        # the encoded string at runtime, which is what is stored.
        with suppress(TokenError):
            # Already expired or blacklisted means nothing left to revoke.
            RefreshToken(outstanding.token).blacklist()  # type: ignore[arg-type]


@extend_schema(
    request=RegisterSerializer,
    responses={201: AccessTokenSerializer},
    description=(
        "Create an account and sign in. Browsers receive the refresh token as "
        "an HttpOnly cookie; send `X-Client: native` to receive it in the body "
        "instead."
    ),
)
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        send_email_verification(user)

        response = Response(_issue_tokens(user), status=status.HTTP_201_CREATED)
        return deliver_tokens(request, response)


@extend_schema(description="Exchange credentials for an access token.")
class LoginView(TokenObtainPairView):
    throttle_scope = "auth"

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return deliver_tokens(request, super().post(request, *args, **kwargs))


@extend_schema(
    request=None,
    responses={200: AccessTokenSerializer},
    description=(
        "Rotate the refresh token. Reads it from the request body, falling back "
        "to the HttpOnly cookie."
    ),
)
class RefreshView(TokenRefreshView):
    throttle_scope = "auth"

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        token = read_refresh_token(request)
        if not token:
            raise InvalidToken("No refresh token in the request body or cookie.")

        serializer = self.get_serializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        return deliver_tokens(request, response)


@extend_schema(
    request=None,
    responses={204: OpenApiResponse(description="Signed out.")},
    description="Blacklist the presented refresh token and clear the cookie.",
)
class LogoutView(APIView):
    # Deliberately AllowAny: signing out must work even when the access token
    # has already expired, which is exactly when a user reaches for it.
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token = read_refresh_token(request)
        if token:
            # Already invalid means sign-out is a no-op, which is still success.
            with suppress(TokenError):
                RefreshToken(token).blacklist()  # type: ignore[arg-type]
        return clear_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))


@extend_schema(description="The signed-in user and their profile.")
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> User:
        # IsAuthenticated has already rejected AnonymousUser.
        return cast(User, self.request.user)


@extend_schema(
    request=PasswordChangeSerializer,
    responses={200: AccessTokenSerializer},
    description="Change the password and sign every other session out.",
)
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = cast(User, request.user)  # IsAuthenticated guarantees this
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        _revoke_all_sessions(user)

        # The caller just proved they hold the current password, so re-issue
        # rather than bouncing them to the login screen.
        response = Response(_issue_tokens(user), status=status.HTTP_200_OK)
        return deliver_tokens(request, response)


@extend_schema(
    request=PasswordResetSerializer,
    responses={204: OpenApiResponse(description="Email sent if the account exists.")},
    description=(
        "Request a reset link. Always returns 204, whether or not the address is registered."
    ),
)
class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email=serializer.validated_data["email"].strip().lower(), is_active=True
        ).first()
        if user is not None:
            send_password_reset(user)

        # Same response either way: a 404 here would turn this endpoint into an
        # account-existence oracle.
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={204: OpenApiResponse(description="Password changed.")},
    description="Complete a reset and sign every session out.",
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Whoever held the old password may still have live sessions.
        _revoke_all_sessions(user)

        return clear_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))


@extend_schema(
    request=EmailVerifySerializer,
    responses={204: OpenApiResponse(description="Address confirmed.")},
    description="Confirm an email address from the emailed link.",
)
class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["user"].mark_email_verified()
        return Response(status=status.HTTP_204_NO_CONTENT)
