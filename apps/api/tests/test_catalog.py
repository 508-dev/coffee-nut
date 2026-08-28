"""Reference data endpoints: canonical vs custom, and typeahead ranking."""

import pytest
from django.urls import reverse

from coffeenut.catalog.models import Country, Grinder, Roaster, Varietal

pytestmark = pytest.mark.django_db


@pytest.fixture
def ethiopia():
    return Country.objects.create(name="Ethiopia", iso_alpha2="ET", iso_alpha3="ETH")


class TestVisibility:
    def test_lists_canonical_plus_own(self, as_user, alice, bob):
        canonical = Roaster.objects.create(name="Onyx Coffee Lab")
        mine = Roaster.objects.create(name="My Corner Cafe", owner=alice)
        Roaster.objects.create(name="Their Cafe", owner=bob)

        response = as_user(alice).get(reverse("roaster-list"))

        assert response.status_code == 200
        names = {row["name"] for row in response.data["results"]}
        assert names == {canonical.name, mine.name}

    def test_another_users_custom_row_is_not_retrievable(self, as_user, alice, bob):
        theirs = Roaster.objects.create(name="Their Cafe", owner=bob)

        response = as_user(alice).get(reverse("roaster-detail", args=[theirs.pk]))

        assert response.status_code == 404

    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("roaster-list")).status_code == 401

    def test_merged_rows_are_hidden_from_lists(self, as_user, alice):
        canonical = Roaster.objects.create(name="Onyx Coffee Lab")
        Roaster.objects.create(name="Onyx Coffee Lab", owner=alice, merged_into=canonical)

        response = as_user(alice).get(reverse("roaster-list"))

        assert len(response.data["results"]) == 1

    def test_a_merged_row_is_still_retrievable_by_id(self, as_user, alice):
        """Existing foreign keys must keep resolving after promotion."""
        canonical = Roaster.objects.create(name="Onyx Coffee Lab")
        merged = Roaster.objects.create(name="Onyx Coffee Lab", owner=alice, merged_into=canonical)

        assert as_user(alice).get(reverse("roaster-detail", args=[merged.pk])).status_code == 200


class TestWriting:
    def test_creating_makes_a_private_row(self, as_user, alice):
        response = as_user(alice).post(reverse("roaster-list"), {"name": "Corner Cafe"})

        assert response.status_code == 201
        assert response.data["is_canonical"] is False
        assert Roaster.objects.get(pk=response.data["id"]).owner_id == alice.id

    def test_client_cannot_create_a_canonical_row(self, as_user, alice):
        """Promotion is a curation step, never a client action."""
        response = as_user(alice).post(reverse("roaster-list"), {"name": "Sneaky", "owner": None})

        assert response.status_code == 201
        assert Roaster.objects.get(pk=response.data["id"]).is_canonical is False

    def test_canonical_rows_cannot_be_edited(self, as_user, alice):
        canonical = Roaster.objects.create(name="Onyx Coffee Lab")

        response = as_user(alice).patch(
            reverse("roaster-detail", args=[canonical.pk]), {"name": "Hijacked"}
        )

        assert response.status_code == 403
        canonical.refresh_from_db()
        assert canonical.name == "Onyx Coffee Lab"

    def test_canonical_rows_cannot_be_deleted(self, as_user, alice):
        canonical = Roaster.objects.create(name="Onyx Coffee Lab")

        response = as_user(alice).delete(reverse("roaster-detail", args=[canonical.pk]))

        assert response.status_code == 403
        assert Roaster.objects.filter(pk=canonical.pk).exists()

    def test_own_rows_can_be_edited(self, as_user, alice):
        mine = Roaster.objects.create(name="Corner Cafe", owner=alice)

        response = as_user(alice).patch(
            reverse("roaster-detail", args=[mine.pk]), {"city": "Melbourne"}
        )

        assert response.status_code == 200
        mine.refresh_from_db()
        assert mine.city == "Melbourne"

    def test_countries_are_entirely_read_only(self, as_user, alice, ethiopia):
        """ISO data: users pick from the list, they do not extend it."""
        response = as_user(alice).post(
            reverse("country-list"), {"name": "Freedonia", "iso_alpha2": "XF", "iso_alpha3": "XFR"}
        )

        assert response.status_code == 405


