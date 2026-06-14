"""Root URLconf (DEC-072 fixture). Mounts the app via an include(<variable>) — the
variable ``api_urls`` aliases the ``apiapp.urls`` submodule (the wagtail shape)."""

from django.urls import include, path

from apiapp import urls as api_urls

urlpatterns = [
    path("api/", include(api_urls)),
]
