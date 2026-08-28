from typing import Any, cast

from django.utils.text import slugify
from rest_framework import serializers

from coffeenut.common.fields import ReferencePrimaryKeyRelatedField

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

# Shared by every reference serializer. `is_canonical` is what the client uses
# to decide whether an entry is editable, so it must always be present.
REFERENCE_FIELDS = ["id", "name", "slug", "is_canonical", "created_at", "updated_at"]
REFERENCE_READ_ONLY = ["id", "slug", "is_canonical", "created_at", "updated_at"]


class ReferenceSerializer(serializers.ModelSerializer):
    is_canonical = serializers.BooleanField(read_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Reject a name the caller has already used.

        The slug is derived in ``Model.save()``, so it never appears in the
        serializer's input and DRF's uniqueness validators cannot see it. Without
        this the partial unique index fires instead and the client gets a 500.

        Only the caller's own rows are considered: canonical and custom names
        live in separate namespaces, so "Onyx Coffee Lab" existing canonically
        must not stop a user creating their own.
        """
        name = attrs.get("name") or getattr(self.instance, "name", None)
        if not name:
            return attrs

        user = self.context["request"].user
        # Meta.model is typed as a bare model class; the manager is not on the stub.
        model = cast(Any, self.Meta.model)
        clashes = model.objects.filter(owner=user, slug=slugify(name)[:220])
        if self.instance is not None:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError({"name": "You already have an entry with this name."})
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("owner", None)
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("owner", None)
        return super().update(instance, validated_data)


class CountrySerializer(ReferenceSerializer):
    class Meta:
        model = Country
        fields = [*REFERENCE_FIELDS, "iso_alpha2", "iso_alpha3"]
        read_only_fields = REFERENCE_READ_ONLY


class RegionSerializer(ReferenceSerializer):
    country = ReferencePrimaryKeyRelatedField(queryset=Country.objects.all())

    class Meta:
        model = Region
        fields = [*REFERENCE_FIELDS, "country", "altitude_min_masl", "altitude_max_masl"]
        read_only_fields = REFERENCE_READ_ONLY


class ProducerSerializer(ReferenceSerializer):
    country = ReferencePrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    region = ReferencePrimaryKeyRelatedField(
        queryset=Region.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Producer
        fields = [
            *REFERENCE_FIELDS,
            "country",
            "region",
            "altitude_min_masl",
            "altitude_max_masl",
            "website",
        ]
        read_only_fields = REFERENCE_READ_ONLY


class RoasterSerializer(ReferenceSerializer):
    country = ReferencePrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Roaster
        fields = [*REFERENCE_FIELDS, "country", "city", "website"]
        read_only_fields = REFERENCE_READ_ONLY


class VarietalSerializer(ReferenceSerializer):
    # DRF's Field.parent is the containing serializer, so a declared field named
    # "parent" collides with it for the type checker. Harmless at runtime:
    # SerializerMetaclass moves declared fields into _declared_fields.
    parent = ReferencePrimaryKeyRelatedField(  # type: ignore[assignment]
        queryset=Varietal.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Varietal
        fields = [*REFERENCE_FIELDS, "parent"]
        read_only_fields = REFERENCE_READ_ONLY


class ProcessMethodSerializer(ReferenceSerializer):
    class Meta:
        model = ProcessMethod
        fields = [*REFERENCE_FIELDS, "category"]
        read_only_fields = REFERENCE_READ_ONLY


class BrewMethodSerializer(ReferenceSerializer):
    class Meta:
        model = BrewMethod
        fields = [*REFERENCE_FIELDS, "parameter_schema"]
        # The schema drives form rendering and server-side validation, so it is
        # ours to define even on a user's custom method.
        read_only_fields = [*REFERENCE_READ_ONLY, "parameter_schema"]


class TastingNoteSerializer(ReferenceSerializer):
    parent = ReferencePrimaryKeyRelatedField(  # type: ignore[assignment]  # see VarietalSerializer
        queryset=TastingNote.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = TastingNote
        fields = [*REFERENCE_FIELDS, "parent", "color"]
        read_only_fields = REFERENCE_READ_ONLY


class GrinderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grinder
        fields = [
            "id",
            "name",
            "burr_type",
            "setting_min",
            "setting_max",
            "step_size",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Mirror the database CHECK constraint so the client gets a field error
        # rather than a 500 from an IntegrityError.
        low = attrs.get("setting_min", getattr(self.instance, "setting_min", None))
        high = attrs.get("setting_max", getattr(self.instance, "setting_max", None))
        if low is not None and high is not None and high < low:
            raise serializers.ValidationError(
                {"setting_max": "Must be greater than or equal to setting_min."}
            )
        return attrs
