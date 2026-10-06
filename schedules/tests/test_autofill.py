import datetime
from zoneinfo import ZoneInfo

from addict import Dict
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from organization.consts import InternalGroupPositionMembershipType as Type
from schedules.models import (
    DefaultAvailability,
    PlanningPeriod,
    RoleOption,
    ScheduleRoster,
    ShiftInterest,
    ShiftSlot,
    ShiftSlotDraft,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ShiftFactory,
    internal_group,
    member_of,
)
from schedules.utils.autofill import UnfilledReason, revert_autofill_run, run_autofill
from users.tests.factories import UserFactory, UserWithPermissionsFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)
INTERESTED = ShiftInterest.InterestTypes.INTERESTED
AVAILABLE = ShiftInterest.InterestTypes.AVAILABLE
UNAVAILABLE = ShiftInterest.InterestTypes.UNAVAILABLE


class AutofillTestCase(TestCase):
    def setUp(self) -> None:
        self.schedule = ScheduleFactory.create(name="Edgar", max_shifts_per_week=2)
        today = timezone.localdate()
        # A Monday at least a week ahead, so all shifts are in the future
        self.monday = today + datetime.timedelta(days=14 - today.weekday())
        self.period = PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=self.monday,
            date_to=self.monday + datetime.timedelta(days=13),
            deadline=timezone.now() - datetime.timedelta(hours=1),
        )
        self.users = {}

    def user(self, name, default=DefaultAvailability.AVAILABLE, role=None, cap=None):
        user = UserFactory.create(email=f"{name}@example.com", first_name=name)
        ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=user,
            autofill_as=role or RoleOption.BARISTA,
            default_availability=default,
            shift_cap=cap,
        )
        self.users[name] = user
        return user

    def slot(
        self, day_offset, hour=16, role=RoleOption.BARISTA, user=None, schedule=None
    ):
        day = self.monday + datetime.timedelta(days=day_offset)
        start = datetime.datetime.combine(day, datetime.time(hour), tzinfo=LOCAL)
        shift = ShiftFactory.create(
            schedule=schedule or self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=4),
        )
        return ShiftSlot.objects.create(shift=shift, user=user, role=role)

    def answer(self, user, slot, interest_type):
        ShiftInterest.objects.create(
            shift=slot.shift, user=user, interest_type=interest_type
        )

    def filled_by(self, slot):
        draft = ShiftSlotDraft.objects.filter(slot=slot).first()
        return draft.user if draft else None

    def reasons(self, run):
        return {row["slot"]: row["reason"] for row in run.unfilled}


class TestCandidates(AutofillTestCase):
    def test__an_empty_slot__gets_an_available_user_as_a_draft(self):
        anna = self.user("anna")
        slot = self.slot(0)
        run = run_autofill(self.period)
        draft = ShiftSlotDraft.objects.get()
        self.assertEqual(
            (draft.slot, draft.user, draft.autofill_run), (slot, anna, run)
        )
        slot.refresh_from_db()
        self.assertIsNone(slot.user)
        self.assertEqual(run.unfilled, [])

    def test__a_filled_slot_and_a_slot_with_a_manual_draft__are_skipped(self):
        anna = self.user("anna")
        self.user("bob")
        self.slot(0, user=anna)
        manual = self.slot(1)
        ShiftSlotDraft.objects.create(slot=manual, user=None)
        run_autofill(self.period)
        self.assertEqual(
            ShiftSlotDraft.objects.filter(autofill_run__isnull=False).count(), 0
        )

    def test__a_user_who_cannot_work__is_not_chosen(self):
        anna = self.user("anna")
        slot = self.slot(0)
        self.answer(anna, slot, UNAVAILABLE)
        run = run_autofill(self.period)
        self.assertIsNone(self.filled_by(slot))
        self.assertEqual(self.reasons(run), {slot.pk: UnfilledReason.NO_CANDIDATES})

    def test__an_opt_in_user__is_chosen_only_with_an_answer(self):
        per = self.user("per", default=DefaultAvailability.OPT_IN)
        silent = self.slot(0)
        asked = self.slot(2)
        self.answer(per, asked, INTERESTED)
        run_autofill(self.period)
        self.assertIsNone(self.filled_by(silent))
        self.assertEqual(self.filled_by(asked), per)

    def test__only_users_with_the_role__are_chosen(self):
        self.user("anna")
        slot = self.slot(0, role=RoleOption.KAFEANSVARLIG)
        run = run_autofill(self.period)
        self.assertEqual(self.reasons(run), {slot.pk: UnfilledReason.NO_ROLE_ON_ROSTER})


