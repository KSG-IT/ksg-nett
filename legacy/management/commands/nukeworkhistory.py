from django.core.management.base import BaseCommand, CommandError

from organization.models import LegacyUserWorkHistory


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.nuke_migrated_users()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def nuke_migrated_users(self):
        self.stdout.write(self.style.SUCCESS("🧨🧨🧨 legacy work history"))
        data = LegacyUserWorkHistory.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"{data}"))
