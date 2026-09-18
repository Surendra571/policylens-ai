import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsOwner
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from apps.documents.tasks import process_document_task
from apps.documents.validators import calculate_sha256, sanitize_filename

from .models import Policy
from .serializers import PolicySerializer

logger = logging.getLogger(__name__)


class PolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for policies strictly scoped to the authenticated user.
    Provides:
    - POST /api/v1/policies/ (Create policy)
    - GET /api/v1/policies/ (List user policies)
    - GET /api/v1/policies/{id}/ (Retrieve single policy with documents)
    - DELETE /api/v1/policies/{id}/ (Delete policy and cascades)
    - POST /api/v1/policies/{id}/documents/ (Upload policy PDF)
    """

    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        # Strict user-level scoping to prevent IDOR vulnerabilities
        if self.request.user.is_authenticated:
            return Policy.objects.filter(user=self.request.user).prefetch_related("documents")
        return Policy.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="documents")
    def upload_document(self, request, pk=None):
        """
        Secure upload endpoint for PDF policy documents.
        Validates file type, magic header bytes, maximum file size,
        sanitizes filename, checks duplicates, and dispatches async processing task.
        """
        policy = self.get_object()

        if "file" not in request.FILES and "file" not in request.data:
            return Response(
                {"success": False, "errors": {"file": ["No file was provided in the request."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = serializer.validated_data["file"]
        clean_filename = sanitize_filename(uploaded_file.name)
        file_hash = calculate_sha256(uploaded_file)

        # Duplicate handling
        existing_doc = Document.objects.filter(policy=policy, file_hash=file_hash).first()
        if existing_doc:
            return Response(
                {
                    "success": False,
                    "errors": {"file": ["This exact PDF document has already been uploaded for this policy."]},
                    "document": DocumentSerializer(existing_doc).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = Document.objects.create(
            policy=policy,
            file=uploaded_file,
            original_filename=clean_filename,
            file_size=uploaded_file.size,
            file_hash=file_hash,
            processing_status=Document.ProcessingStatus.UPLOADED,
        )

        # Trigger async Celery processing pipeline placeholder
        try:
            process_document_task.delay(str(doc.id))
        except Exception as exc:  # noqa: BLE001 - asynchronous dispatch is best effort
            logger.warning("Asynchronous task dispatch deferred: %s", exc)

        return Response(
            {
                "success": True,
                "message": "Document uploaded successfully and queued for asynchronous processing.",
                "document": DocumentSerializer(doc).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """
        POST /api/v1/policies/{id}/analyze/
        Triggers asynchronous policy analysis pipeline via Celery.
        Sets status = ANALYZING and returns 202 Accepted.
        """
        policy = self.get_object()

        # Check if policy has any documents uploaded
        if not policy.documents.exists():
            return Response(
                {
                    "success": False,
                    "error": "No documents found for this policy. Please upload a policy PDF before initiating analysis.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set status to ANALYZING immediately for frontend polling
        policy.status = Policy.Status.ANALYZING
        policy.save(update_fields=["status", "updated_at"])

        # Dispatch Celery task asynchronously
        from .tasks import analyze_policy_task

        try:
            analyze_policy_task.delay(str(policy.id))
        except Exception as exc:  # noqa: BLE001 - asynchronous dispatch is best effort
            logger.warning(
                "Celery dispatch deferred or running synchronously in testing: %s",
                exc,
            )

        return Response(
            {
                "success": True,
                "message": "Policy analysis initiated asynchronously.",
                "policy_id": str(policy.id),
                "status": Policy.Status.ANALYZING,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"], url_path="analysis")
    def analysis(self, request, pk=None):
        """
        GET /api/v1/policies/{id}/analysis/
        Allows the frontend to poll processing status or retrieve structured analysis results.
        Returns:
        - policy metadata
        - coverage
        - exclusions
        - waiting periods
        - deductibles
        - limits
        - conditions
        - claim requirements
        - important points with preserved evidence
        """
        policy = self.get_object()

        # If analysis is still pending or analyzing, inform frontend cleanly for polling
        if policy.status in (Policy.Status.PENDING, Policy.Status.PROCESSING, Policy.Status.ANALYZING):
            return Response(
                {
                    "status": policy.status,
                    "analyzed": False,
                    "analyzed_at": None,
                    "policy_id": str(policy.id),
                    "message": "Policy analysis is in progress. Please continue polling.",
                },
                status=status.HTTP_200_OK,
            )

        if policy.status == Policy.Status.FAILED:
            safe_err = policy.error_message or "Policy analysis encountered an error. Please retry analysis."
            return Response(
                {
                    "status": Policy.Status.FAILED,
                    "analyzed": False,
                    "analyzed_at": None,
                    "policy_id": str(policy.id),
                    "error": safe_err,
                    "message": safe_err,
                },
                status=status.HTTP_200_OK,
            )

        # Completed or Analyzed: fetch all categorized clauses
        clauses = list(policy.clauses.all())
        from apps.clauses.models import Clause
        from apps.clauses.serializers import ClauseSerializer

        def get_category_clauses(cat):
            return [c for c in clauses if c.category == cat]

        coverages = get_category_clauses(Clause.Category.COVERAGE)
        exclusions = get_category_clauses(Clause.Category.EXCLUSION)
        waiting_periods = get_category_clauses(Clause.Category.WAITING_PERIOD)
        deductibles = get_category_clauses(Clause.Category.DEDUCTIBLE)
        limits = get_category_clauses(Clause.Category.LIMIT)
        conditions = get_category_clauses(Clause.Category.CONDITION)
        claim_requirements = get_category_clauses(Clause.Category.CLAIM_REQUIREMENT)
        eligibility = get_category_clauses(Clause.Category.ELIGIBILITY)
        renewal = get_category_clauses(Clause.Category.RENEWAL)
        cancellation = get_category_clauses(Clause.Category.CANCELLATION)
        other_clauses = get_category_clauses(Clause.Category.OTHER)

        # Curate important points preserving evidence
        important_points = []
        for c in (limits + waiting_periods + deductibles + exclusions + conditions)[:10]:
            important_points.append(
                {
                    "category": c.category,
                    "title": c.title,
                    "explanation": c.explanation,
                    "evidence": {
                        "source_text": c.source_text,
                        "page_number": c.page_number,
                        "section": c.section,
                        "confidence": c.confidence,
                    },
                }
            )

        period_dict = (
            {
                "start": policy.policy_period_start.isoformat() if policy.policy_period_start else None,
                "end": policy.policy_period_end.isoformat() if policy.policy_period_end else None,
            }
            if (policy.policy_period_start or policy.policy_period_end)
            else None
        )

        payload = {
            "status": policy.status,
            "analyzed": True,
            "analyzed_at": policy.analyzed_at,
            "metadata": {
                "policy_id": str(policy.id),
                "name": policy.name,
                "provider": policy.provider,
                "policy_type": policy.policy_type,
                "sum_insured": policy.sum_insured,
                "premium": policy.premium,
                "policy_period_start": policy.policy_period_start.isoformat() if policy.policy_period_start else None,
                "policy_period_end": policy.policy_period_end.isoformat() if policy.policy_period_end else None,
                "policy_period": period_dict,
                "uploaded_at": policy.uploaded_at,
                "analyzed_at": policy.analyzed_at,
            },
            "summary": {
                "total_clauses": len(clauses),
                "total_coverages": len(coverages),
                "total_exclusions": len(exclusions),
                "total_waiting_periods": len(waiting_periods),
                "total_deductibles": len(deductibles),
                "total_limits": len(limits),
                "total_conditions": len(conditions),
                "total_claim_requirements": len(claim_requirements),
                "total_eligibility": len(eligibility),
                "total_renewal": len(renewal),
                "total_cancellation": len(cancellation),
                "total_other_clauses": len(other_clauses),
            },
            "coverages": ClauseSerializer(coverages, many=True).data,
            "exclusions": ClauseSerializer(exclusions, many=True).data,
            "waiting_periods": ClauseSerializer(waiting_periods, many=True).data,
            "deductibles": ClauseSerializer(deductibles, many=True).data,
            "limits": ClauseSerializer(limits, many=True).data,
            "conditions": ClauseSerializer(conditions, many=True).data,
            "claim_requirements": ClauseSerializer(claim_requirements, many=True).data,
            "eligibility": ClauseSerializer(eligibility, many=True).data,
            "renewal": ClauseSerializer(renewal, many=True).data,
            "cancellation": ClauseSerializer(cancellation, many=True).data,
            "other_clauses": ClauseSerializer(other_clauses, many=True).data,
            "important_points": important_points,
            # Top-level conceptual fields
            "policy_name": policy.name,
            "provider": policy.provider,
            "policy_type": policy.get_policy_type_display(),
            "sum_insured": policy.sum_insured,
            "premium": policy.premium,
            "policy_period": period_dict,
            "coverage": ClauseSerializer(coverages, many=True).data,
        }

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="clauses")
    def list_clauses(self, request, pk=None):
        """
        GET /api/v1/policies/{id}/clauses/
        Lists all clauses extracted for the policy, with optional category filter:
        GET /api/v1/policies/{id}/clauses/?category=EXCLUSION
        """
        policy = self.get_object()
        clauses_qs = policy.clauses.all().order_by("category", "page_number")

        category_param = request.query_params.get("category")
        if category_param:
            clauses_qs = clauses_qs.filter(category=category_param.upper())

        from apps.clauses.serializers import ClauseSerializer

        serializer = ClauseSerializer(clauses_qs, many=True)
        return Response(
            {
                "policy_id": str(policy.id),
                "count": clauses_qs.count(),
                "clauses": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="chat")
    def chat(self, request, pk=None):
        """
        POST /api/v1/policies/{id}/chat/
        Policy-specific AI chat with grounded citations, tenant isolation, and conversation history.
        """
        policy = self.get_object()

        question = request.data.get("question")
        if not question or not str(question).strip():
            return Response(
                {"error": "Question is required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ai_engine.rag import PolicyRAGPipeline
        from apps.chat.models import Conversation, Message

        conversation_id = request.data.get("conversation_id")
        conversation = None
        if conversation_id:
            conversation = Conversation.objects.filter(id=conversation_id, user=request.user, policy=policy).first()

        if not conversation:
            conversation = Conversation.objects.create(
                user=request.user,
                policy=policy,
                title=f"Chat: {question[:40]}",
            )

        # Store user message
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=question.strip(),
        )

        rag_pipeline = PolicyRAGPipeline()
        result = rag_pipeline.answer_question(
            policy=policy,
            question=question.strip(),
            user=request.user,
        )

        # Store assistant message
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result["answer"],
            citations=result["citations"],
        )

        return Response(
            {
                "answer": result["answer"],
                "confidence": result["confidence"],
                "citations": result["citations"],
                "conversation_id": str(conversation.id),
            },
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def policies_status(request):
    return Response({"module": "policies", "status": "initialized"}, status=status.HTTP_200_OK)
