from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from .filters import UpdatedSinceFilterBackend
from .models import OwnedQuerySet
from .permissions import IsOwner


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Base viewset for user-owned resources.

    Subclasses set ``queryset`` and ``serializer_class`` and inherit tenancy.
    They must not override ``get_queryset`` without calling ``super()`` — the
    sweep in ``tests/test_tenancy.py`` walks the router and will fail if they do.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    # Read from settings rather than restating DRF's defaults, so changing
    # DEFAULT_FILTER_BACKENDS does not silently skip this base class. The stubs
    # declare it Sequence[str]; DRF resolves the import strings to classes.
    filter_backends = [
        UpdatedSinceFilterBackend,
        *api_settings.DEFAULT_FILTER_BACKENDS,  # type: ignore[list-item]
    ]

    def get_queryset(self) -> QuerySet:
        # Scoping happens here rather than in a permission class, so an
        # unauthorised row is absent rather than forbidden: callers get 404,
        # which does not confirm the id exists.
        queryset = super().get_queryset()
        if not isinstance(queryset, OwnedQuerySet):
            # Loud failure beats a silent tenancy hole. Without an OwnedQuerySet
            # there is no visible_to(), so a plain .objects.all() here would
            # serve every user's rows to everyone.
            raise ImproperlyConfigured(
                f"{type(self).__name__}.queryset must be an OwnedQuerySet "
                f"(got {type(queryset).__name__}). Models inheriting OwnedModel "
                f"get one automatically; a custom manager must subclass it."
            )
        return queryset.visible_to(self.request.user)

    def perform_create(self, serializer: Any) -> None:
        serializer.save(owner=self.request.user)
