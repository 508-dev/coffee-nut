from django.urls import path

from .views import PublicBrewView

app_name = "sharing"

urlpatterns = [
    path("brews/<str:share_token>/", PublicBrewView.as_view(), name="public-brew"),
]
