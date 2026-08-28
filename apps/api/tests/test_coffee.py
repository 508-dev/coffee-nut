"""Coffee and Bag: the product/purchase split."""

import pytest
from django.urls import reverse

from coffeenut.catalog.models import Country, ProcessMethod, Roaster
from coffeenut.coffee.models import Bag, Coffee

pytestmark = pytest.mark.django_db


@pytest.fixture
def ethiopia():
    return Country.objects.create(name="Ethiopia", iso_alpha2="ET", iso_alpha3="ETH")


@pytest.fixture
def washed():
    return ProcessMethod.objects.create(name="Washed", category="washed")


@pytest.fixture
def coffee(alice, ethiopia, washed):
    return Coffee.objects.create(
        owner=alice, name="Yirgacheffe Kochere", country=ethiopia, process=washed
    )


class TestCoffee:
    def test_creates_with_only_a_name(self, as_user, alice):
        """Someone who knows nothing but the name must still be able to save."""
        response = as_user(alice).post(reverse("coffee-list"), {"name": "Mystery Bag"})

        assert response.status_code == 201
        assert Coffee.objects.get(pk=response.data["id"]).owner_id == alice.id

    def test_records_the_brief_s_origin_fields(self, as_user, alice, ethiopia, washed):
        response = as_user(alice).post(
            reverse("coffee-list"),
            {
                "name": "Yirgacheffe Kochere",
                "country": str(ethiopia.pk),
                "process": str(washed.pk),
                "harvest_year": 2025,
                "roast_level": "light",
            },
        )

        assert response.status_code == 201
        assert response.data["harvest_year"] == 2025

    def test_cannot_reference_another_users_roaster(self, as_user, alice, bob):
        theirs = Roaster.objects.create(name="Bob's Cafe", owner=bob)

        response = as_user(alice).post(
            reverse("coffee-list"), {"name": "X", "roaster": str(theirs.pk)}
        )

        assert response.status_code == 400

    def test_rejects_an_implausible_harvest_year(self, as_user, alice):
        response = as_user(alice).post(reverse("coffee-list"), {"name": "X", "harvest_year": 1200})

        assert response.status_code == 400
        assert any(e["field"] == "harvest_year" for e in response.data["errors"])

    def test_rejects_inverted_altitudes(self, as_user, alice):
        response = as_user(alice).post(
            reverse("coffee-list"),
            {"name": "X", "altitude_min_masl": 2000, "altitude_max_masl": 1000},
        )

        assert response.status_code == 400

    def test_is_private_to_its_owner(self, as_user, bob, coffee):
        assert as_user(bob).get(reverse("coffee-detail", args=[coffee.pk])).status_code == 404

    def test_filters_by_country(self, as_user, alice, coffee, ethiopia):
        Coffee.objects.create(owner=alice, name="Other")

        response = as_user(alice).get(reverse("coffee-list"), {"country": str(ethiopia.pk)})

        assert [c["name"] for c in response.data["results"]] == [coffee.name]


class TestBag:
    def test_records_a_purchase(self, as_user, alice, coffee):
        response = as_user(alice).post(
            reverse("bag-list"),
            {
                "coffee": str(coffee.pk),
                "purchase_date": "2026-08-20",
                "roast_date": "2026-08-18",
                "weight_grams": "250.0",
            },
        )

        assert response.status_code == 201
        assert Bag.objects.get(pk=response.data["id"]).coffee_id == coffee.id

    def test_rebuying_reuses_one_coffee(self, as_user, alice, coffee):
        """The whole point of the Coffee/Bag split."""
        client = as_user(alice)
        for date in ("2026-06-01", "2026-08-01"):
            client.post(reverse("bag-list"), {"coffee": str(coffee.pk), "purchase_date": date})

        assert Bag.objects.filter(coffee=coffee).count() == 2
        assert Coffee.objects.filter(owner=alice).count() == 1

    def test_cannot_attach_to_another_users_coffee(self, as_user, alice, bob):
        """The classic IDOR: the id exists, so existence checks alone pass it."""
        theirs = Coffee.objects.create(owner=bob, name="Bob's Coffee")

        response = as_user(alice).post(reverse("bag-list"), {"coffee": str(theirs.pk)})

        assert response.status_code == 400
        assert not Bag.objects.filter(coffee=theirs).exists()

    def test_rejects_a_roast_date_after_purchase(self, as_user, alice, coffee):
        response = as_user(alice).post(
            reverse("bag-list"),
            {"coffee": str(coffee.pk), "purchase_date": "2026-08-01", "roast_date": "2026-08-20"},
        )

        assert response.status_code == 400
        assert any(e["field"] == "roast_date" for e in response.data["errors"])

    def test_price_requires_a_currency(self, as_user, alice, coffee):
        response = as_user(alice).post(
            reverse("bag-list"), {"coffee": str(coffee.pk), "price_amount": "24.00"}
        )

        assert response.status_code == 400
        assert any(e["field"] == "price_currency" for e in response.data["errors"])

    def test_currency_is_normalised_to_uppercase(self, as_user, alice, coffee):
        response = as_user(alice).post(
            reverse("bag-list"),
            {"coffee": str(coffee.pk), "price_amount": "24.00", "price_currency": "aud"},
        )

        assert response.status_code == 201
        assert response.data["price_currency"] == "AUD"

    def test_filters_to_open_bags(self, as_user, alice, coffee):
        Bag.objects.create(owner=alice, coffee=coffee, is_finished=True)
        open_bag = Bag.objects.create(owner=alice, coffee=coffee, is_finished=False)

        response = as_user(alice).get(reverse("bag-list"), {"is_finished": "false"})

        assert [b["id"] for b in response.data["results"]] == [str(open_bag.pk)]


class TestExpand:
    def test_ids_by_default(self, as_user, alice, coffee):
        """Assert on the rendered JSON: that is what a client actually sees."""
        body = as_user(alice).get(reverse("coffee-detail", args=[coffee.pk])).json()

        assert body["country"] == str(coffee.country_id)

    def test_expands_a_relation(self, as_user, alice, coffee):
        body = (
            as_user(alice)
            .get(reverse("coffee-detail", args=[coffee.pk]), {"expand": "country"})
            .json()
        )

        assert body["country"]["name"] == "Ethiopia"

    def test_expands_a_nested_path(self, as_user, alice, coffee):
        bag = Bag.objects.create(owner=alice, coffee=coffee)

        body = (
            as_user(alice)
            .get(reverse("bag-detail", args=[bag.pk]), {"expand": "coffee.country"})
            .json()
        )

        assert body["coffee"]["country"]["name"] == "Ethiopia"

    def test_unknown_field_is_rejected_not_ignored(self, as_user, alice, coffee):
        """A typo must surface, not silently return ids."""
        response = as_user(alice).get(
            reverse("coffee-detail", args=[coffee.pk]), {"expand": "nonsense"}
        )

        assert response.status_code == 400

    def test_excessive_depth_is_rejected(self, as_user, alice, coffee):
        response = as_user(alice).get(
            reverse("coffee-detail", args=[coffee.pk]), {"expand": "a.b.c.d.e"}
        )

        assert response.status_code == 400
