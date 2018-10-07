from django.db.models.signals import pre_save
from django.dispatch import receiver

from economy.models import SociBankAccount, Purchase


@receiver(pre_save, sender=Purchase)
def my_handler(instance: Purchase, **_kwargs):
    if instance.source:
        instance.source.remove_funds(amount=instance.total_amount)
        SociBankAccount.objects.soci_master_account().add_funds(amount=instance.total_amount)
