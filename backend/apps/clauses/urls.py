from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClauseViewSet, clauses_status

router = DefaultRouter()
router.register(r"", ClauseViewSet, basename="clause")

urlpatterns = [
    path("status/", clauses_status, name="clauses-status"),
    path("", include(router.urls)),
]
