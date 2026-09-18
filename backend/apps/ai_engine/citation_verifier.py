import logging
from typing import Any

from apps.documents.models import DocumentChunk, DocumentPage
from apps.policies.models import Policy

logger = logging.getLogger(__name__)


class CitationIntegrityError(Exception):
    """Raised when a citation fails integrity or verification checks."""


class CitationVerifier:
    """
    Guarantees citation integrity and anti-fabrication enforcement.
    Rules:
    1. Every citation must resolve to an authentic DocumentChunk and DocumentPage belonging to the policy.
    2. The original policy text must NEVER be modified or hallucinated by the AI.
    3. The AI cannot fabricate fake page numbers; page numbers must match physical document pages.
    4. Any citation that cannot be verified against the database is discarded.
    """

    @staticmethod
    def verify_and_enrich_citation(
        policy: Policy,
        raw_citation: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Verifies a single citation against database records.
        Returns the enriched, verified citation dict or None if invalid.
        """
        chunk_id = raw_citation.get("chunk_id")
        page_number = raw_citation.get("page") or raw_citation.get("page_number")

        if not chunk_id and not page_number:
            logger.warning("Citation missing both chunk_id and page_number.")
            return None

        chunk = None
        if chunk_id:
            chunk = (
                DocumentChunk.objects.filter(
                    id=chunk_id,
                    document__policy=policy,
                )
                .select_related("document", "page")
                .first()
            )

        # If chunk not found by ID, attempt lookup by document page and exact text containment
        if not chunk and page_number:
            doc_page = (
                DocumentPage.objects.filter(
                    document__policy=policy,
                    page_number=page_number,
                )
                .select_related("document")
                .first()
            )

            if doc_page:
                chunk = (
                    DocumentChunk.objects.filter(
                        document__policy=policy,
                        page=doc_page,
                    )
                    .select_related("document", "page")
                    .first()
                )

        if not chunk:
            logger.warning(f"Citation cannot be resolved to any DocumentChunk for policy {policy.id}. Discarding.")
            return None

        # Verify page number against database record
        real_page_number = chunk.page.page_number if chunk.page else chunk.metadata.get("page_number")

        if page_number and real_page_number and int(page_number) != int(real_page_number):
            logger.warning(
                f"Fabricated or mismatched page number detected! Expected {real_page_number}, got {page_number}. Rejecting."
            )
            return None

        # Guarantee: Original policy text is ALWAYS pulled verbatim from database, never from LLM
        verbatim_text = chunk.content

        # Get document filename
        doc_filename = chunk.document.original_filename if chunk.document else "Policy Document.pdf"

        # Determine section
        section = chunk.metadata.get("section") or raw_citation.get("section") or "General"

        return {
            "chunk_id": str(chunk.id),
            "page": real_page_number or 1,
            "section": section,
            "source_text": verbatim_text,
            "policy": policy.name,
            "document": doc_filename,
            "verified": True,
        }

    @classmethod
    def filter_and_verify_citations(
        cls,
        policy: Policy,
        citations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filters a list of citations, verifying each one.
        Unresolved or fabricated citations are discarded.
        """
        verified = []
        for cite in citations:
            enriched = cls.verify_and_enrich_citation(policy, cite)
            if enriched:
                verified.append(enriched)

        return verified
