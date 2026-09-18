import datetime
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.policies.models import Policy
from apps.documents.models import Document, DocumentPage, DocumentChunk
from apps.clauses.models import Clause
from apps.ai_engine.extraction import extract_structured_policy
from apps.policies.tasks import analyze_policy

User = get_user_model()

SAMPLE_HEALTH_INSURANCE_TEXT = """SYNTHETIC TEST DOCUMENT — NOT A REAL INSURANCE CONTRACT
Page 1
SYNTHETIC SAMPLE POLICY
SampleCare Health Protect
Provider: Demo Insurance Company Ltd. Type: Health Insurance
Policy Period
01-Apr-2026 to 31-Mar-2027
Sum Insured / Limit
I10,00,000
Premium
I18,500
Policy Number
DEMO-2026-01
1. Coverage
• In-patient hospitalization
• Day-care procedures
• Emergency ambulance up to I5,000 per hospitalization
• Pre- and post-hospitalization expenses for 30 and 60 days respectively
2. Exclusions
• Cosmetic surgery unless medically necessary after an accident
• Self-inflicted injury
• Routine dental treatment unless caused by an accident
3. Waiting Periods
• Pre-existing diseases: 24 months
• Specified procedures: 12 months
• Initial waiting period for illness: 30 days
4. Important Conditions
• Room rent is limited to I5,000 per day; proportionate deductions may apply.
• Cashless treatment is subject to network-hospital availability and authorization.
• Claim intimation should be made within 24 hours for emergencies and 48 hours for planned hospitalization.
5. Claim Documentation
• Claim form
• Hospital bills and discharge summary
• Diagnostic reports where applicable
• Valid identity and policy documents
Important: This is a synthetic document created for software development, OCR, document extraction, RAG, citation, and UI testing.
"""


