from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import Sitater
from quotes.models import LegacyQuote, Quote


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

        with transaction.atomic():
            for (_, quote) in enumerate(legacy_quotes):
                self.stdout.write(self.style.SUCCESS(f"Migrerer sitat: {quote.tekst}"))
                # make quote.tid timezone aware
                datetime_created = quote.tid
                if not datetime_created.tzinfo:
                    datetime_created = timezone.make_aware(
                        quote.tid, timezone.get_current_timezone()
                    )

                Quote.objects.get_or_create(
                    text=quote.tekst,
                    created_at=datetime_created,
                    reported_by=None,
                    verified_by=None,
                    context=None,
                )
            self.stdout.write(self.style.SUCCESS("Done migrating quotes"))
