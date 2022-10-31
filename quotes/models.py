from django.db import models
from django.db.models import Sum, Index
from common.models import TimestampedModel
from users.models import User
from django.db.models.functions import Coalesce
from django.utils import timezone


class Quote(TimestampedModel):
    text = models.TextField()
    reported_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="reported_quotes",
        on_delete=models.DO_NOTHING,
    )
    migrated_from_sg = models.BooleanField(default=False)

    tagged = models.ManyToManyField(User, blank=True, related_name="quotes")

    # None indicates not validated. Change the name of this
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="verified_quotes",
        on_delete=models.SET_NULL,
    )
    context = models.CharField(max_length=200, null=True, blank=True)

    @classmethod
    def get_pending_quotes(cls):
        return (
            cls.objects.filter(verified_by__isnull=True)
            .exclude(migrated_from_sg=True)
            .order_by("-created_at")
        )

    @classmethod
    def get_approved_quotes(cls):
        return (
            cls.objects.filter(verified_by__isnull=False)
            | cls.objects.filter(migrated_from_sg=True)
        ).order_by("-created_at")

    @classmethod
    def get_popular_quotes_in_current_semester(cls):
        # TODO TESTS
        now = timezone.datetime.now()
        current_month = now.month
        if current_month < 7:
            semester_start = timezone.datetime(year=now.year, month=1, day=1)
        else:
            semester_start = timezone.datetime(year=now.year, month=7, day=1)

        semester_start = timezone.make_aware(semester_start)
        popular_quotes = (
            cls.objects.filter(
                verified_by__isnull=False, created_at__gte=semester_start
            )
            .annotate(total_votes=Coalesce(Sum("votes__value"), 0))
            .order_by("-total_votes")[:10]
        )
        return popular_quotes

    @classmethod
    def get_current_semester_shorthand(cls):
        short_year_format = str(timezone.datetime.now().year)[2:]
        semester_prefix = "H" if timezone.datetime.now().month > 7 else "V"
        return f"{semester_prefix}{short_year_format}"

    @classmethod
    def get_popular_quotes_all_time(cls):
        # TODO TESTS
        popular_quotes = (
            cls.objects.filter(verified_by__isnull=False)
            .annotate(total_votes=Coalesce(Sum("votes__value"), 0))
            .order_by("-total_votes")[:10]
        )
        return popular_quotes

    def get_semester_of_quote(self) -> str:
        """
        get_semester_of_quote renders the `created` attribute into a "semester-year"-representation.
        Examples:
            2018-01-01 => V18
            2014-08-30 => H14
            2012-12-30 => H12
        :return: The "semester-year" display of the `created` attribute.
        """
        short_year_format = str(self.created_at.year)[2:]
        semester_prefix = "H" if self.created_at.month > 7 else "V"
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
        return self.votes.aggregate(value=Sum("value"))["value"]

    def __str__(self):
        return "Quote by %s" % (self.tagged.all(),)

    def __repr__(self):
        return "Quote(text=%s,tagged=%s)" % (
            self.text,
            self.tagged.all(),
        )

    class Meta:
        verbose_name_plural = "quotes"

        indexes = [
            # This field is used to check for pending and non-pending quotes, and
            # should thus be indexed.
            Index(fields=["verified_by"])
        ]
        ordering = ["created_at"]


class QuoteVote(models.Model):
    quote = models.ForeignKey(Quote, related_name="votes", on_delete=models.CASCADE)
    # 1 for thumbs up, -1 for thumbs down. Having the field as an integer field
    # allows for future flexibility such as allowing for extra-value thumbs-up etc.
    # We can also get the total tally now by aggregating the sum of this column.
    value = models.SmallIntegerField()
    caster = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="quote_votes"
    )

    class Meta:
        verbose_name_plural = "quote votes"

        indexes = [
            # We index on quote, as we will have to filter on a specific quote
            # on every hit to the quote from our APIs needing the fully vote-tally.
            Index(fields=["quote"])
        ]

        unique_together = ("quote", "caster")

    def __str__(self):
        if self.value > 0:
            return "Up-vote from %s to quote by %s" % (
                self.caster.first_name,
                self.quote.tagged.all(),
            )
        else:
            return "Down-vote from %s to quote by %s" % (
                self.caster.first_name,
                self.quote.tagged.all(),
            )

    def __repr__(self):
        return f"QuoteVote(quote={self.quote_id},value={self.value},caster={self.caster.first_name})"


class LegacyQuote(models.Model):
    datetime_created = models.DateTimeField()
    text = models.TextField()

    def __str__(self):
        return self.text
