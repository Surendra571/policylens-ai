import uuid

from django.db import models
from pgvector.django import VectorField

from apps.policies.models import Policy


class Document(models.Model):
    """Document model representing an uploaded insurance policy PDF."""

    class ProcessingStatus(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        EXTRACTING = "EXTRACTING", "Extracting Text"
        OCR = "OCR", "OCR Processing"
        CHUNKING = "CHUNKING", "Chunking Document"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class DocumentQuality(models.TextChoices):
        TEXT_PDF = "TEXT_PDF", "Digital Text PDF"
        SCANNED_PDF = "SCANNED_PDF", "Scanned Image PDF"
        MIXED_PDF = "MIXED_PDF", "Mixed Text & Images"
        LOW_TEXT = "LOW_TEXT", "Low Text Density"
        OCR_REQUIRED = "OCR_REQUIRED", "OCR Required"
        UNREADABLE = "UNREADABLE", "Unreadable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    file = models.FileField(upload_to="policy_documents/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0, help_text="File size in bytes")
    file_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    page_count = models.PositiveIntegerField(default=0)
    processing_status = models.CharField(
        max_length=50,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
        db_index=True,
    )
    document_quality = models.CharField(
        max_length=50,
        choices=DocumentQuality.choices,
        default=DocumentQuality.TEXT_PDF,
        blank=True,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="", help_text="Safe error details if failed")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["policy", "processing_status"], name="doc_policy_status_idx"),
            models.Index(fields=["policy", "file_hash"], name="doc_policy_hash_idx"),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.get_processing_status_display()})"


class DocumentPage(models.Model):
    """DocumentPage model preserving page-by-page extracted content and provenance."""

    class ExtractionMethod(models.TextChoices):
        PYMUPDF = "PYMUPDF", "PyMuPDF Direct"
        OCR_TESSERACT = "OCR_TESSERACT", "Tesseract OCR"
        HYBRID = "HYBRID", "Hybrid Direct + OCR"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="pages",
        db_index=True,
    )
    page_number = models.PositiveIntegerField(db_index=True)
    raw_text = models.TextField(blank=True, default="", help_text="Raw uncleaned text extracted from page")
    cleaned_text = models.TextField(blank=True, default="", help_text="Normalized text preserving layout and structure")
    extracted_text = models.TextField(blank=True, default="", help_text="Extracted text (synced with cleaned_text)")
    extraction_method = models.CharField(
        max_length=50,
        choices=ExtractionMethod.choices,
        default=ExtractionMethod.PYMUPDF,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.cleaned_text and self.extracted_text:
            self.cleaned_text = self.extracted_text
        elif not self.extracted_text and self.cleaned_text:
            self.extracted_text = self.cleaned_text
        if not self.raw_text:
            self.raw_text = self.cleaned_text or self.extracted_text
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Document Page"
        verbose_name_plural = "Document Pages"
        ordering = ["document", "page_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "page_number"],
                name="unique_document_page_number",
            )
        ]
        indexes = [
            models.Index(fields=["document", "page_number"], name="docpage_doc_page_idx"),
        ]

    def __str__(self):
        return f"Page {self.page_number} of {self.document.original_filename}"


class DocumentChunk(models.Model):
    """DocumentChunk model storing chunked text and vector embeddings for RAG retrieval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_index=True,
    )
    page = models.ForeignKey(
        DocumentPage,
        on_delete=models.CASCADE,
        related_name="chunks",
        null=True,
        blank=True,
        db_index=True,
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    embedding = VectorField(dimensions=768, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk_index",
            )
        ]
        indexes = [
            models.Index(fields=["document", "page"], name="docchunk_doc_page_idx"),
        ]

    def __str__(self):
        return f"Chunk #{self.chunk_index} ({self.document.original_filename})"
