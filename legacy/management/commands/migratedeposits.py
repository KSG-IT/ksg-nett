import pytz
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import Innskudd
from economy.models import Deposit, SociBankAccount


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migratedeposits()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migratedeposits(self):
        legacy_deposits = Innskudd.objects.using("legacy").all()
        self.stdout.write(
            self.style.SUCCESS(
                f"Migrating {legacy_deposits.count()} legacy deposits to new table"
            )
        )
        for deposit in legacy_deposits:
            with transaction.atomic():

                # ToDo this timezone aware logic. Look at the timezone legacy objects
                aware_datetime = deposit.registrert
                if not aware_datetime.tzinfo:

                    aware_datetime = timezone.make_aware(
                        deposit.registrert, timezone=pytz.timezone(settings.TIME_ZONE)
                    )
                self.stdout.write(
                    self.style.SUCCESS(f"Migrating deposit: {deposit.kommentar}")
                )
                deposit = Deposit.objects.create(
                    amount=deposit.penger,
                    created_at=aware_datetime,
                    account=SociBankAccount.objects.get(user__sg_id=deposit.person.id),
                    approved_at=aware_datetime,
                    description=deposit.kommentar,
                    approved=deposit.godkjent,
                )
                deposit.created_at = aware_datetime
                if deposit.approved:
                    deposit.approved_at = aware_datetime
                deposit.save()
