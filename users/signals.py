from django.db.models import signals
from django.dispatch import receiver
from .models import User

from economy.models import SociBankAccount


@receiver(signals.post_save, sender=User)
def create_soci_bank_account(sender, instance: User, created, **kwargs):
    # We use getattr here as accessing the field directly when the relation does not
    # exist will throw an error.
    if created and getattr(instance, "bank_account", None) is not None:
        SociBankAccount.objects.create(user=instance)