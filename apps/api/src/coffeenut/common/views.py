from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from .filters import UpdatedSinceFilterBackend, rank_for_typeahead
from .models import OwnedQuerySet, ReferenceQuerySet
from .pagination import ReferencePagination
from .permissions import IsOwner, IsOwnerOrCanonicalReadOnly


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


class ReferenceModelViewSet(viewsets.ModelViewSet):
    """Base viewset for reference data.

    Lists canonical rows plus the caller's own; creates rows owned by the
    caller; refuses writes to canonical rows. ``?q=`` switches the list into
    typeahead mode.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrCanonicalReadOnly]
    pagination_class = ReferencePagination
    # No OrderingFilter: it would let a client override the relevance ranking
    # that ?q= applies, which is the whole point of the endpoint.
    filter_backends = [UpdatedSinceFilterBackend, DjangoFilterBackend]

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        if not isinstance(queryset, ReferenceQuerySet):
            raise ImproperlyConfigured(
                f"{type(self).__name__}.queryset must be a ReferenceQuerySet "
                f"(got {type(queryset).__name__})."
            )
        # Merged rows are superseded by a canonical equivalent; keep them
        # resolvable by id but out of lists and typeahead.
        queryset = queryset.available_to(self.request.user)
        if self.action == "list":
            queryset = queryset.unmerged()

        term = self.request.query_params.get("q", "").strip()
        if term and self.action == "list":
            return rank_for_typeahead(queryset, term)
        return queryset

    def perform_create(self, serializer: Any) -> None:
        # Anything a user adds is theirs and private. Promotion to canonical is
        # a curation step we perform, never a client action.
        serializer.save(owner=self.request.user)
