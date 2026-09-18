import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.policies.models import Policy
from apps.documents.models import Document, DocumentPage, DocumentChunk
from apps.clauses.models import Clause
from apps.ai_engine.schemas import (
    PolicyAnalysis,
    CoverageItem,
    ExclusionItem,
)
from apps.ai_engine.llm_client import MockLLMClient

User = get_user_model()


@pytest.mark.django_db
class TestPolicyAnalysisAPIs:
    """Test suite for Phase 9 Policy Analysis endpoints and Celery execution pipeline."""

    def setup_method(self):
        self.client_a = APIClient()
        self.client_b = APIClient()

        self.user_a = User.objects.create_user(
            username="analyst_alice",
            email="alice@policylens.ai",
            password="Password123!",
        )
        self.user_b = User.objects.create_user(
            username="analyst_bob",
            email="bob@policylens.ai",
            password="Password123!",
        )

        self.client_a.force_authenticate(user=self.user_a)
        self.client_b.force_authenticate(user=self.user_b)

        self.policy_a = Policy.objects.create(
            user=self.user_a,
            name="Optima Secure Plan",
            provider="HDFC ERGO",
            policy_type=Policy.PolicyType.INDIVIDUAL,
            status=Policy.Status.PENDING,
        )
        self.policy_b = Policy.objects.create(
            user=self.user_b,
            name="Star Health Premier",
            provider="Star Health",
            policy_type=Policy.PolicyType.FAMILY_FLOATER,
            status=Policy.Status.PENDING,
        )

        # Upload a test document for policy A
        pdf = SimpleUploadedFile("optima_policy.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        self.doc_a = Document.objects.create(
            policy=self.policy_a,
            file=pdf,
            original_filename="optima_policy.pdf",
            processing_status=Document.ProcessingStatus.COMPLETED,
        )

        # Add Document pages and chunks
        self.page1 = DocumentPage.objects.create(
            document=self.doc_a,
            page_number=1,
            extracted_text="SECTION 1: COVERAGE\nInpatient Hospitalization covers all medically necessary treatment.",
        )
        self.chunk1 = DocumentChunk.objects.create(
            document=self.doc_a,
            page=self.page1,
            chunk_index=0,
            content="SECTION 1: COVERAGE\nInpatient Hospitalization covers all medically necessary treatment.",
            metadata={"page_number": 1, "section": "SECTION 1: COVERAGE"},
        )

        self.page2 = DocumentPage.objects.create(
            document=self.doc_a,
            page_number=2,
            extracted_text="SECTION 2: EXCLUSIONS\nCosmetic surgery is permanently excluded from this policy.",
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.doc_a,
            page=self.page2,
            chunk_index=1,
            content="SECTION 2: EXCLUSIONS\nCosmetic surgery is permanently excluded from this policy.",
            metadata={"page_number": 2, "section": "SECTION 2: EXCLUSIONS"},
        )

    # 1. POST /api/v1/policies/{id}/analyze Tests
    @patch("apps.policies.tasks.analyze_policy_task.delay")
    def test_post_analyze_starts_async_task_and_sets_status(self, mock_task):
        """POST /analyze sets policy status to ANALYZING, dispatches Celery task, and returns 202."""
        response = self.client_a.post(f"/api/v1/policies/{self.policy_a.id}/analyze/")
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["success"] is True
        assert response.data["status"] == Policy.Status.ANALYZING
        assert response.data["policy_id"] == str(self.policy_a.id)

        self.policy_a.refresh_from_db()
        assert self.policy_a.status == Policy.Status.ANALYZING
        mock_task.assert_called_once_with(str(self.policy_a.id))

    def test_post_analyze_cross_user_forbidden(self):
        """IDOR Prevention: User A cannot trigger analysis on User B's policy (returns 404)."""
        response = self.client_a.post(f"/api/v1/policies/{self.policy_b.id}/analyze/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.policy_b.refresh_from_db()
        assert self.policy_b.status == Policy.Status.PENDING

    def test_post_analyze_without_document_fails_gracefully(self):
        """Calling analyze on a policy without documents returns 400."""
        empty_policy = Policy.objects.create(
            user=self.user_a,
            name="Empty Policy",
            provider="None",
            status=Policy.Status.PENDING,
        )
        response = self.client_a.post(f"/api/v1/policies/{empty_policy.id}/analyze/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "document" in response.data["error"].lower()

    # 2. GET /api/v1/policies/{id}/analysis Polling & Results Tests
    def test_get_analysis_polling_in_progress(self):
        """When policy status is ANALYZING, GET /analysis returns 200 with analyzed=False for polling."""
        self.policy_a.status = Policy.Status.ANALYZING
        self.policy_a.save(update_fields=["status"])

        response = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/analysis/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Policy.Status.ANALYZING
        assert response.data["analyzed"] is False
        assert response.data["analyzed_at"] is None

    def test_get_analysis_failed_status(self):
        """When policy status is FAILED, GET /analysis returns 200 with failed status."""
        self.policy_a.status = Policy.Status.FAILED
        self.policy_a.save(update_fields=["status"])

        response = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/analysis/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Policy.Status.FAILED
        assert response.data["analyzed"] is False

    def test_get_analysis_completed_returns_structured_payload(self):
        """When completed, GET /analysis returns full categorized analysis with preserved evidence."""
        # Create sample clauses representing different categories
        Clause.objects.create(
            policy=self.policy_a,
            category=Clause.Category.COVERAGE,
            title="Inpatient Hospitalization",
            explanation="Covers hospital stays exceeding 24 hours.",
            source_text="Inpatient Hospitalization covers all medically necessary treatment.",
            page_number=1,
            section="SECTION 1: COVERAGE",
            confidence=0.98,
        )
        Clause.objects.create(
            policy=self.policy_a,
            category=Clause.Category.EXCLUSION,
            title="Cosmetic Surgery Exclusion",
            explanation="Aesthetic and cosmetic surgeries are not covered.",
            source_text="Cosmetic surgery is permanently excluded from this policy.",
            page_number=2,
            section="SECTION 2: EXCLUSIONS",
            confidence=1.0,
        )
        Clause.objects.create(
            policy=self.policy_a,
            category=Clause.Category.LIMIT,
            title="Room Rent Sub-limit",
            explanation="Single Private AC Room without room rent capping.",
            source_text="Inpatient Hospitalization covers all medically necessary treatment.",
            page_number=1,
            section="SECTION 1: COVERAGE",
            confidence=0.95,
        )

        now = timezone.now()
        self.policy_a.status = Policy.Status.COMPLETED
        self.policy_a.analyzed_at = now
        self.policy_a.save(update_fields=["status", "analyzed_at"])

        response = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/analysis/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Policy.Status.COMPLETED
        assert response.data["analyzed"] is True
        assert response.data["analyzed_at"] is not None

        # Check metadata
        meta = response.data["metadata"]
        assert meta["name"] == "Optima Secure Plan"
        assert meta["provider"] == "HDFC ERGO"

        # Check summary
        summary = response.data["summary"]
        assert summary["total_clauses"] == 3
        assert summary["total_coverages"] == 1
        assert summary["total_exclusions"] == 1
        assert summary["total_limits"] == 1

        # Check categorised lists
        assert len(response.data["coverages"]) == 1
        assert len(response.data["exclusions"]) == 1
        assert len(response.data["limits"]) == 1

        # Check important points with evidence preservation
        important = response.data["important_points"]
        assert len(important) >= 1
        first_pt = important[0]
        assert "evidence" in first_pt
        assert first_pt["evidence"]["page_number"] in (1, 2)
        assert len(first_pt["evidence"]["source_text"]) > 0

    def test_get_analysis_cross_user_forbidden(self):
        """User A cannot access User B's policy analysis (returns 404)."""
        response = self.client_a.get(f"/api/v1/policies/{self.policy_b.id}/analysis/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # 3. GET /api/v1/policies/{id}/clauses Tests
    def test_get_clauses_endpoint_with_category_filter(self):
        """GET /clauses returns owner clauses and supports ?category= query filter."""
        Clause.objects.create(
            policy=self.policy_a,
            category=Clause.Category.COVERAGE,
            title="Day Care Treatments",
            explanation="Day care surgeries are covered.",
            source_text="Inpatient Hospitalization covers all medically necessary treatment.",
            page_number=1,
        )
        Clause.objects.create(
            policy=self.policy_a,
            category=Clause.Category.EXCLUSION,
            title="Self-Inflicted Injury",
            explanation="Intentional self-injury is not covered.",
            source_text="Cosmetic surgery is permanently excluded from this policy.",
            page_number=2,
        )

        # Get all clauses
        res_all = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/clauses/")
        assert res_all.status_code == status.HTTP_200_OK
        assert res_all.data["count"] == 2

        # Filter by EXCLUSION
        res_filtered = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/clauses/?category=EXCLUSION")
        assert res_filtered.status_code == status.HTTP_200_OK
        assert res_filtered.data["count"] == 1
        assert res_filtered.data["clauses"][0]["category"] == "EXCLUSION"
        assert res_filtered.data["clauses"][0]["title"] == "Self-Inflicted Injury"
        assert res_filtered.data["clauses"][0]["page_number"] == 2

    def test_get_clauses_cross_user_forbidden(self):
        """User A cannot access User B's clauses endpoint (returns 404)."""
        response = self.client_a.get(f"/api/v1/policies/{self.policy_b.id}/clauses/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # 4. Celery Async Task Execution Test
    def test_analyze_policy_task_execution(self):
        """Test analyze_policy Celery task executes end-to-end with Mock LLM client."""
        from apps.policies.tasks import analyze_policy

        mock_analysis = PolicyAnalysis(
            coverages=[
                CoverageItem(
                    title="Hospitalization Expense",
                    explanation="Inpatient stays covered up to sum insured.",
                    source_text="Inpatient Hospitalization covers all medically necessary treatment.",
                    page_number=1,
                    section="SECTION 1: COVERAGE",
                    confidence=0.99,
                )
            ],
            exclusions=[
                ExclusionItem(
                    title="Cosmetic Exclusions",
                    explanation="Cosmetic procedures not covered.",
                    source_text="Cosmetic surgery is permanently excluded from this policy.",
                    page_number=2,
                    section="SECTION 2: EXCLUSIONS",
                    confidence=1.0,
                )
            ],
        )

        with patch("apps.policies.tasks.get_llm_client", return_value=MockLLMClient(mock_response=mock_analysis)):
            result = analyze_policy(str(self.policy_a.id))

        assert result["status"] == "COMPLETED"
        assert result["clauses_count"] == 2

        self.policy_a.refresh_from_db()
        assert self.policy_a.status == Policy.Status.COMPLETED
        assert self.policy_a.analyzed_at is not None
        assert self.policy_a.clauses.count() == 2

