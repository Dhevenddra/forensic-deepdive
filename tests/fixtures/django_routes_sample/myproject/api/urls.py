"""App URLconf (DEC-065 fixture) — included under ``api/v1/`` by the root.

Exercises: a module-qualified view (``views.vet_list``), a class-based view
(``VetDetail.as_view()``), a bare imported view in a ``re_path`` regex
(``legacy_view``), a DRF ``DefaultRouter`` (``OwnerViewSet`` CRUD), and an
unresolvable view (``views.does_not_exist`` — honest unmatched, no fabrication).
"""

from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from . import views
from .views import legacy_view

router = DefaultRouter()
router.register(r"owners", views.OwnerViewSet)

urlpatterns = [
    path("vets/", views.vet_list),
    path("vets/<int:pk>/", views.VetDetail.as_view()),
    re_path(r"^pets/(?P<pet_id>[0-9]+)/$", legacy_view),
    path("missing/", views.does_not_exist),
]
urlpatterns += router.urls
