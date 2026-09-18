import pytest
from django.contrib.auth import get_user_model

from apps.ai_engine.citation_verifier import CitationVerifier
from apps.ai_engine.rag import PolicyRAGPipeline
from apps.documents.models import Document, DocumentChunk, DocumentPage
from apps.policies.models import Policy

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="cite_user",
        email="cite@policylens.ai",
        password="Password123!",
    )


@pytest.fixture
def policy_bundle(db, test_user):
    policy = Policy.objects.create(
        user=test_user,
        name="Star Comprehensive Health",
        provider="Star Health",
        policy_type=Policy.PolicyType.INDIVIDUAL,
    )
    doc = Document.objects.create(
        policy=policy,
        original_filename="star_health_policy.pdf",
        file_size=2048,
        file_hash="star_hash_123",
        processing_status=Document.ProcessingStatus.COMPLETED,
    )
    page_18 = DocumentPage.objects.create(
        document=doc,
        page_number=18,
        extracted_text="Pre-existing conditions have a waiting period of 36 months of continuous coverage.",
    )
    chunk_18 = DocumentChunk.objects.create(
        document=doc,
        page=page_18,
        chunk_index=0,
        content="Pre-existing conditions have a waiting period of 36 months of continuous coverage from inception.",
        metadata={"section": "Exclusions", "page_number": 18},
    )
    return policy, doc, page_18, chunk_18


@pytest.fixture
def foreign_policy_bundle(db, test_user):
    policy = Policy.objects.create(
        user=test_user,
        name="Other Insurer Plan",
        provider="Other Insurer",
        policy_type=Policy.PolicyType.INDIVIDUAL,
    )
    doc = Document.objects.create(
        policy=policy,
        original_filename="other_plan.pdf",
        file_size=1024,
        file_hash="other_hash_456",
        processing_status=Document.ProcessingStatus.COMPLETED,
    )
    page_5 = DocumentPage.objects.create(
        document=doc,
        page_number=5,
        extracted_text="Dental care is excluded under this policy.",
    )
    chunk_5 = DocumentChunk.objects.create(
        document=doc,
        page=page_5,
        chunk_index=0,
        content="Dental care is excluded under this policy.",
        metadata={"section": "Dental Exclusions", "page_number": 5},
    )
    return policy, doc, page_5, chunk_5


@pytest.mark.django_db
class TestCitationIntegrity:
    """Test suite validating strict citation verification, anti-fabrication, and source immutability."""

    def test_valid_citation_resolves_and_enriches_metadata(self, policy_bundle):
        policy, doc, _page_18, chunk_18 = policy_bundle

        raw_citation = {
            "chunk_id": str(chunk_18.id),
            "page": 18,
            "section": "Exclusions",
            "source_text": "Sample text",
        }

        verified = CitationVerifier.verify_and_enrich_citation(policy, raw_citation)
        assert verified is not None
        assert verified["page"] == 18
        assert verified["section"] == "Exclusions"
        # Must pull exact verbatim text from database, not raw_citation
        assert verified["source_text"] == chunk_18.content
        assert verified["policy"] == policy.name
        assert verified["document"] == doc.original_filename
        assert verified["verified"] is True

    def test_fabricated_page_number_rejected(self, policy_bundle):
        policy, _doc, _page_18, chunk_18 = policy_bundle

        # AI attempts to claim the clause is on fake page 99
        fabricated_citation = {
            "chunk_id": str(chunk_18.id),
            "page": 99,
            "section": "Exclusions",
        }

        verified = CitationVerifier.verify_and_enrich_citation(policy, fabricated_citation)
        # Fake page number must be rejected
        assert verified is None

    def test_cross_policy_citation_rejected(self, policy_bundle, foreign_policy_bundle):
        policy_a, _, _, _ = policy_bundle
        _policy_b, _, _, chunk_b = foreign_policy_bundle

        # Attempt to cite Policy B's chunk under Policy A
        cross_policy_citation = {
            "chunk_id": str(chunk_b.id),
            "page": 5,
            "section": "Dental Exclusions",
        }

        verified = CitationVerifier.verify_and_enrich_citation(policy_a, cross_policy_citation)
        assert verified is None

    def test_nonexistent_citation_rejected(self, policy_bundle):
        policy, _, _, _ = policy_bundle

        fake_citation = {
            "chunk_id": "00000000-0000-0000-0000-000000000000",
            "page": 42,
            "section": "Ghost Section",
        }

        verified = CitationVerifier.verify_and_enrich_citation(policy, fake_citation)
        assert verified is None

    def test_rag_pipeline_filters_unresolved_citations(self, policy_bundle):
        policy, doc, _page_18, chunk_18 = policy_bundle

        pipeline = PolicyRAGPipeline()
        res = pipeline.answer_question(
            policy=policy,
            question="What is the pre-existing conditions waiting period?",
        )

        assert res["confidence"] in ("high", "medium")
        assert len(res["citations"]) > 0
        for cite in res["citations"]:
            assert cite["page"] == 18
            assert cite["section"] == "Exclusions"
            assert cite["source_text"] == chunk_18.content
            assert cite["policy"] == policy.name
            assert cite["document"] == doc.original_filename
            assert cite["verified"] is True
