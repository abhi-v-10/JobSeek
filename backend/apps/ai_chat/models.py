import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatSession(models.Model):
    """
    Represents one SeekBot conversation thread for a user.
    Example:
    - React Internship Search
    - Resume Review for Backend Role
    - AI Engineer Roadmap
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions"
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"
        indexes = [
            models.Index(fields=["user", "is_active", "-updated_at"]),
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.title or self.id}"

    def is_expired(self, inactivity_days=30):
        if not self.is_active:
            return True

        limit = timezone.now() - timezone.timedelta(days=inactivity_days)
        return self.updated_at < limit

    def mark_inactive(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])


class ChatMessage(models.Model):
    """
    Stores every message inside a chat session.
    """

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("jobs", "Jobs"),
        ("resume_feedback", "Resume Feedback"),
        ("roadmap", "Roadmap"),
        ("error", "Error"),
        ("interview", "Interview"),
    ]

    id = models.BigAutoField(primary_key=True)

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPE_CHOICES,
        default="text"
    )

    content = models.TextField()

    metadata = models.JSONField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {preview}"