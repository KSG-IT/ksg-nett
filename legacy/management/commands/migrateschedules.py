from django.core.management.base import BaseCommand, CommandError

from legacy.models import Arrangementer, Barer, Bartyper


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_schedules()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_schedules(self):
        self.stdout.write(self.style.SUCCESS("Migrating legacy schedules to new table"))
        legacy_bars = Barer.objects.using("legacy").all()
        for bar in legacy_bars:
            print(bar.navn)

        legacy_shift = Arrangementer.objects.using("legacy").all()
        for shift in legacy_shift:
            print(shift.tittel)

        legacy_bar_types = Bartyper.objects.using("legacy").all()
        for bar_type in legacy_bar_types:
            print(bar_type.navn)
