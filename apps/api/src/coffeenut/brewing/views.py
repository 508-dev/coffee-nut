import django_filters

from coffeenut.common.expand import ExpandableViewSetMixin
from coffeenut.common.pagination import BrewedAtCursorPagination
from coffeenut.common.views import OwnedModelViewSet

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
