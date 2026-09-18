from rest_framework import serializers

from apps.clauses.serializers import ClauseSerializer
from apps.documents.serializers import DocumentSerializer

from .models import Policy


class PolicySerializer(serializers.ModelSerializer):
    """Serializer for insurance policies."""

    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "user",
            "name",
            "provider",
            "policy_type",
            "status",
            "sum_insured",
            "premium",
            "policy_period_start",
            "policy_period_end",
            "error_message",
            "documents",
            "uploaded_at",
            "analyzed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "uploaded_at", "created_at", "updated_at")


class PolicyMetadataSerializer(serializers.Serializer):
    """Metadata summary representation for policy."""

    policy_id = serializers.UUIDField(source="id")
    name = serializers.CharField()
    provider = serializers.CharField()
    policy_type = serializers.CharField()
    sum_insured = serializers.CharField(allow_null=True, required=False)
    premium = serializers.CharField(allow_null=True, required=False)
    policy_period_start = serializers.DateField(allow_null=True, required=False)
    policy_period_end = serializers.DateField(allow_null=True, required=False)
    uploaded_at = serializers.DateTimeField()
    analyzed_at = serializers.DateTimeField(allow_null=True)


class ImportantPointSerializer(serializers.Serializer):
    """Important highlight with grounded document evidence."""

    category = serializers.CharField()
    title = serializers.CharField()
    explanation = serializers.CharField()
    evidence = serializers.DictField()


class PolicyAnalysisSummaryResponseSerializer(serializers.Serializer):
    """Full structured policy analysis payload returned to frontend."""

    status = serializers.CharField()
    analyzed = serializers.BooleanField()
    analyzed_at = serializers.DateTimeField(allow_null=True)
    metadata = PolicyMetadataSerializer()
    summary = serializers.DictField()
    coverages = ClauseSerializer(many=True)
    exclusions = ClauseSerializer(many=True)
    waiting_periods = ClauseSerializer(many=True)
    deductibles = ClauseSerializer(many=True)
    limits = ClauseSerializer(many=True)
    conditions = ClauseSerializer(many=True)
    claim_requirements = ClauseSerializer(many=True)
    eligibility = ClauseSerializer(many=True, required=False)
    renewal = ClauseSerializer(many=True, required=False)
    cancellation = ClauseSerializer(many=True, required=False)
    other_clauses = ClauseSerializer(many=True, required=False)
    important_points = ImportantPointSerializer(many=True)
