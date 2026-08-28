"""Cursor pagination.

Offset paging double-serves or skips rows when the underlying list changes
between requests, which is exactly what happens on a brew list during active
logging. Cursor paging is stable under concurrent inserts.
"""

from rest_framework.pagination import CursorPagination, PageNumberPagination


class CoffeeNutCursorPagination(CursorPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = "-created_at"


class BrewedAtCursorPagination(CoffeeNutCursorPagination):
    """For brews, where the user's mental ordering is brew time, not row age."""

    ordering = "-brewed_at"


class ReferencePagination(PageNumberPagination):
    """Page numbers, not cursors, for reference lookups.

    Cursor pagination needs a stable ordering column, which would fight the
    relevance ranking typeahead applies. These lists are also small and read
    far more often than they change, so the drawbacks of offset paging do not
    bite here.
    """

    page_size = 50
    max_page_size = 200
    page_size_query_param = "page_size"
