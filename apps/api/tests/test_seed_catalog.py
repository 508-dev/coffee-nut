"""The seed command runs against live databases, so it must be safe to re-run."""

import pytest
from django.core.management import call_command

from coffeenut.catalog.models import BrewMethod, Country, Roaster, TastingNote, Varietal
from coffeenut.common.models import ReferenceSource

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_catalog", quiet=True)


def test_seeds_canonical_rows(seeded):
    assert Country.objects.canonical().count() > 200
    assert Country.objects.get(iso_alpha2="ET").name == "Ethiopia"


def test_seeded_rows_are_marked_as_seed_data(seeded):
    assert Country.objects.get(iso_alpha2="ET").source == ReferenceSource.SEED


def test_running_twice_creates_no_duplicates(seeded):
    before = {m.__name__: m.objects.count() for m in (Country, Varietal, BrewMethod, TastingNote)}

    call_command("seed_catalog", quiet=True)

    after = {m.__name__: m.objects.count() for m in (Country, Varietal, BrewMethod, TastingNote)}
    assert before == after


def test_reseeding_preserves_primary_keys(seeded):
    """User coffees hold these ids; re-seeding must not orphan them."""
    original = Country.objects.get(iso_alpha2="ET").pk

    call_command("seed_catalog", quiet=True)

    assert Country.objects.get(iso_alpha2="ET").pk == original


def test_seeding_leaves_user_rows_alone(alice, seeded):
    mine = Roaster.objects.create(name="My Corner Cafe", owner=alice)

    call_command("seed_catalog", quiet=True)

    mine.refresh_from_db()
    assert mine.owner_id == alice.id
    assert mine.source == ReferenceSource.MANUAL


def test_self_referencing_parents_are_linked(seeded):
    caturra_parent = Varietal.objects.get(slug="caturra").parent
    jasmine_parent = TastingNote.objects.get(slug="jasmine").parent

    assert caturra_parent is not None and caturra_parent.slug == "bourbon"
    assert jasmine_parent is not None and jasmine_parent.slug == "floral"


def test_brew_methods_declare_their_parameters(seeded):
    espresso = BrewMethod.objects.get(slug="espresso")

    assert "yield_grams" in espresso.relevant_fields
    assert "dose_grams" in espresso.required_fields
    # Espresso has no brew-water weight; that would be a pour-over field.
    assert "bloom_water_grams" not in espresso.relevant_fields


def test_no_roasters_or_producers_are_seeded(seeded):
    """Deliberate: a half-complete canonical list is worse than none, because
    users trust it, miss their roaster, and create a duplicate anyway."""
    assert Roaster.objects.canonical().count() == 0
