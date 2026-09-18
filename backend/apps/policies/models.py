import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Policy(models.Model):
    """Insurance Policy model representing an uploaded and analyzed policy."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        ANALYZING = "ANALYZING", "Analyzing"
        ANALYZED = "ANALYZED", "Analyzed"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class PolicyType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual Health"
        FAMILY_FLOATER = "FAMILY_FLOATER", "Family Floater"
        SENIOR_CITIZEN = "SENIOR_CITIZEN", "Senior Citizen"
        CRITICAL_ILLNESS = "CRITICAL_ILLNESS", "Critical Illness"
        TOP_UP = "TOP_UP", "Top-up / Super Top-up"
        GROUP = "GROUP", "Group Health Insurance"
        HEALTH = "HEALTH", "Health Insurance"
        LIFE = "LIFE", "Life Insurance"
        TERM_LIFE = "TERM_LIFE", "Term Life Insurance"
        MOTOR = "MOTOR", "Motor Insurance"
        CAR = "CAR", "Car Insurance"
        BIKE = "BIKE", "Two-Wheeler / Bike Insurance"
        TRAVEL = "TRAVEL", "Travel Insurance"
        HOME = "HOME", "Home Insurance"
        PROPERTY = "PROPERTY", "Property Insurance"
        PERSONAL_ACCIDENT = "PERSONAL_ACCIDENT", "Personal Accident Insurance"
        CORPORATE = "CORPORATE", "Corporate Insurance"
        COMMERCIAL = "COMMERCIAL", "Commercial / SME Insurance"
        OTHER = "OTHER", "Other Insurance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="policies",
        db_index=True,
    )
    name = models.CharField(max_length=255, help_text="Policy product name, e.g. Star Comprehensive")
    provider = models.CharField(
        max_length=255,
        help_text="Insurance company name, e.g. Star Health, HDFC ERGO, Care Health",
        db_index=True,
    )
    policy_type = models.CharField(
        max_length=50,
        choices=PolicyType.choices,
        default=PolicyType.INDIVIDUAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    sum_insured = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. ₹10,00,000")
    premium = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. ₹18,500")
    policy_period_start = models.DateField(null=True, blank=True)
    policy_period_end = models.DateField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="", help_text="Diagnostic failure message if analysis failed")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="policy_user_created_idx"),
            models.Index(fields=["provider", "policy_type"], name="policy_prov_type_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider}) - {self.get_status_display()}"

