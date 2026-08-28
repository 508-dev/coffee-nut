from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from coffeenut.common.views import OwnedModelViewSet, ReferenceModelViewSet

from . import serializers as s
from .models import (
    BrewMethod,
    Country,
    Grinder,
    ProcessMethod,
    Producer,
    Region,
    Roaster,
    TastingNote,
    Varietal,
)

TYPEAHEAD_PARAM = OpenApiParameter(
    name="q",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description=(
        "Typeahead search. Returns prefix matches first, then canonical "
        "entries, then alphabetically."
    ),
)


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class CountryViewSet(ReferenceModelViewSet):
    queryset = Country.objects.all()
    serializer_class = s.CountrySerializer
    # Countries are ISO data. Users pick from the list; they do not add to it.
    http_method_names = ["get", "head", "options"]


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class RegionViewSet(ReferenceModelViewSet):
    queryset = Region.objects.select_related("country")
    serializer_class = s.RegionSerializer
    filterset_fields = ["country"]


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class ProducerViewSet(ReferenceModelViewSet):
    queryset = Producer.objects.select_related("country", "region")
    serializer_class = s.ProducerSerializer
    filterset_fields = ["country", "region"]


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class RoasterViewSet(ReferenceModelViewSet):
    queryset = Roaster.objects.select_related("country")
    serializer_class = s.RoasterSerializer
    filterset_fields = ["country"]


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class VarietalViewSet(ReferenceModelViewSet):
    queryset = Varietal.objects.all()
    serializer_class = s.VarietalSerializer


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class ProcessMethodViewSet(ReferenceModelViewSet):
    queryset = ProcessMethod.objects.all()
    serializer_class = s.ProcessMethodSerializer
    filterset_fields = ["category"]


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class BrewMethodViewSet(ReferenceModelViewSet):
    queryset = BrewMethod.objects.all()
    serializer_class = s.BrewMethodSerializer


@extend_schema_view(list=extend_schema(parameters=[TYPEAHEAD_PARAM]))
class TastingNoteViewSet(ReferenceModelViewSet):
    queryset = TastingNote.objects.all()
    serializer_class = s.TastingNoteSerializer
    filterset_fields = ["parent"]


class GrinderViewSet(OwnedModelViewSet):
    """A user's own equipment. Fully private, no canonical variant."""

    queryset = Grinder.objects.all()
    serializer_class = s.GrinderSerializer
