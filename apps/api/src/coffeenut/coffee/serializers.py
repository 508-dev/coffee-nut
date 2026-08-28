from typing import Any

from rest_framework import serializers

from coffeenut.catalog.models import (
    Country,
    ProcessMethod,
    Producer,
    Region,
    Roaster,
    Varietal,
)
from coffeenut.catalog.serializers import (
    CountrySerializer,
    ProcessMethodSerializer,
    ProducerSerializer,
    RegionSerializer,
    RoasterSerializer,
    VarietalSerializer,
)
from coffeenut.common.expand import ExpandableSerializer
from coffeenut.common.fields import (
    OwnedPrimaryKeyRelatedField,
    ReferencePrimaryKeyRelatedField,
)

from .models import Bag, Coffee

OWNED_READ_ONLY = ["id", "owner", "share_token", "created_at", "updated_at"]


def _reference(model: Any) -> ReferencePrimaryKeyRelatedField:
    """Optional reference relation, scoped to canonical rows plus the caller's."""
    return ReferencePrimaryKeyRelatedField(
        queryset=model.objects.all(), required=False, allow_null=True
    )


class CoffeeSerializer(ExpandableSerializer):
    roaster = _reference(Roaster)
    country = _reference(Country)
    region = _reference(Region)
    producer = _reference(Producer)
    process = _reference(ProcessMethod)
    varietals = ReferencePrimaryKeyRelatedField(
        queryset=Varietal.objects.all(), many=True, required=False
    )

    expandable_fields = {
        "roaster": lambda: RoasterSerializer,
        "country": lambda: CountrySerializer,
        "region": lambda: RegionSerializer,
        "producer": lambda: ProducerSerializer,
        "process": lambda: ProcessMethodSerializer,
        "varietals": lambda: VarietalSerializer,
    }

    class Meta:
        model = Coffee
        fields = [
            "id",
            "name",
            "roaster",
            "country",
            "region",
            "producer",
            "process",
            "varietals",
            "harvest_year",
            "roast_level",
            "altitude_min_masl",
            "altitude_max_masl",
            "is_decaf",
            "notes",
            "visibility",
            "created_at",
            "updated_at",
        ]
        read_only_fields = OWNED_READ_ONLY

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        low = self._resolve("altitude_min_masl", attrs)
        high = self._resolve("altitude_max_masl", attrs)
        if low is not None and high is not None and high < low:
            raise serializers.ValidationError(
                {"altitude_max_masl": "Must be greater than or equal to altitude_min_masl."}
            )

        year = self._resolve("harvest_year", attrs)
        if year is not None and not 1900 <= year <= 2100:
            raise serializers.ValidationError({"harvest_year": "Must be between 1900 and 2100."})

        # Mirroring the CHECK constraints here turns an IntegrityError 500 into
        # a field error the form can render.
        return attrs

    def _resolve(self, field: str, attrs: dict[str, Any]) -> Any:
        """Value after this write, accounting for PATCH leaving fields absent."""
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)


class BagSerializer(ExpandableSerializer):
    coffee = OwnedPrimaryKeyRelatedField(queryset=Coffee.objects.all())
    purchased_from = _reference(Roaster)

    expandable_fields = {
        "coffee": lambda: CoffeeSerializer,
        "purchased_from": lambda: RoasterSerializer,
    }

    class Meta:
        model = Bag
        fields = [
            "id",
            "coffee",
            "purchased_from",
            "purchase_date",
            "roast_date",
            "opened_date",
            "finished_date",
            "weight_grams",
            "price_amount",
            "price_currency",
            "is_finished",
            "notes",
            "visibility",
            "created_at",
            "updated_at",
        ]
        read_only_fields = OWNED_READ_ONLY

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        roast = self._resolve("roast_date", attrs)
        purchase = self._resolve("purchase_date", attrs)
        if roast and purchase and roast > purchase:
            raise serializers.ValidationError(
                {"roast_date": "A bag cannot be roasted after it was purchased."}
            )

        currency = self._resolve("price_currency", attrs)
        amount = self._resolve("price_amount", attrs)
        if amount is not None and not currency:
            raise serializers.ValidationError(
                {"price_currency": "Required when a price is recorded."}
            )
        if currency and len(currency) != 3:
            raise serializers.ValidationError(
                {"price_currency": "Use a three-letter ISO 4217 code, such as AUD."}
            )
        return attrs

    def _resolve(self, field: str, attrs: dict[str, Any]) -> Any:
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        validated = super().to_internal_value(data)
        if isinstance(validated.get("price_currency"), str):
            validated["price_currency"] = validated["price_currency"].upper()
        return validated
