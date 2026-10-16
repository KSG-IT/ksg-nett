from django.db import models

from schedules.models import RoleOption
from users.models import User


class Chat(models.Model):
    """
    A group chat. It knows nothing about shifts: it has members and messages.
    A shift chat is found by its members and its time window.
    """

    class Meta:
        verbose_name_plural = "Chats"
        default_related_name = "chats"
        permissions = [
            ("create_mega_chat", "Can create a mega chat"),
            ("add_to_mega_chat", "Can add members to a mega chat"),
        ]
        indexes = [models.Index(fields=["last_message_at"])]

    name = models.CharField(max_length=128)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Nobody can post after this time. Members can read the chat for ever.
    closes_at = models.DateTimeField()
    # Set by the code that sends a message. Sorts the inbox without an aggregate.
    last_message_at = models.DateTimeField(null=True, blank=True)
    # A mega chat lets users with the permission add members. A shift chat does
    # not: its members follow the roster of the shift.
    members_editable = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ChatMembership(models.Model):
    class Meta:
        verbose_name_plural = "Chat memberships"
        default_related_name = "memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["chat", "user"], name="unique_chat_membership"
            )
        ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    # Read receipts. Not indexed: it changes every few seconds, and an index
    # on a changing column stops heap-only updates.
    last_read_message = models.ForeignKey(
        "chat.ChatMessage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        db_index=False,
    )
    # Presence. Not indexed, for the same reason.
    last_seen_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} in {self.chat}"


class ChatMessage(models.Model):
    class Meta:
        verbose_name_plural = "Chat messages"
        default_related_name = "messages"
        # Serves the poll for new messages: chat_id = ? AND id > ? ORDER BY id.
        indexes = [models.Index(fields=["chat", "id"])]

    # The composite index above covers lookups by chat.
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, db_index=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    # The sender's shift role when the message was sent. Null when none.
    role = models.CharField(
        max_length=64, choices=RoleOption.choices, null=True, blank=True
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # A moderator hid the message. The body stays for review.
    hidden_at = models.DateTimeField(null=True, blank=True)
    hidden_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"
