from django.db import models
from django.utils import timezone
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


class SummaryReadReceipt(models.Model):
    """
    One row per user and summary. `opened_at` is set when the user opens the
    summary. `read_at` is set when the user reaches the end of it. The reporter
    gets a receipt too, but the counts leave it out (see `summaries.receipts`).
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["summary", "user"], name="unique_summary_read_receipt"
            )
        ]

    summary = models.ForeignKey(
        Summary, on_delete=models.CASCADE, related_name="read_receipts"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="summary_read_receipts"
    )
    opened_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        state = "read" if self.read_at else "opened"
        return f"{self.user} {state} {self.summary}"
