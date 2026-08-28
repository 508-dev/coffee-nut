"""Read-only shapes for the anonymous share page.

These are an explicit allowlist, deliberately not the authenticated serializers
with fields excluded. Someone will add a field to a private serializer one day;
an allowlist means that field cannot leak into a public page by default. The
cost is remembering to add genuinely public fields here too, which is the safer
direction to fail in.

Excluded on purpose: price and where the bag was bought, the owner's email and
id, the owner's private notes on the bag and coffee, and every timestamp other
than the brew itself.
"""

from rest_framework import serializers

from coffeenut.brewing.models import Brew
from coffeenut.coffee.models import Bag, Coffee


class PublicCoffeeSerializer(serializers.ModelSerializer):
    roaster = serializers.CharField(source="roaster.name", read_only=True, default=None)
    country = serializers.CharField(source="country.name", read_only=True, default=None)
    region = serializers.CharField(source="region.name", read_only=True, default=None)
    producer = serializers.CharField(source="producer.name", read_only=True, default=None)
    process = serializers.CharField(source="process.name", read_only=True, default=None)
    varietals: serializers.SlugRelatedField = serializers.SlugRelatedField(
        slug_field="name", many=True, read_only=True
    )

    class Meta:
        model = Coffee
        fields = [
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
        ]


class PublicBagSerializer(serializers.ModelSerializer):
    coffee = PublicCoffeeSerializer(read_only=True)

    class Meta:
        model = Bag
        # No price, no purchased_from, no notes: what someone paid and where
        # they shop is not part of a brew recipe.
        fields = ["coffee", "roast_date"]


class PublicBrewSerializer(serializers.ModelSerializer):
    bag = PublicBagSerializer(read_only=True)
    method = serializers.CharField(source="method.name", read_only=True)
    grinder = serializers.CharField(source="grinder.name", read_only=True, default=None)
    tasting_notes: serializers.SlugRelatedField = serializers.SlugRelatedField(
        slug_field="name", many=True, read_only=True
    )
    # The person, not the account: a display name, never an email or id.
    shared_by = serializers.CharField(source="owner.display_name", read_only=True)
    ratio = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Brew
        fields = [
            "brewed_at",
            "method",
            "bag",
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
            "acidity",
            "sweetness",
            "body",
            "bitterness",
            "aftertaste",
            "shared_by",
        ]


class ShareLinkSerializer(serializers.Serializer):
    """Response for enabling a share link."""

    share_token = serializers.UUIDField(read_only=True)
    share_url = serializers.URLField(read_only=True)
