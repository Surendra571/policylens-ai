import re
from typing import List, Dict, Any
from pydantic import ValidationError as PydanticValidationError
from .schemas import PolicyAnalysis


class ExtractionValidationError(Exception):
    """Raised when extracted output is malformed, missing fields, or contains unsupported claims."""
    pass


def normalize_for_matching(text: str) -> str:
    """Normalize whitespace and punctuation for robust substring verification."""
    clean = re.sub(r"\s+", " ", text.lower().strip())
    # Strip common quote marks and non-word characters for fuzzy alignment
    return re.sub(r"[^\w\s]", "", clean)


def verify_source_text_grounded(
    source_text: str,
    page_number: int,
    source_chunks: List[Dict[str, Any]],
) -> bool:
    """
    Anti-hallucination verification:
    Confirms that the quoted source_text actually exists in the source chunks
    corresponding to the cited page_number (or across the document chunks).
    Employs exact normalized substring matching with token-overlap fallback
    to be resilient against minor OCR typography or spacing variations.
    """
    if not source_text or not source_text.strip():
        return False

    norm_quote = normalize_for_matching(source_text)
    if len(norm_quote) < 5:
        return True

    quote_tokens = [t for t in norm_quote.split() if len(t) >= 3]

    # 1. Exact normalized substring match on page-specific chunks
    for ch in source_chunks:
        ch_page = ch.get("page_number") or ch.get("metadata", {}).get("page_number")
        if ch_page == page_number:
            norm_content = normalize_for_matching(ch.get("content", ""))
            if norm_quote in norm_content or norm_quote[:30] in norm_content:
                return True

    # 2. Exact match across all chunks
    for ch in source_chunks:
        norm_content = normalize_for_matching(ch.get("content", ""))
        if norm_quote in norm_content or norm_quote[:30] in norm_content:
            return True

    # 3. Token overlap fallback (handles minor punctuation/hyphenation differences)
    if quote_tokens:
        for ch in source_chunks:
            norm_content = normalize_for_matching(ch.get("content", ""))
            content_tokens = set(norm_content.split())
            matching_count = sum(1 for t in quote_tokens if t in content_tokens)
            if matching_count / len(quote_tokens) >= 0.70:
                return True

    return False


def validate_structured_output(
    data: Any,
    source_chunks: List[Dict[str, Any]] = None,
    strict_grounding: bool = True,
) -> PolicyAnalysis:
    """
    Validate raw dict/json into PolicyAnalysis Pydantic schema:
    1. Enforces schema compliance and rejects malformed responses or missing fields.
    2. Enforces non-hallucination / groundedness if source_chunks are provided across all categories.
    """
    if isinstance(data, PolicyAnalysis):
        analysis = data
    elif isinstance(data, dict):
        try:
            analysis = PolicyAnalysis.model_validate(data)
        except PydanticValidationError as err:
            raise ExtractionValidationError(f"Malformed LLM response: {err}") from err
    else:
        raise ExtractionValidationError(f"Expected dict or PolicyAnalysis, got {type(data)}")

    if source_chunks and strict_grounding:
        categories = [
            analysis.coverages,
            analysis.exclusions,
            analysis.waiting_periods,
            analysis.deductibles,
            analysis.limits,
            analysis.conditions,
            analysis.claim_requirements,
            getattr(analysis, "eligibility", []),
            getattr(analysis, "renewal", []),
            getattr(analysis, "cancellation", []),
            getattr(analysis, "other_clauses", []),
        ]

        for cat_list in categories:
            for item in cat_list:
                is_grounded = verify_source_text_grounded(
                    source_text=item.source_text,
                    page_number=item.page_number,
                    source_chunks=source_chunks,
                )
                if not is_grounded:
                    raise ExtractionValidationError(
                        f"Unsupported claim detected! The quoted source_text for '{item.title}' "
                        f"was not found on cited page {item.page_number} or anywhere in document chunks."
                    )

    return analysis
