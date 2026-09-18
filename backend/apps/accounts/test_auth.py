import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationEndpoints:
    """Test suite for user registration, authentication, and JWT lifecycle."""

    def setup_method(self):
        self.client = APIClient()

    def test_register_success(self):
        """Verify successful user registration returns 201 and JWT tokens."""
        payload = {
            "email": "freshuser@policylens.ai",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "Arjun",
            "last_name": "Mehta",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert response.data["user"]["email"] == "freshuser@policylens.ai"

        # Check password is never stored in plaintext
        user = User.objects.get(email="freshuser@policylens.ai")
        assert user.password != "SecurePassword123!"
        assert user.check_password("SecurePassword123!")

    def test_register_duplicate_email_rejected(self):
        """Ensure duplicate email registration is rejected with 400."""
        User.objects.create_user(
            username="existing",
            email="duplicate@policylens.ai",
            password="Password123!",
        )
        payload = {
            "email": "duplicate@policylens.ai",
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data)

    def test_register_password_mismatch(self):
        """Ensure mismatched passwords return 400."""
        payload = {
            "email": "mismatch@policylens.ai",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in str(response.data).lower()

    def test_register_short_password(self):
        """Ensure short passwords (< 8 chars) are rejected."""
        payload = {
            "email": "short@policylens.ai",
            "password": "short",
            "password_confirm": "short",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self):
        """Verify login with valid credentials returns 200 and tokens."""
        User.objects.create_user(
            username="loginuser",
            email="login@policylens.ai",
            password="CorrectPassword123!",
        )
        payload = {
            "email": "login@policylens.ai",
            "password": "CorrectPassword123!",
        }
        response = self.client.post("/api/v1/auth/login/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    def test_login_invalid_password(self):
        """Verify login with incorrect password returns 401."""
        User.objects.create_user(
            username="wrongpassuser",
            email="wrongpass@policylens.ai",
            password="CorrectPassword123!",
        )
        payload = {
            "email": "wrongpass@policylens.ai",
            "password": "WrongPassword123!",
        }
        response = self.client.post("/api/v1/auth/login/", payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_email(self):
        """Verify login with unknown email returns 401."""
        payload = {
            "email": "unknown@policylens.ai",
            "password": "SomePassword123!",
        }
        response = self.client.post("/api/v1/auth/login/", payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self):
        """Verify refreshing token with valid refresh token."""
        user = User.objects.create_user(
            username="refreshuser",
            email="refresh@policylens.ai",
            password="Password123!",
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = str(RefreshToken.for_user(user))

        response = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_me_endpoint_authenticated(self):
        """Verify GET /api/v1/auth/me returns authenticated user data."""
        user = User.objects.create_user(
            username="meuser",
            email="me@policylens.ai",
            password="Password123!",
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == "me@policylens.ai"

    def test_me_endpoint_unauthenticated(self):
        """Verify GET /api/v1/auth/me without token returns 401."""
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
