from django.db import models
from model_utils.fields import StatusField

from summaries.consts import SummaryType
from users.models import User


class Summary(models.Model):

    type = models.CharField(max_length=32, choices=SummaryType.choices)
    contents = models.TextField(null=False, blank=True)
    participants = models.ManyToManyField(User, blank=True, related_name="summaries")
    reporter = models.ForeignKey(
        User,
        null=False,
        blank=False,
        on_delete=models.DO_NOTHING,
        related_name="reported_summaries",
    )
    date = models.DateTimeField(null=False, blank=False)
    updated_at = models.DateTimeField(auto_now=True)

    def get_short_summary_type_name(self):
        return self.get_type_display()

    def __str__(self):
        return f"{self.get_type_display()} at {self.date.strftime('%Y-%m-%d')}"

    def __repr__(self):
        return f"Summary({self.type=}, {self.date=})"

    class Meta:
        verbose_name_plural = "Summaries"
        default_related_name = "summaries"