@pytest.mark.django_db
class TestSampleHealthInsuranceRegression:
    """Regression test suite for 01_Health_Insurance_Sample.pdf pipeline extraction and API."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="test_policyholder",
            email="holder@policylens.ai",
            password="SecurePassword123!",
        )
        self.policy = Policy.objects.create(
            user=self.user,
            name="01 Health Insurance Sample",
            provider="Sample 01",
            policy_type=Policy.PolicyType.INDIVIDUAL,
            status=Policy.Status.PENDING,
        )
        pdf_file = SimpleUploadedFile(
            "01_Health_Insurance_Sample.pdf",
            b"%PDF-1.4 sample content",
            content_type="application/pdf",
        )
        self.document = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="01_Health_Insurance_Sample.pdf",
            processing_status=Document.ProcessingStatus.COMPLETED,
        )
        self.page = DocumentPage.objects.create(
            document=self.document,
            page_number=1,
            extracted_text=SAMPLE_HEALTH_INSURANCE_TEXT,
        )
        self.chunk = DocumentChunk.objects.create(
            document=self.document,
            page=self.page,
            chunk_index=0,
            content=SAMPLE_HEALTH_INSURANCE_TEXT,
            metadata={"page_number": 1, "section": "General"},
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sample_policy_pipeline_extraction(self):
        """Verify extraction parses metadata, all 5 clause categories, financial terms, and citations."""
        extract_structured_policy(document_id=str(self.document.id))

        self.policy.refresh_from_db()

        # 1. Verify Metadata
        assert self.policy.name == "SampleCare Health Protect"
        assert self.policy.provider == "Demo Insurance Company Ltd."
        assert self.policy.get_policy_type_display() == "Health Insurance"
        assert self.policy.sum_insured == "₹10,00,000"
        assert self.policy.premium == "₹18,500"
        assert self.policy.policy_period_start == datetime.date(2026, 4, 1)
        assert self.policy.policy_period_end == datetime.date(2027, 3, 31)
        assert self.policy.status == Policy.Status.COMPLETED

        # 2. Verify Clause Category Counts
        coverages = self.policy.clauses.filter(category=Clause.Category.COVERAGE)
        exclusions = self.policy.clauses.filter(category=Clause.Category.EXCLUSION)
        waiting_periods = self.policy.clauses.filter(category=Clause.Category.WAITING_PERIOD)
        conditions = self.policy.clauses.filter(category=Clause.Category.CONDITION)
        limits = self.policy.clauses.filter(category=Clause.Category.LIMIT)
        claims = self.policy.clauses.filter(category=Clause.Category.CLAIM_REQUIREMENT)

        assert coverages.count() == 4
        assert exclusions.count() == 3
        assert waiting_periods.count() == 3
        assert conditions.count() == 3
        assert limits.count() == 1  # Room rent limit
        assert claims.count() == 4

        # 3. Verify Verbatim Citations and Grounded Page Numbers
        all_clauses = list(self.policy.clauses.all())
        assert len(all_clauses) == 18
        for clause in all_clauses:
            assert clause.page_number == 1
            assert len(clause.source_text) > 0
            assert clause.confidence >= 0.9

        # 4. Check specific coverage item content
        cov_texts = [c.source_text for c in coverages]
        assert "In-patient hospitalization" in cov_texts
        assert "Day-care procedures" in cov_texts

    def test_sample_policy_analysis_api_endpoint(self):
        """Verify GET /api/v1/policies/{id}/analysis/ returns structured clauses and summary counts."""
        # Execute extraction first
        extract_structured_policy(document_id=str(self.document.id))

        response = self.client.get(f"/api/v1/policies/{self.policy.id}/analysis/")
        assert response.status_code == 200

        data = response.data
        assert data["status"] == "COMPLETED"
        assert data["analyzed"] is True

        # Check metadata in API response
        metadata = data["metadata"]
        assert metadata["name"] == "SampleCare Health Protect"
        assert metadata["provider"] == "Demo Insurance Company Ltd."
        assert metadata["sum_insured"] == "₹10,00,000"
        assert metadata["premium"] == "₹18,500"
        assert metadata["policy_period"]["start"] == "2026-04-01"
        assert metadata["policy_period"]["end"] == "2027-03-31"

        # Check summary counts
        summary = data["summary"]
        assert summary["total_coverages"] == 4
        assert summary["total_exclusions"] == 3
        assert summary["total_waiting_periods"] == 3
        assert summary["total_conditions"] == 3
        assert summary["total_limits"] == 1
        assert summary["total_claim_requirements"] == 4
        assert summary["total_clauses"] == 18

        # Check top-level conceptual fields
        assert data["policy_name"] == "SampleCare Health Protect"
        assert data["provider"] == "Demo Insurance Company Ltd."
        assert data["policy_type"] == "Health Insurance"
        assert data["sum_insured"] == "₹10,00,000"
        assert data["premium"] == "₹18,500"

    def test_analysis_fails_and_records_safe_error_on_empty_content(self):
        """Verify requirements 8 & 9: analysis marks FAILED and stores safe error if no clauses extract."""
        empty_policy = Policy.objects.create(
            user=self.user,
            name="Empty Policy",
            provider="Empty Insurer",
            status=Policy.Status.PENDING,
        )
        empty_doc = Document.objects.create(
            policy=empty_policy,
            file=SimpleUploadedFile("empty.pdf", b"test", content_type="application/pdf"),
            original_filename="empty.pdf",
            processing_status=Document.ProcessingStatus.COMPLETED,
        )
        # Empty page with no clauses
        page = DocumentPage.objects.create(
            document=empty_doc,
            page_number=1,
            extracted_text="This page contains only irrelevant header text with no clauses.",
        )
        DocumentChunk.objects.create(
            document=empty_doc,
            page=page,
            chunk_index=0,
            content="This page contains only irrelevant header text with no clauses.",
            metadata={"page_number": 1, "section": "General"},
        )

        res = analyze_policy(str(empty_policy.id))
        assert res["status"] == "FAILED"

        empty_policy.refresh_from_db()
        assert empty_policy.status == Policy.Status.FAILED
        assert len(empty_policy.error_message) > 0