class TestOrder(AutofillTestCase):
    def test__the_user_with_fewer_shifts__wins_over_interest(self):
        anna = self.user("anna")
        bob = self.user("bob")
        self.slot(-7, user=anna)  # before the period, still counted
        slot = self.slot(0)
        self.answer(anna, slot, INTERESTED)
        run_autofill(self.period)
        self.assertEqual(self.filled_by(slot), bob)

    def test__interested__wins_over_available_at_equal_counts(self):
        self.user("anna")
        bob = self.user("bob")
        slot = self.slot(0)
        self.answer(bob, slot, INTERESTED)
        run_autofill(self.period)
        self.assertEqual(self.filled_by(slot), bob)

    def test__the_hardest_slot__is_filled_first(self):
        anna = self.user("anna")
        bob = self.user("bob")
        easy = self.slot(0, hour=10)
        hard = self.slot(0, hour=16)
        self.answer(anna, hard, UNAVAILABLE)
        run_autofill(self.period)
        self.assertEqual((self.filled_by(hard), self.filled_by(easy)), (bob, anna))

    def test__one_user__gets_many_slots_over_the_period(self):
        anna = self.user("anna")
        slots = [self.slot(day) for day in (0, 2, 7, 9)]
        run_autofill(self.period)
        self.assertEqual([self.filled_by(slot) for slot in slots], [anna] * 4)


class TestRules(AutofillTestCase):
    def test__no_two_shifts_on_one_day(self):
        anna = self.user("anna")
        first = self.slot(0, hour=10)
        second = self.slot(0, hour=18)
        run = run_autofill(self.period)
        filled = [self.filled_by(first), self.filled_by(second)]
        self.assertEqual(filled.count(anna), 1)
        self.assertEqual(
            list(self.reasons(run).values()), [UnfilledReason.BUSY_SAME_DAY]
        )

    def test__a_shift_in_another_schedule__counts_for_the_same_day(self):
        anna = self.user("anna")
        self.slot(0, hour=10, user=anna, schedule=ScheduleFactory.create(name="Lyche"))
        slot = self.slot(0, hour=18)
        run_autofill(self.period)
        self.assertIsNone(self.filled_by(slot))

    def test__the_weekly_limit(self):
        self.schedule.max_shifts_per_week = 1
        self.schedule.save()
        anna = self.user("anna")
        monday = self.slot(0)
        wednesday = self.slot(2)
        next_week = self.slot(7)
        run = run_autofill(self.period)
        self.assertEqual(
            [self.filled_by(slot) for slot in (monday, wednesday, next_week)].count(
                anna
            ),
            2,
        )
        self.assertEqual(
            list(self.reasons(run).values()), [UnfilledReason.WEEKLY_LIMIT]
        )

    def test__the_shift_cap(self):
        per = self.user("per", default=DefaultAvailability.OPT_IN, cap=1)
        first = self.slot(0)
        second = self.slot(2)
        for slot in (first, second):
            self.answer(per, slot, INTERESTED)
        run = run_autofill(self.period)
        self.assertEqual([self.filled_by(first), self.filled_by(second)], [per, None])
        self.assertEqual(list(self.reasons(run).values()), [UnfilledReason.SHIFT_CAP])


