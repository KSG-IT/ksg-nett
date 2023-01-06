from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import (
    Verv,
    Grupper,
    Status,
    Vervhistorikk,
    Grupperhistorikk,
    Statushistorikk,
)
from organization.models import LegacyUserWorkHistory
from users.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_user_work_history()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_user_work_history(self):
        verv = Verv.objects.using("legacy").all()
        grupper = Grupper.objects.using("legacy").all()
        status = Status.objects.using("legacy").all()

        verv_history = Vervhistorikk.objects.using("legacy").all()
        grupper_history = Grupperhistorikk.objects.using("legacy").all()
        status_history = Statushistorikk.objects.using("legacy").all()

        # Get all unique user ids in verv_history
        verv_user_ids = list(set(verv_history.values_list("person", flat=True)))
        grupper_user_ids = list(set(grupper_history.values_list("person", flat=True)))
        status_user_ids = list(set(status_history.values_list("person", flat=True)))

        with transaction.atomic():
            print(len(verv_user_ids))
            print(len(grupper_user_ids))
            print(len(status_user_ids))

            for user_id in verv_user_ids:
                user_verv_history = verv_history.using("legacy").filter(person=user_id)
                user = User.objects.get(sg_id=user_id)

                print(f"migrating verv history for {user.get_full_name()}")
                for verv_history_entry in user_verv_history:
                    # get verv object
                    verv_reference = Verv.objects.using("legacy").get(
                        id=verv_history_entry.verv.id
                    )
                    ref = LegacyUserWorkHistory.objects.create(
                        user=user,
                        identifying_name=f"{verv_reference.navn}, {verv_reference.status.navn}",
                        date_from=verv_history_entry.fradato,
                        date_to=verv_history_entry.tildato,
                    )
            for user_id in grupper_user_ids:
                user_group_history = grupper_history.using("legacy").filter(
                    person=user_id
                )
                user = User.objects.get(sg_id=user_id)
                print(f"created verv history entry {ref}")
                for grupper_history_entry in user_group_history:
                    grupper_reference = Grupper.objects.using("legacy").get(
                        id=grupper_history_entry.gruppe.id
                    )
                    ref = LegacyUserWorkHistory.objects.create(
                        user=user,
                        identifying_name=f"{grupper_reference.navn}: {grupper_reference.stillingsnavn}",
                        date_from=grupper_history_entry.fradato,
                        date_to=grupper_history_entry.tildato,
                    )
                    print(f"created verv history entry {ref}")

            for user_id in status_user_ids:
                user_status_history = status_history.using("legacy").filter(
                    person=user_id
                )
                user = User.objects.get(sg_id=user_id)
                for status_history_entry in user_status_history:
                    status_reference = Status.objects.using("legacy").get(
                        id=status_history_entry.status.id
                    )
                    ref = LegacyUserWorkHistory.objects.create(
                        user=user,
                        identifying_name=status_reference.navn,
                        date_from=status_history_entry.fradato,
                        date_to=status_history_entry.tildato,
                    )

                    print(f"created verv history entry {ref}")

            print(f"Done migrating user work history")
            print(
                f"Created {LegacyUserWorkHistory.objects.count()} work history entries"
            )
