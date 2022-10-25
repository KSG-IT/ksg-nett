from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import Referater
from summaries.models import LegacySummary
from users.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_summaries()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_summaries(self):
        self.stdout.write(self.style.SUCCESS("Migrating legacy summaries to new table"))
        legacy_summaries = Referater.objects.using("legacy").all()
        self.stdout.write(
            self.style.SUCCESS(f"Migrating {len(legacy_summaries)} summaries")
        )
        with transaction.atomic():
            for summary in legacy_summaries:
                self.stdout.write(
                    self.style.SUCCESS(f"Migrating summary: {summary.tittel}")
                )
                registered = timezone.make_aware(
                    summary.registrert, timezone.get_current_timezone()
                )
                reporter = User.objects.filter(sg_id=summary.referent.id).first()
                LegacySummary.objects.get_or_create(
                    date=summary.dato,
                    title=summary.tittel,
                    participants=summary.tilstede,
                    contents=summary.innhold,
                    reporter=reporter,
                    registered=registered,
                )
