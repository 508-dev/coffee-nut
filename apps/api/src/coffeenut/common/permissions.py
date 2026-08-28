from typing import Any

from rest_framework.permissions import BasePermission
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
