import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.clauses.models import Clause
from apps.documents.models import Document
from apps.policies.models import Policy

from .llm_client import BaseLLMClient, get_llm_client
from .prompts import build_extraction_prompt
from .schemas import PolicyAnalysis
from .validators import ExtractionValidationError, validate_structured_output

logger = logging.getLogger(__name__)


def _normalize_policy_type(raw_type: str | None) -> str:
    if not raw_type:
        return Policy.PolicyType.OTHER
    t = raw_type.upper().replace("-", "_").replace(" ", "_")
    valid_choices = [c[0] for c in Policy.PolicyType.choices]
    if t in valid_choices:
        return t
    if "TERM" in t:
        return Policy.PolicyType.TERM_LIFE
    if "LIFE" in t:
        return Policy.PolicyType.LIFE
    if "MOTOR" in t or "AUTO" in t or "VEHICLE" in t:
        return Policy.PolicyType.MOTOR
    if "CAR" in t or "FOUR_WHEELER" in t:
        return Policy.PolicyType.CAR
    if "BIKE" in t or "TWO_WHEELER" in t or "SCOOTER" in t:
        return Policy.PolicyType.BIKE
    if "TRAVEL" in t or "TRIP" in t:
        return Policy.PolicyType.TRAVEL
    if "HOME" in t:
        return Policy.PolicyType.HOME
    if "PROPERTY" in t or "FIRE" in t or "BURGLARY" in t:
        return Policy.PolicyType.PROPERTY
    if "ACCIDENT" in t:
        return Policy.PolicyType.PERSONAL_ACCIDENT
    if "CORPORATE" in t or "COMMERCIAL" in t or "SME" in t:
        return Policy.PolicyType.COMMERCIAL
    if "FAMILY" in t or "FLOATER" in t:
        return Policy.PolicyType.FAMILY_FLOATER
    if "SENIOR" in t:
        return Policy.PolicyType.SENIOR_CITIZEN
    if "CRITICAL" in t:
        return Policy.PolicyType.CRITICAL_ILLNESS
    if "TOP" in t:
        return Policy.PolicyType.TOP_UP
    if "GROUP" in t:
        return Policy.PolicyType.GROUP
    if "INDIVIDUAL" in t:
        return Policy.PolicyType.INDIVIDUAL
    if "HEALTH" in t or "MEDICLAIM" in t or "MEDICAL" in t:
        return Policy.PolicyType.HEALTH
    return Policy.PolicyType.OTHER


def _merge_analyses(base: PolicyAnalysis, addition: PolicyAnalysis) -> PolicyAnalysis:
    """Merge structured analyses from multiple chunk batches without duplicating clauses."""
    for field in [
        "provider",
        "policy_name",
        "policy_type",
        "policy_number",
        "uin",
        "sum_insured",
        "premium",
        "policy_period_start",
        "policy_period_end",
        "insured_name",
        "plan_name",
        "deductible",
    ]:
        if not getattr(base.metadata, field, None) and getattr(addition.metadata, field, None):
            setattr(base.metadata, field, getattr(addition.metadata, field))

    for attr in [
        "coverages",
        "exclusions",
        "waiting_periods",
        "deductibles",
        "limits",
        "conditions",
        "claim_requirements",
        "eligibility",
        "renewal",
        "cancellation",
        "other_clauses",
    ]:
        base_list = getattr(base, attr)
        seen_titles = {item.title.strip().lower() for item in base_list}
        for item in getattr(addition, attr):
            if item.title.strip().lower() not in seen_titles:
                base_list.append(item)
                seen_titles.add(item.title.strip().lower())
    return base


def _parse_date(d_str: str | None):
    if not d_str:
        return None
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(d_str.strip(), fmt).date()
        except ValueError:
            pass
    return None


