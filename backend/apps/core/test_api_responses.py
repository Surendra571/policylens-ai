import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.policies.models import Policy

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="api_tester",
        email="apitester@policylens.ai",
        password="Password123!",
    )


@pytest.mark.django_db
class TestAPIResponseFormatsAndErrors:
    """
    Test suite validating API response contracts:
    - Success responses
    - Validation errors (400)
    - Authorization errors (401 / 403)
    - Resource not found (404)
    - Server error fallback (500)
    """

    def test_success_response_structure(self, api_client, auth_user):
        api_client.force_authenticate(user=auth_user)
        response = api_client.post(
            "/api/v1/policies/",
            {
                "name": "Health Shield Plus",
                "provider": "Bajaj Allianz",
                "policy_type": Policy.PolicyType.INDIVIDUAL,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["name"] == "Health Shield Plus"
        assert response.data["provider"] == "Bajaj Allianz"

    def test_validation_error_format_400(self, api_client, auth_user):
        api_client.force_authenticate(user=auth_user)
        # Missing required provider field
        response = api_client.post(
            "/api/v1/policies/",
            {"name": "Incomplete Policy"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Custom exception handler ensures consistent error envelope
        assert "error" in response.data or "provider" in response.data

    def test_unauthenticated_request_401(self, api_client):
        response = api_client.get("/api/v1/policies/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_nonexistent_resource_404(self, api_client, auth_user):
        api_client.force_authenticate(user=auth_user)
        response = api_client.get("/api/v1/policies/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_server_error_handler_fallback(self):
        from apps.core.exceptions import custom_exception_handler

        # Test custom exception handler handles unhandled internal exceptions cleanly
        unhandled_exc = Exception("Critical unexpected failure")
        res = custom_exception_handler(unhandled_exc, {})
        assert res is not None
        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert res.data["success"] is False
        assert res.data["error"]["status_code"] == 500
        assert "internal server error" in res.data["error"]["message"].lower()
