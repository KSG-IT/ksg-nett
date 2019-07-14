from django.db import models
from model_utils.fields import StatusField

from summaries.consts import SUMMARY_TYPE_CHOICES, SUMMARY_TYPE_SHORT_NAMES
from users.models import User


class Summary(models.Model):
    STATUS = SUMMARY_TYPE_CHOICES

    summary_type = StatusField(
        max_length=16,
        null=False,
    )
    contents = models.TextField(null=False, blank=True)
    participants = models.ManyToManyField(
        User,
        blank=True,
        related_name='summaries'
    )
    reporter = models.ForeignKey(
        User,
        null=False,
        blank=False,
        on_delete=models.DO_NOTHING,
        related_name='reported_summaries'
    )
    date = models.DateTimeField(null=False, blank=False)
    updated_at = models.DateTimeField(auto_now=True)

    def get_short_summary_type_name(self):
        return SUMMARY_TYPE_SHORT_NAMES[self.summary_type]

    def __str__(self):
        return "%s at %s" % (
            self.STATUS[self.summary_type],
            self.date.strftime("%Y-%m-%d")
        )

    def __repr__(self):
        return "Summary(type=%s, date=%s)" % (
            self.summary_type,
            self.date.strftime("%Y-%m-%d")
        )

    class Meta:
        verbose_name_plural = 'Summaries'
        default_related_name = 'summaries'
