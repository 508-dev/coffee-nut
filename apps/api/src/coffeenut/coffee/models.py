"""Product identity and purchases.

``Coffee`` is the thing a roaster sells; ``Bag`` is one purchase of it. Buying
the same lot twice reuses one ``Coffee`` and adds a second ``Bag``, which is
what makes "how did this year's harvest compare?" answerable.
"""

from django.db import models

from coffeenut.catalog.models import Country, ProcessMethod, Producer, Region, Roaster, Varietal
from coffeenut.common.models import OwnedModel


class RoastLevel(models.TextChoices):
    LIGHT = "light", "Light"
    MEDIUM_LIGHT = "medium_light", "Medium-light"
    MEDIUM = "medium", "Medium"
    MEDIUM_DARK = "medium_dark", "Medium-dark"
    DARK = "dark", "Dark"


class Coffee(OwnedModel):
    """A coffee product.

    Every reference field is optional on purpose: someone who knows only
    "Ethiopian, washed" must still be able to save the record and fill the rest
    in later.
    """

    name = models.CharField(max_length=200)
    roaster = models.ForeignKey(
        Roaster, null=True, blank=True, on_delete=models.SET_NULL, related_name="coffees"
    )
    country = models.ForeignKey(
        Country, null=True, blank=True, on_delete=models.SET_NULL, related_name="coffees"
    )
    region = models.ForeignKey(
        Region, null=True, blank=True, on_delete=models.SET_NULL, related_name="coffees"
    )
    producer = models.ForeignKey(
        Producer, null=True, blank=True, on_delete=models.SET_NULL, related_name="coffees"
    )
    process = models.ForeignKey(
        ProcessMethod, null=True, blank=True, on_delete=models.SET_NULL, related_name="coffees"
    )
    varietals = models.ManyToManyField(Varietal, blank=True, related_name="coffees")

    harvest_year = models.PositiveSmallIntegerField(null=True, blank=True)
    roast_level = models.CharField(
        max_length=16, choices=RoastLevel.choices, blank=True, default=""
    )
    altitude_min_masl = models.PositiveIntegerField(null=True, blank=True)
    altitude_max_masl = models.PositiveIntegerField(null=True, blank=True)
    is_decaf = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta(OwnedModel.Meta):
        abstract = False
        ordering = ["-created_at"]
        indexes = [
            *OwnedModel.Meta.indexes,
            models.Index(fields=["owner", "name"], name="coffee_own_name"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(harvest_year__isnull=True)
                | models.Q(harvest_year__gte=1900, harvest_year__lte=2100),
                name="coffee_harvest_year_sane",
            ),
            models.CheckConstraint(
                condition=models.Q(altitude_min_masl__isnull=True)
                | models.Q(altitude_max_masl__isnull=True)
                | models.Q(altitude_max_masl__gte=models.F("altitude_min_masl")),
                name="coffee_altitude_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Bag(OwnedModel):
    """One purchase of a :class:`Coffee`.

    ``roast_date`` lives here rather than on ``Coffee`` because freshness is a
    property of the physical bag, and it is the field most likely to differ
    between two purchases of the same coffee.
    """

    coffee = models.ForeignKey(Coffee, on_delete=models.CASCADE, related_name="bags")
    # Often not the roaster: the cafe that sold it. Keeping them apart is what
    # makes "recommend a bag from a local cafe" answerable.
    purchased_from = models.ForeignKey(
        Roaster, null=True, blank=True, on_delete=models.SET_NULL, related_name="bags_sold"
    )

    purchase_date = models.DateField(null=True, blank=True)
    roast_date = models.DateField(null=True, blank=True)
    opened_date = models.DateField(null=True, blank=True)
    finished_date = models.DateField(null=True, blank=True)

    weight_grams = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=3, blank=True, default="")

    is_finished = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta(OwnedModel.Meta):
        abstract = False
        ordering = ["-purchase_date", "-created_at"]
        indexes = [
            *OwnedModel.Meta.indexes,
            models.Index(fields=["owner", "is_finished"], name="bag_own_finished"),
            models.Index(fields=["coffee", "-created_at"], name="bag_coffee_created"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight_grams__isnull=True) | models.Q(weight_grams__gt=0),
                name="bag_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(price_amount__isnull=True) | models.Q(price_amount__gte=0),
                name="bag_price_not_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(roast_date__isnull=True)
                | models.Q(purchase_date__isnull=True)
                | models.Q(roast_date__lte=models.F("purchase_date")),
                name="bag_roasted_before_purchase",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.coffee.name} ({self.purchase_date or 'undated'})"
