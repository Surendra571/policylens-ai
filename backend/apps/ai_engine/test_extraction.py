import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.policies.models import Policy
from apps.documents.models import Document, DocumentPage, DocumentChunk
from apps.clauses.models import Clause
from apps.ai_engine.schemas import (
    PolicyAnalysis,
    ExclusionItem,
    Limit,
)
from apps.ai_engine.validators import validate_structured_output, ExtractionValidationError
from apps.ai_engine.llm_client import MockLLMClient, get_llm_client
from apps.ai_engine.extraction import extract_structured_policy

User = get_user_model()


class TestStructuredExtractionSchemasAndValidators:
    """Test suite for Pydantic schemas, validation, and anti-hallucination checks."""

    def setup_method(self):
        self.sample_chunks = [
            {
                "page_number": 3,
                "section": "Coverage",
                "content": "Inpatient hospitalization expenses are covered up to the Sum Insured.",
            },
            {
                "page_number": 7,
                "section": "Exclusions",
                "content": "Cosmetic, aesthetic, or plastic surgery of any kind is permanently excluded.",
            },
            {
                "page_number": 12,
                "section": "Waiting Periods",
                "content": "A waiting period of 24 months shall apply for all pre-existing diseases.",
            },
        ]

    def test_valid_structured_response_passes(self):
        """Valid structured output matching schema and supported by chunks passes validation."""
        data = {
            "coverages": [
                {
                    "title": "Inpatient Hospitalization",
                    "explanation": "Hospital stays are covered up to the maximum policy sum insured.",
                    "source_text": "Inpatient hospitalization expenses are covered up to the Sum Insured.",
                    "page_number": 3,
                    "section": "Coverage",
                    "confidence": 0.99,
                }
            ],
            "exclusions": [
                {
                    "title": "Cosmetic Surgery",
                    "explanation": "Cosmetic and plastic surgery procedures are not payable.",
                    "source_text": "Cosmetic, aesthetic, or plastic surgery of any kind is permanently excluded.",
                    "page_number": 7,
                    "section": "Exclusions",
                    "confidence": 1.0,
                }
            ],
            "waiting_periods": [
                {
                    "title": "Pre-Existing Disease Waiting Period",
                    "explanation": "Existing medical conditions are covered after 24 months.",
                    "source_text": "A waiting period of 24 months shall apply for all pre-existing diseases.",
                    "page_number": 12,
                    "section": "Waiting Periods",
                    "duration_months": 24,
                    "confidence": 0.98,
                }
            ],
        }

        result = validate_structured_output(data, source_chunks=self.sample_chunks)
        assert len(result.coverages) == 1
        assert len(result.exclusions) == 1
        assert len(result.waiting_periods) == 1
        assert result.coverages[0].page_number == 3
        assert result.waiting_periods[0].duration_months == 24

    def test_malformed_response_rejected(self):
        """Malformed input (not a dict or invalid types) is rejected."""
        with pytest.raises(ExtractionValidationError):
            validate_structured_output("Invalid raw text string")

        with pytest.raises(ExtractionValidationError):
            validate_structured_output({"coverages": "Not a list"})

    def test_missing_required_fields_rejected(self):
        """Extracted items missing required fields (e.g. source_text or page_number) fail validation."""
        # Missing source_text
        bad_data = {
            "coverages": [
                {
                    "title": "Hospitalization",
                    "explanation": "Covered.",
                    "page_number": 3,
                    # missing source_text
                }
            ]
        }
        with pytest.raises(ExtractionValidationError):
            validate_structured_output(bad_data, source_chunks=self.sample_chunks)

        # Invalid page number (< 1)
        bad_page = {
            "coverages": [
                {
                    "title": "Hospitalization",
                    "explanation": "Covered.",
                    "source_text": "Inpatient hospitalization expenses are covered up to the Sum Insured.",
                    "page_number": 0,  # invalid page
                }
            ]
        }
        with pytest.raises(ExtractionValidationError):
            validate_structured_output(bad_page, source_chunks=self.sample_chunks)

    def test_unsupported_claim_hallucination_rejected(self):
        """
        ANTI-HALLUCINATION TEST:
        If the model invents a clause whose source_text does not exist in the source chunks,
        it must be caught and rejected.
        """
        hallucinated_data = {
            "coverages": [
                {
                    "title": "Free Global Air Ambulance",
                    "explanation": "The policy provides free worldwide helicopter evacuations.",
                    "source_text": "Unlimited worldwide air ambulance provided at zero extra cost.",
                    "page_number": 3,
                    "section": "Coverage",
                    "confidence": 0.95,
                }
            ]
        }

        with pytest.raises(ExtractionValidationError) as excinfo:
            validate_structured_output(hallucinated_data, source_chunks=self.sample_chunks)

        assert "Unsupported claim detected" in str(excinfo.value)


