import re
import logging
from typing import List, Dict, Any
from django.db import connection
from apps.documents.models import DocumentChunk
from apps.policies.models import Policy
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "up", "about", "into", "over", "after", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "can", "could", "will", "would", "should", "this", "that", "these",
    "those", "what", "which", "who", "whom", "how", "when", "where", "why",
}


class PolicyRetriever:
    """
    Retrieval service strictly scoped to a specific policy and user.
    Enforces tenant isolation: retrieval NEVER queries across another user's policies.
    On PostgreSQL: executes database-side pgvector similarity search (CosineDistance).
    On SQLite / Unit Tests: seamlessly falls back to Python in-memory cosine ranking.
    """

    def __init__(self, top_k: int = 5, min_score: float = 0.2):
        self.top_k = top_k
        self.min_score = min_score
        self.embedding_service = EmbeddingService(dimension=768)

    def retrieve(self, policy: Policy, query: str, user=None) -> List[Dict[str, Any]]:
        """
        Retrieve top relevant chunks for a policy.
        Enforces user ownership validation prior to retrieval.
        """
        if user and policy.user != user:
            raise PermissionError("User is not authorized to retrieve from this policy.")

        if not query or not query.strip():
            return []

        # Scope strictly to chunks belonging to this specific policy
        chunks_qs = DocumentChunk.objects.filter(
            document__policy=policy
        ).select_related("document", "page")

        if not chunks_qs.exists():
            return []

        query_vec = self.embedding_service.get_embedding(query)
        is_postgres = connection.vendor == "postgresql"

        # 1. PostgreSQL pgvector native similarity retrieval
        if is_postgres:
            try:
                from pgvector.django import CosineDistance

                # Only evaluate chunks with valid embeddings
                vector_chunks = (
                    DocumentChunk.objects.filter(
                        document__policy=policy,
                        embedding__isnull=False,
                    )
                    .select_related("document", "page")
                    .annotate(distance=CosineDistance("embedding", query_vec))
                    .order_by("distance")[: self.top_k]
                )

                results = []
                for chunk in vector_chunks:
                    # Distance is 1 - cosine_similarity (range 0 to 2)
                    sim_score = max(0.0, 1.0 - float(chunk.distance))
                    if sim_score >= self.min_score:
                        page_num = (
                            chunk.page.page_number
                            if chunk.page
                            else chunk.metadata.get("page_number", 1)
                        )
                        section = chunk.metadata.get("section", "General")
                        results.append({
                            "chunk_id": str(chunk.id),
                            "page_number": page_num,
                            "section": section,
                            "source_text": chunk.content,
                            "score": round(sim_score, 4),
                        })

                if results:
                    return results

            except Exception as pg_err:
                logger.warning(
                    f"pgvector query failed, falling back to hybrid scoring: {pg_err}"
                )

        # 2. Hybrid keyword + vector scoring fallback (SQLite and test suite compatibility)
        query_words = [w for w in re.findall(r"\b\w+\b", query.lower()) if w not in STOP_WORDS]
        if not query_words:
            query_words = re.findall(r"\b\w+\b", query.lower())

        scored_chunks = []
        for chunk in chunks_qs:
            content_words = set(re.findall(r"\b\w+\b", chunk.content.lower()))
            matched_terms = [w for w in query_words if w in content_words]
            term_score = len(matched_terms) / max(len(query_words), 1)

            vec_score = 0.0
            if chunk.embedding:
                try:
                    vec_score = sum(a * b for a, b in zip(query_vec, chunk.embedding))
                except Exception:
                    vec_score = 0.0

            total_score = (term_score * 0.7) + (vec_score * 0.3)

            # Require non-trivial term match
            if term_score >= 0.2 and total_score >= self.min_score:
                page_num = (
                    chunk.page.page_number
                    if chunk.page
                    else chunk.metadata.get("page_number", 1)
                )
                section = chunk.metadata.get("section", "General")
                scored_chunks.append({
                    "chunk_id": str(chunk.id),
                    "page_number": page_num,
                    "section": section,
                    "source_text": chunk.content,
                    "score": round(total_score, 4),
                })

        # Rank by score descending
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[: self.top_k]
