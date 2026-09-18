from typing import List, Optional
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
    pass


class ExclusionItem(BaseExtractedItem):
    """Standard exclusions, permanent exclusions, or un-covered conditions."""
    pass


class WaitingPeriod(BaseExtractedItem):
    """Initial waiting period (30 days), specific disease waiting period (24m), or pre-existing diseases (24-48m)."""
    duration_months: Optional[int] = Field(default=None, description="Waiting duration in months if applicable")


class Deductible(BaseExtractedItem):
    """Co-payment percentage, voluntary/compulsory deductible amount."""
    amount_or_percentage: Optional[str] = Field(default=None, description="e.g. 10% co-pay or Rs. 10,000 deductible")


class Limit(BaseExtractedItem):
    """Sub-limits on room rent, ICU charges, cataract surgery, modern treatments, etc."""
    limit_type: Optional[str] = Field(default=None, description="e.g. ROOM_RENT, ICU, AYUSH")


class Condition(BaseExtractedItem):
    """General terms, renewal terms, cancellation policies, free-look period, disclosure norms."""
    pass


class ClaimRequirement(BaseExtractedItem):
    """Intimation timeline (e.g. 24 hours), document submission (e.g. 15-30 days), TPA details."""
    pass


class EligibilityItem(BaseExtractedItem):
    """Entry age, maximum renewal age, vehicle eligibility, family relationship rules."""
    pass


class RenewalItem(BaseExtractedItem):
    """Lifelong renewability, grace period, portability, migration rights."""
    pass


class CancellationItem(BaseExtractedItem):
    """Cancellation terms, free-look period, surrender conditions, premium refund grid."""
    pass


class OtherClauseItem(BaseExtractedItem):
    """Special endorsements, definitions, statutory notices, or unclassified valid policy terms."""
    pass


class PolicyMetadata(BaseModel):
    """High-level policy identification information."""
    provider: Optional[str] = Field(default=None, description="Insurer name, e.g. Star Health, HDFC ERGO, ICICI Lombard, LIC")
    policy_name: Optional[str] = Field(default=None, description="Product / plan name, e.g. Optima Secure, Motor Comprehensive")
    policy_type: Optional[str] = Field(default=None, description="HEALTH, MOTOR, LIFE, TRAVEL, PROPERTY, etc.")
    policy_number: Optional[str] = Field(default=None, description="Policy schedule number or certificate number")
    uin: Optional[str] = Field(default=None, description="IRDAI Unique Identification Number or Policy Registration")
    sum_insured: Optional[str] = Field(default=None, description="Primary Sum Insured / Sum Assured / IDV / Limit, e.g. ₹10,00,000")
    premium: Optional[str] = Field(default=None, description="Annual or total premium, e.g. ₹18,500")
    policy_period_start: Optional[str] = Field(default=None, description="Coverage start date, e.g. 2026-04-01")
    policy_period_end: Optional[str] = Field(default=None, description="Coverage end date, e.g. 2027-03-31")
    insured_name: Optional[str] = Field(default=None, description="Name of policyholder or insured person")
    plan_name: Optional[str] = Field(default=None, description="Specific plan tier or option, e.g. Gold / Platinum")
    deductible: Optional[str] = Field(default=None, description="Compulsory or voluntary deductible")
    sum_insured_options: List[str] = Field(default_factory=list, description="Available sum insured tiers")


class PolicyAnalysis(BaseModel):
    """Comprehensive structured extraction result container for any valid insurance contract."""
    metadata: PolicyMetadata = Field(default_factory=PolicyMetadata)
    coverages: List[CoverageItem] = Field(default_factory=list)
    exclusions: List[ExclusionItem] = Field(default_factory=list)
    waiting_periods: List[WaitingPeriod] = Field(default_factory=list)
    deductibles: List[Deductible] = Field(default_factory=list)
    limits: List[Limit] = Field(default_factory=list)
    conditions: List[Condition] = Field(default_factory=list)
    claim_requirements: List[ClaimRequirement] = Field(default_factory=list)
    eligibility: List[EligibilityItem] = Field(default_factory=list)
    renewal: List[RenewalItem] = Field(default_factory=list)
    cancellation: List[CancellationItem] = Field(default_factory=list)
    other_clauses: List[OtherClauseItem] = Field(default_factory=list)
