"""Concrete models that exist only to exercise the abstract bases.

Installed by ``coffeenut.settings.test`` only. Without these, the tenancy and
reference-scoping primitives could not be tested until a domain app happened to
use them — which is exactly backwards.
"""

from django.db import models

from coffeenut.common.models import OwnedModel, ReferenceModel


class OwnedThing(OwnedModel):
    label = models.CharField(max_length=100, blank=True)

    class Meta(OwnedModel.Meta):
        abstract = False


class ReferenceThing(ReferenceModel):
    class Meta(ReferenceModel.Meta):
        abstract = False