@pytest.mark.django_db
class TestPolicyExtractionCoordinator:
    """Test suite for the end-to-end database-backed extraction workflow."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="analyst_user",
            email="analyst@policylens.ai",
            password="Password123!",
        )
        self.policy = Policy.objects.create(
            user=self.user,
            name="Optima Restore",
            provider="HDFC ERGO",
            status=Policy.Status.PENDING,
        )
        pdf = SimpleUploadedFile("optima.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.doc = Document.objects.create(
            policy=self.policy,
            file=pdf,
            original_filename="optima.pdf",
            processing_status=Document.ProcessingStatus.COMPLETED,
        )

        # Create Pages and Chunks
        self.page1 = DocumentPage.objects.create(
            document=self.doc,
            page_number=1,
            extracted_text="SECTION 1: COVERAGE\nDaily room rent is eligible up to Single Private AC Room.",
        )
        self.chunk1 = DocumentChunk.objects.create(
            document=self.doc,
            page=self.page1,
            chunk_index=0,
            content="SECTION 1: COVERAGE\nDaily room rent is eligible up to Single Private AC Room.",
            metadata={"page_number": 1, "section": "SECTION 1: COVERAGE"},
        )

        self.page2 = DocumentPage.objects.create(
            document=self.doc,
            page_number=2,
            extracted_text="SECTION 2: EXCLUSIONS\nObesity treatment or hormone replacement is not covered.",
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.doc,
            page=self.page2,
            chunk_index=1,
            content="SECTION 2: EXCLUSIONS\nObesity treatment or hormone replacement is not covered.",
            metadata={"page_number": 2, "section": "SECTION 2: EXCLUSIONS"},
        )

    def test_end_to_end_extraction_persists_clauses_and_updates_policy(self):
        """Verify extraction executes, populates Clause table, and updates policy status to ANALYZED."""
        mock_response = PolicyAnalysis(
            limits=[
                Limit(
                    title="Room Rent Limit",
                    explanation="Policy allows admission to Single Private AC rooms without financial capping.",
                    source_text="Daily room rent is eligible up to Single Private AC Room.",
                    page_number=1,
                    section="SECTION 1: COVERAGE",
                    limit_type="ROOM_RENT",
                    confidence=0.98,
                )
            ],
            exclusions=[
                ExclusionItem(
                    title="Obesity Treatment Exclusion",
                    explanation="Surgical and medical weight loss treatments are not payable.",
                    source_text="Obesity treatment or hormone replacement is not covered.",
                    page_number=2,
                    section="SECTION 2: EXCLUSIONS",
                    confidence=1.0,
                )
            ],
        )

        mock_client = MockLLMClient(mock_response=mock_response)
        result = extract_structured_policy(document_id=str(self.doc.id), llm_client=mock_client)

        assert len(result.limits) == 1
        assert len(result.exclusions) == 1

        # Verify Clauses created in PostgreSQL
        clauses = list(self.policy.clauses.order_by("page_number"))
        assert len(clauses) == 2

        # Check Limit Clause
        assert clauses[0].category == Clause.Category.LIMIT
        assert clauses[0].title == "Room Rent Limit"
        assert clauses[0].page_number == 1
        assert "Single Private AC Room" in clauses[0].source_text

        # Check Exclusion Clause
        assert clauses[1].category == Clause.Category.EXCLUSION
        assert clauses[1].title == "Obesity Treatment Exclusion"
        assert clauses[1].page_number == 2

        # Verify Policy status updated
        self.policy.refresh_from_db()
        assert self.policy.status in (Policy.Status.COMPLETED, Policy.Status.ANALYZED)
        assert self.policy.analyzed_at is not None

    def test_llm_factory_returns_mock_or_configured_client(self):
        """Test provider abstraction factory."""
        client = get_llm_client("mock")
        assert isinstance(client, MockLLMClient)
        generated = client.generate("Test prompt")
        assert len(generated) > 0
