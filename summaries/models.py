from django.db import models


# Create your models here.
from summaries.consts import SUMMARY_TYPE_CHOICES, SUMMARY_TYPE_OTHER, SUMMARY_TYPE_CHOICES_DICT
from users.models import User


class Summary(models.Model):
    summary_type = models.CharField(
        max_length=4,
        null=False,
        choices=SUMMARY_TYPE_CHOICES,
        default=SUMMARY_TYPE_OTHER
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

    def __str__(self):
        return "%s at %s" % (
            SUMMARY_TYPE_CHOICES_DICT[self.summary_type],
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
