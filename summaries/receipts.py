from django.db.models import Count, Exists, F, OuterRef, Q
from django.utils import timezone

from summaries.models import Summary, SummaryReadReceipt


def record_opened(summary: Summary, user) -> SummaryReadReceipt:
    """Create the receipt on the first open. Later opens change nothing."""
    receipt, _ = SummaryReadReceipt.objects.get_or_create(summary=summary, user=user)
    return receipt


def record_read(summary: Summary, user) -> SummaryReadReceipt:
    """Set `read_at` once. A user can reach the end without a call to `record_opened`."""
    receipt = record_opened(summary, user)
    # An update that filters on `read_at` keeps the first value if two requests race.
    SummaryReadReceipt.objects.filter(pk=receipt.pk, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    receipt.refresh_from_db()
    return receipt


def counted_receipts(summary: Summary):
    """The receipts that count in the statistics: every user except the reporter."""
    return SummaryReadReceipt.objects.filter(summary=summary).exclude(
        user_id=summary.reporter_id
    )


def with_receipt_data(summaries, user):
    """
    Annotate a list of summaries with the counts and the state of `user`, so the
    list resolver runs one query for all rows. `SummaryNode` reads these names.
    """
    # Without a reporter, every receipt counts.
    counted = Q(reporter__isnull=True) | ~Q(read_receipts__user_id=F("reporter_id"))
    read = Q(read_receipts__read_at__isnull=False)
    mine = SummaryReadReceipt.objects.filter(summary=OuterRef("pk"), user=user)
    return summaries.annotate(
        receipts_opened=Count("read_receipts", filter=counted),
        receipts_read=Count("read_receipts", filter=counted & read),
        receipts_opened_by_me=Exists(mine),
        receipts_read_by_me=Exists(mine.filter(read_at__isnull=False)),
    )
