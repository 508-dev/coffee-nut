"""The single API router.

Every user-owned viewset registers here. ``tests/test_tenancy.py`` walks this
registry, so an endpoint added without owner scoping fails CI automatically
rather than waiting for someone to notice.
"""

from rest_framework.routers import DefaultRouter

from coffeenut.catalog import views as catalog_views

api_router = DefaultRouter()

# Reference data: canonical rows plus each user's own additions.
api_router.register("countries", catalog_views.CountryViewSet, basename="country")
api_router.register("regions", catalog_views.RegionViewSet, basename="region")
api_router.register("producers", catalog_views.ProducerViewSet, basename="producer")
api_router.register("roasters", catalog_views.RoasterViewSet, basename="roaster")
api_router.register("varietals", catalog_views.VarietalViewSet, basename="varietal")
api_router.register("processes", catalog_views.ProcessMethodViewSet, basename="process")
api_router.register("brew-methods", catalog_views.BrewMethodViewSet, basename="brew-method")
api_router.register("tasting-notes", catalog_views.TastingNoteViewSet, basename="tasting-note")

# User-owned resources.
api_router.register("grinders", catalog_views.GrinderViewSet, basename="grinder")

# Domain apps register here as they land:
#   api_router.register("coffees", CoffeeViewSet, basename="coffee")
#   api_router.register("bags", BagViewSet, basename="bag")
#   api_router.register("brews", BrewViewSet, basename="brew")
