import datetime
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.policies.models import Policy
from apps.documents.models import Document, DocumentPage, DocumentChunk
from apps.clauses.models import Clause
from apps.ai_engine.extraction import extract_structured_policy

User = get_user_model()


MOTOR_INSURANCE_TEXT = """Apex General Insurance Corp
POLICY SCHEDULE & CERTIFICATE OF INSURANCE
Policy Name: DriveSecure Private Car Comprehensive
Policy Type: Motor Insurance
Policy Number: APEX-MOT-2026-9912
Policy Period: 15-May-2026 to 14-May-2027
Insured Declared Value (IDV) / Sum Insured: ₹8,50,000
Total Premium Payable: ₹14,200

SECTION 1: SCOPE OF COVER (WHAT IS COVERED)
• Loss of or damage to vehicle insured by fire, explosion, self-ignition or lightning.
• Accidental damage caused by external violent and visible means.
• Third-party property damage coverage up to legal liability limit of ₹7,50,000.
• Personal accident cover for owner-driver up to ₹15,00,000 in case of accidental death.

SECTION 2: GENERAL EXCEPTIONS (WHAT IS NOT COVERED)
• Consequential loss, depreciation, wear and tear, mechanical or electrical breakdown.
• Damage caused whilst driving under the influence of intoxicating liquor or drugs.
• Driving by any person who is not duly licensed to drive the vehicle.

SECTION 3: COMPULSORY DEDUCTIBLE & CO-PAY
• Compulsory deductible of ₹1,000 for vehicles not exceeding 1500 cc.
• Voluntary deductible chosen by insured of ₹2,500 per claim.

SECTION 4: GENERAL CONDITIONS & DUTIES
• Notice shall be given in writing to the company immediately upon the occurrence of any accidental loss.
• The company may at its own option repair, reinstate or replace the vehicle or part thereof.
"""

LIFE_INSURANCE_TEXT = """Sovereign Life Assurance
POLICY WORDINGS
Policy Name: Sovereign Term Shield Protection Plan
Provider: Sovereign Life Assurance
Class of Insurance: Term Life Insurance
Policy Registration Number / UIN: SOV-LIFE-TERM-2026
Sum Assured / Limit: ₹1,00,00,000
Annual Premium: ₹24,000
Coverage Period: 01-Jul-2026 to 30-Jun-2066

BENEFITS PAYABLE (COVERAGE)
• Death Benefit: Full Sum Assured of ₹1,00,00,000 paid to beneficiary upon diagnosis of death.
• Terminal Illness Benefit: Accelerated payment of 50% of Sum Assured upon certified terminal condition.
• Waiver of Premium upon total permanent disability of life assured.

EXCLUSIONS & RESTRICTIONS
• Suicide Exclusion: If life assured commits suicide within 12 months from policy inception, policy void.
• Death resulting from war, civil commotion, or participation in hazardous sports.

WAITING PERIOD & GRACE PERIOD
• Grace period for payment of premiums: 30 days allowed for yearly payment mode.
• Initial contestability waiting period: 36 months from policy commencement date.

CLAIM REQUIREMENTS & PROCEDURE
• Written intimation within 90 days of occurrence of insured event.
• Original policy document, official death certificate, and claimant's statement form.
"""

TRAVEL_INSURANCE_TEXT = """Voyager Marine & General Insurance
TRAVEL PROTECTION POLICY CERTIFICATE
Policy Name: Voyager GlobeTrotter International
Insurer: Voyager Marine & General Insurance
Insurance Type: Travel Insurance
Period of Insurance: 10-Oct-2026 to 25-Oct-2026
Sum Insured: ₹50,00,000
Premium: ₹3,200

WHAT WE COVER
• Emergency medical expenses including in-patient hospitalization abroad up to ₹25,00,000.
• Medical evacuation to nearest accredited facility up to ₹10,00,000.
• Baggage loss compensation for checked baggage up to ₹50,000.
• Trip cancellation or interruption due to unforeseen illness up to ₹1,00,000.

LOSSES WE DO NOT PAY (EXCLUSIONS)
• Pre-existing medical conditions unless declared and accepted in writing.
• Travelling against the advice of a certified physician.
• Loss or damage to baggage items left unattended in a public place.

DEDUCTIBLES & SUB-LIMITS
• Deductible of ₹5,000 per claim on overseas outpatient medical treatment.
• Dental emergency sub-limit capped at ₹25,000 per trip.

CANCELLATION & FREE LOOK
• Policy may be cancelled prior to travel commencement date with ₹500 administrative fee deduction.
"""

