import datetime
from zoneinfo import ZoneInfo

from addict import Dict
from django.conf import settings
from django.core import mail
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
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
    ShiftSlot,
    ShiftSlotDraft,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ShiftFactory,
    internal_group,
    member_of,
)
from schedules.utils.roster import annotate_shift_counts
from users.tests.factories import UserFactory, UserWithPermissionsFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)


class DraftTestCase(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.edgar = internal_group("Edgar")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=self.edgar)
        self.manager = UserWithPermissionsFactory.create(
            permissions=("schedules.change_schedule", "schedules.change_shiftslot"),
            email="manager@example.com",
        )
        member_of(self.manager, self.edgar, Type.FUNCTIONARY)
        self.anna = UserFactory.create(email="anna@example.com", notify_on_shift=True)
        self.bob = UserFactory.create(email="bob@example.com", notify_on_shift=False)
        self.day = timezone.localdate() + datetime.timedelta(days=10)
        self.first = self.slot(self.day)
        self.second = self.slot(self.day)
        self.later = self.slot(self.day + datetime.timedelta(days=7))

    def slot(self, day, user=None):
        start = datetime.datetime.combine(day, datetime.time(16), tzinfo=LOCAL)
        shift = ShiftFactory.create(
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=5),
        )
        return ShiftSlot.objects.create(shift=shift, user=user, role=RoleOption.BARISTA)

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    def schedule_id(self):
        return to_global_id("ScheduleNode", self.schedule.pk)

    DRAFT = """
        mutation Draft($slot: ID!, $user: ID) {
          draftSlot(shiftSlotId: $slot, userId: $user) {
            shiftSlot { user { id } draft { user { id } } }
          }
        }
    """

    def draft(self, slot, user, by=None):
        return self.execute(
            self.DRAFT,
            {
                "slot": to_global_id("ShiftSlotNode", slot.pk),
                "user": to_global_id("UserNode", user.pk) if user else None,
            },
            by,
        )

    LOCK = """
        mutation Lock($id: ID!, $from: Date, $to: Date) {
          lockDraft(scheduleId: $id, dateFrom: $from, dateTo: $to) {
            changedSlots notifiedUsers
          }
        }
    """

    def lock(self, date_from=None, date_to=None):
        with self.captureOnCommitCallbacks(execute=True):
            executed = self.execute(
                self.LOCK,
                {
                    "id": self.schedule_id(),
                    "from": date_from.isoformat() if date_from else None,
                    "to": date_to.isoformat() if date_to else None,
                },
            )
        self.assertNotIn("errors", executed)
        return executed["data"]["lockDraft"]


