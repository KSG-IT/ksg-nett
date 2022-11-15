from functools import reduce

import pytz
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from legacy.models import Referater
from organization.models import InternalGroup
from summaries.models import Summary
from users.models import User

import operator
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery


def create_summary(summaries, internal_group=None):
    for legacy_summary in summaries:
        summary = Summary()
        summary.internal_group = None
        content_with_attendees = legacy_summary.tilstede + "\n" + legacy_summary.innhold
        summary.contents = content_with_attendees
        summary.date = legacy_summary.dato
        reporter = User.objects.filter(sg_id=legacy_summary.referent.id).first()
        summary.reporter = reporter
        summary.save()

        registered = legacy_summary.registrert

        if not hasattr(registered, "tz_info"):
            registered = timezone.make_aware(
                legacy_summary.registrert,
                timezone=pytz.timezone(settings.TIME_ZONE),
            )

        if internal_group:
            legacy_summary.internal_group = internal_group
            summary.title = None
        else:
            summary.title = legacy_summary.tittel
        summary.created_at = registered
        summary.updated_at = registered
        summary.save()


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
            create_summary(legacy_summaries, internal_group=None)
