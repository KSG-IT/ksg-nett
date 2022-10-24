from django.core.management.base import BaseCommand, CommandError

from legacy.models import Sitater
from quotes.models import LegacyQuote


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_quotes()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_quotes(self):
        legacy_quotes = Sitater.objects.using("legacy").all()
        self.stdout.write(self.style.SUCCESS("Migrating legacy quotes to new table"))
        self.stdout.write(self.style.SUCCESS(f"Migrating {len(legacy_quotes)} quotes"))
        for (_, quote) in enumerate(legacy_quotes):
            self.stdout.write(self.style.SUCCESS(f"Migrerer sitat: {quote.tekst}"))
            LegacyQuote.objects.get_or_create(
                text=quote.tekst,
                datetime_created=quote.tid,
            )
        self.stdout.write(self.style.SUCCESS("Done migrating quotes"))
