import hashlib
import os
import re

from django.conf import settings
from rest_framework.exceptions import ValidationError

MAX_UPLOAD_SIZE_MB = getattr(settings, "MAX_UPLOAD_SIZE_MB", 20)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the uploaded filename to prevent directory traversal, path injection,
    and dangerous character encoding.
    """
    # Strip both forward and backward slashes to prevent cross-OS path traversal
    clean_name = filename.replace("\\", "/").split("/")[-1]
    # Remove null bytes and control characters
    clean_name = re.sub(r"[\x00-\x1f\x7f]", "", clean_name)
    # Remove leading dots to prevent hidden files or relative path traversal
    clean_name = re.sub(r"^\.+", "", clean_name)
    # Only allow safe alphanumeric, dots, underscores, and dashes
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)

    if not clean or clean.strip("_.") == "":
        clean = "policy_document.pdf"

    return clean[:200]


def calculate_sha256(file_obj) -> str:
    """Calculate SHA256 hex digest of the uploaded file while resetting seek position."""
    hasher = hashlib.sha256()
    file_obj.seek(0)
    for chunk in file_obj.chunks(chunk_size=65536):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


def validate_pdf_file(file_obj):
    """
    Strict validation of uploaded file:
    1. Size check against MAX_UPLOAD_SIZE_MB
    2. File extension must be .pdf
    3. Content type / MIME check must be application/pdf
    4. Magic bytes inspection: must begin with %PDF
    5. Security inspection: rejects dangerous PDF launch/executable actions
    """
    if file_obj.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(f"File size exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB.")

    if file_obj.size == 0:
        raise ValidationError("Uploaded file is empty.")

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext != ".pdf":
        raise ValidationError("Only PDF files (.pdf) are supported.")

    content_type = getattr(file_obj, "content_type", "")
    if content_type and content_type.lower() not in (
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
    ):
        raise ValidationError(f"Invalid MIME type '{content_type}'. Must be 'application/pdf'.")

    # Inspect magic header bytes
    file_obj.seek(0)
    header = file_obj.read(5)
    file_obj.seek(0)
    if not header.startswith(b"%PDF"):
        raise ValidationError("Invalid PDF file: Missing %PDF header signature.")

    # Inspect first 1MB for malicious executable launch tags
    sample_content = file_obj.read(min(file_obj.size, 1024 * 1024))
    file_obj.seek(0)
    if b"/Launch" in sample_content:
        raise ValidationError("Malicious or unsafe PDF: Executable launch action detected.")

    return True
