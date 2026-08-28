from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwner(BasePermission):
    """Backstop behind queryset scoping.

    If ``get_queryset`` is written correctly this never fires, because a row the
    caller cannot see is never fetched in the first place. That redundancy is
    the point: it converts a future scoping mistake from a data leak into a 403.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user
        if user is None or user.is_anonymous:
            return False
        return getattr(obj, "owner_id", None) == user.id


class IsOwnerOrCanonicalReadOnly(BasePermission):
    """Reference data: read anything visible, write only your own rows.

    Canonical rows (``owner IS NULL``) are curated by us and read-only to
    everyone, including staff going through the API.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        owner_id = getattr(obj, "owner_id", None)
        if owner_id is None:
            return False  # canonical
        user = request.user
        return user is not None and not user.is_anonymous and owner_id == user.id
