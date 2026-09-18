from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, documents_status

router = DefaultRouter()
router.register(r"", DocumentViewSet, basename="document")

urlpatterns = [
    path("status/", documents_status, name="documents-status"),
    path("", include(router.urls)),
]
