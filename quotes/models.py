from django.db import models
from django.db.models import Sum, Index
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel
from quotes.managers import QuoteDefaultQuerySet

from users.models import User


class Quote(TimeStampedModel):
    text = models.TextField()
    reported_by = models.ForeignKey(
        User,
        null=False,
        blank=False,
        related_name="reported_quotes",
        on_delete=models.DO_NOTHING
    )

    tagged = models.ManyToManyField(
        User,
        #null=False,
        blank=True,
        related_name='quotes'
    )

    # None indicates not validated
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='verified_quotes',
        on_delete=models.SET_NULL
    )
    context = models.CharField(max_length=200, null=True, blank=True)


    # Managers
    objects = models.Manager()
    pending_objects = QueryManager(verified_by__isnull=True)
    verified_objects = QueryManager(verified_by__isnull=False)
    highscore_objects= QuoteDefaultQuerySet.as_manager()

    def get_semester_of_quote(self) -> str:
        """
        get_semester_of_quote renders the `created` attribute into a "semester-year"-representation.
        Examples:
            2018-01-01 => V18
            2014-08-30 => H14
            2012-12-30 => H12
        :return: The "semester-year" display of the `created` attribute.
        """
        short_year_format = str(self.created.year)[2:]
        semester_prefix = "H" if self.created.month > 7 else "V"
        return f"{semester_prefix}{short_year_format}"

    @property
    def sum(self):
        """
        Get the sum of votes on this quote. As quote-votes have values 1 or -1 we
        can simply aggregate the value field.
        :return Int:
        """
        if self.votes.count() == 0:
            return 0
        return self.votes.aggregate(value=Sum('value'))['value']

    def __str__(self):
        return "Quote by %s" % (self.quoter,)

    def __repr__(self):
        return "Quote(text=%s,quoter=%s)" % (self.text, self.quoter,)

    class Meta:
        verbose_name_plural = 'quotes'

        indexes = [
            # This field is used to check for pending and non-pending quotes, and
            # should thus be indexed.
            Index(fields=['verified_by'])
        ]
        ordering = ['created']


class QuoteVote(models.Model):
    quote = models.ForeignKey(
        Quote,
        related_name='votes',
        on_delete=models.CASCADE
    )
    # 1 for thumbs up, -1 for thumbs down. Having the field as an integer field
    # allows for future flexibility such as allowing for extra-value thumbs-up etc.
    # We can also get the total tally now by aggregating the sum of this column.
    value = models.SmallIntegerField()
    caster = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name_plural = 'quote votes'

        indexes = [
            # We index on quote, as we will have to filter on a specific quote
            # on every hit to the quote from our APIs needing the fully vote-tally.
            Index(fields=['quote'])
        ]

        unique_together = (
            ('quote', 'caster')
        )

    def __str__(self):
        if self.value > 0:
            return "Up-vote from %s to quote by %s" % (self.caster.first_name, self.quote.quoter,)
        else:
            return "Down-vote from %s to quote by %s" % (self.caster.first_name, self.quote.quoter,)

    def __repr__(self):
        return f"QuoteVote(quote={self.quote_id},value={self.value},caster={self.caster.first_name})"
