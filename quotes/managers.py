from django.db import models


class QuotePendingManager(models.Manager):
    """
    This class returns the pending quotes.
    """
    def get_queryset(self):
        return super(QuotePendingManager, self)\
            .get_queryset()\
            .filter(verified_by__isnull=True)


class QuoteVerifiedManager(models.Manager):
    """
    This class returns the verified quotes.
    """
    def get_queryset(self):
        return super(QuoteVerifiedManager, self)\
            .get_queryset()\
            .filter(verified_by__isnull=False)
