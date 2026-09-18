import uuid
from django.db import models
from apps.policies.models import Policy


class Clause(models.Model):
    """Clause model representing an extracted, categorized, and simplified policy term."""

    class Category(models.TextChoices):
        COVERAGE = "COVERAGE", "Coverage"
        EXCLUSION = "EXCLUSION", "Exclusion"
        WAITING_PERIOD = "WAITING_PERIOD", "Waiting Period"
        DEDUCTIBLE = "DEDUCTIBLE", "Deductible / Co-pay"
        LIMIT = "LIMIT", "Sub-limit / Capping"
        CONDITION = "CONDITION", "Condition"
        CLAIM_REQUIREMENT = "CLAIM_REQUIREMENT", "Claim Requirement"
        ELIGIBILITY = "ELIGIBILITY", "Eligibility"
        PREMIUM = "PREMIUM", "Premium"
        SUM_INSURED = "SUM_INSURED", "Sum Insured / Limit of Liability"
        POLICY_PERIOD = "POLICY_PERIOD", "Policy Period / Term"
        RENEWAL = "RENEWAL", "Renewal"
        CANCELLATION = "CANCELLATION", "Cancellation"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="clauses",
        db_index=True,
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    title = models.CharField(max_length=255, help_text="Short descriptor, e.g. Pre-existing disease waiting period")
    explanation = models.TextField(help_text="Simple plain-language summary for consumers")
    source_text = models.TextField(help_text="Verbatim quote from original policy document")
    page_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Page number where the clause appears in the PDF",
    )
    section = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Policy section or heading title, e.g. Section 4.1",
    )
    confidence = models.FloatField(
        default=1.0,
        help_text="Extraction confidence score between 0.0 and 1.0",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clause"
        verbose_name_plural = "Clauses"
        ordering = ["policy", "category", "page_number"]
        indexes = [
            models.Index(fields=["policy", "category"], name="clause_policy_cat_idx"),
            models.Index(fields=["policy", "page_number"], name="clause_policy_page_idx"),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title} (p. {self.page_number or 'N/A'})"

