import logging
from celery import shared_task
from apps.policies.models import Policy
from apps.ai_engine.extraction import extract_structured_policy
from apps.ai_engine.llm_client import get_llm_client

logger = logging.getLogger(__name__)

TRANSIENT_TASK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


@shared_task(
    bind=True,
    name="apps.policies.tasks.analyze_policy",
    autoretry_for=TRANSIENT_TASK_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def analyze_policy(self, policy_id: str, provider: str = None):
    """
    Asynchronous Celery task orchestrating the complete insurance policy analysis pipeline:
    1. Fetch policy and verify documents exist.
    2. Set policy.status = ANALYZING (idempotent status assurance).
    3. Ensure document has finished chunking and embedding.
    4. Call extract_structured_policy to run LLM extraction, grounding verification, and clause persistence.
    5. Set policy.status = COMPLETED and record analyzed_at timestamp.
    6. Retries automatically on transient network/LLM provider timeouts with exponential backoff.
    """
    logger.info(f"Starting asynchronous analysis for Policy ID: {policy_id}")
    try:
        policy = Policy.objects.get(id=policy_id)
        policy.status = Policy.Status.ANALYZING
        policy.save(update_fields=["status", "updated_at"])

        # Fetch latest or primary document for this policy
        doc = policy.documents.order_by("-created_at").first()
        if not doc:
            raise ValueError(f"Policy {policy_id} has no uploaded documents to analyze.")

        # Ensure chunks and embeddings exist
        if doc.chunks.count() == 0:
            logger.info(f"Document {doc.id} has no chunks yet. Triggering chunking before analysis.")
            from apps.documents.tasks import process_document
            process_document(str(doc.id))

        if doc.chunks.count() == 0:
            raise ValueError(f"Document {doc.id} could not generate chunks for analysis.")

        # Run structured policy extraction
        llm_client = get_llm_client(provider=provider)
        _ = extract_structured_policy(
            document_id=str(doc.id),
            llm_client=llm_client,
            strict_validation=True,
        )

        # Verify clauses were persisted
        policy.refresh_from_db()
        if policy.clauses.count() == 0:
            raise ValueError(f"Analysis produced 0 clauses for Policy ID {policy_id}.")

        logger.info(
            f"Successfully completed analysis for Policy ID {policy_id}. Clauses created: {policy.clauses.count()}"
        )
        return {
            "status": "COMPLETED",
            "policy_id": str(policy_id),
            "clauses_count": policy.clauses.count(),
        }

    except TRANSIENT_TASK_EXCEPTIONS as exc:
        logger.warning(
            f"Transient failure during analysis for Policy ID {policy_id} (Attempt {self.request.retries + 1}): {exc}"
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except Exception as exc:
        safe_error = f"{exc.__class__.__name__}: {str(exc)}"
        logger.error(f"Analysis failed permanently for Policy ID {policy_id}: {safe_error}")
        try:
            policy = Policy.objects.get(id=policy_id)
            policy.status = Policy.Status.FAILED
            policy.error_message = safe_error
            policy.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass
        return {
            "status": "FAILED",
            "policy_id": str(policy_id),
            "error": safe_error,
        }


analyze_policy_task = analyze_policy
