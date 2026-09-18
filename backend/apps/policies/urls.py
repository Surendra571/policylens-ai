from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PolicyViewSet, policies_status

router = DefaultRouter()
router.register(r"", PolicyViewSet, basename="policy")

urlpatterns = [
    path("status/", policies_status, name="policies-status"),
    path("", include(router.urls)),
]
