from django.db import models


class Event(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    datetime_start = models.DateTimeField(null=False)
    datetime_end = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)

    attendees = models.ManyToManyField("users.User", related_name="events_attended")
    waitlist = models.ManyToManyField("users.User", related_name="events_waitlisted")

    def __str__(self):
        return f"Event '{self.title}'"
