import logging

from django.core.cache import cache
from django.db import connection
from django.db.utils import OperationalError
from django.utils import timezone
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Standardized production health check endpoint.
    Reports discrete service statuses without exposing credentials, connection strings, or stack traces.
    """
    db_ok = False
    try:
        connection.ensure_connection()
        db_ok = True
        db_status = "healthy"
    except OperationalError:
        db_status = "unavailable"

    redis_ok = False
    try:
        cache.set("_policylens_health", "ok", timeout=5)
        if cache.get("_policylens_health") == "ok":
            redis_ok = True
            redis_status = "healthy"
        else:
            redis_status = "unresponsive"
    except (RedisError, OSError):
        redis_status = "unavailable"

    # Celery infrastructure status check
    celery_status = "healthy" if redis_ok else "degraded"

    is_healthy = db_ok and redis_ok
    overall_status = "healthy" if is_healthy else ("degraded" if (db_ok or redis_ok) else "unhealthy")
    http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        {
            "status": overall_status,
            "service": "policylens-ai-backend",
            "version": "1.0.0",
            "timestamp": timezone.now().isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status,
                "cache": redis_status,
                "celery": celery_status,
            },
        },
        status=http_status,
    )
