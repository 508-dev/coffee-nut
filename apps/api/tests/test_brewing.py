"""Brews, method-aware validation, and the flows from the brief."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from coffeenut.brewing.models import Brew
from coffeenut.catalog.models import BrewMethod, Grinder, TastingNote
from coffeenut.coffee.models import Bag, Coffee

pytestmark = pytest.mark.django_db


@pytest.fixture
def pour_over():
    return BrewMethod.objects.create(
        name="Pour Over",
        parameter_schema={
            "fields": ["dose_grams", "water_grams", "water_temp_c"],
            "required": ["dose_grams", "water_grams"],
        },
    )


@pytest.fixture
def espresso():
    return BrewMethod.objects.create(
        name="Espresso",
        parameter_schema={
            "fields": ["dose_grams", "yield_grams"],
            "required": ["dose_grams", "yield_grams"],
        },
    )


@pytest.fixture
def bag(alice):
    coffee = Coffee.objects.create(owner=alice, name="Yirgacheffe Kochere")
    return Bag.objects.create(owner=alice, coffee=coffee, purchase_date="2026-08-20")


def brew_payload(bag, method, **overrides):
    return {
        "bag": str(bag.pk),
        "method": str(method.pk),
        "dose_grams": "14.0",
        "water_grams": "170.0",
        **overrides,
    }


class TestBrew:
    def test_records_a_brew(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        assert response.status_code == 201
        assert Brew.objects.get(pk=response.data["id"]).owner_id == alice.id

    def test_brewed_at_defaults_to_now(self, as_user, alice, bag, pour_over):
        """The brief wants date and time prefilled, and editable later."""
        response = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        assert response.data["brewed_at"] is not None

    def test_brewed_at_can_be_edited(self, as_user, alice, bag, pour_over):
        created = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        response = as_user(alice).patch(
            reverse("brew-detail", args=[created.data["id"]]),
            {"brewed_at": "2026-08-01T09:30:00Z"},
        )

        assert response.status_code == 200
        assert response.data["brewed_at"].startswith("2026-08-01")

    def test_ratio_is_computed_not_stored(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        # 170 water / 14 dose
        assert float(response.data["ratio"]) == pytest.approx(12.14, abs=0.01)

    def test_cannot_attach_to_another_users_bag(self, as_user, alice, bob, pour_over):
        """The IDOR the scoped relation field exists to stop."""
        their_coffee = Coffee.objects.create(owner=bob, name="Theirs")
        their_bag = Bag.objects.create(owner=bob, coffee=their_coffee)

        response = as_user(alice).post(reverse("brew-list"), brew_payload(their_bag, pour_over))

        assert response.status_code == 400
        assert not Brew.objects.filter(bag=their_bag).exists()

    def test_cannot_use_another_users_grinder(self, as_user, alice, bob, bag, pour_over):
        their_grinder = Grinder.objects.create(owner=bob, name="Their Comandante")

        response = as_user(alice).post(
            reverse("brew-list"), brew_payload(bag, pour_over, grinder=str(their_grinder.pk))
        )

        assert response.status_code == 400

    def test_brews_are_private(self, as_user, alice, bob, bag, pour_over):
        brew = Brew.objects.create(owner=alice, bag=bag, method=pour_over)

        assert as_user(bob).get(reverse("brew-detail", args=[brew.pk])).status_code == 404


class TestMethodAwareValidation:
    def test_espresso_requires_a_yield(self, as_user, alice, bag, espresso):
        response = as_user(alice).post(
            reverse("brew-list"),
            {"bag": str(bag.pk), "method": str(espresso.pk), "dose_grams": "18.0"},
        )

        assert response.status_code == 400
        assert any(e["field"] == "yield_grams" for e in response.data["errors"])

    def test_pour_over_does_not_require_a_yield(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        assert response.status_code == 201

    def test_the_error_names_the_method(self, as_user, alice, bag, espresso):
        response = as_user(alice).post(
            reverse("brew-list"), {"bag": str(bag.pk), "method": str(espresso.pk)}
        )

        messages = [e["message"] for e in response.data["errors"]]
        assert any("Espresso" in m for m in messages)


class TestValueGuards:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("dose_grams", "0"),
            ("water_grams", "-5"),
            ("water_temp_c", "150"),
            ("acidity", 9),
            ("bitterness", 0),
        ],
    )
    def test_rejects_impossible_values(self, as_user, alice, bag, pour_over, field, value):
        response = as_user(alice).post(
            reverse("brew-list"), brew_payload(bag, pour_over, **{field: value})
        )

        assert response.status_code == 400
        assert any(e["field"] == field for e in response.data["errors"])

    def test_bloom_water_cannot_exceed_total_water(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(
            reverse("brew-list"), brew_payload(bag, pour_over, bloom_water_grams="500.0")
        )

        assert response.status_code == 400

    def test_extras_rejects_nested_objects(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(
            reverse("brew-list"),
            brew_payload(bag, pour_over, extras={"agitation": {"nested": "no"}}),
            format="json",
        )

        assert response.status_code == 400

    def test_extras_accepts_flat_values(self, as_user, alice, bag, pour_over):
        response = as_user(alice).post(
            reverse("brew-list"),
            brew_payload(bag, pour_over, extras={"agitation": "swirl", "pours": 3}),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["extras"] == {"agitation": "swirl", "pours": 3}


class TestVerdict:
    def test_liked_starts_unrated(self, as_user, alice, bag, pour_over):
        """null is unrated, which is not the same as a thumbs down."""
        response = as_user(alice).post(reverse("brew-list"), brew_payload(bag, pour_over))

        assert response.data["liked"] is None

    def test_thumbs_up_and_down_are_distinct_from_unrated(self, as_user, alice, bag, pour_over):
        client = as_user(alice)
        for liked in (True, False, None):
            client.post(
                reverse("brew-list"), brew_payload(bag, pour_over, liked=liked), format="json"
            )

        assert Brew.objects.filter(liked=True).count() == 1
        assert Brew.objects.filter(liked=False).count() == 1
        assert Brew.objects.filter(liked__isnull=True).count() == 1

    def test_filters_to_liked_brews(self, as_user, alice, bag, pour_over):
        Brew.objects.create(owner=alice, bag=bag, method=pour_over, liked=True)
        Brew.objects.create(owner=alice, bag=bag, method=pour_over, liked=False)

        response = as_user(alice).get(reverse("brew-list"), {"liked": "true"})

        assert len(response.data["results"]) == 1


class TestBagBrews:
    def test_lists_brews_for_one_bag(self, as_user, alice, bag, pour_over):
        Brew.objects.create(owner=alice, bag=bag, method=pour_over)
        other_bag = Bag.objects.create(owner=alice, coffee=bag.coffee)
        Brew.objects.create(owner=alice, bag=other_bag, method=pour_over)

        response = as_user(alice).get(reverse("bag-brews", args=[bag.pk]))

        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_another_users_bag_is_not_reachable(self, as_user, bob, bag):
        assert as_user(bob).get(reverse("bag-brews", args=[bag.pk])).status_code == 404


class TestBriefWalkthrough:
    """The example flow from the brief, end to end."""

    def test_buy_a_bag_brew_it_then_compare(self, as_user, alice):
        call_command("seed_catalog", quiet=True)
        client = as_user(alice)

        # "a bag of Ethiopian washed, freshly roasted by their local cafe"
        cafe = client.post(reverse("roaster-list"), {"name": "Local Cafe"}).data
        ethiopia = client.get(reverse("country-list"), {"q": "ethiopia"}).data["results"][0]
        washed = client.get(reverse("process-list"), {"q": "washed"}).data["results"][0]

        coffee = client.post(
            reverse("coffee-list"),
            {
                "name": "Ethiopian Washed",
                "roaster": cafe["id"],
                "country": ethiopia["id"],
                "process": washed["id"],
            },
        ).data

        bag = client.post(
            reverse("bag-list"),
            {
                "coffee": coffee["id"],
                "purchased_from": cafe["id"],
                "purchase_date": "2026-08-20",
                "roast_date": "2026-08-18",
                "weight_grams": "250.0",
            },
        ).data

        # "14g ground at 3, 170ml at 98C, flowery light notes, thumbs up"
        grinder = client.post(
            reverse("grinder-list"), {"name": "Electric", "burr_type": "conical"}
        ).data
        pour_over = client.get(reverse("brew-method-list"), {"q": "pour over"}).data["results"][0]
        floral = TastingNote.objects.get(slug="floral")

        brew = client.post(
            reverse("brew-list"),
            {
                "bag": bag["id"],
                "method": pour_over["id"],
                "grinder": grinder["id"],
                "grind_setting": "3",
                "dose_grams": "14.0",
                "water_grams": "170.0",
                "water_temp_c": "98.0",
                "tasting_notes": [str(floral.pk)],
                "liked": True,
            },
            format="json",
        )
        assert brew.status_code == 201, brew.data

        # "view the list of brews against this bag, with method and verdict"
        listing = client.get(reverse("bag-brews", args=[bag["id"]]))
        assert len(listing.data["results"]) == 1
        assert listing.data["results"][0]["liked"] is True

        # One request gets everything the share page needs.
        detail = client.get(
            reverse("brew-detail", args=[brew.data["id"]]),
            {"expand": "bag.coffee.roaster,method,tasting_notes"},
        ).json()
        assert detail["bag"]["coffee"]["roaster"]["name"] == "Local Cafe"
        assert detail["method"]["name"] == "Pour Over"
        assert [n["name"] for n in detail["tasting_notes"]] == ["Floral"]
