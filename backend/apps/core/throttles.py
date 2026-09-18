from rest_framework.throttling import UserRateThrottle


class DocumentUploadThrottle(UserRateThrottle):
    """Throttle for document upload operations (10/min/user)."""

    scope = "document_upload"


class PolicyAnalysisThrottle(UserRateThrottle):
    """Throttle for async policy analysis triggers (10/min/user)."""

    scope = "policy_analysis"


class PolicyChatThrottle(UserRateThrottle):
    """Throttle for policy question-answering chat endpoints (30/min/user)."""

    scope = "policy_chat"
