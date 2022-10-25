from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.nuke_migrated_users()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def nuke_migrated_users(self):
        self.stdout.write(self.style.SUCCESS("🧨🧨🧨 migrated users"))
        data = User.objects.filter(migrated_from_sg=True).delete()
        self.stdout.write(self.style.SUCCESS(f"{data}"))
