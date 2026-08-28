"""A single brew: one attempt against one bag."""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from coffeenut.catalog.models import BrewMethod, Grinder, TastingNote
from coffeenut.coffee.models import Bag
from coffeenut.common.models import OwnedModel

# Taste axes are recorded 1-5. Anything finer than that is false precision for
# someone tasting at their kitchen bench.
TASTE_MIN = 1
TASTE_MAX = 5


def _taste_axis(help_text: str) -> models.PositiveSmallIntegerField:
    return models.PositiveSmallIntegerField(null=True, blank=True, help_text=help_text)


class Brew(OwnedModel):
    """One brew.

    Method-specific parameters are real columns rather than a JSON blob. Three
    clients consume this API, and a blob is invisible to OpenAPI, unvalidatable
    at the database layer, and awkward to filter or aggregate on. Nearly every
    field below applies to two or more methods, so the table is not as wide as
    it first looks. ``extras`` remains for genuinely experimental parameters.
    """

    bag = models.ForeignKey(Bag, on_delete=models.CASCADE, related_name="brews")
    method = models.ForeignKey(BrewMethod, on_delete=models.PROTECT, related_name="brews")
    # Prefilled by the client and editable afterwards, per the brief.
    brewed_at = models.DateTimeField(default=timezone.now)

    # --- Dose -------------------------------------------------------------
    dose_grams = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    water_grams = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    water_temp_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    # --- Grind ------------------------------------------------------------
    grinder = models.ForeignKey(
        Grinder, null=True, blank=True, on_delete=models.SET_NULL, related_name="brews"
    )
    # Free text: "3", "12 clicks", "medium-fine". Grinders share no scale, which
    # is why the grinder itself is recorded alongside.
    grind_setting = models.CharField(max_length=64, blank=True, default="")
    grind_microns = models.PositiveIntegerField(null=True, blank=True)

    # --- Time -------------------------------------------------------------
    total_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    bloom_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    bloom_water_grams = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    # --- Espresso ---------------------------------------------------------
    pressure_bar = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    yield_grams = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    # --- Verdict ----------------------------------------------------------
    # Nullable on purpose: null is unrated, which is a different thing from a
    # thumbs down and matters for "show me my good brews".
    liked = models.BooleanField(null=True, blank=True)
    tasting_notes = models.ManyToManyField(TastingNote, blank=True, related_name="brews")
    notes = models.TextField(blank=True, default="")

    # --- Taste profile ----------------------------------------------------
    acidity = _taste_axis("1 (flat) to 5 (bright)")
    sweetness = _taste_axis("1 (dry) to 5 (sweet)")
    body = _taste_axis("1 (thin) to 5 (heavy)")
    bitterness = _taste_axis("1 (none) to 5 (harsh)")
    aftertaste = _taste_axis("1 (short) to 5 (lingering)")

    # Escape hatch for parameters a method needs that no column covers yet.
    extras = models.JSONField(default=dict, blank=True)

    class Meta(OwnedModel.Meta):
        abstract = False
        ordering = ["-brewed_at"]
        indexes = [
            *OwnedModel.Meta.indexes,
            models.Index(fields=["bag", "-brewed_at"], name="brew_bag_brewed"),
            models.Index(fields=["owner", "-brewed_at"], name="brew_own_brewed"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(dose_grams__isnull=True) | models.Q(dose_grams__gt=0),
                name="brew_dose_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(water_grams__isnull=True) | models.Q(water_grams__gt=0),
                name="brew_water_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(water_temp_c__isnull=True)
                | models.Q(water_temp_c__gte=0, water_temp_c__lte=100),
                name="brew_water_temp_range",
            ),
            models.CheckConstraint(
                condition=models.Q(yield_grams__isnull=True) | models.Q(yield_grams__gt=0),
                name="brew_yield_positive",
            ),
            *[
                models.CheckConstraint(
                    condition=models.Q(**{f"{axis}__isnull": True})
                    | models.Q(**{f"{axis}__gte": TASTE_MIN, f"{axis}__lte": TASTE_MAX}),
                    name=f"brew_{axis}_range",
                )
                for axis in ("acidity", "sweetness", "body", "bitterness", "aftertaste")
            ],
        ]

    def __str__(self) -> str:
        return f"{self.method.name} @ {self.brewed_at:%Y-%m-%d %H:%M}"

    @property
    def ratio(self) -> Decimal | None:
        """Water to coffee, computed rather than stored."""
        if self.dose_grams and self.water_grams:
            return (self.water_grams / self.dose_grams).quantize(Decimal("0.01"))
        return None
