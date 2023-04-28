from django.db import models


class WaitListUser(models.Model):
    class Meta:
        unique_together = ("user", "event")

    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE)
    datetime_joined = models.DateTimeField(auto_now_add=True)


class Event(models.Model):
    class Meta:
        ordering = ["datetime_start"]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    title = models.CharField(max_length=255)
    description = models.TextField()

    datetime_start = models.DateTimeField()
    datetime_end = models.DateTimeField(null=True, blank=True)
    datetime_registration_start = models.DateTimeField(null=True, blank=True)

    location = models.CharField(max_length=255, null=True, blank=True)
    participants = models.ManyToManyField(
        "users.User", blank=True, related_name="events_attending"
    )
    wait_list = models.ManyToManyField(
        "users.User",
        through=WaitListUser,
        blank=True,
        related_name="events_on_wait_list",
    )

    max_participants = models.IntegerField(null=True, blank=True)
    invited_internal_groups = models.ManyToManyField(
        "organization.InternalGroup", blank=True, related_name="available_events"
    )

    def __str__(self):
        return self.title
