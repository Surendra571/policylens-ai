from django.contrib import admin
from .models import Document, DocumentPage, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "policy", "file_size", "page_count", "processing_status", "created_at")
    list_filter = ("processing_status",)
    search_fields = ("original_filename", "policy__name", "policy__provider")
    date_hierarchy = "created_at"


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ("page_number", "document", "extraction_method", "created_at")
    list_filter = ("extraction_method",)
    search_fields = ("document__original_filename", "extracted_text")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("chunk_index", "document", "page", "created_at")
    search_fields = ("document__original_filename", "content")

