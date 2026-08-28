"""Shared filter backends."""

from django.db.models import QuerySet
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
