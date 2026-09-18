from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.core.permissions import IsOwner
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for conversations strictly scoped to authenticated user."""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Conversation.objects.filter(user=self.request.user)
        return Conversation.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for messages strictly scoped to conversations owned by user."""

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Message.objects.filter(conversation__user=self.request.user)
        return Message.objects.none()


@api_view(["GET"])
@permission_classes([AllowAny])
def chat_status(request):
    return Response({"module": "chat", "status": "initialized"}, status=status.HTTP_200_OK)
