import django_filters
from django.db.models import Count, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from coffeenut.common.expand import ExpandableViewSetMixin
from coffeenut.common.views import OwnedModelViewSet

from .models import Bag, Coffee
from .serializers import BagSerializer, CoffeeSerializer


class CoffeeFilter(django_filters.FilterSet):
    varietal = django_filters.UUIDFilter(field_name="varietals", distinct=True)
    harvest_year_min = django_filters.NumberFilter(field_name="harvest_year", lookup_expr="gte")
    harvest_year_max = django_filters.NumberFilter(field_name="harvest_year", lookup_expr="lte")

    class Meta:
        model = Coffee
        fields = ["roaster", "country", "region", "producer", "process", "roast_level", "is_decaf"]


class CoffeeViewSet(ExpandableViewSetMixin, OwnedModelViewSet):
    # Reference joins are cheap and always wanted, so they are eager by default
    # rather than only when ?expand= asks. That keeps list views to one query
    # whether or not the client expands.
    queryset = Coffee.objects.select_related(
        "roaster", "country", "region", "producer", "process"
    ).prefetch_related("varietals")
    serializer_class = CoffeeSerializer
    filterset_class = CoffeeFilter
    search_fields = ["name", "notes"]
    ordering_fields = ["created_at", "name", "harvest_year"]


class BagFilter(django_filters.FilterSet):
    purchased_after = django_filters.DateFilter(field_name="purchase_date", lookup_expr="gte")
    purchased_before = django_filters.DateFilter(field_name="purchase_date", lookup_expr="lte")

    class Meta:
        model = Bag
        fields = ["coffee", "purchased_from", "is_finished"]


class BagViewSet(ExpandableViewSetMixin, OwnedModelViewSet):
    queryset = Bag.objects.select_related(
        "coffee", "coffee__roaster", "coffee__country", "purchased_from"
    )
    serializer_class = BagSerializer
    filterset_class = BagFilter
    search_fields = ["coffee__name", "notes"]
    ordering_fields = ["purchase_date", "roast_date", "created_at"]

    @extend_schema(
        responses={200: None},
        description="Brews recorded against this bag, newest first.",
    )
    @action(detail=True, methods=["get"])
    def brews(self, request: Request, pk: str | None = None) -> Response:
        """Convenience nesting of ``/brews/?bag=``.

        The brief's "show my friend how I brewed this bag" flow starts from a
        bag, so it gets a direct route rather than a filter the client has to
        know to build.
        """
        # Imported here: brewing imports coffee, so a module-level import would
        # be circular.
        from coffeenut.brewing.serializers import BrewSerializer

        bag = self.get_object()
        queryset: QuerySet = bag.brews.select_related("method", "grinder").prefetch_related(
            "tasting_notes"
        )

        page = self.paginate_queryset(queryset)
        serializer = BrewSerializer(
            page if page is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(responses={200: None}, description="Counts for the dashboard.")
    @action(detail=False, methods=["get"])
    def stats(self, request: Request) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        totals = queryset.aggregate(
            bags=Count("id", distinct=True), brews=Count("brews", distinct=True)
        )
        return Response(
            {
                "bags": totals["bags"],
                "open_bags": queryset.filter(is_finished=False).count(),
                "brews": totals["brews"],
            }
        )
