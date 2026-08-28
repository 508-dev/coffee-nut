"""Reference data.

Every model here except :class:`Grinder` is a :class:`ReferenceModel`: one table
holding both our curated rows (``owner IS NULL``) and each user's private
additions. That keeps foreign keys uniform — a ``Coffee`` points at a
``Roaster`` without caring which kind it is — and makes promoting a popular
custom entry to canonical a data change rather than a migration.
"""

from django.db import models

from coffeenut.common.models import OwnedModel, ReferenceModel


class Country(ReferenceModel):
    """ISO 3166-1. Canonical only; users do not invent countries."""

    iso_alpha2 = models.CharField(max_length=2, unique=True)
    iso_alpha3 = models.CharField(max_length=3, unique=True)

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name_plural = "countries"
        ordering = ["name"]


class Region(ReferenceModel):
    """A growing region: Yirgacheffe, Huila, Antigua."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regions")
    altitude_min_masl = models.PositiveIntegerField(null=True, blank=True)
    altitude_max_masl = models.PositiveIntegerField(null=True, blank=True)

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]
        constraints = [
            *ReferenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(altitude_max_masl__gte=models.F("altitude_min_masl"))
                | models.Q(altitude_min_masl__isnull=True)
                | models.Q(altitude_max_masl__isnull=True),
                name="region_altitude_range",
            ),
        ]


class Producer(ReferenceModel):
    """A farm, estate, co-operative, or washing station."""

    country = models.ForeignKey(
        Country, null=True, blank=True, on_delete=models.SET_NULL, related_name="producers"
    )
    region = models.ForeignKey(
        Region, null=True, blank=True, on_delete=models.SET_NULL, related_name="producers"
    )
    altitude_min_masl = models.PositiveIntegerField(null=True, blank=True)
    altitude_max_masl = models.PositiveIntegerField(null=True, blank=True)
    website = models.URLField(blank=True, default="")

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]


class Roaster(ReferenceModel):
    """Whoever roasted the beans, and separately whoever sold them.

    The local cafe a user buys from is usually a custom row; the well-known
    roasters are canonical.
    """

    country = models.ForeignKey(
        Country, null=True, blank=True, on_delete=models.SET_NULL, related_name="roasters"
    )
    city = models.CharField(max_length=120, blank=True, default="")
    website = models.URLField(blank=True, default="")

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]


class Varietal(ReferenceModel):
    """Bourbon, Typica, Geisha, SL28. ``parent`` captures known lineage."""

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]


class ProcessCategory(models.TextChoices):
    WASHED = "washed", "Washed"
    NATURAL = "natural", "Natural"
    HONEY = "honey", "Honey"
    OTHER = "other", "Other"


class ProcessMethod(ReferenceModel):
    """How the cherry was processed. Grouped so filters can ask broad questions."""

    category = models.CharField(
        max_length=16, choices=ProcessCategory.choices, default=ProcessCategory.OTHER
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]


class BrewMethod(ReferenceModel):
    """Pour over, espresso, moka pot, and so on.

    ``parameter_schema`` does not store brew data. It declares which ``Brew``
    columns are relevant to this method and which are required, so the form and
    the serializer stay method-aware while the API contract stays typed. Adding
    a method is a fixture change, not a migration.

    Shape::

        {"fields": ["dose_grams", "water_grams", ...],   # ordered, for the UI
         "required": ["dose_grams", "water_grams"]}
    """

    parameter_schema = models.JSONField(default=dict, blank=True)

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]

    @property
    def relevant_fields(self) -> list[str]:
        return list(self.parameter_schema.get("fields", []))

    @property
    def required_fields(self) -> list[str]:
        return list(self.parameter_schema.get("required", []))


class TastingNote(ReferenceModel):
    """Flavour descriptors, shallowly hierarchical (``floral`` -> ``jasmine``).

    Deliberately not seeded from the SCA / World Coffee Research Flavor Wheel,
    which is copyrighted. See docs/architecture.md §10.2.
    """

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    color = models.CharField(max_length=7, blank=True, default="")

    class Meta(ReferenceModel.Meta):
        abstract = False
        ordering = ["name"]


class BurrType(models.TextChoices):
    CONICAL = "conical", "Conical burr"
    FLAT = "flat", "Flat burr"
    BLADE = "blade", "Blade"
    UNKNOWN = "unknown", "Unknown"


class Grinder(OwnedModel):
    """A user's grinder.

    Owned rather than reference data: settings are meaningless across machines,
    so there is nothing canonical to share. Recording which grinder produced a
    setting is what makes "fineness 3" comparable to the user's own past brews.
    """

    name = models.CharField(max_length=120)
    burr_type = models.CharField(max_length=16, choices=BurrType.choices, default=BurrType.UNKNOWN)
    setting_min = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    setting_max = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    step_size = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta(OwnedModel.Meta):
        abstract = False
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(setting_max__gte=models.F("setting_min"))
                | models.Q(setting_min__isnull=True)
                | models.Q(setting_max__isnull=True),
                name="grinder_setting_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name
