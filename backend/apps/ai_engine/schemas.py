from pydantic import BaseModel, Field, field_validator


class BaseExtractedItem(BaseModel):
    """Base schema for all extracted insurance policy terms."""

    title: str = Field(..., min_length=1, description="Concise title for the clause or term")
    explanation: str = Field(..., min_length=1, description="Clear plain-language explanation")
    source_text: str = Field(..., min_length=1, description="Verbatim quote from original policy document")
    page_number: int = Field(..., ge=1, description="Exact 1-based page number where the text appears")
    section: str = Field(default="General", description="Policy section or heading title")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

    @field_validator("title", "explanation", "source_text")
    @classmethod
    def check_non_empty_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only.")
        return v.strip()


class CoverageItem(BaseExtractedItem):
    """Inpatient hospitalization, day care, road ambulance, organ donor expenses, etc."""


class ExclusionItem(BaseExtractedItem):
    """Standard exclusions, permanent exclusions, or un-covered conditions."""


class WaitingPeriod(BaseExtractedItem):
    """Initial waiting period (30 days), specific disease waiting period (24m), or pre-existing diseases (24-48m)."""

    duration_months: int | None = Field(default=None, description="Waiting duration in months if applicable")


class Deductible(BaseExtractedItem):
    """Co-payment percentage, voluntary/compulsory deductible amount."""

    amount_or_percentage: str | None = Field(default=None, description="e.g. 10% co-pay or Rs. 10,000 deductible")


class Limit(BaseExtractedItem):
    """Sub-limits on room rent, ICU charges, cataract surgery, modern treatments, etc."""

    limit_type: str | None = Field(default=None, description="e.g. ROOM_RENT, ICU, AYUSH")


class Condition(BaseExtractedItem):
    """General terms, renewal terms, cancellation policies, free-look period, disclosure norms."""


class ClaimRequirement(BaseExtractedItem):
    """Intimation timeline (e.g. 24 hours), document submission (e.g. 15-30 days), TPA details."""


class EligibilityItem(BaseExtractedItem):
    """Entry age, maximum renewal age, vehicle eligibility, family relationship rules."""


class RenewalItem(BaseExtractedItem):
    """Lifelong renewability, grace period, portability, migration rights."""


class CancellationItem(BaseExtractedItem):
    """Cancellation terms, free-look period, surrender conditions, premium refund grid."""


class OtherClauseItem(BaseExtractedItem):
    """Special endorsements, definitions, statutory notices, or unclassified valid policy terms."""


class PolicyMetadata(BaseModel):
    """High-level policy identification information."""

    provider: str | None = Field(
        default=None, description="Insurer name, e.g. Star Health, HDFC ERGO, ICICI Lombard, LIC"
    )
    policy_name: str | None = Field(
        default=None, description="Product / plan name, e.g. Optima Secure, Motor Comprehensive"
    )
    policy_type: str | None = Field(default=None, description="HEALTH, MOTOR, LIFE, TRAVEL, PROPERTY, etc.")
    policy_number: str | None = Field(default=None, description="Policy schedule number or certificate number")
    uin: str | None = Field(default=None, description="IRDAI Unique Identification Number or Policy Registration")
    sum_insured: str | None = Field(
        default=None, description="Primary Sum Insured / Sum Assured / IDV / Limit, e.g. ₹10,00,000"
    )
    premium: str | None = Field(default=None, description="Annual or total premium, e.g. ₹18,500")
    policy_period_start: str | None = Field(default=None, description="Coverage start date, e.g. 2026-04-01")
    policy_period_end: str | None = Field(default=None, description="Coverage end date, e.g. 2027-03-31")
    insured_name: str | None = Field(default=None, description="Name of policyholder or insured person")
    plan_name: str | None = Field(default=None, description="Specific plan tier or option, e.g. Gold / Platinum")
    deductible: str | None = Field(default=None, description="Compulsory or voluntary deductible")
    sum_insured_options: list[str] = Field(default_factory=list, description="Available sum insured tiers")


class PolicyAnalysis(BaseModel):
    """Comprehensive structured extraction result container for any valid insurance contract."""

    metadata: PolicyMetadata = Field(default_factory=PolicyMetadata)
    coverages: list[CoverageItem] = Field(default_factory=list)
    exclusions: list[ExclusionItem] = Field(default_factory=list)
    waiting_periods: list[WaitingPeriod] = Field(default_factory=list)
    deductibles: list[Deductible] = Field(default_factory=list)
    limits: list[Limit] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    claim_requirements: list[ClaimRequirement] = Field(default_factory=list)
    eligibility: list[EligibilityItem] = Field(default_factory=list)
    renewal: list[RenewalItem] = Field(default_factory=list)
    cancellation: list[CancellationItem] = Field(default_factory=list)
    other_clauses: list[OtherClauseItem] = Field(default_factory=list)
