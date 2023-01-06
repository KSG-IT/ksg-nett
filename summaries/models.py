from django.db import models
from users.models import User


class Summary(models.Model):
    class Meta:
        verbose_name_plural = "Summaries"
        default_related_name = "summaries"

    internal_group = models.ForeignKey(
        "organization.InternalGroup", null=True, blank=True, on_delete=models.SET_NULL
    )
    # If internal group is null we use the title
    title = models.CharField(max_length=128, null=True, blank=True)
    contents = models.TextField(null=False, blank=True)
    participants = models.ManyToManyField(
        User, blank=True, related_name="meetings_attended_summaries"
    )
    reporter = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reported_summaries",
    )
    date = models.DateField(null=False, blank=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.internal_group:
            return f"{self.internal_group.name} - {self.date}"
        return f"{self.title} - {self.date}"

    def get_display_name(self):
        if self.internal_group:
            return self.internal_group.name
        return self.title