class TestDraftSlot(DraftTestCase):
    def test__a_draft__does_not_change_the_slot(self):
        executed = self.draft(self.first, self.anna)
        self.assertNotIn("errors", executed)
        slot = executed["data"]["draftSlot"]["shiftSlot"]
        self.assertIsNone(slot["user"])
        self.assertEqual(
            slot["draft"]["user"]["id"], to_global_id("UserNode", self.anna.pk)
        )
        self.first.refresh_from_db()
        self.assertIsNone(self.first.user)
        self.assertEqual(ShiftSlotDraft.objects.get().changed_by, self.manager)

    def test__a_manual_draft__has_no_autofill_run(self):
        self.draft(self.first, self.anna)
        executed = self.execute(
            """
            query Drafts($id: ID!, $from: Date!) {
              schedule(id: $id) {
                shiftsFromRange(shiftsFrom: $from, numberOfWeeks: 1) {
                  slots { draft { autofillRun { id } } }
                }
              }
            }
            """,
            {"id": self.schedule_id(), "from": self.day.isoformat()},
        )
        self.assertNotIn("errors", executed)
        drafts = [
            slot["draft"]
            for shift in executed["data"]["schedule"]["shiftsFromRange"]
            for slot in shift["slots"]
            if slot["draft"]
        ]
        self.assertEqual(drafts, [{"autofillRun": None}])

    def test__shifts_from_range__does_not_query_per_slot(self):
        query = """
            query Slots($id: ID!, $from: Date!) {
              schedule(id: $id) {
                shiftsFromRange(shiftsFrom: $from, numberOfWeeks: 1) {
                  schedule { id }
                  slots { role user { id } draft { user { id } } }
                }
              }
            }
            """
        variables = {"id": self.schedule_id(), "from": self.day.isoformat()}

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                executed = self.execute(query, variables)
            self.assertNotIn("errors", executed)
            return len(queries)

        count_queries()  # Warm the permission and content type caches
        before = count_queries()
        for _ in range(5):
            slot = self.slot(self.day, user=UserFactory.create())
            ShiftSlotDraft.objects.create(slot=slot, user=self.anna)
        self.assertEqual(count_queries(), before)

    def test__normalized_shifts_from_range__does_not_query_per_shift(self):
        query = """
            query Normalized($id: ID!, $from: Date!) {
              normalizedShiftsFromRange(
                scheduleId: $id, shiftsFrom: $from, numberOfWeeks: 1
              ) {
                ... on ShiftDayWeek {
                  shiftDays {
                    shifts { isFilled schedule { id } slots { role user { id } } }
                  }
                }
              }
            }
            """
        variables = {"id": self.schedule_id(), "from": self.day.isoformat()}

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                executed = self.execute(query, variables)
            self.assertNotIn("errors", executed)
            return len(queries)

        count_queries()  # Warm the permission and content type caches
        before = count_queries()
        for _ in range(5):
            self.slot(self.day, user=UserFactory.create())
        self.assertEqual(count_queries(), before)

    def test__a_draft_back_to_the_current_user__removes_the_draft(self):
        self.draft(self.first, self.anna)
        self.draft(self.first, None)
        self.assertFalse(ShiftSlotDraft.objects.exists())

    def test__a_draft_without_a_user__removes_the_person_at_lock(self):
        self.first.user = self.anna
        self.first.save()
        self.draft(self.first, None)
        self.assertIsNone(ShiftSlotDraft.objects.get().user)
        self.lock()
        self.first.refresh_from_db()
        self.assertIsNone(self.first.user)

    def test__a_member__cannot_see_drafts(self):
        self.draft(self.first, self.anna)
        executed = self.execute(
            '{ shift(id: "%s") { slots { draft { id } } } }'
            % to_global_id("ShiftNode", self.first.shift_id),
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["shift"]["slots"], [{"draft": None}])

    def test__a_member__does_not_see_a_drafted_shift_as_their_own(self):
        self.draft(self.first, self.anna)
        executed = self.execute("{ myUpcomingShifts { id } }", user=self.anna)
        self.assertEqual(executed["data"]["myUpcomingShifts"], [])

    def test__a_manager_of_another_group__cannot_draft(self):
        other = UserWithPermissionsFactory.create(
            permissions=("schedules.change_schedule", "schedules.change_shiftslot"),
            email="other@example.com",
        )
        member_of(other, internal_group("Lyche"), Type.FUNCTIONARY)
        self.assertIn("errors", self.draft(self.first, self.anna, by=other))
        self.assertFalse(ShiftSlotDraft.objects.exists())

    def test__draft_count__counts_the_drafts_in_the_dates(self):
        self.draft(self.first, self.anna)
        self.draft(self.later, self.bob)
        executed = self.execute(
            '{ schedule(id: "%s") { all: draftCount on: draftCount(dateFrom: "%s",'
            ' dateTo: "%s") } }' % (self.schedule_id(), self.day, self.day)
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["schedule"], {"all": 2, "on": 1})


