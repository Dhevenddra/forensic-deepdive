"""App URLconf (DEC-072 fixture) — reached via the root's include(api_urls), so every
route here must carry the ``api/`` parent prefix. Exercises a CBV (AccountView), a deep
dotted view path (apiapp.deep.handlers.deep_view), and a DRF router with @action."""

import apiapp.deep.handlers
from django.urls import path
from rest_framework.routers import DefaultRouter

from apiapp import views

router = DefaultRouter()
router.register("users", views.UserViewSet)

urlpatterns = [
    path("account/", views.AccountView.as_view()),
    path("deep/", apiapp.deep.handlers.deep_view),
]
urlpatterns += router.urls
