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
        styret_keywords = [
            "styret",
            "styret møte",
            "styretmøte",
            "styremøte",
            "styre",
            "syre",
        ]
        drift_keywords = ["drift", "driftsmøte", "driftsmøtet"]
        souschef_keywords = [
            "souschef",
            "souschefmøte",
            "souschefmøtet",
            "Souchefmøte",
            "sc",
            "kjøkken",
        ]
        hovmester_keywords = [
            "hovmester",
            "hovmestermøte",
            "hovmestermøtet",
            "hm",
            "HM-møte",
        ]
        kafeansvarlig_keywords = [
            "kafeansvarlig",
            "kafeansvarligmøte",
            "kafeansvarligmøtet",
            "ka",
            "kake",
            "edgar",
        ]
        daglighallen_bar_keywords = [
            "daglighallen bar",
            "daglighallenbarmøte",
            "daglighallenbarmøtet",
            "dh",
            "bar",
        ]
        brygg_keywords = ["brygg", "bryggmøte", "bryggmøtet", "bryggemøte"]
        arrangement_keywords = [
            "arrangement",
            "arrangementmøte",
            "arrangementmøtet",
            "arr",
            "arrangements",
        ]
        barsjef_keywords = [
            "barsjef",
            "barsjefmøte",
            "barsjefmøtet",
            "Ba r Sj eF mØT e",
            "Baar sjef møte",
            "baarsjefene",
            "Ba r sje f mø te",
            "B arsj efm øte",
            "BASJEFMØTE",
        ]
        spritbarsjef_keywords = [
            "spritbarsjef",
            "spritbarsjefmøte",
            "spritbarsjefmøtet",
            "sprit",
            "sbs",
        ]
        oko_keywords = ["øko", "økomøte", "Økomøte"]

        styret = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in styret_keywords))
        )
        styret = styret.exclude(tittel__icontains="drift")
        drift = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in drift_keywords))
        ).exclude(id__in=[x.id for x in styret])

        souschef = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in souschef_keywords))
        )
        hovmester = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in hovmester_keywords))
        )
        kafeansvarlig = legacy_summaries.filter(
            reduce(
                operator.or_, (Q(tittel__icontains=x) for x in kafeansvarlig_keywords)
            )
        )
        daglighallen_bar = legacy_summaries.filter(
            reduce(
                operator.or_,
                (Q(tittel__icontains=x) for x in daglighallen_bar_keywords),
            )
        )
        brygg = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in brygg_keywords))
        )
        arrangement = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in arrangement_keywords))
        )
        barsjef = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in barsjef_keywords))
        )
        spritbarsjef = legacy_summaries.filter(
            reduce(
                operator.or_, (Q(tittel__icontains=x) for x in spritbarsjef_keywords)
            )
        )
        oko = legacy_summaries.filter(
            reduce(operator.or_, (Q(tittel__icontains=x) for x in oko_keywords))
        )
        ksg_it = legacy_summaries.filter(
            reduce(
                operator.or_,
                (Q(tittel__icontains=x) for x in ["ksg-it", "kit", "KSG-IT"]),
            )
        )

        rest = (
            legacy_summaries.exclude(id__in=[x.id for x in styret])
            .exclude(id__in=[x.id for x in drift])
            .exclude(id__in=[x.id for x in souschef])
            .exclude(id__in=[x.id for x in hovmester])
            .exclude(id__in=[x.id for x in kafeansvarlig])
            .exclude(id__in=[x.id for x in daglighallen_bar])
            .exclude(id__in=[x.id for x in brygg])
            .exclude(id__in=[x.id for x in arrangement])
            .exclude(id__in=[x.id for x in barsjef])
            .exclude(id__in=[x.id for x in spritbarsjef])
            .exclude(id__in=[x.id for x in oko])
            .exclude(id__in=[x.id for x in ksg_it])
        )

        with transaction.atomic():
            internal_group_styret = InternalGroup.objects.get(name="Styret")
            create_summary(styret, internal_group=internal_group_styret)

            create_summary(drift, internal_group=None)

            internal_group_souschef = InternalGroup.objects.get(name="Lyche kjøkken")
            create_summary(souschef, internal_group=internal_group_souschef)

            internal_group_hovmester = InternalGroup.objects.get(name="Lyche bar")
            create_summary(hovmester, internal_group=internal_group_hovmester)

            internal_group_kafeansvarlig = InternalGroup.objects.get(name="Edgar")
            create_summary(kafeansvarlig, internal_group=internal_group_kafeansvarlig)

            internal_group_daglighallen_bar = InternalGroup.objects.get(
                name="Daglighallen bar"
            )
            create_summary(
                daglighallen_bar, internal_group=internal_group_daglighallen_bar
            )

            internal_group_brygg = InternalGroup.objects.get(
                name="Daglighallen bryggeri"
            )
            create_summary(brygg, internal_group=internal_group_brygg)

            internal_group_arrangement = InternalGroup.objects.get(name="Arrangement")
            create_summary(arrangement, internal_group=internal_group_arrangement)

            internal_group_barsjef = InternalGroup.objects.get(name="Bargjengen")
            create_summary(barsjef, internal_group=internal_group_barsjef)

            internal_group_spritbarsjef = InternalGroup.objects.get(name="Spritgjengen")
            create_summary(spritbarsjef, internal_group=internal_group_spritbarsjef)

            internal_group_oko = InternalGroup.objects.get(name="Økonomigjengen")
            create_summary(oko, internal_group=internal_group_oko)

            internal_group_ksg_it = InternalGroup.objects.get(name="KSG-IT")
            create_summary(ksg_it, internal_group=internal_group_ksg_it)

            create_summary(rest, internal_group=None)
