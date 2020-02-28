from django.db.models import signals
from django.dispatch import receiver
from .models import User

from economy.models import SociBankAccount


@receiver(signals.post_save, sender=User)
def create_soci_bank_account(sender, instance, created, **kwargs):
    if created:
        SociBankAccount.objects.create(user=instance)