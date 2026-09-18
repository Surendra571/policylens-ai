import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.chat.models import Conversation, Message
from apps.clauses.models import Clause
from apps.documents.models import Document, DocumentChunk, DocumentPage
from apps.policies.models import Policy

User = get_user_model()


@pytest.mark.django_db
class TestDatabaseArchitecture:
    """Comprehensive test suite for Phase 2 database architecture."""

    def test_user_creation(self):
        """Test custom user creation with UUID and email username."""
        user = User.objects.create_user(
            username="testuser",
            email="test@policylens.ai",
            password="securepassword123",
        )
        assert user.id is not None
        assert str(user) == "test@policylens.ai"
        assert user.check_password("securepassword123")
        assert user.created_at is not None

    def test_policy_relationships_and_status(self):
        """Test policy model and its association with User."""
        user = User.objects.create_user(
            username="policyholder",
            email="holder@example.com",
            password="pass",
        )
        policy = Policy.objects.create(
            user=user,
            name="Optima Secure",
            provider="HDFC ERGO",
            policy_type=Policy.PolicyType.FAMILY_FLOATER,
            status=Policy.Status.PENDING,
        )
        assert policy.id is not None
        assert policy.user == user
        assert user.policies.count() == 1
        assert "Optima Secure" in str(policy)

    def test_document_and_page_hierarchy(self):
        """Test Document -> DocumentPage -> DocumentChunk hierarchy."""
        user = User.objects.create_user(
            username="docuser",
            email="docuser@example.com",
            password="pass",
        )
        policy = Policy.objects.create(
            user=user,
            name="Star Comprehensive",
            provider="Star Health",
        )
        pdf_file = SimpleUploadedFile("policy.pdf", b"%PDF-1.4 test policy", content_type="application/pdf")
        doc = Document.objects.create(
            policy=policy,
            file=pdf_file,
            original_filename="star_comprehensive.pdf",
            file_size=1024,
            page_count=10,
            processing_status=Document.ProcessingStatus.PENDING,
        )
        assert doc.policy == policy
        assert policy.documents.count() == 1

        # Create Document Page
        page1 = DocumentPage.objects.create(
            document=doc,
            page_number=1,
            extracted_text="Policy terms and conditions for Star Health.",
            extraction_method=DocumentPage.ExtractionMethod.PYMUPDF,
        )
        assert page1.document == doc
        assert doc.pages.count() == 1

        # Check unique constraint on (document, page_number)
        with transaction.atomic(), pytest.raises(IntegrityError):
            DocumentPage.objects.create(
                document=doc,
                page_number=1,
                extracted_text="Duplicate page 1",
            )

        # Create Document Chunk
        chunk = DocumentChunk.objects.create(
            document=doc,
            page=page1,
            chunk_index=0,
            content="Policy terms intro section",
            embedding=[0.05] * 768,
            metadata={"source": "header", "tokens": 5},
        )
        assert chunk.document == doc
        assert chunk.page == page1
        assert doc.chunks.count() == 1
        assert page1.chunks.count() == 1

        # Check unique constraint on (document, chunk_index)
        with transaction.atomic(), pytest.raises(IntegrityError):
            DocumentChunk.objects.create(
                document=doc,
                page=page1,
                chunk_index=0,
                content="Duplicate chunk index",
            )

    def test_clause_categories_and_citations(self):
        """Test Clause creation across various Indian insurance categories."""
        user = User.objects.create_user(
            username="clauseuser",
            email="clause@example.com",
            password="pass",
        )
        policy = Policy.objects.create(
            user=user,
            name="Care Supreme",
            provider="Care Health",
        )

        clause_categories = [
            Clause.Category.COVERAGE,
            Clause.Category.EXCLUSION,
            Clause.Category.WAITING_PERIOD,
            Clause.Category.DEDUCTIBLE,
            Clause.Category.LIMIT,
            Clause.Category.CONDITION,
            Clause.Category.CLAIM_REQUIREMENT,
            Clause.Category.OTHER,
        ]

        for cat in clause_categories:
            clause = Clause.objects.create(
                policy=policy,
                category=cat,
                title=f"{cat} clause title",
                explanation=f"Explanation for {cat}",
                source_text="Verbatim quote from section 3.1",
                page_number=4,
                section="Section 3: Benefits",
                confidence=0.98,
            )
            assert clause.category == cat

        assert policy.clauses.count() == len(clause_categories)

    def test_conversation_and_message_provenance(self):
        """Test Conversation and Message chat history with citations."""
        user = User.objects.create_user(
            username="chatuser",
            email="chat@example.com",
            password="pass",
        )
        policy = Policy.objects.create(
            user=user,
            name="Niva Bupa ReAssure 2.0",
            provider="Niva Bupa",
        )
        conv = Conversation.objects.create(user=user, policy=policy, title="Room rent query")
        assert conv.user == user
        assert conv.policy == policy

        user_msg = Message.objects.create(
            conversation=conv,
            role=Message.Role.USER,
            content="Is there a room rent capping on single private room?",
        )
        bot_msg = Message.objects.create(
            conversation=conv,
            role=Message.Role.ASSISTANT,
            content="No, ReAssure 2.0 covers single private room without capping as per clause 4.2.",
            citations=[{"page_number": 6, "quote": "Room rent: No sub-limit on single private AC room."}],
        )

        assert conv.messages.count() == 2
        assert user_msg.role == Message.Role.USER
        assert bot_msg.role == Message.Role.ASSISTANT
        assert len(bot_msg.citations) == 1
        assert bot_msg.citations[0]["page_number"] == 6

    def test_cascade_deletions(self):
        """Verify cascade deletion integrity across policy and related child entities."""
        user = User.objects.create_user(
            username="cascadeuser",
            email="cascade@example.com",
            password="pass",
        )
        policy = Policy.objects.create(
            user=user,
            name="Test Policy",
            provider="Provider",
        )
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF content", content_type="application/pdf")
        doc = Document.objects.create(policy=policy, file=pdf, original_filename="doc.pdf")
        page = DocumentPage.objects.create(document=doc, page_number=1, extracted_text="test")
        DocumentChunk.objects.create(document=doc, page=page, chunk_index=0, content="test chunk")
        Clause.objects.create(policy=policy, title="Clause 1", category=Clause.Category.COVERAGE)
        conv = Conversation.objects.create(user=user, policy=policy)
        Message.objects.create(conversation=conv, content="hello")

        policy.delete()
        assert Document.objects.count() == 0
        assert DocumentPage.objects.count() == 0
        assert DocumentChunk.objects.count() == 0
        assert Clause.objects.count() == 0
        assert Conversation.objects.count() == 0
        assert Message.objects.count() == 0
        assert User.objects.filter(id=user.id).exists()
