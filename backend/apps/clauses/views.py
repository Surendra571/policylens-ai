from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.core.permissions import IsOwner
from .models import Clause
from .serializers import ClauseSerializer


class ClauseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for extracted clauses strictly scoped to the policies owned by authenticated user."""

    serializer_class = ClauseSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Clause.objects.filter(policy__user=self.request.user)
        return Clause.objects.none()


@api_view(["GET"])
@permission_classes([AllowAny])
def clauses_status(request):
    return Response({"module": "clauses", "status": "initialized"}, status=status.HTTP_200_OK)
