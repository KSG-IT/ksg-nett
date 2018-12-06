from django.db import models
from django.db.models import Sum, Index
from django.utils import timezone
import datetime

from quotes.managers import QuotePendingManager, QuoteVerifiedManager
from users.models import User
from common.templatetags.ksg_helpers import get_semester_year_shorthand


class Quote(models.Model):
    text = models.TextField()
    quoter = models.ForeignKey(
        User,
        null=False,
        blank=False,
        related_name='quotes',
        on_delete=models.DO_NOTHING
    )

    # None indicates not validated
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='verified_quotes',
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Managers
    objects = models.Manager()
    pending_objects = QuotePendingManager()
    verified_objects = QuoteVerifiedManager()

    def get_semester_of_quote(self) -> str:
        """
        get_semester_of_quote renders the `created_at` attribute into a "semester-year"-representation.
        Examples:
            2018-01-01 => V18
            2014-08-30 => H14
            2012-12-30 => H12
        :return: The "semester-year" display of the `created_at` attribute.
        """
        short_year_format = str(self.created_at.year)[2:]
        semester_prefix = "H" if self.created_at.month > 7 else "V"
        return f"{semester_prefix}{short_year_format}"

    def get_quotes_this_semester(self):
        """
        Method for quotes created this semester, returns an Array containing said quotes
        :return Array
        """
        current_semester = datetime.datetime.today()
        current_semester_shorthand = get_semester_year_shorthand(current_semester)
        all_quotes = Quote.objects.all()
        quotes_this_semester = []

        for quote in all_quotes:
            semester_of_quote = get_semester_year_shorthand(quote.created_at)
            if semester_of_quote == current_semester_shorthand:
                quotes_this_semester.append(quote)

        return quotes_this_semester

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
        return "Quote by %s" % (self.quoter.first_name,)

    def __repr__(self):
        return "Quote(text=%s,quoter=%s)" % (self.text, self.quoter.first_name,)

    class Meta:
        verbose_name_plural = 'quotes'

        indexes = [
            # This field is used to check for pending and non-pending quotes, and
            # should thus be indexed.
            Index(fields=['verified_by'])
        ]
        ordering = ['created_at']


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
            return "Up-vote from %s to quote by %s" % (self.caster.first_name, self.quote.quoter.first_name,)
        else:
            return "Down-vote from %s to quote by %s" % (self.caster.first_name, self.quote.quoter.first_name,)

    def __repr__(self):
        return f"QuoteVote(quote={self.quote_id},value={self.value},caster={self.caster.first_name})"
