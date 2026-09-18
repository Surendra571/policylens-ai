import uuid

from django.conf import settings
from django.db import models

from apps.policies.models import Policy


class Conversation(models.Model):
    """Conversation model managing a chat session scoped to an insurance policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )
    title = models.CharField(max_length=255, default="Policy Consultation", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "policy"], name="conv_user_policy_idx"),
        ]

    def __str__(self):
        return f"Conversation: {self.policy.name} ({self.user.email})"


class Message(models.Model):
    """Message model tracking conversational messages and their strict grounded citations."""

    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"
        SYSTEM = "SYSTEM", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    content = models.TextField(help_text="Message body")
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of citations: [{'page_number': 3, 'quote': '...'}]",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="msg_conv_created_idx"),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}..."
