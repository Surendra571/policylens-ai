import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.clauses.models import Clause
from apps.documents.models import Document
from apps.policies.models import Policy

User = get_user_model()


@pytest.mark.django_db
class TestAuthorizationAndIDORPrevention:
    """Rigorous tests ensuring complete isolation of user data and IDOR vulnerability prevention."""

    def setup_method(self):
        self.client_a = APIClient()
        self.client_b = APIClient()

        # Create User A and User B
        self.user_a = User.objects.create_user(
            username="user_a",
            email="usera@policylens.ai",
            password="Password123!",
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="userb@policylens.ai",
            password="Password123!",
        )

        self.client_a.force_authenticate(user=self.user_a)
        self.client_b.force_authenticate(user=self.user_b)

        # Create Policy for User A
        self.policy_a = Policy.objects.create(
            user=self.user_a,
            name="Policy A Star",
            provider="Star Health",
        )
        # Create Policy for User B
        self.policy_b = Policy.objects.create(
            user=self.user_b,
            name="Policy B Care",
            provider="Care Health",
        )

        # Create Document for User B
        pdf_b = SimpleUploadedFile("policy_b.pdf", b"%PDF-1.4 sample", content_type="application/pdf")
        self.doc_b = Document.objects.create(
            policy=self.policy_b,
            file=pdf_b,
            original_filename="policy_b.pdf",
        )

        # Create Clause for User B
        self.clause_b = Clause.objects.create(
            policy=self.policy_b,
            title="Waiting Period 24 months",
            category=Clause.Category.WAITING_PERIOD,
            explanation="Pre-existing diseases covered after 24 months.",
            source_text="PED waiting period is 24 months.",
            page_number=3,
        )

        # Create Conversation and Message for User B
        self.conv_b = Conversation.objects.create(
            user=self.user_b,
            policy=self.policy_b,
            title="User B Conversation",
        )
        self.msg_b = Message.objects.create(
            conversation=self.conv_b,
            role=Message.Role.USER,
            content="What is my waiting period?",
        )

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must receive 401 Unauthorized."""
        anonymous_client = APIClient()
        response = anonymous_client.get(f"/api/v1/policies/{self.policy_a.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_access_own_policy(self):
        """User A can retrieve their own policy."""
        response = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Policy A Star"

    def test_idor_user_cannot_access_other_users_policy(self):
        """
        CRITICAL IDOR TEST:
        User A requesting User B's policy must receive 404 Not Found.
        """
        response = self.client_a.get(f"/api/v1/policies/{self.policy_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_user_cannot_modify_other_users_policy(self):
        """User A cannot modify User B's policy."""
        response = self.client_a.patch(
            f"/api/v1/policies/{self.policy_b.id}/",
            {"name": "Hacked Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.policy_b.refresh_from_db()
        assert self.policy_b.name == "Policy B Care"

    def test_idor_user_cannot_delete_other_users_policy(self):
        """User A cannot delete User B's policy."""
        response = self.client_a.delete(f"/api/v1/policies/{self.policy_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Policy.objects.filter(id=self.policy_b.id).exists()

    def test_policy_list_isolation(self):
        """Policy list must only return policies belonging to the requesting user."""
        response = self.client_a.get("/api/v1/policies/")
        assert response.status_code == status.HTTP_200_OK
        policy_ids = [p["id"] for p in response.data["results"]]
        assert str(self.policy_a.id) in policy_ids
        assert str(self.policy_b.id) not in policy_ids

    def test_idor_user_cannot_access_other_users_document(self):
        """User A cannot access User B's documents."""
        response = self.client_a.get(f"/api/v1/documents/{self.doc_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_user_cannot_access_other_users_clauses(self):
        """User A cannot access User B's policy clauses."""
        response = self.client_a.get(f"/api/v1/clauses/{self.clause_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_user_cannot_access_other_users_conversation(self):
        """User A cannot access User B's conversations."""
        response = self.client_a.get(f"/api/v1/chat/conversations/{self.conv_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_user_cannot_access_other_users_message(self):
        """User A cannot access User B's messages."""
        response = self.client_a.get(f"/api/v1/chat/messages/{self.msg_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