class TestTypeahead:
    def test_filters_by_substring(self, as_user, alice):
        Roaster.objects.create(name="Onyx Coffee Lab")
        Roaster.objects.create(name="Tim Wendelboe")

        response = as_user(alice).get(reverse("roaster-list"), {"q": "onyx"})

        assert [r["name"] for r in response.data["results"]] == ["Onyx Coffee Lab"]

    def test_prefix_matches_outrank_substring_matches(self, as_user, alice):
        Roaster.objects.create(name="Old Coffee Company")
        Roaster.objects.create(name="Coffee Collective")

        response = as_user(alice).get(reverse("roaster-list"), {"q": "coffee"})

        assert response.data["results"][0]["name"] == "Coffee Collective"

    def test_canonical_outranks_custom_on_a_tie(self, as_user, alice):
        Roaster.objects.create(name="Coffee Collective")
        Roaster.objects.create(name="Coffee Collective", owner=alice)

        response = as_user(alice).get(reverse("roaster-list"), {"q": "coffee c"})

        assert response.data["results"][0]["is_canonical"] is True

    def test_search_is_case_insensitive(self, as_user, alice):
        Roaster.objects.create(name="Onyx Coffee Lab")

        assert len(as_user(alice).get(reverse("roaster-list"), {"q": "ONYX"}).data["results"]) == 1

    def test_search_does_not_reach_other_users(self, as_user, alice, bob):
        Roaster.objects.create(name="Secret Cafe", owner=bob)

        response = as_user(alice).get(reverse("roaster-list"), {"q": "secret"})

        assert response.data["results"] == []


class TestRelations:
    def test_cannot_point_a_region_at_another_users_country(self, as_user, alice, bob):
        """Reference FKs are scoped too, not just owned ones."""
        private_country = Country.objects.create(
            name="Bobland", iso_alpha2="XB", iso_alpha3="XBL", owner=bob
        )

        response = as_user(alice).post(
            reverse("region-list"), {"name": "Nowhere", "country": str(private_country.pk)}
        )

        assert response.status_code == 400

    def test_can_point_at_a_canonical_country(self, as_user, alice, ethiopia):
        response = as_user(alice).post(
            reverse("region-list"), {"name": "My Farm Valley", "country": str(ethiopia.pk)}
        )

        assert response.status_code == 201

    def test_varietal_parent_may_be_canonical(self, as_user, alice):
        bourbon = Varietal.objects.create(name="Bourbon")

        response = as_user(alice).post(
            reverse("varietal-list"), {"name": "My Selection", "parent": str(bourbon.pk)}
        )

        assert response.status_code == 201


class TestGrinders:
    def test_grinders_are_private(self, as_user, alice, bob):
        Grinder.objects.create(name="Bob's Comandante", owner=bob)
        mine = Grinder.objects.create(name="My Encore", owner=alice)

        response = as_user(alice).get(reverse("grinder-list"))

        assert [g["name"] for g in response.data["results"]] == [mine.name]

    def test_creating_assigns_the_caller(self, as_user, alice):
        response = as_user(alice).post(
            reverse("grinder-list"), {"name": "Encore", "burr_type": "conical"}
        )

        assert response.status_code == 201
        assert Grinder.objects.get(pk=response.data["id"]).owner_id == alice.id

    def test_inverted_setting_range_is_a_field_error_not_a_500(self, as_user, alice):
        response = as_user(alice).post(
            reverse("grinder-list"), {"name": "Odd", "setting_min": 10, "setting_max": 2}
        )

        assert response.status_code == 400
        assert any(e["field"] == "setting_max" for e in response.data["errors"])
