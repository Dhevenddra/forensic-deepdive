"""App views (DEC-072 fixture)."""

from django.views import View
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet


class AccountView(View):
    def get(self, request):
        return None

    def post(self, request):
        return None


class UserViewSet(ModelViewSet):
    def list(self, request):
        return None

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk):
        return None

    @action(detail=False)
    def recent(self, request):
        return None
