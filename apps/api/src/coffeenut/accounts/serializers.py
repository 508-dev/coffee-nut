from typing import Any

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import Profile, User
from .tokens import email_verification_token, password_reset_token


def _validate_password(password: str, user: User) -> None:
    """Run Django's validators and re-raise as a DRF field error."""
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)}) from exc


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["preferred_units", "timezone", "bio"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    email_verified = serializers.BooleanField(source="is_email_verified", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "email_verified", "date_joined", "profile"]
        # Email changes need re-verification, so they are their own flow rather
        # than a field on this endpoint.
        read_only_fields = ["id", "email", "email_verified", "date_joined"]

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        profile_data = validated_data.pop("profile", None)
        user = super().update(instance, validated_data)
        if profile_data:
            for field, value in profile_data.items():
                setattr(user.profile, field, value)
            user.profile.save()
        return user


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        # This does confirm an address is registered. Password reset below
        # deliberately does not, but hiding it here would mean silently
        # discarding a signup; the honest error is the better trade.
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Validators compare the password against user attributes, so they need
        # a populated (unsaved) instance to be effective.
        _validate_password(
            attrs["password"],
            User(email=attrs["email"], display_name=attrs.get("display_name", "")),
        )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        return User.objects.create_user(**validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        _validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class _UidTokenSerializer(serializers.Serializer):
    """Shared uid/token decoding for the emailed-link endpoints."""

    uid = serializers.CharField()
    token = serializers.CharField()
    token_generator: Any = None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(attrs["uid"])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
            # One message for a bad uid and a bad token alike: distinguishing
            # them would let someone probe which accounts exist.
            raise serializers.ValidationError("Invalid or expired link.") from exc

        if not self.token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired link.")

        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(_UidTokenSerializer):
    new_password = serializers.CharField(write_only=True)
    token_generator = password_reset_token

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        _validate_password(attrs["new_password"], attrs["user"])
        return attrs


class EmailVerifySerializer(_UidTokenSerializer):
    token_generator = email_verification_token


class AccessTokenSerializer(serializers.Serializer):
    """Response shape for the token endpoints.

    ``refresh`` is present only for native clients; browsers receive it as an
    HttpOnly cookie instead. Declared for the OpenAPI schema.
    """

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True, required=False)
