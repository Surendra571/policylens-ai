from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.core.views import health_check

urlpatterns = [
    # System Administration
    path("admin/", admin.site.urls),

    # Health Check Endpoints
    path("api/health/", health_check, name="health-check"),
    path("api/v1/health/", health_check, name="api-v1-health-check"),

    # OpenAPI 3 Schema & Swagger / Redoc Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API Version 1 Endpoints
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/policies/", include("apps.policies.urls")),
    path("api/v1/documents/", include("apps.documents.urls")),
    path("api/v1/clauses/", include("apps.clauses.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/ai/", include("apps.ai_engine.urls")),
    path("api/v1/core/", include("apps.core.urls")),
]
