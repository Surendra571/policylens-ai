import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.documents.models import Document, DocumentChunk, DocumentPage
from apps.policies.models import Policy

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username="chat_alice",
        email="alice@policylens.ai",
        password="SecurePassword123!",
        first_name="Alice",
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username="chat_bob",
        email="bob@policylens.ai",
        password="SecurePassword123!",
        first_name="Bob",
    )


@pytest.fixture
def policy_a(db, user_a):
    policy = Policy.objects.create(
        user=user_a,
        name="Optima Secure Health",
        provider="HDFC ERGO",
        policy_type=Policy.PolicyType.INDIVIDUAL,
    )
    doc = Document.objects.create(
        policy=policy,
        original_filename="optima_secure.pdf",
        file_size=1024,
        file_hash="hash123",
        processing_status=Document.ProcessingStatus.COMPLETED,
    )
    page_12 = DocumentPage.objects.create(
        document=doc,
        page_number=12,
        extracted_text="Maternity expenses are covered up to INR 50,000 after a waiting period of 24 months.",
    )
    DocumentChunk.objects.create(
        document=doc,
        page=page_12,
        chunk_index=0,
        content="Maternity expenses are covered up to INR 50,000 after a waiting period of 24 months of continuous coverage.",
        metadata={"section": "Maternity Benefits", "page_number": 12},
    )
    page_18 = DocumentPage.objects.create(
        document=doc,
        page_number=18,
        extracted_text="Pre-existing diseases have a 36-month waiting period.",
    )
    DocumentChunk.objects.create(
        document=doc,
        page=page_18,
        chunk_index=1,
        content="Pre-existing diseases have a 36-month waiting period from the initial policy commencement date.",
        metadata={"section": "Waiting Periods", "page_number": 18},
    )
    return policy


@pytest.mark.django_db
class TestPolicySpecificAIChat:
    """Test suite validating Policy AI Chat, citations, grounding, and cross-user isolation."""

    def test_unauthenticated_chat_rejected(self, api_client, policy_a):
        url = f"/api/v1/policies/{policy_a.id}/chat/"
        response = api_client.post(url, {"question": "Is maternity covered?"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_question_returns_answer_and_citations(self, api_client, user_a, policy_a):
        api_client.force_authenticate(user=user_a)
        url = f"/api/v1/policies/{policy_a.id}/chat/"

        response = api_client.post(url, {"question": "Is maternity expenses covered?"}, format="json")
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert "answer" in data
        assert "confidence" in data
        assert len(data["citations"]) > 0

        first_cite = data["citations"][0]
        assert first_cite["page"] == 12
        assert first_cite["section"] == "Maternity Benefits"
        assert "50,000" in first_cite["source_text"]

        # Confirm conversation and message records stored in DB
        assert Conversation.objects.filter(user=user_a, policy=policy_a).exists()
        assert Message.objects.filter(conversation__policy=policy_a, role=Message.Role.USER).exists()
        assert Message.objects.filter(conversation__policy=policy_a, role=Message.Role.ASSISTANT).exists()

    def test_irrelevant_question_insufficient_evidence(self, api_client, user_a, policy_a):
        api_client.force_authenticate(user=user_a)
        url = f"/api/v1/policies/{policy_a.id}/chat/"

        response = api_client.post(url, {"question": "Does this cover space shuttle collision damage?"}, format="json")
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert "could not find sufficient information" in data["answer"].lower()
        assert data["confidence"] == "low"
        assert len(data["citations"]) == 0

    def test_cross_policy_and_cross_user_isolation(self, api_client, user_b, policy_a):
        """User B must never be able to chat with User A's policy."""
        api_client.force_authenticate(user=user_b)
        url = f"/api/v1/policies/{policy_a.id}/chat/"

        response = api_client.post(url, {"question": "Is maternity covered?"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_conversation_history_continuation(self, api_client, user_a, policy_a):
        api_client.force_authenticate(user=user_a)
        url = f"/api/v1/policies/{policy_a.id}/chat/"

        # First message
        res1 = api_client.post(url, {"question": "What is the pre-existing disease waiting period?"}, format="json")
        assert res1.status_code == status.HTTP_200_OK
        conv_id = res1.data["conversation_id"]

        # Follow-up message on existing conversation
        res2 = api_client.post(
            url,
            {"question": "How many months?", "conversation_id": conv_id},
            format="json",
        )
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["conversation_id"] == conv_id

        # Check total messages in conversation
        messages = Message.objects.filter(conversation_id=conv_id)
        assert messages.count() == 4  # 2 user + 2 assistant

    def test_policy_retriever_scoping_and_cross_policy_isolation(self, user_a, user_b, policy_a):
        from apps.ai_engine.retrieval import PolicyRetriever

        retriever = PolicyRetriever(top_k=3, min_score=0.1)

        # Retrieval for owner succeeds
        results_a = retriever.retrieve(policy=policy_a, query="maternity waiting period", user=user_a)
        assert len(results_a) > 0
        for r in results_a:
            assert "chunk_id" in r
            assert "page_number" in r
            assert "score" in r

        # Retrieval for unauthorized user raises PermissionError
        with pytest.raises(PermissionError):
            retriever.retrieve(policy=policy_a, query="maternity", user=user_b)

        # Empty or whitespace query returns empty list
        assert retriever.retrieve(policy=policy_a, query="   ", user=user_a) == []
