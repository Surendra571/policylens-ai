from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsOwner

from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for documents strictly scoped to the policies owned by authenticated user."""

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Document.objects.filter(policy__user=self.request.user)
        return Document.objects.none()


@api_view(["GET"])
@permission_classes([AllowAny])
def documents_status(request):
    return Response({"module": "documents", "status": "initialized"}, status=status.HTTP_200_OK)
