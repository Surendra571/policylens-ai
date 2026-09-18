from django.urls import path

from .views import ai_status

urlpatterns = [
    path("status/", ai_status, name="ai-status"),
]
