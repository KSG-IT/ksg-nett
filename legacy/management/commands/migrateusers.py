from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from common.util import strip_chars_from_string
from legacy.models import Personer
from schedules.utils.schedules import create_i_cal_token_for_user
from users.models import User
from economy.models import SociBankAccount


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_users()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_users(self):
        legacy_users = Personer.objects.using("legacy").all()
        self.stdout.write(self.style.SUCCESS("Migrating legacy users to new table"))
        self.stdout.write(self.style.SUCCESS(f"Migrating {len(legacy_users)} users"))
        with transaction.atomic():
            for (_, user) in enumerate(legacy_users):
                self.stdout.write(self.style.SUCCESS(f"Migrerer bruker: {user.navn}"))

                stripped_name = strip_chars_from_string(
                    user.navn, ["(", ")", '"' "«", '"', "«", "«", "»", "»"]
                )
                print(f"{user.navn} -> {stripped_name}")
                split_name = stripped_name.split(" ")
                first_name = split_name[0].strip()
                last_name = " ".join(split_name[1:]).strip()

                if first_name.lower() == "z":
                    self.stdout.write(f"Found user with first name 'z', cleaning up")
                    self.stdout.write(
                        f"First name: {first_name} Last name: {last_name}"
                    )
                    split_name = last_name.split(" ")
                    first_name = split_name[0].strip()
                    last_name = " ".join(split_name[1:]).strip()
                    self.stdout.write(f"Cleaned name: {first_name} {last_name}")

                # truncate max length fields
                first_name = first_name[:30]
                last_name = last_name[:30]
                user.studie = user.studie[:50]
                user.hjemstedsadresse = user.hjemstedsadresse[:50]
                user.adresse = user.adresse[:50]
                user.telefon = user.telefon[:50]

                new_user = User.objects.create(
                    migrated_from_sg=True,
                    sg_id=user.id,
                    email=user.email,
                    username=user.email,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=user.fodselsdato,
                    study_address=user.adresse.strip(),
                    study=user.studie.strip(),
                    home_town=user.hjemstedsadresse.strip(),
                    phone=user.telefon.strip(),
                    # Default to is_active=False and set true in migration wizard
                    is_active=False,
                    requires_migration_wizard=True,
                )
                card_uuid = user.kortnummer

                if card_uuid:
                    card_uuid = card_uuid.strip()

                if card_uuid == "":
                    self.stdout.write(f"Invalid card_uuid, setting to null")
                    card_uuid = None
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Oppretter bankkonto: (kornummer: {card_uuid}, saldo: {user.saldo})"
                    )
                )
                exist_check = SociBankAccount.objects.filter(
                    card_uuid=card_uuid
                ).exists()
                if exist_check:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Bankkonto med kortnummer {card_uuid} eksisterer allerede"
                        )
                    )
                    card_uuid = None

                SociBankAccount.objects.create(
                    user=new_user,
                    balance=user.saldo,
                    card_uuid=card_uuid,
                )
