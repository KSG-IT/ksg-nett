from django.db import models
from django.db.models import Sum, Index

from quotes.managers import QuotePendingManager, QuoteVerifiedManager
from users.models import User


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


class QuoteVote(models.Model):
    quote = models.ForeignKey(Quote, related_name='votes', on_delete=models.CASCADE)
    # 1 for thumbs up, -1 for thumbs down. Having the field as an integer field
    # allows for future flexibility such as allowing for extra-value thumbs-up etc.
    # We can also get the total tally now by aggregating the sum of this column.
    value = models.SmallIntegerField()
    caster = models.ForeignKey(User, on_delete=models.CASCADE)

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
        return "QuoteVote(quote=%d,value=%d,caster=%s)" % (
            self.quote_id,
            self.value,
            self.caster.first_name
        )
