from django.db import models

# Create your models here.
from summaries.consts import SUMMARY_TYPE_CHOICES, SUMMARY_TYPE_OTHER, SUMMARY_TYPE_CHOICES_DICT, \
    SUMMARY_TYPE_SHORT_NAMES_DICT
from users.models import User


class Summary(models.Model):
    summary_type = models.CharField(
        max_length=16,
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

    def get_short_summary_type_name(self):
        return SUMMARY_TYPE_SHORT_NAMES_DICT.get(self.summary_type)

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