def extract_structured_policy(
    document_id: str,
    llm_client: BaseLLMClient | None = None,
    strict_validation: bool = True,
) -> PolicyAnalysis:
    """
    Execute structured extraction across document chunks:
    1. Fetches chunks from PostgreSQL.
    2. Builds non-hallucinating extraction prompt (windowed batching for large docs).
    3. Prompts LLM for structured PolicyAnalysis schema.
    4. Validates output and verifies source quotations exist in chunks.
    5. Stores extracted items as Clause records in PostgreSQL.
    6. Updates policy status to ANALYZED.
    """
    doc = Document.objects.select_related("policy").get(id=document_id)
    policy = doc.policy

    chunks_qs = doc.chunks.select_related("page").order_by("chunk_index")
    chunks_data: list[dict[str, Any]] = []
    for ch in chunks_qs:
        chunks_data.append(
            {
                "page_number": ch.page.page_number if ch.page else ch.metadata.get("page_number", 1),
                "section": ch.metadata.get("section", "General"),
                "content": ch.content,
            }
        )

    if not chunks_data:
        logger.warning(f"Document {document_id} has no chunks to extract.")
        return PolicyAnalysis()

    client = llm_client or get_llm_client()

    # 1. Generate structured output (with windowed batching for large documents >= 15 chunks)
    raw_analysis = None
    if len(chunks_data) <= 15:
        prompt = build_extraction_prompt(
            chunks=chunks_data,
            metadata={"name": policy.name, "provider": policy.provider},
        )
        try:
            raw_analysis = client.generate_structured(prompt=prompt, schema=PolicyAnalysis)
        except Exception as exc:  # noqa: BLE001 - fallback to heuristic parser if client fails
            logger.warning(f"Client extraction raised: {exc}. Attempting heuristic fallback.")
    else:
        logger.info(f"Document {document_id} has {len(chunks_data)} chunks. Processing in windowed batches.")
        batch_size = 12
        stride = 10
        accumulated = PolicyAnalysis()
        has_any_llm_success = False
        for i in range(0, len(chunks_data), stride):
            batch_chunks = chunks_data[i : i + batch_size]
            prompt = build_extraction_prompt(
                chunks=batch_chunks,
                metadata={"name": policy.name, "provider": policy.provider},
            )
            try:
                batch_res = client.generate_structured(prompt=prompt, schema=PolicyAnalysis)
                if batch_res:
                    accumulated = _merge_analyses(accumulated, batch_res)
                    has_any_llm_success = True
            except Exception as exc:  # noqa: BLE001 - batch failure must not abort other batches
                logger.warning(f"Batch extraction [{i}:{i+batch_size}] raised: {exc}")
        if has_any_llm_success:
            raw_analysis = accumulated

    # If extraction returned 0 clauses, fall back to heuristic document parser
    has_items = raw_analysis and (
        len(raw_analysis.coverages)
        + len(raw_analysis.exclusions)
        + len(raw_analysis.waiting_periods)
        + len(raw_analysis.deductibles)
        + len(raw_analysis.limits)
        + len(raw_analysis.conditions)
        + len(raw_analysis.claim_requirements)
        + len(raw_analysis.eligibility)
        + len(raw_analysis.renewal)
        + len(raw_analysis.cancellation)
        + len(raw_analysis.other_clauses)
        > 0
    )
    if not has_items:
        from .heuristic_parser import parse_insurance_document_text

        raw_analysis = parse_insurance_document_text(chunks=chunks_data)

    # 2. Validate against schema and verify grounding / quotes against source chunks
    validated_analysis = validate_structured_output(
        data=raw_analysis,
        source_chunks=chunks_data,
        strict_grounding=strict_validation,
    )

    # 3. Store extracted items in PostgreSQL Clause table
    clause_objs = []
    category_mapping = [
        (validated_analysis.coverages, Clause.Category.COVERAGE),
        (validated_analysis.exclusions, Clause.Category.EXCLUSION),
        (validated_analysis.waiting_periods, Clause.Category.WAITING_PERIOD),
        (validated_analysis.deductibles, Clause.Category.DEDUCTIBLE),
        (validated_analysis.limits, Clause.Category.LIMIT),
        (validated_analysis.conditions, Clause.Category.CONDITION),
        (validated_analysis.claim_requirements, Clause.Category.CLAIM_REQUIREMENT),
        (validated_analysis.eligibility, Clause.Category.ELIGIBILITY),
        (validated_analysis.renewal, Clause.Category.RENEWAL),
        (validated_analysis.cancellation, Clause.Category.CANCELLATION),
        (validated_analysis.other_clauses, Clause.Category.OTHER),
    ]

    for item_list, category in category_mapping:
        for item in item_list:
            clause_objs.append(
                Clause(
                    policy=policy,
                    category=category,
                    title=item.title,
                    explanation=item.explanation,
                    source_text=item.source_text,
                    page_number=item.page_number,
                    section=item.section,
                    confidence=item.confidence,
                )
            )

    if not clause_objs:
        raise ExtractionValidationError(
            f"No structured policy terms or clauses could be extracted from document {document_id}."
        )

    with transaction.atomic():
        # Clear prior clauses for this policy if re-analyzing (idempotency)
        policy.clauses.all().delete()
        Clause.objects.bulk_create(clause_objs)

        # Update policy metadata from extracted document terms
        update_fields = ["status", "analyzed_at", "updated_at", "error_message"]
        meta = validated_analysis.metadata
        if meta.policy_name:
            policy.name = meta.policy_name
            update_fields.append("name")
        if meta.provider:
            policy.provider = meta.provider
            update_fields.append("provider")
        if meta.policy_type:
            policy.policy_type = _normalize_policy_type(meta.policy_type)
            update_fields.append("policy_type")
        if meta.sum_insured:
            policy.sum_insured = meta.sum_insured
            update_fields.append("sum_insured")
        if meta.premium:
            policy.premium = meta.premium
            update_fields.append("premium")
        if meta.policy_period_start:
            policy.policy_period_start = _parse_date(meta.policy_period_start)
            update_fields.append("policy_period_start")
        if meta.policy_period_end:
            policy.policy_period_end = _parse_date(meta.policy_period_end)
            update_fields.append("policy_period_end")

        policy.error_message = ""
        policy.status = Policy.Status.COMPLETED
        policy.analyzed_at = timezone.now()
        policy.save(update_fields=list(set(update_fields)))

    logger.info(f"Structured extraction completed for Policy ID {policy.id}. Persisted {len(clause_objs)} clauses.")
    return validated_analysis
