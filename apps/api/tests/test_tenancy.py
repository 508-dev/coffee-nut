"""Cross-user access must fail, on every endpoint, forever.

Two layers of test here:

* ``TestOwnedViewSetScoping`` exercises the shared base directly, so the
  mechanism is covered before any domain app exists.
* ``test_registered_viewsets_scope_by_owner`` walks the live router, so a new
  endpoint that forgets owner scoping fails CI without anyone updating a list.
"""

import pytest
from model_bakery import baker
from rest_framework import serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from coffeenut.api_router import api_router
from coffeenut.common.models import OwnedModel
from coffeenut.common.views import OwnedModelViewSet
from tests.testapp.models import OwnedThing

pytestmark = pytest.mark.django_db


class _ThingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnedThing
        fields = ["id", "label", "visibility", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class _ThingViewSet(OwnedModelViewSet):
    queryset = OwnedThing.objects.all()
    serializer_class = _ThingSerializer


class TestOwnedViewSetScoping:
    factory = APIRequestFactory()

    def _call(self, method, action, user, **kwargs):
        request = getattr(self.factory, method)("/", **kwargs)
        force_authenticate(request, user=user)
        return _ThingViewSet.as_view(action)(request, **kwargs.pop("url_kwargs", {}))

    def test_owner_can_retrieve(self, alice):
        thing = OwnedThing.objects.create(owner=alice, label="mine")
        request = self.factory.get("/")
        force_authenticate(request, user=alice)

        response = _ThingViewSet.as_view({"get": "retrieve"})(request, pk=str(thing.pk))

        assert response.status_code == 200

    def test_other_user_gets_404_not_403(self, alice, bob):
        """404 rather than 403: a 403 would confirm the id exists."""
        thing = OwnedThing.objects.create(owner=alice, label="mine")
        request = self.factory.get("/")
        force_authenticate(request, user=bob)

        response = _ThingViewSet.as_view({"get": "retrieve"})(request, pk=str(thing.pk))

        assert response.status_code == 404

    def test_other_user_cannot_update(self, alice, bob):
        thing = OwnedThing.objects.create(owner=alice, label="mine")
        request = self.factory.patch("/", {"label": "hijacked"}, format="json")
        force_authenticate(request, user=bob)

        response = _ThingViewSet.as_view({"patch": "partial_update"})(request, pk=str(thing.pk))

        assert response.status_code == 404
        thing.refresh_from_db()
        assert thing.label == "mine"

    def test_other_user_cannot_destroy(self, alice, bob):
        thing = OwnedThing.objects.create(owner=alice)
        request = self.factory.delete("/")
        force_authenticate(request, user=bob)

        response = _ThingViewSet.as_view({"delete": "destroy"})(request, pk=str(thing.pk))

        assert response.status_code == 404
        assert OwnedThing.objects.filter(pk=thing.pk).exists()

    def test_list_excludes_other_users(self, alice, bob):
        OwnedThing.objects.create(owner=alice, label="mine")
        OwnedThing.objects.create(owner=bob, label="theirs")
        request = self.factory.get("/")
        force_authenticate(request, user=alice)

        response = _ThingViewSet.as_view({"get": "list"})(request)

        assert response.status_code == 200
        assert [row["label"] for row in response.data["results"]] == ["mine"]

    def test_anonymous_is_rejected(self, alice):
        OwnedThing.objects.create(owner=alice)

        response = _ThingViewSet.as_view({"get": "list"})(self.factory.get("/"))

        assert response.status_code == 401

    def test_create_ignores_client_supplied_owner(self, alice, bob):
        """A spoofed owner must be ignored, not rejected: rejection leaks that
        the id is real."""
        request = self.factory.post("/", {"label": "new", "owner": str(bob.pk)}, format="json")
        force_authenticate(request, user=alice)

        response = _ThingViewSet.as_view({"post": "create"})(request)

        assert response.status_code == 201
        assert OwnedThing.objects.get(pk=response.data["id"]).owner_id == alice.id

    def test_updated_since_filters_the_list(self, alice):
        OwnedThing.objects.create(owner=alice, label="old")
        request = self.factory.get("/", {"updated_since": "2999-01-01T00:00:00Z"})
        force_authenticate(request, user=alice)

        response = _ThingViewSet.as_view({"get": "list"})(request)

        assert response.status_code == 200
        assert response.data["results"] == []

    def test_updated_since_rejects_junk(self, alice):
        request = self.factory.get("/", {"updated_since": "last tuesday"})
        force_authenticate(request, user=alice)

        response = _ThingViewSet.as_view({"get": "list"})(request)

        assert response.status_code == 400


def _owned_viewsets():
    found = []
    for prefix, viewset, _basename in api_router.registry:
        queryset = getattr(viewset, "queryset", None)
        if queryset is not None and issubclass(queryset.model, OwnedModel):
            found.append((prefix, viewset))
    return found


@pytest.mark.parametrize(
    ("prefix", "viewset"),
    _owned_viewsets(),
    ids=[prefix for prefix, _ in _owned_viewsets()],
)
def test_registered_viewsets_scope_by_owner(prefix, viewset, alice, bob):
    """Every owned resource on the router hides other users' rows."""
    instance = baker.make(viewset.queryset.model, owner=alice)
    request = APIRequestFactory().get("/")
    force_authenticate(request, user=bob)

    response = viewset.as_view({"get": "retrieve"})(request, pk=str(instance.pk))

    assert response.status_code == 404, (
        f"/{prefix}/ leaks another user's row; it likely overrides get_queryset() "
        f"without calling super(), or does not extend OwnedModelViewSet."
    )


def test_router_walk_is_not_silently_vacuous():
    """Guards the guard.

    ``test_registered_viewsets_scope_by_owner`` generates no cases while the
    router is empty. This test fails the moment owned viewsets are registered
    but the walk stops finding them — for instance if someone swaps ``queryset``
    for a bare ``get_queryset`` override, which would make the sweep blind.
    """
    registered = len(api_router.registry)
    discovered = len(_owned_viewsets())

    if registered == 0:
        pytest.skip("No viewsets registered yet; the tenancy sweep activates with them.")

    assert discovered > 0, (
        f"{registered} viewset(s) registered but none expose a `queryset` "
        f"attribute, so the tenancy sweep cannot see them."
    )