class TestRerunAndRevert(AutofillTestCase):
    def test__a_rerun__replaces_autofill_drafts_and_keeps_manual_drafts(self):
        anna = self.user("anna")
        bob = self.user("bob")
        manual = self.slot(0)
        other = self.slot(2)
        ShiftSlotDraft.objects.create(slot=manual, user=bob)
        first = run_autofill(self.period)
        second = run_autofill(self.period)
        self.assertEqual(self.filled_by(manual), bob)
        self.assertEqual(ShiftSlotDraft.objects.get(slot=other).autofill_run, second)
        self.assertFalse(ShiftSlotDraft.objects.filter(autofill_run=first).exists())
        self.assertEqual(self.filled_by(other), anna)

    def test__revert__removes_only_the_drafts_of_the_run(self):
        self.user("anna")
        bob = self.user("bob")
        manual = self.slot(0)
        ShiftSlotDraft.objects.create(slot=manual, user=bob)
        self.slot(2)
        run = run_autofill(self.period)
        self.assertEqual(revert_autofill_run(run), 1)
        self.assertEqual(
            list(ShiftSlotDraft.objects.all()),
            [ShiftSlotDraft.objects.get(slot=manual)],
        )


class TestAutofillGraphQL(AutofillTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.graphql_client = Client(schema)
        group = internal_group("Edgar")
        self.schedule.internal_group = group
        self.schedule.save()
        self.manager = UserWithPermissionsFactory.create(
            permissions=("schedules.change_schedule", "schedules.change_shiftslot"),
            email="manager@example.com",
        )
        member_of(self.manager, group, Type.FUNCTIONARY)
        self.anna = self.user("anna")
        self.filled = self.slot(0)
        self.empty = self.slot(0, hour=20)

    def execute(self, query, variables, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    RUN = """
        mutation Run($id: ID!) {
          runAutofill(planningPeriodId: $id) {
            autofillRun {
              id
              draftCount
              unfilled { shiftSlot { id } reason candidateCount }
            }
          }
        }
    """

    def test__run_autofill__returns_the_drafts_and_the_empty_slots(self):
        executed = self.execute(
            self.RUN, {"id": to_global_id("PlanningPeriodNode", self.period.pk)}
        )
        self.assertNotIn("errors", executed)
        run = executed["data"]["runAutofill"]["autofillRun"]
        self.assertEqual(run["draftCount"], 1)
        self.assertEqual(
            run["unfilled"],
            [
                {
                    "shiftSlot": {"id": to_global_id("ShiftSlotNode", self.empty.pk)},
                    "reason": "BUSY_SAME_DAY",
                    "candidateCount": 1,
                }
            ],
        )

    def test__run_autofill__needs_a_manager(self):
        executed = self.execute(
            self.RUN,
            {"id": to_global_id("PlanningPeriodNode", self.period.pk)},
            user=self.anna,
        )
        self.assertIn("errors", executed)
        self.assertFalse(ShiftSlotDraft.objects.exists())

    def test__a_manual_change_of_an_autofill_draft__makes_it_manual(self):
        run_autofill(self.period)
        bob = self.user("bob")
        slot = ShiftSlotDraft.objects.get().slot
        executed = self.execute(
            """
            mutation Draft($slot: ID!, $user: ID) {
              draftSlot(shiftSlotId: $slot, userId: $user) { shiftSlot { id } }
            }
            """,
            {
                "slot": to_global_id("ShiftSlotNode", slot.pk),
                "user": to_global_id("UserNode", bob.pk),
            },
        )
        self.assertNotIn("errors", executed)
        self.assertIsNone(ShiftSlotDraft.objects.get(slot=slot).autofill_run)

    def test__revert_autofill_run(self):
        run = run_autofill(self.period)
        executed = self.execute(
            "mutation Revert($id: ID!) { revertAutofillRun(id: $id) { removedDrafts } }",
            {"id": to_global_id("ScheduleAutofillRunNode", run.pk)},
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["revertAutofillRun"]["removedDrafts"], 1)
        self.assertFalse(ShiftSlotDraft.objects.exists())
