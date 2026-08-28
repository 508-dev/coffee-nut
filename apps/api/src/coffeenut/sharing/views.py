from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from coffeenut.brewing.models import Brew

from .serializers import PublicBrewSerializer


def share_url_for(token: Any) -> str:
    return f"{settings.PUBLIC_SHARE_BASE_URL.rstrip('/')}/{token}"


@extend_schema(
    description=(
        "A brew shared by unguessable link. No authentication. Returns 404 for "
        "an unknown, revoked, or private token."
    ),
    responses={200: PublicBrewSerializer},
)
class PublicBrewView(RetrieveAPIView):
    serializer_class = PublicBrewSerializer
    permission_classes = [AllowAny]
    # No authentication at all: a stale or malformed Authorization header from
    # a logged-in user's browser must not turn a public page into a 401.
    authentication_classes: list[Any] = []
    throttle_scope = "public_share"

    def get_object(self) -> Brew:
        brew = (
            Brew.objects.shared_by_token(self.kwargs["share_token"])
            .select_related(
                "owner",
                "method",
                "grinder",
                "bag",
                "bag__coffee",
                "bag__coffee__roaster",
                "bag__coffee__country",
                "bag__coffee__region",
                "bag__coffee__producer",
                "bag__coffee__process",
            )
            .prefetch_related("tasting_notes", "bag__coffee__varietals")
            .first()
        )
        if brew is None:
            # 404 rather than 403: a 403 would confirm that a token once
            # existed, which is exactly what a revoked link should not do.
            raise NotFound()
        return brew

    def finalize_response(self, request: Request, response: Response, *args: Any, **kwargs: Any):
        response = super().finalize_response(request, response, *args, **kwargs)
        # Unlisted means unlisted. An unguessable URL should not end up in a
        # search index because someone pasted it somewhere crawlable.
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
