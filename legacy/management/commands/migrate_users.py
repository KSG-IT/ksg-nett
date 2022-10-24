from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

"""
 email = models.TextField(unique=True, blank=True, null=True)
    passord = models.CharField(max_length=32)
    kortnummer = models.CharField(max_length=10, blank=True, null=True)
    status = models.ForeignKey('Status', models.DO_NOTHING, db_column='status')
    navn = models.TextField(blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    hjemstedsadresse = models.TextField(blank=True, null=True)
    studie = models.TextField(blank=True, null=True)
    fodselsdato = models.DateField(blank=True, null=True)
    telefon = models.TextField(blank=True, null=True)
    begynte = models.CharField(max_length=6, blank=True, null=True)
    saldo = models.FloatField()
    sistonline = models.DateTimeField(blank=True, null=True)
    login = models.TextField(blank=True, null=True)
    by = models.TextField(blank=True, null=True)
    stilling = models.ForeignKey(Grupper, models.DO_NOTHING, db_column='stilling', blank=True, null=True)
"""
from legacy.models import Personer
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
                split_name = user.navn.split(" ")
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

                new_user = User.objects.create(
                    email=user.email,
                    username=user.email,
                    first_name=first_name,
                    last_name=last_name,
                    migrated_from_sg=True,
                    date_of_birth=user.fodselsdato,
                    study_address=user.adresse,
                    home_town=user.hjemstedsadresse,
                    phone=user.telefon,
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

                bank_account = SociBankAccount.objects.create(
                    user=new_user,
                    balance=user.saldo,
                    card_uuid=card_uuid,
                )