class TestLockAndDiscard(DraftTestCase):
    def test__lock__copies_the_drafts_to_the_slots(self):
        self.draft(self.first, self.anna)
        self.draft(self.second, self.bob)
        result = self.lock()
        self.assertEqual(result["changedSlots"], 2)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual((self.first.user, self.second.user), (self.anna, self.bob))
        self.assertFalse(ShiftSlotDraft.objects.exists())

    def test__lock__sends_one_email_per_user_with_the_setting(self):
        self.draft(self.first, self.anna)
        self.draft(self.later, self.anna)
        self.draft(self.second, self.bob)
        result = self.lock()
        self.assertEqual(result["notifiedUsers"], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["anna@example.com"])
        self.assertIn("2 nye vakter", mail.outbox[0].subject)

    def test__lock__keeps_drafts_outside_the_dates(self):
        self.draft(self.first, self.anna)
        self.draft(self.later, self.anna)
        self.lock(self.day, self.day)
        self.later.refresh_from_db()
        self.assertIsNone(self.later.user)
        self.assertEqual(ShiftSlotDraft.objects.get().slot, self.later)

    def test__lock__needs_a_manager(self):
        self.draft(self.first, self.anna)
        executed = self.execute(self.LOCK, {"id": self.schedule_id()}, user=self.anna)
        self.assertIn("errors", executed)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.user)

    def test__discard__deletes_the_drafts_in_the_dates(self):
        self.draft(self.first, self.anna)
        self.draft(self.later, self.anna)
        executed = self.execute(
            """
            mutation Discard($id: ID!, $from: Date, $to: Date) {
              discardDraft(scheduleId: $id, dateFrom: $from, dateTo: $to) { discarded }
            }
            """,
            {"id": self.schedule_id(), "from": str(self.day), "to": str(self.day)},
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["discardDraft"]["discarded"], 1)
        self.assertEqual(ShiftSlotDraft.objects.get().slot, self.later)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.user)


class TestPublishPlanningPeriod(DraftTestCase):
    PUBLISH = """
        mutation Publish($id: ID!) {
          publishPlanningPeriod(id: $id) {
            planningPeriod { status }
            changedSlots
          }
        }
    """

    def setUp(self) -> None:
        super().setUp()
        self.period = PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=self.day,
            date_to=self.day + datetime.timedelta(days=2),
            deadline=timezone.now() - datetime.timedelta(days=1),
        )

    def publish(self, user=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.execute(
                self.PUBLISH,
                {"id": to_global_id("PlanningPeriodNode", self.period.pk)},
                user,
            )

    def test__publish__locks_the_drafts_of_the_period(self):
        self.draft(self.first, self.anna)
        self.draft(self.later, self.anna)
        executed = self.publish()
        self.assertNotIn("errors", executed)
        result = executed["data"]["publishPlanningPeriod"]
        self.assertEqual(result["planningPeriod"]["status"], "PUBLISHED")
        self.assertEqual(result["changedSlots"], 1)
        self.later.refresh_from_db()
        self.assertIsNone(self.later.user)

    def test__publish__needs_a_manager(self):
        self.assertIn("errors", self.publish(user=self.anna))
        self.period.refresh_from_db()
        self.assertIsNone(self.period.published_at)


class TestDraftsInRosterCounts(DraftTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.second.user = self.bob
        self.second.save()
        for user in (self.anna, self.bob):
            ScheduleRoster.objects.create(
                schedule=self.schedule,
                user=user,
                autofill_as=RoleOption.BARISTA,
                default_availability=DefaultAvailability.AVAILABLE,
            )
        # Anna gets the first slot. Bob loses his slot.
        self.draft(self.first, self.anna)
        self.draft(self.second, None)

    def planned(self, user, include_drafts):
        rows = annotate_shift_counts(
            ScheduleRoster.objects.filter(user=user), include_drafts=include_drafts
        )
        return rows.get().shifts_planned

    def test__with_drafts__counts_the_drafted_plan(self):
        self.assertEqual(self.planned(self.anna, True), 1)
        self.assertEqual(self.planned(self.bob, True), 0)

    def test__without_drafts__counts_the_slots(self):
        self.assertEqual(self.planned(self.anna, False), 0)
        self.assertEqual(self.planned(self.bob, False), 1)

    def test__the_roster__shows_drafts_to_a_manager_only(self):
        query = '{ schedule(id: "%s") { roster { user { id } shiftsPlanned } } }' % (
            self.schedule_id()
        )
        manager_rows = self.execute(query)["data"]["schedule"]["roster"]
        anna_id = to_global_id("UserNode", self.anna.pk)
        self.assertEqual(
            {row["user"]["id"]: row["shiftsPlanned"] for row in manager_rows}[anna_id],
            1,
        )
        own_rows = self.execute(query, user=self.anna)["data"]["schedule"]["roster"]
        self.assertEqual(own_rows, [{"user": {"id": anna_id}, "shiftsPlanned": 0}])
