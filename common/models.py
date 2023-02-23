from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(default=timezone.datetime.now)
    updated_at = models.DateTimeField(auto_now=True)


class FeatureFlag(models.Model):

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(default="", blank=True)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}: {self.enabled}"
