import pytz
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import Sitater, Innskudd
from economy.models import Deposit, SociBankAccount

"""
person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
registrert = models.DateTimeField()
penger = models.FloatField()
type = models.CharField(max_length=1)
godkjent = models.BooleanField()
kommentar = models.TextField(blank=True, null=True)
"""


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
        with transaction.atomic():
            for deposit in legacy_deposits:

                # ToDo this timezone aware logic. Look at the timezone legacy objects
                aware_datetime = deposit.registrert
                if not aware_datetime.tzinfo:

                    aware_datetime = timezone.make_aware(
                        deposit.registrert, timezone=pytz.timezone(settings.TIME_ZONE)
                    )
                self.stdout.write(
                    self.style.SUCCESS(f"Migrating deposit: {deposit.kommentar}")
                )
                Deposit.objects.get_or_create(
                    amount=deposit.penger,
                    created_at=aware_datetime,
                    account=SociBankAccount.objects.filter(
                        user__sg_id=deposit.person.id
                    ).first(),
                    signed_off_time=aware_datetime,
                    description=deposit.kommentar,
                    migrated_from_sg=True,
                )
