from rest_framework import serializers

from .models import Document, DocumentChunk, DocumentPage
from .validators import validate_pdf_file


class DocumentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentPage
        fields = ("id", "document", "page_number", "extracted_text", "extraction_method", "created_at")
        read_only_fields = ("id", "created_at")


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ("id", "document", "page", "chunk_index", "content", "metadata", "created_at")
        read_only_fields = ("id", "created_at")


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id",
            "policy",
            "file",
            "original_filename",
            "file_size",
            "file_hash",
            "page_count",
            "processing_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "file_hash", "created_at", "updated_at")


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        validate_pdf_file(value)
        return value