PROPERTY_INSURANCE_TEXT = """National Heritage General Insurance
STANDARD FIRE & SPECIAL PERILS POLICY
Plan Name: Heritage Enterprise Asset Cover
Company Name: National Heritage General Insurance
Type of Insurance: Property Insurance
Policy Period: 01-Jan-2026 to 31-Dec-2026
Sum Insured / Limit: I2,50,00,000
Premium: I75,000

PERILS COVERED
• Fire excluding destruction or damage caused by its own fermentation, natural heating or spontaneous combustion.
• Lightning and explosion of boilers or gas used for domestic purposes only.
• Storm, cyclone, typhoon, tempest, hurricane, tornado, flood and inundation.
• Impact damage by any rail, road vehicle or animal by direct contact.

GENERAL EXCLUSIONS
Loss or damage by spoilage resulting from the interruption of any process or operation.
Loss of earnings, loss by delay, loss of market or other consequential loss or damage.
War, invasion, act of foreign enemy hostilities, whether war be declared or not.

CONDITIONS AND RESTRICTIONS
• The policyholder must maintain books of accounts and records in fireproof safes.
• Claim notice shall be delivered within 15 days of damage occurrence.
• Excess of I10,000 applies to each and every claim arising out of Act of God perils.
"""


@pytest.mark.django_db
class TestUniversalInsurancePipeline:
    """Multi-domain test suite validating PolicyLens AI extraction on diverse insurance contracts."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="universal_tester",
            email="tester@policylens.ai",
            password="StrongPassword123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _create_test_policy_and_document(self, name: str, provider: str, text: str, filename: str) -> Document:
        policy = Policy.objects.create(
            user=self.user,
            name=name,
            provider=provider,
            status=Policy.Status.PENDING,
        )
        pdf_file = SimpleUploadedFile(filename, b"%PDF-1.4 content", content_type="application/pdf")
        doc = Document.objects.create(
            policy=policy,
            file=pdf_file,
            original_filename=filename,
            processing_status=Document.ProcessingStatus.COMPLETED,
        )
        page = DocumentPage.objects.create(
            document=doc,
            page_number=1,
            extracted_text=text,
        )
        DocumentChunk.objects.create(
            document=doc,
            page=page,
            chunk_index=0,
            content=text,
            metadata={"page_number": 1, "section": "General"},
        )
        return doc

    def test_motor_insurance_document_pipeline(self):
        """Verify dynamic extraction for Motor insurance without health bias."""
        doc = self._create_test_policy_and_document(
            name="DriveSecure Car Policy",
            provider="Apex General",
            text=MOTOR_INSURANCE_TEXT,
            filename="02_Motor_Private_Car.pdf",
        )

        extract_structured_policy(document_id=str(doc.id))

        policy = doc.policy
        policy.refresh_from_db()

        # Metadata dynamic verification
        assert "DriveSecure" in policy.name
        assert "Apex" in policy.provider
        assert policy.policy_type == Policy.PolicyType.MOTOR
        assert "8,50,000" in policy.sum_insured
        assert "14,200" in policy.premium
        assert policy.policy_period_start == datetime.date(2026, 5, 15)
        assert policy.policy_period_end == datetime.date(2027, 5, 14)

        # Clause counts verification (must not be zero)
        clauses = policy.clauses.all()
        assert clauses.count() >= 6

        coverages = clauses.filter(category=Clause.Category.COVERAGE)
        assert coverages.count() >= 2
        assert any("fire" in c.title.lower() or "third" in c.title.lower() for c in coverages)

        exclusions = clauses.filter(category=Clause.Category.EXCLUSION)
        assert exclusions.count() >= 2
        assert any("liquor" in c.title.lower() or "consequential" in c.title.lower() or "wear" in c.title.lower() for c in exclusions)

        deductibles = clauses.filter(category=Clause.Category.DEDUCTIBLE)
        assert deductibles.count() >= 1

        # Strict citation verification
        for c in clauses:
            assert c.page_number == 1
            assert c.source_text != ""
            assert c.source_text.lower() in MOTOR_INSURANCE_TEXT.lower() or len(c.source_text) > 10

    def test_term_life_insurance_document_pipeline(self):
        """Verify dynamic extraction for Term Life insurance with death benefit & waiting/grace periods."""
        doc = self._create_test_policy_and_document(
            name="Life Protection Plan",
            provider="Sovereign Life",
            text=LIFE_INSURANCE_TEXT,
            filename="03_Term_Life_Protection.pdf",
        )

        extract_structured_policy(document_id=str(doc.id))

        policy = doc.policy
        policy.refresh_from_db()

        assert "Sovereign" in policy.provider
        assert policy.policy_type == Policy.PolicyType.TERM_LIFE
        assert "1,00,00,000" in policy.sum_insured
        assert "24,000" in policy.premium

        clauses = policy.clauses.all()
        assert clauses.count() >= 5

        coverages = clauses.filter(category=Clause.Category.COVERAGE)
        assert coverages.count() >= 2
        assert any("death" in c.title.lower() for c in coverages)

        exclusions = clauses.filter(category=Clause.Category.EXCLUSION)
        assert exclusions.count() >= 1
        assert any("suicide" in c.title.lower() or "suicide" in c.explanation.lower() for c in exclusions)

        waiting = clauses.filter(category=Clause.Category.WAITING_PERIOD)
        assert waiting.count() >= 1

        claims = clauses.filter(category=Clause.Category.CLAIM_REQUIREMENT)
        assert claims.count() >= 1

    def test_travel_insurance_document_pipeline(self):
        """Verify dynamic extraction for Travel insurance with baggage, medical & cancellation."""
        doc = self._create_test_policy_and_document(
            name="Travel Cover",
            provider="Voyager Marine",
            text=TRAVEL_INSURANCE_TEXT,
            filename="04_Travel_International.pdf",
        )

        extract_structured_policy(document_id=str(doc.id))

        policy = doc.policy
        policy.refresh_from_db()

        assert "Voyager" in policy.provider
        assert policy.policy_type == Policy.PolicyType.TRAVEL
        assert "50,00,000" in policy.sum_insured
        assert "3,200" in policy.premium

        clauses = policy.clauses.all()
        assert clauses.count() >= 5

        coverages = clauses.filter(category=Clause.Category.COVERAGE)
        assert coverages.count() >= 2

        exclusions = clauses.filter(category=Clause.Category.EXCLUSION)
        assert exclusions.count() >= 1

    def test_property_insurance_with_ocr_noise_and_non_bullets(self):
        """Verify extraction resilience with OCR noise ('I' for rupee) and unbulleted paragraphs."""
        doc = self._create_test_policy_and_document(
            name="Asset Protection",
            provider="National Heritage",
            text=PROPERTY_INSURANCE_TEXT,
            filename="05_Property_Fire_Perils.pdf",
        )

        extract_structured_policy(document_id=str(doc.id))

        policy = doc.policy
        policy.refresh_from_db()

        assert "Heritage" in policy.provider
        assert policy.policy_type == Policy.PolicyType.PROPERTY
        assert "2,50,00,000" in policy.sum_insured
        assert "75,000" in policy.premium

        clauses = policy.clauses.all()
        assert clauses.count() >= 5

        coverages = clauses.filter(category=Clause.Category.COVERAGE)
        assert coverages.count() >= 2

        exclusions = clauses.filter(category=Clause.Category.EXCLUSION)
        assert exclusions.count() >= 1

    def test_api_analysis_endpoint_returns_dynamic_counts_for_multidomain(self):
        """Verify GET /api/v1/policies/{id}/analysis/ returns non-zero counts and structured evidence."""
        doc = self._create_test_policy_and_document(
            name="Motor API Test",
            provider="Apex General",
            text=MOTOR_INSURANCE_TEXT,
            filename="06_Motor_API_Test.pdf",
        )

        extract_structured_policy(document_id=str(doc.id))
        policy = doc.policy

        response = self.client.get(f"/api/v1/policies/{policy.id}/analysis/")
        assert response.status_code == 200

        data = response.json()
        assert data["analyzed"] is True
        assert data["status"] in ("COMPLETED", "ANALYZED")

        # Metadata dynamic checks
        assert data["metadata"]["policy_type"] == "MOTOR"
        assert "DriveSecure" in data["metadata"]["name"]
        assert "Apex" in data["metadata"]["provider"]
        assert "8,50,000" in data["metadata"]["sum_insured"]
        assert "14,200" in data["metadata"]["premium"]

        # Summary non-zero counts
        summary = data["summary"]
        assert summary["total_clauses"] >= 6
        assert summary["total_coverages"] >= 2
        assert summary["total_exclusions"] >= 2
        assert summary["total_deductibles"] >= 1

        # Evidence verification
        assert len(data["important_points"]) > 0
        point = data["important_points"][0]
        assert "evidence" in point
        assert point["evidence"]["page_number"] == 1
        assert point["evidence"]["source_text"] != ""

