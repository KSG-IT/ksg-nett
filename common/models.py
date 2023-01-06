from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(default=timezone.datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
