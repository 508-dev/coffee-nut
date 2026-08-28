"""Shared filter backends."""

from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import APIView


class UpdatedSinceFilterBackend(BaseFilterBackend):
    """``?updated_since=<iso8601>`` on every list endpoint.

    Paired with the index on ``updated_at``, this is the minimum a client needs
    to sync incrementally instead of refetching everything. It is here from the
    start because adding it later means backfilling indexes on a live table.
    """

    def filter_queryset(self, request: Request, queryset: QuerySet, view: APIView) -> QuerySet:
        raw = request.query_params.get("updated_since")
        if not raw:
            return queryset

        parsed = parse_datetime(raw)
        if parsed is None:
            raise ValidationError(
                {"updated_since": "Must be an ISO 8601 datetime, e.g. 2026-08-27T12:00:00Z."}
            )
        return queryset.filter(updated_at__gte=parsed)


def rank_for_typeahead(queryset: QuerySet, term: str) -> QuerySet:
    """Order a reference queryset by how well each row answers ``term``.

    Prefix matches first, because someone typing "eth" means Ethiopia rather
    than "Southern Ethiopia". Canonical rows break the tie, so curated data
    surfaces above a user's own near-duplicate. Name last, for stability.
    """
    return (
        queryset.filter(name__icontains=term)
        .annotate(
            _prefix_rank=Case(
                When(name__istartswith=term, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            _canonical_rank=Case(
                When(owner__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("_prefix_rank", "_canonical_rank", "name")
    )
