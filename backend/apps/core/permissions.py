from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Object-level permission allowing only the owner of the resource
    or parent resource hierarchy to view or mutate it.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Direct ownership: User, Policy, Conversation
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Policy child: Document, Clause
        if hasattr(obj, "policy"):
            return obj.policy.user == request.user

        # Document child: DocumentPage, DocumentChunk
        if hasattr(obj, "document"):
            return obj.document.policy.user == request.user

        # Conversation child: Message
        if hasattr(obj, "conversation"):
            return obj.conversation.user == request.user

        return False
