import datetime

from addict import Dict
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from organization.consts import InternalGroupPositionMembershipType as Type
from schedules.models import (
    RoleOption,
    Shift,
    ShiftInterest,
    ShiftSlot,
    ShiftSlotDraft,
    ShiftTemplate,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftFactory,
    ShiftSlotTemplateFactory,
    ShiftTemplateFactory,
    internal_group,
    member_of,
)
from schedules.utils.templates import apply_schedule_template, replace_impact
from users.tests.factories import UserFactory, UserWithPermissionsFactory


class TemplateTestCase(TestCase):
    def setUp(self) -> None:
        group = internal_group("Edgar")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=group)
        self.template = ScheduleTemplateFactory.create(schedule=self.schedule)
        for day in (ShiftTemplate.Day.MONDAY, ShiftTemplate.Day.WEDNESDAY):
            shift_template = ShiftTemplateFactory.create(
                name=f"Kveld {day}",
                schedule_template=self.template,
                day=day,
                time_start=datetime.time(16),
                time_end=datetime.time(21),
            )
            ShiftSlotTemplateFactory.create(
                shift_template=shift_template, role=RoleOption.BARISTA, count=2
            )
        today = timezone.localdate()
        self.monday = today + datetime.timedelta(days=14 - today.weekday())
        self.manager = UserWithPermissionsFactory.create(
            permissions=("schedules.add_shift",), email="manager@example.com"
        )
        member_of(self.manager, group, Type.FUNCTIONARY)

    def week(self, weeks_after=0):
        return self.monday + datetime.timedelta(weeks=weeks_after)

    def template_shifts(self):
        return Shift.objects.filter(generated_from=self.template)


class TestApplyScheduleTemplate(TemplateTestCase):
    def test__generating_twice__does_not_duplicate_shifts_or_slots(self):
        apply_schedule_template(self.template, self.week(), 2)
        apply_schedule_template(self.template, self.week(), 2)
        self.assertEqual(self.template_shifts().count(), 4)
        self.assertEqual(
            ShiftSlot.objects.filter(shift__generated_from=self.template).count(), 8
        )

    def test__a_start_in_the_middle_of_a_week__replaces_the_whole_week(self):
        apply_schedule_template(self.template, self.week(), 1)
        wednesday = self.week() + datetime.timedelta(days=2)
        apply_schedule_template(self.template, wednesday, 1)
        self.assertEqual(self.template_shifts().count(), 2)
        self.assertEqual(
            ShiftSlot.objects.filter(shift__generated_from=self.template).count(), 4
        )

    def test__shifts_after_the_range__are_kept(self):
        apply_schedule_template(self.template, self.week(3), 1)
        later = list(self.template_shifts())
        apply_schedule_template(self.template, self.week(), 1)
        self.assertTrue(all(Shift.objects.filter(pk=s.pk).exists() for s in later))
        self.assertEqual(self.template_shifts().count(), 4)

    def test__shifts_not_from_the_template__are_kept(self):
        start = timezone.make_aware(
            datetime.datetime.combine(self.week(), datetime.time(10))
        )
        manual = ShiftFactory.create(
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=4),
        )
        apply_schedule_template(self.template, self.week(), 1)
        self.assertTrue(Shift.objects.filter(pk=manual.pk).exists())


class TestReplaceImpact(TemplateTestCase):
    def test__counts_what_a_new_generation_would_delete(self):
        apply_schedule_template(self.template, self.week(), 1)
        anna = UserFactory.create(email="anna@example.com")
        first, second = ShiftSlot.objects.filter(
            shift__generated_from=self.template
        ).order_by("id")[:2]
        first.user = anna
        first.save()
        ShiftSlotDraft.objects.create(slot=second, user=anna)
        ShiftInterest.objects.create(
            shift=first.shift,
            user=anna,
            interest_type=ShiftInterest.InterestTypes.INTERESTED,
        )
        impact = replace_impact(self.template, self.week(), 1)
        self.assertEqual(
            (
                impact.shifts_to_create,
                impact.shifts_to_delete,
                impact.filled_slots_to_delete,
                impact.answers_to_delete,
                impact.drafts_to_delete,
            ),
            (2, 2, 1, 1, 1),
        )
        self.assertTrue(impact.needs_confirmation)

    def test__empty_shifts__need_no_confirmation(self):
        apply_schedule_template(self.template, self.week(), 1)
        self.assertFalse(
            replace_impact(self.template, self.week(), 1).needs_confirmation
        )


class TestGenerateMutation(TemplateTestCase):
    GENERATE = """
        mutation Generate($id: ID!, $start: Date!, $confirm: Boolean) {
          generateShiftsFromTemplate(
            scheduleTemplateId: $id, startDate: $start, numberOfWeeks: 1,
            confirmDelete: $confirm
          ) { shiftsCreated }
        }
    """
    PREVIEW = """
        query Preview($id: ID!, $start: Date!) {
          templateGenerationPreview(
            scheduleTemplateId: $id, startDate: $start, numberOfWeeks: 1
          ) {
            firstDay lastDay shiftsToCreate shiftsToDelete filledSlotsToDelete
            answersToDelete draftsToDelete needsConfirmation
          }
        }
    """

    def setUp(self) -> None:
        super().setUp()
        self.graphql_client = Client(schema)
        apply_schedule_template(self.template, self.week(), 1)
        slot = ShiftSlot.objects.filter(shift__generated_from=self.template).first()
        slot.user = UserFactory.create(email="anna@example.com")
        slot.save()

    def execute(self, query, confirm=None, user=None):
        variables = {
            "id": to_global_id("ScheduleTemplateNode", self.template.pk),
            "start": self.week().isoformat(),
        }
        if confirm is not None:
            variables["confirm"] = confirm
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    def test__a_delete_of_filled_slots__is_refused_without_confirmation(self):
        before = set(self.template_shifts().values_list("pk", flat=True))
        executed = self.execute(self.GENERATE)
        self.assertIn("errors", executed)
        self.assertIn("confirmDelete", executed["errors"][0]["message"])
        self.assertEqual(
            set(self.template_shifts().values_list("pk", flat=True)), before
        )

    def test__with_confirmation__the_week_is_generated_again(self):
        executed = self.execute(self.GENERATE, confirm=True)
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["generateShiftsFromTemplate"]["shiftsCreated"], 2
        )
        self.assertFalse(ShiftSlot.objects.filter(user__isnull=False).exists())

    def test__the_preview__shows_the_counts_and_the_dates(self):
        executed = self.execute(self.PREVIEW)
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["templateGenerationPreview"],
            {
                "firstDay": self.week().isoformat(),
                "lastDay": (self.week() + datetime.timedelta(days=6)).isoformat(),
                "shiftsToCreate": 2,
                "shiftsToDelete": 2,
                "filledSlotsToDelete": 1,
                "answersToDelete": 0,
                "draftsToDelete": 0,
                "needsConfirmation": True,
            },
        )

    def test__the_preview__needs_a_manager(self):
        member = UserFactory.create(email="member@example.com")
        self.assertIn("errors", self.execute(self.PREVIEW, user=member))
