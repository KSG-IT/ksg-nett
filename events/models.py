from django.db import models
from django.conf import settings

# Create your models here.

class Gang(models.Model):
    gang_name = models.CharField(max_length=100)
    # Placeholder

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_ksg_wide = models.BooleanField(default=False)
    gang = models.ForeignKey(Gang, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="events_attending")
    