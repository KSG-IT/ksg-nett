from django.db import models

from users.models import User


class PushSubscription(models.Model):
    """
    One browser on one device that accepts Web Push. A user can have several.
    The browser gives `endpoint`, `p256dh` and `auth` when it subscribes.
    """

    class Meta:
        verbose_name_plural = "Push subscriptions"
        default_related_name = "push_subscriptions"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Push subscription {self.pk} for {self.user}"
