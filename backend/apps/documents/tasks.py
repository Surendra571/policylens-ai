import logging
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import Document, DocumentPage, DocumentChunk
from .processors.pdf_extractor import extract_pages_from_pdf
from .processors.chunker import PolicyAwareChunker

logger = logging.getLogger(__name__)

TRANSIENT_TASK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


@shared_task(
    bind=True,
    name="apps.documents.tasks.extract_document_pages",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def extract_document_pages(self, document_id: str):
    """
    Extract text from PDF pages using PyMuPDF (with OCR fallback for scanned pages).
    Idempotent: removes existing pages before creating new ones.
    """
    doc = Document.objects.get(id=document_id)
    doc.processing_status = Document.ProcessingStatus.EXTRACTING
    doc.save(update_fields=["processing_status", "updated_at"])
    logger.info(f"Extracting pages for Document ID: {document_id}")

    with doc.file.open("rb") as f:
        file_bytes = f.read()

    extracted_result = extract_pages_from_pdf(file_bytes)
    if isinstance(extracted_result, tuple):
        pages_data, doc_quality = extracted_result
    else:
        pages_data = extracted_result
        doc_quality = Document.DocumentQuality.TEXT_PDF

    if doc_quality == Document.DocumentQuality.UNREADABLE or not pages_data:
        doc.processing_status = Document.ProcessingStatus.FAILED
        doc.document_quality = doc_quality
        doc.error_message = "We couldn't reliably read this document. Please upload a clearer PDF."
        doc.save(update_fields=["processing_status", "document_quality", "error_message", "updated_at"])
        raise ValueError("We couldn't reliably read this document. Please upload a clearer PDF.")

    with transaction.atomic():
        doc.pages.all().delete()

        page_objs = []
        for p in pages_data:
            page_objs.append(
                DocumentPage(
                    document=doc,
                    page_number=p["page_number"],
                    raw_text=p.get("raw_text", p.get("extracted_text", "")),
                    cleaned_text=p.get("cleaned_text", p.get("extracted_text", "")),
                    extracted_text=p.get("cleaned_text", p.get("extracted_text", "")),
                    extraction_method=p["extraction_method"],
                )
            )
        DocumentPage.objects.bulk_create(page_objs)

        doc.page_count = len(pages_data)
        doc.document_quality = doc_quality
        doc.save(update_fields=["page_count", "document_quality", "updated_at"])

    logger.info(f"Document ID {document_id}: Successfully extracted {len(page_objs)} pages (Quality: {doc_quality}).")
    return len(page_objs)


@shared_task(
    bind=True,
    name="apps.documents.tasks.process_ocr",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    max_retries=2,
)
def process_ocr(self, document_id: str):
    """Secondary OCR task to refine pages if needed."""
    doc = Document.objects.get(id=document_id)
    doc.processing_status = Document.ProcessingStatus.OCR
    doc.save(update_fields=["processing_status", "updated_at"])
    logger.info(f"Running OCR task for Document ID: {document_id}")
    return True


@shared_task(
    bind=True,
    name="apps.documents.tasks.create_chunks",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def create_chunks(
    self,
    document_id: str,
    max_chunk_size: int = None,
    chunk_overlap: int = None,
):
    """
    Create DocumentChunk records using PolicyAwareChunker.
    Preserves:
    - Page boundaries
    - Section boundaries
    - Headings and clause relationships
    - Metadata schema: document_id, page_number, section, chunk_index
    Idempotent: clears existing chunks for the document before re-chunking.
    """
    doc = Document.objects.get(id=document_id)
    doc.processing_status = Document.ProcessingStatus.CHUNKING
    doc.save(update_fields=["processing_status", "updated_at"])
    logger.info(f"Chunking Document ID: {document_id}")

    pages = list(doc.pages.order_by("page_number"))
    page_map = {p.page_number: p for p in pages}

    chunk_size = max_chunk_size or getattr(settings, "POLICY_CHUNK_SIZE", 1000)
    overlap = chunk_overlap or getattr(settings, "POLICY_CHUNK_OVERLAP", 150)

    chunker = PolicyAwareChunker(max_chunk_size=chunk_size, chunk_overlap=overlap)
    chunks_data = chunker.chunk_document(document_id=str(doc.id), pages=pages)

    chunk_objs = []
    with transaction.atomic():
        doc.chunks.all().delete()

        for ch in chunks_data:
            p_num = ch["metadata"]["page_number"]
            page_obj = page_map.get(p_num)
            chunk_objs.append(
                DocumentChunk(
                    document=doc,
                    page=page_obj,
                    chunk_index=ch["metadata"]["chunk_index"],
                    content=ch["content"],
                    metadata=ch["metadata"],
                    embedding=None,  # Populated asynchronously in generate_chunk_embeddings
                )
            )

        if chunk_objs:
            DocumentChunk.objects.bulk_create(chunk_objs)

    logger.info(f"Document ID {document_id}: Generated {len(chunk_objs)} policy-aware chunks.")
    return len(chunk_objs)


@shared_task(
    bind=True,
    name="apps.documents.tasks.generate_chunk_embeddings",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def generate_chunk_embeddings(self, document_id: str, force: bool = False):
    """
    Asynchronously generates and saves vector embeddings for chunks of a document.
    Requirements:
    1. Generates embedding for every valid chunk.
    2. Stores vector on DocumentChunk (768 dimensions).
    3. Preserves metadata (page_number, section, chunk_index).
    4. Idempotent: skips chunks that already have valid embeddings unless force=True.
    5. Batches embedding calls where appropriate.
    6. Does not log sensitive policy contents.
    """
    doc = Document.objects.get(id=document_id)
    chunks_qs = doc.chunks.all().order_by("chunk_index")

    if not force:
        chunks_to_embed = [c for c in chunks_qs if c.embedding is None]
    else:
        chunks_to_embed = list(chunks_qs)

    if not chunks_to_embed:
        logger.info(f"Document ID {document_id}: All chunks already embedded. Skipping.")
        return 0

    from apps.ai_engine.embeddings import EmbeddingService

    embedding_service = EmbeddingService(dimension=768)
    batch_size = 32
    embedded_count = 0

    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i : i + batch_size]
        texts = [chunk.content for chunk in batch]

        try:
            vectors = embedding_service.get_embeddings(texts)
            with transaction.atomic():
                for chunk_obj, vec in zip(batch, vectors):
                    chunk_obj.embedding = vec
                    chunk_obj.save(update_fields=["embedding", "updated_at"])
                embedded_count += len(batch)
        except Exception as exc:
            logger.error(
                f"Embedding generation failed for batch of document {document_id}: {exc.__class__.__name__}"
            )
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    logger.info(
        f"Document ID {document_id}: Successfully generated embeddings for {embedded_count} chunks."
    )
    return embedded_count


@shared_task(
    bind=True,
    name="apps.documents.tasks.process_document",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def process_document(self, document_id: str):
    """
    Coordinator task orchestrating the complete ingestion pipeline:
    Extract Pages -> Chunk -> Generate Embeddings -> Completed.
    """
    logger.info(f"Initiating document processing workflow for ID: {document_id}")
    try:
        doc = Document.objects.get(id=document_id)
        doc.processing_status = Document.ProcessingStatus.PROCESSING
        doc.error_message = ""
        doc.save(update_fields=["processing_status", "error_message", "updated_at"])

        extract_document_pages(document_id)
        create_chunks(document_id)
        generate_chunk_embeddings(document_id)

        doc.refresh_from_db()
        doc.processing_status = Document.ProcessingStatus.COMPLETED
        doc.error_message = ""
        doc.save(update_fields=["processing_status", "error_message", "updated_at"])

        return {"status": "success", "document_id": document_id}

    except Exception as exc:
        safe_error = f"{exc.__class__.__name__}: {str(exc)}"
        logger.error(f"Processing failed for Document ID {document_id}: {safe_error}")
        try:
            doc = Document.objects.get(id=document_id)
            doc.processing_status = Document.ProcessingStatus.FAILED
            doc.error_message = safe_error[:500]
            doc.save(update_fields=["processing_status", "error_message", "updated_at"])
        except Exception:
            pass
        return {"status": "failed", "document_id": document_id, "error": safe_error}


process_document_task = process_document
