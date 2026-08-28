"""Public share links.

The riskiest surface in the app: an anonymous endpoint reading owned data. The
leak tests below are the point of the file.
"""

import uuid

import pytest
from django.urls import reverse

from coffeenut.brewing.models import Brew
from coffeenut.catalog.models import BrewMethod, Grinder, Roaster, TastingNote
from coffeenut.coffee.models import Bag, Coffee
from coffeenut.common.models import Visibility

pytestmark = pytest.mark.django_db


@pytest.fixture
def method():
    return BrewMethod.objects.create(name="Pour Over")


@pytest.fixture
def brew(alice, method):
    roaster = Roaster.objects.create(name="Local Cafe", owner=alice)
    coffee = Coffee.objects.create(owner=alice, name="Ethiopian Washed", roaster=roaster)
    bag = Bag.objects.create(
        owner=alice,
        coffee=coffee,
        purchased_from=roaster,
        price_amount="24.00",
        price_currency="AUD",
        notes="private bag note",
        roast_date="2026-08-18",
    )
    grinder = Grinder.objects.create(owner=alice, name="Electric")
    brew = Brew.objects.create(
        owner=alice,
        bag=bag,
        method=method,
        grinder=grinder,
        grind_setting="3",
        dose_grams="14.0",
        water_grams="170.0",
        water_temp_c="98.0",
        liked=True,
        notes="flowery and light",
    )
    brew.tasting_notes.add(TastingNote.objects.create(name="Floral"))
    return brew


def public_url(token):
    return reverse("sharing:public-brew", args=[str(token)])


class TestEnablingSharing:
    def test_owner_can_publish_a_brew(self, as_user, alice, brew):
        response = as_user(alice).post(reverse("brew-share", args=[brew.pk]))

        assert response.status_code == 200
        assert response.data["share_url"].endswith(response.data["share_token"])
        brew.refresh_from_db()
        assert brew.visibility == Visibility.UNLISTED

    def test_brews_start_unshared(self, as_user, alice, brew):
        """Default unselected, per the brief."""
        assert brew.share_token is None
        assert brew.visibility == Visibility.PRIVATE

    def test_republishing_keeps_the_same_link(self, as_user, alice, brew):
        client = as_user(alice)
        first = client.post(reverse("brew-share", args=[brew.pk])).data["share_token"]

        second = client.post(reverse("brew-share", args=[brew.pk])).data["share_token"]

        assert first == second

    def test_rotating_breaks_the_old_link(self, as_user, api_client, alice, brew):
        client = as_user(alice)
        old = client.post(reverse("brew-share", args=[brew.pk])).data["share_token"]

        new = client.post(
            reverse("brew-share", args=[brew.pk]), {"rotate": True}, format="json"
        ).data["share_token"]

        assert new != old
        assert api_client.get(public_url(old)).status_code == 404
        assert api_client.get(public_url(new)).status_code == 200

    def test_revoking_kills_the_link_immediately(self, as_user, api_client, alice, brew):
        client = as_user(alice)
        token = client.post(reverse("brew-share", args=[brew.pk])).data["share_token"]

        assert client.delete(reverse("brew-share", args=[brew.pk])).status_code == 204
        assert api_client.get(public_url(token)).status_code == 404

    def test_another_user_cannot_publish_your_brew(self, as_user, bob, brew):
        response = as_user(bob).post(reverse("brew-share", args=[brew.pk]))

        assert response.status_code == 404
        brew.refresh_from_db()
        assert brew.share_token is None


class TestPublicAccess:
    @pytest.fixture
    def token(self, as_user, alice, brew):
        return as_user(alice).post(reverse("brew-share", args=[brew.pk])).data["share_token"]

    def test_anyone_with_the_link_can_read_it(self, api_client, token):
        response = api_client.get(public_url(token))

        assert response.status_code == 200
        assert response.data["method"] == "Pour Over"

    def test_includes_the_bag_details_the_brief_asks_for(self, api_client, token):
        body = api_client.get(public_url(token)).json()

        assert body["bag"]["coffee"]["name"] == "Ethiopian Washed"
        assert body["bag"]["coffee"]["roaster"] == "Local Cafe"
        assert body["bag"]["roast_date"] == "2026-08-18"

    def test_includes_the_recipe(self, api_client, token):
        body = api_client.get(public_url(token)).json()

        assert body["dose_grams"] == "14.00"
        assert body["water_grams"] == "170.0"
        assert body["grind_setting"] == "3"
        assert body["grinder"] == "Electric"
        assert body["tasting_notes"] == ["Floral"]
        assert body["liked"] is True

    def test_unknown_token_is_404(self, api_client):
        assert api_client.get(public_url(uuid.uuid4())).status_code == 404

    def test_malformed_token_is_404_not_500(self, api_client):
        assert api_client.get(public_url("not-a-uuid")).status_code == 404

    def test_a_private_brew_is_404_even_with_its_token(self, api_client, alice, brew):
        """A token alone is not enough; visibility must agree."""
        brew.share_token = uuid.uuid4()
        brew.save(update_fields=["share_token"])

        assert api_client.get(public_url(brew.share_token)).status_code == 404

    def test_is_not_indexable(self, api_client, token):
        response = api_client.get(public_url(token))

        assert "noindex" in response["X-Robots-Tag"]

    def test_a_stale_auth_header_does_not_break_it(self, api_client, token):
        """A logged-out browser may still send a dead token; the page is public."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer expired.rubbish.token")

        assert api_client.get(public_url(token)).status_code == 200


class TestNoLeaks:
    @pytest.fixture
    def body(self, api_client, as_user, alice, brew):
        token = as_user(alice).post(reverse("brew-share", args=[brew.pk])).data["share_token"]
        return api_client.get(public_url(token)).json()

    def test_does_not_expose_the_owner_account(self, body, alice):
        serialised = str(body)
        assert alice.email not in serialised
        assert str(alice.pk) not in serialised

    def test_does_not_expose_what_was_paid(self, body):
        serialised = str(body)
        assert "24.00" not in serialised
        assert "AUD" not in serialised

    def test_does_not_expose_private_bag_notes(self, body):
        assert "private bag note" not in str(body)

    def test_does_not_expose_internal_ids(self, body):
        """Ids invite probing other endpoints; the public page needs none."""
        assert "id" not in body
        assert "id" not in body["bag"]["coffee"]

    def test_shares_only_a_display_name(self, body):
        assert body["shared_by"] == "Alice"

    def test_public_fields_are_an_allowlist(self):
        """Guards the guard: adding a field to Brew must not publish it.

        If this fails, a new field was added to the model. Decide whether it is
        public and add it to PublicBrewSerializer.Meta.fields deliberately.
        """
        from coffeenut.sharing.serializers import PublicBrewSerializer

        published = set(PublicBrewSerializer().fields)
        expected = {
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
        }
        assert published == expected
