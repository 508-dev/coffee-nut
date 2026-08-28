import django_filters
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from coffeenut.common.expand import ExpandableViewSetMixin
from coffeenut.common.pagination import BrewedAtCursorPagination
from coffeenut.common.views import OwnedModelViewSet
from coffeenut.sharing.serializers import ShareLinkSerializer
from coffeenut.sharing.views import share_url_for

from .models import Brew
from .serializers import BrewSerializer


class BrewFilter(django_filters.FilterSet):
    brewed_after = django_filters.IsoDateTimeFilter(field_name="brewed_at", lookup_expr="gte")
    brewed_before = django_filters.IsoDateTimeFilter(field_name="brewed_at", lookup_expr="lte")
    tasting_note = django_filters.UUIDFilter(field_name="tasting_notes", distinct=True)
    coffee = django_filters.UUIDFilter(field_name="bag__coffee")

    class Meta:
        model = Brew
        fields = ["bag", "method", "grinder", "liked"]


class BrewViewSet(ExpandableViewSetMixin, OwnedModelViewSet):
    queryset = Brew.objects.select_related(
        "bag", "bag__coffee", "bag__coffee__roaster", "method", "grinder"
    ).prefetch_related("tasting_notes")
    serializer_class = BrewSerializer
    filterset_class = BrewFilter
    # Brews are ordered by when they were brewed, not when the row was created:
    # the brief allows editing the timestamp afterwards.
    pagination_class = BrewedAtCursorPagination
    search_fields = ["notes", "grind_setting", "bag__coffee__name"]
    ordering_fields = ["brewed_at", "created_at"]

    @extend_schema(
        methods=["POST"],
        request=None,
        responses={200: ShareLinkSerializer},
        description=(
            'Publish this brew by unguessable link. Pass {"rotate": true} to '
            "issue a new token, which immediately breaks the previous URL."
        ),
    )
    @extend_schema(
        methods=["DELETE"],
        responses={204: OpenApiResponse(description="Link revoked.")},
        description="Revoke the link. The token is cleared, so it cannot be revived.",
    )
    @action(detail=True, methods=["post", "delete"])
    def share(self, request: Request, pk: str | None = None) -> Response:
        # get_object() runs the owner scoping, so another user's brew is a 404
        # here rather than something they could publish.
        brew = self.get_object()

        if request.method == "DELETE":
            brew.disable_sharing()
            return Response(status=status.HTTP_204_NO_CONTENT)

        rotate = bool(request.data.get("rotate", False)) if hasattr(request.data, "get") else False
        token = brew.enable_sharing(rotate=rotate)
        return Response({"share_token": str(token), "share_url": share_url_for(token)})
