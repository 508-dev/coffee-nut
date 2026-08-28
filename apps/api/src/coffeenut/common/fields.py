"""Relation fields that refuse to point at another user's data.

This is the layer that is easiest to forget and most costly to miss. Without
it, ``POST /brews/ {"bag": "<someone else's bag id>"}`` succeeds: the bag exists
and the serializer only checks existence. Routing every user-owned foreign key
through these fields makes that structurally impossible rather than a rule each
serializer has to remember.
"""

from typing import Any

from rest_framework import serializers


class _ScopedRelatedField(serializers.PrimaryKeyRelatedField):
    scope_method: str

    def get_queryset(self) -> Any:
        queryset = super().get_queryset()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return getattr(queryset, self.scope_method)(user)


class OwnedPrimaryKeyRelatedField(_ScopedRelatedField):
    """Accepts only rows the requesting user owns.

    A reference to another user's row fails as ``does_not_exist`` rather than
    ``permission_denied``, so the response cannot be used to probe whether an
    id exists.
    """

    scope_method = "owned_by"


class ReferencePrimaryKeyRelatedField(_ScopedRelatedField):
    """Accepts canonical rows plus the requesting user's own custom rows."""

    scope_method = "available_to"
