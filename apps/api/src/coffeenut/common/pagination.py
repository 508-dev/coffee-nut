"""Cursor pagination.

Offset paging double-serves or skips rows when the underlying list changes
between requests, which is exactly what happens on a brew list during active
logging. Cursor paging is stable under concurrent inserts.
"""

from rest_framework.pagination import CursorPagination


class CoffeeNutCursorPagination(CursorPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = "-created_at"


class BrewedAtCursorPagination(CoffeeNutCursorPagination):
    """For brews, where the user's mental ordering is brew time, not row age."""

    ordering = "-brewed_at"
