from typing import Any

from rest_framework import serializers

from coffeenut.catalog.models import BrewMethod, Grinder, TastingNote
from coffeenut.catalog.serializers import (
    BrewMethodSerializer,
    GrinderSerializer,
    TastingNoteSerializer,
)
from coffeenut.coffee.models import Bag
from coffeenut.coffee.serializers import BagSerializer
from coffeenut.common.expand import ExpandableSerializer
from coffeenut.common.fields import (
    OwnedPrimaryKeyRelatedField,
    ReferencePrimaryKeyRelatedField,
)

from .models import TASTE_MAX, TASTE_MIN, Brew

TASTE_AXES = ("acidity", "sweetness", "body", "bitterness", "aftertaste")

# Fields a BrewMethod.parameter_schema may name. Guards against a schema
# requiring something that is not a real column, which would make the endpoint
# permanently un-satisfiable.
SCHEMA_FIELDS = {
    "dose_grams",
    "water_grams",
    "water_temp_c",
    "grinder",
    "grind_setting",
    "grind_microns",
    "total_time_seconds",
    "bloom_time_seconds",
    "bloom_water_grams",
    "pressure_bar",
    "yield_grams",
}


class BrewSerializer(ExpandableSerializer):
    bag = OwnedPrimaryKeyRelatedField(queryset=Bag.objects.all())
    grinder = OwnedPrimaryKeyRelatedField(
        queryset=Grinder.objects.all(), required=False, allow_null=True
    )
    method = ReferencePrimaryKeyRelatedField(queryset=BrewMethod.objects.all())
    tasting_notes = ReferencePrimaryKeyRelatedField(
        queryset=TastingNote.objects.all(), many=True, required=False
    )
    ratio = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True, allow_null=True
    )

    expandable_fields = {
        "bag": lambda: BagSerializer,
        "method": lambda: BrewMethodSerializer,
        "grinder": lambda: GrinderSerializer,
        "tasting_notes": lambda: TastingNoteSerializer,
    }

    class Meta:
        model = Brew
        fields = [
            "id",
            "bag",
            "method",
            "brewed_at",
            "dose_grams",
            "water_grams",
            "water_temp_c",
            "ratio",
            "grinder",
            "grind_setting",
            "grind_microns",
            "total_time_seconds",
            "bloom_time_seconds",
            "bloom_water_grams",
            "pressure_bar",
            "yield_grams",
            "liked",
            "tasting_notes",
            "notes",
            *TASTE_AXES,
            "extras",
            "visibility",
            "share_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "share_token", "visibility", "created_at", "updated_at"]

    def _resolve(self, field: str, attrs: dict[str, Any]) -> Any:
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)

    def validate_extras(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be an object.")
        for key, item in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError("Keys must be strings.")
            if not isinstance(item, str | int | float | bool | type(None)):
                raise serializers.ValidationError(
                    f"{key!r} must be a string, number, boolean, or null."
                )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        errors: dict[str, Any] = {}

        for axis in TASTE_AXES:
            value = self._resolve(axis, attrs)
            if value is not None and not TASTE_MIN <= value <= TASTE_MAX:
                errors[axis] = f"Must be between {TASTE_MIN} and {TASTE_MAX}."

        for field in ("dose_grams", "water_grams", "yield_grams"):
            value = self._resolve(field, attrs)
            if value is not None and value <= 0:
                errors[field] = "Must be greater than 0."

        temp = self._resolve("water_temp_c", attrs)
        if temp is not None and not 0 <= temp <= 100:
            errors["water_temp_c"] = "Must be between 0 and 100 degrees Celsius."

        bloom = self._resolve("bloom_water_grams", attrs)
        water = self._resolve("water_grams", attrs)
        if bloom is not None and water is not None and bloom > water:
            errors["bloom_water_grams"] = "Cannot exceed the total water."

        errors.update(self._validate_against_method(attrs))

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _validate_against_method(self, attrs: dict[str, Any]) -> dict[str, str]:
        """Enforce the chosen method's declared required fields.

        This is what keeps the contract typed while the form stays method-aware:
        espresso demands a yield, pour over does not.
        """
        method = self._resolve("method", attrs)
        if method is None:
            return {}

        errors: dict[str, str] = {}
        for field in method.required_fields:
            if field not in SCHEMA_FIELDS:
                # A fixture naming a column that does not exist would otherwise
                # make this method impossible to satisfy. Ignore it loudly in
                # tests rather than rejecting every brew.
                continue
            value = self._resolve(field, attrs)
            if value in (None, ""):
                errors[field] = f"Required for {method.name} brews."
        return errors
