"""Abstract bases shared by every domain app.

This module must not import from the domain apps. It is the bottom of the
dependency graph on purpose.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from coffeenut.accounts.models import User


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted (anyone with the link)"
    # Reserved. Not reachable from the v1 API, but present so that adding a
    # public feed later is a serializer change rather than a data migration.
    PUBLIC = "public", "Public"


class ReferenceSource(models.TextChoices):
    MANUAL = "manual", "User entered"
    SEED = "seed", "Curated seed data"


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class OwnedQuerySet(models.QuerySet):
    """The single sanctioned entry point to user-owned rows.

    Nothing outside this class should filter on ``owner``. When sharing between
    users arrives, ``visible_to`` grows a join and every endpoint in the
    codebase inherits it for free.
    """

    def visible_to(self, user: User | AnonymousUser | None) -> Self:
        if user is None or user.is_anonymous:
            return self.none()
        return self.filter(owner=user)

    def owned_by(self, user: User | AnonymousUser | None) -> Self:
        """Strictly the user's own rows.

        Identical to ``visible_to`` today. They diverge the moment another user
        can share a row with you: you may *see* it without *owning* it. Use this
        one for writes and ``visible_to`` for reads.
        """
        if user is None or user.is_anonymous:
            return self.none()
        return self.filter(owner=user)

    def shared_by_token(self, token: str | uuid.UUID | None) -> Self:
        """Rows reachable anonymously through a share link."""
        if not token:
            return self.none()
        try:
            token = uuid.UUID(str(token))
        except (ValueError, AttributeError, TypeError):
            return self.none()
        return self.filter(share_token=token, visibility=Visibility.UNLISTED)


class OwnedModel(TimestampedModel):
    """Base for every row that belongs to exactly one user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    # Nullable and unique. Postgres permits many NULLs under a unique index, so
    # unshared rows do not contend. Lives on the base so that making bags or
    # coffees shareable later needs no migration.
    share_token = models.UUIDField(
        null=True, blank=True, unique=True, db_index=True, editable=False
    )

    objects = OwnedQuerySet.as_manager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="%(class)s_own_created"),
        ]

    @property
    def is_shared(self) -> bool:
        return self.visibility == Visibility.UNLISTED and self.share_token is not None

    def enable_sharing(self, *, rotate: bool = False) -> uuid.UUID:
        """Publish by unguessable link. Rotating invalidates the previous URL."""
        if rotate or self.share_token is None:
            self.share_token = uuid.uuid4()
        self.visibility = Visibility.UNLISTED
        self.save(update_fields=["share_token", "visibility", "updated_at"])
        return self.share_token

    def disable_sharing(self) -> None:
        """Revoke immediately. Clearing the token means an old URL cannot be revived."""
        self.share_token = None
        self.visibility = Visibility.PRIVATE
        self.save(update_fields=["share_token", "visibility", "updated_at"])


class ReferenceQuerySet(models.QuerySet):
    def canonical(self) -> Self:
        return self.filter(owner__isnull=True)

    def available_to(self, user: User | AnonymousUser | None) -> Self:
        """Canonical rows, plus the caller's own custom rows."""
        if user is None or user.is_anonymous:
            return self.filter(owner__isnull=True)
        return self.filter(Q(owner__isnull=True) | Q(owner=user))

    def unmerged(self) -> Self:
        return self.filter(merged_into__isnull=True)


class ReferenceModel(TimestampedModel):
    """Base for lookup data that is either curated by us or added by one user.

    ``owner IS NULL`` means canonical. One table rather than two keeps foreign
    keys uniform: a Coffee points at a Roaster without caring which kind it is.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    # Populated when a row originates from an external provider. Unused in v1,
    # but present so that adding a provider later is not a migration across
    # every reference table.
    source = models.CharField(max_length=64, default=ReferenceSource.MANUAL)
    # Empty string rather than NULL, per Django convention: one representation
    # of "absent" avoids queries having to test for both.
    external_id = models.CharField(max_length=200, blank=True, default="")
    synced_at = models.DateTimeField(null=True, blank=True)
    # Promotion path: when many users type the same roaster, we create the
    # canonical row and point the custom ones at it without breaking their
    # existing foreign keys.
    merged_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merged_from",
    )

    objects = ReferenceQuerySet.as_manager()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(owner__isnull=True),
                name="%(class)s_canon_slug",
            ),
            models.UniqueConstraint(
                fields=["owner", "slug"],
                condition=Q(owner__isnull=False),
                name="%(class)s_owned_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    @property
    def is_canonical(self) -> bool:
        return self.owner_id is None
