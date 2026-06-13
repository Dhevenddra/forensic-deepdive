"""Root URLconf (DEC-065 fixture) — mounts the api app under a prefix."""

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("myproject.api.urls")),
]
