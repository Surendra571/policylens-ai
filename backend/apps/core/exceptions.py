import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "success": False,
            "error": {
                "status_code": response.status_code,
                "message": response.data if isinstance(response.data, dict | list) else str(response.data),
            },
        }
    else:
        logger.error(f"Unhandled exception in API: {exc}", exc_info=exc)
        return Response(
            {
                "success": False,
                "error": {
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "An unexpected internal server error occurred.",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
