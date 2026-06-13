"""App views (DEC-065 fixture) — the handlers the URLconf routes resolve to."""

from django.views import View
from rest_framework.viewsets import ModelViewSet


def vet_list(request):
    return None


class VetDetail(View):
    def get(self, request, pk):
        return None


def legacy_view(request, pet_id):
    return None


class OwnerViewSet(ModelViewSet):
    queryset = None
