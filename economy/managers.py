from django.conf import settings
from django.db import models


class SociBankAccountManager(models.Manager):
    def soci_master_account(self):
        return self.get_queryset().get(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
