from django.db import models
from django.utils import timezone

from users.models import User
from organization.models import InternalGroupPosition


class Event(models.Model):
    class Meta:
        default_related_name = "events"
        verbose_name_plural = "Events"

    title = models.CharField(unique=True, max_length=80)
    description = models.TextField(max_length=1024)
    date = models.DateTimeField(blank=True, null=True)

    max_participants = models.IntegerField(default=10)
    participants = models.ManyToManyField(User, blank=True, related_name="attended_events")

    allowed_to_join = models.ManyToManyField(InternalGroupPosition, blank=True)

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.title
