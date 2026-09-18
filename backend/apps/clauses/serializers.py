from rest_framework import serializers
from .models import Clause


class ClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clause
        fields = (
            "id",
            "policy",
            "category",
            "title",
            "explanation",
            "source_text",
            "page_number",
            "section",
            "confidence",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
