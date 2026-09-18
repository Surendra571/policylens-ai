from unittest.mock import patch
import fitz
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.policies.models import Policy
from apps.documents.models import Document, DocumentPage
from apps.documents.processors.cleaner import clean_extracted_text
from apps.documents.processors.ocr import is_ocr_needed
from apps.documents.processors.chunker import chunk_page_text
from apps.documents.tasks import (
    process_document,
    extract_document_pages,
    create_chunks,
    generate_chunk_embeddings,
)

User = get_user_model()


def generate_test_pdf(pages_text: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with specified text per page using PyMuPDF."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest.mark.django_db
class TestDocumentProcessingPipeline:
    """Test suite for Phase 5: PDF extraction, OCR fallback, cleaning, and chunking."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="pipelinetester",
            email="tester@policylens.ai",
            password="Password123!",
        )
        self.policy = Policy.objects.create(
            user=self.user,
            name="Care Health Advantage",
            provider="Care Health",
        )

    def test_clean_extracted_text_normalization(self):
        """Verify text cleaner fixes hyphenation, multiple spaces, and non-printable noise."""
        raw = "The pa-\ntient was admit-\nted.\x00\x07  Multiple   spaces\n\n\n\nParagraph two."
        cleaned = clean_extracted_text(raw)
        assert "patient" in cleaned
        assert "admitted" in cleaned
        assert "\x00" not in cleaned
        assert "\n\n\n\n" not in cleaned
        assert "Paragraph two." in cleaned

    def test_is_ocr_needed_detection(self):
        """Ensure pages with minimal or no text trigger OCR fallback."""
        assert is_ocr_needed("") is True
        assert is_ocr_needed("123") is True
        assert is_ocr_needed("This is a standard page with plenty of legible insurance policy clauses.") is False

    def test_text_pdf_extraction_and_page_numbering(self):
        """Verify exact page-by-page extraction preserving 1-based page numbers."""
        page1_content = "Clause 1.1: Health coverage begins 30 days after policy inception."
        page2_content = "Clause 1.2: Waiting period for pre-existing disease is 24 months."
        pdf_bytes = generate_test_pdf([page1_content, page2_content])

        pdf_file = SimpleUploadedFile("policy.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="policy.pdf",
            file_size=len(pdf_bytes),
        )

        extract_document_pages(str(doc.id))

        doc.refresh_from_db()
        assert doc.page_count == 2
        assert doc.pages.count() == 2

        pages = list(doc.pages.order_by("page_number"))
        assert pages[0].page_number == 1
        assert "Clause 1.1" in pages[0].extracted_text
        assert pages[0].extraction_method == DocumentPage.ExtractionMethod.PYMUPDF

        assert pages[1].page_number == 2
        assert "Clause 1.2" in pages[1].extracted_text
        assert pages[1].extraction_method == DocumentPage.ExtractionMethod.PYMUPDF

    def test_empty_page_handling(self):
        """Verify pipeline gracefully handles pages with no text content."""
        pdf_bytes = generate_test_pdf(["Page 1 has text", "", "Page 3 has text"])
        pdf_file = SimpleUploadedFile("empty_page_test.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="empty_page_test.pdf",
            file_size=len(pdf_bytes),
        )

        extract_document_pages(str(doc.id))

        doc.refresh_from_db()
        assert doc.page_count == 3
        pages = list(doc.pages.order_by("page_number"))
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[1].extracted_text == ""  # empty page handled safely
        assert pages[2].page_number == 3

    @patch("apps.documents.processors.pdf_extractor.extract_text_via_ocr")
    def test_scanned_pdf_ocr_fallback(self, mock_ocr):
        """Verify OCR fallback triggers when page has minimal direct text."""
        mock_ocr.return_value = "Extracted via Tesseract OCR for scanned policy document."

        # Page with 5 chars (less than min_ocr_chars 40)
        pdf_bytes = generate_test_pdf(["Scan"])
        pdf_file = SimpleUploadedFile("scanned.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="scanned.pdf",
            file_size=len(pdf_bytes),
        )

        extract_document_pages(str(doc.id))

        mock_ocr.assert_called_once()
        page = doc.pages.first()
        assert "Tesseract OCR" in page.extracted_text
        assert page.extraction_method in (
            DocumentPage.ExtractionMethod.OCR_TESSERACT,
            DocumentPage.ExtractionMethod.HYBRID,
        )

    def test_chunk_creation_and_provenance(self):
        """Verify chunk creation guarantees that chunks strictly map to their originating page."""
        text = "Paragraph 1: Hospitalization benefit.\n\nParagraph 2: Day care procedures.\n\nParagraph 3: AYUSH benefit."
        chunks = chunk_page_text(page_number=4, text=text, chunk_size=100)

        assert len(chunks) >= 2
        for ch in chunks:
            assert ch["page_number"] == 4
            assert ch["metadata"]["page_number"] == 4
            assert len(ch["content"]) > 0

    def test_complete_process_document_workflow(self):
        """Test end-to-end coordinator task: UPLOADED -> EXTRACTING -> CHUNKING -> COMPLETED."""
        pdf_bytes = generate_test_pdf([
            "Section 1: Inpatient Care.\nRoom rent capped at 1% of sum insured.",
            "Section 2: Pre and post hospitalization covered up to 60 and 90 days respectively.",
        ])
        pdf_file = SimpleUploadedFile("complete_test.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="complete_test.pdf",
            file_size=len(pdf_bytes),
            processing_status=Document.ProcessingStatus.UPLOADED,
        )

        result = process_document(str(doc.id))
        assert result["status"] == "success"

        doc.refresh_from_db()
        assert doc.processing_status == Document.ProcessingStatus.COMPLETED
        assert doc.page_count == 2
        assert doc.pages.count() == 2
        assert doc.chunks.count() >= 2

        # Check chunk integrity and embeddings
        first_chunk = doc.chunks.first()
        assert first_chunk.page.page_number == 1
        assert first_chunk.metadata["page_number"] == 1
        assert first_chunk.chunk_index == 0
        assert first_chunk.embedding is not None
        assert len(first_chunk.embedding) == 768

    def test_idempotency_allows_safe_retry(self):
        """Running process_document multiple times should not duplicate pages or chunks."""
        pdf_bytes = generate_test_pdf(["Page 1 text", "Page 2 text"])
        pdf_file = SimpleUploadedFile("retry_test.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="retry_test.pdf",
            file_size=len(pdf_bytes),
        )

        # First run
        process_document(str(doc.id))
        doc.refresh_from_db()
        initial_pages = doc.pages.count()
        initial_chunks = doc.chunks.count()

        # Second run (retry)
        process_document(str(doc.id))
        doc.refresh_from_db()
        assert doc.pages.count() == initial_pages
        assert doc.chunks.count() == initial_chunks
        assert doc.processing_status == Document.ProcessingStatus.COMPLETED

    def test_failure_handling_and_safe_error_storage(self):
        """Corrupt or missing files set status to FAILED and store safe error details without crashing."""
        # Create a document pointing to a broken / non-PDF content
        bad_file = SimpleUploadedFile("corrupt.pdf", b"Not a PDF file at all", content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=bad_file,
            original_filename="corrupt.pdf",
            file_size=20,
        )

        result = process_document(str(doc.id))
        assert result["status"] == "failed"

        doc.refresh_from_db()
        assert doc.processing_status == Document.ProcessingStatus.FAILED
        assert len(doc.error_message) > 0
        # Verify document content itself is not dumped in error message
        assert "Not a PDF file at all" not in doc.error_message

    def test_generate_chunk_embeddings_skips_existing_unless_forced(self):
        """Embedding generation is idempotent and skips already-embedded chunks."""
        pdf_bytes = generate_test_pdf(["Section on waiting periods."])
        pdf_file = SimpleUploadedFile("emb_test.pdf", pdf_bytes, content_type="application/pdf")
        doc = Document.objects.create(
            policy=self.policy,
            file=pdf_file,
            original_filename="emb_test.pdf",
            file_size=len(pdf_bytes),
        )
        extract_document_pages(str(doc.id))
        create_chunks(str(doc.id))


        # First call generates embeddings
        count1 = generate_chunk_embeddings(str(doc.id))
        assert count1 > 0

        # Second call skips existing chunks
        count2 = generate_chunk_embeddings(str(doc.id), force=False)
        assert count2 == 0

        # Forced call regenerates embeddings
        count3 = generate_chunk_embeddings(str(doc.id), force=True)
        assert count3 == count1
