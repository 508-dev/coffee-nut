"""The single API router.

Every user-owned viewset registers here. ``tests/test_tenancy.py`` walks this
registry, so an endpoint added without owner scoping fails CI automatically
rather than waiting for someone to notice.
"""

from rest_framework.routers import DefaultRouter

api_router = DefaultRouter()

# Domain apps register here as they land:
#   api_router.register("coffees", CoffeeViewSet, basename="coffee")
#   api_router.register("bags", BagViewSet, basename="bag")
#   api_router.register("brews", BrewViewSet, basename="brew")
