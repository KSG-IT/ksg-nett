from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class PurchaseTransactionLogEntry(models.Model):
    """
    Tracks economic transactions coming from the X-App API calls for a given user. Intended
    to be used for debugging and auditing purposes.
    """

    class Meta:
        verbose_name = "Purchase transaction log entry"
        verbose_name_plural = "Purchase transaction log entries"

    class TransactionSourceOptions(models.TextChoices):
        API = ("API", "API")

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="purchase_transaction_log_entries",
    )
    amount = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_source = models.CharField(
        max_length=10, choices=TransactionSourceOptions.choices
    )

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.transaction_source} - {self.timestamp}"


class BlacklistedSong(models.Model):
    class Meta:
        verbose_name = "Blacklisted song"
        verbose_name_plural = "Blacklisted songs"

    name = models.CharField(max_length=100)
    spotify_song_id = models.CharField(max_length=100, unique=True)
    blacklisted_until = models.DateTimeField(null=True)
    blacklisted_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="blacklisted_songs",
    )
