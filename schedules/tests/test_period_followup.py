import datetime
from zoneinfo import ZoneInfo

from addict import Dict
from django.conf import settings
from django.core import mail
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
)
from schedules.tests.factories import (
    ScheduleFactory,
    ShiftFactory,
    internal_group,
    member_of,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)


class FollowupTestCase(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        group = internal_group("Edgar")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=group)
        self.manager = UserWithPermissionsFactory.create(
            permissions="schedules.change_schedule", email="manager@example.com"
        )
        member_of(self.manager, group, Type.FUNCTIONARY)
        self.anna = self.on_roster("anna", DefaultAvailability.AVAILABLE)
        self.bob = self.on_roster("bob", DefaultAvailability.AVAILABLE)
        self.per = self.on_roster("per", DefaultAvailability.OPT_IN)
        today = timezone.localdate()
        self.day = today + datetime.timedelta(days=10)
        self.period = PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=self.day,
            date_to=self.day + datetime.timedelta(days=6),
            deadline=timezone.now() + datetime.timedelta(days=3),
        )
        self.shift = self.shift_on(self.day)
        for _ in range(2):
            ShiftSlot.objects.create(shift=self.shift, role=RoleOption.BARISTA)
        self.other = self.shift_on(self.day + datetime.timedelta(days=1))
        ShiftSlot.objects.create(shift=self.other, role=RoleOption.BARISTA)

    def on_roster(self, name, default):
        user = UserFactory.create(email=f"{name}@example.com", first_name=name)
        ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=user,
            autofill_as=RoleOption.BARISTA,
            default_availability=default,
        )
        return user

    def shift_on(self, day):
        start = datetime.datetime.combine(day, datetime.time(16), tzinfo=LOCAL)
        return ShiftFactory.create(
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=5),
        )

    def answer(self, user, shift, interest_type, note="", source=None):
        ShiftInterest.objects.create(
            shift=shift,
            user=user,
            interest_type=interest_type,
            note=note,
            source=source or ShiftInterest.Source.MANUAL,
        )

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    def period_id(self):
        return to_global_id("PlanningPeriodNode", self.period.pk)


class TestReminder(FollowupTestCase):
    REMIND = """
        mutation Remind($id: ID!) {
          sendPlanningPeriodReminder(planningPeriodId: $id) {
            recipients
            planningPeriod { reminderSentAt }
          }
        }
    """

    def remind(self, user=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.execute(self.REMIND, {"id": self.period_id()}, user)

    def test__the_reminder__goes_to_roster_users_with_the_default_available(self):
        executed = self.remind()
        self.assertNotIn("errors", executed)
        result = executed["data"]["sendPlanningPeriodReminder"]
        self.assertEqual(result["recipients"], 2)
        self.assertIsNotNone(result["planningPeriod"]["reminderSentAt"])
        self.assertEqual(
            sorted(message.to[0] for message in mail.outbox),
            ["anna@example.com", "bob@example.com"],
        )

    def test__the_reminder__ignores_notify_on_shift(self):
        self.anna.notify_on_shift = False
        self.anna.save()
        self.remind()
        self.assertIn(["anna@example.com"], [message.to for message in mail.outbox])

    def test__the_reminder__has_the_deadline_and_a_link(self):
        self.remind()
        body = mail.outbox[0].body
        deadline = timezone.localtime(self.period.deadline, LOCAL)
        self.assertIn(deadline.strftime("%d.%m kl %H:%M"), body)
        self.assertIn(settings.APP_URL + "/schedules/me/availability", body)

    def test__a_closed_period__gets_no_reminder(self):
        self.period.deadline = timezone.now() - datetime.timedelta(minutes=1)
        self.period.save()
        self.assertIn("errors", self.remind())
        self.assertEqual(mail.outbox, [])

    def test__a_member__cannot_send_reminders(self):
        self.assertIn("errors", self.remind(user=self.anna))
        self.assertEqual(mail.outbox, [])


class TestResponseNumbers(FollowupTestCase):
    STATS = """
        query Stats($id: ID!) {
          planningPeriod(id: $id) {
            responseStats {
              rosterCount
              optInCount
              usersWithAnswers
              optInWithInterest
              interested
              available
              unavailable
              unavailablePrefilled
              withNote
            }
          }
        }
    """

    def stats(self, user=None):
        executed = self.execute(self.STATS, {"id": self.period_id()}, user)
        self.assertNotIn("errors", executed)
        return executed["data"]["planningPeriod"]["responseStats"]

    def test__the_numbers_count_the_answers_in_the_period(self):
        self.answer(self.anna, self.shift, ShiftInterest.InterestTypes.INTERESTED)
        self.answer(
            self.anna,
            self.other,
            ShiftInterest.InterestTypes.UNAVAILABLE,
            note="Forelesning",
            source=ShiftInterest.Source.UNAVAILABILITY,
        )
        self.answer(
            self.bob, self.shift, ShiftInterest.InterestTypes.UNAVAILABLE, note="Syk"
        )
        self.answer(self.per, self.other, ShiftInterest.InterestTypes.AVAILABLE)
        self.assertEqual(
            self.stats(),
            {
                "rosterCount": 3,
                "optInCount": 1,
                "usersWithAnswers": 3,
                "optInWithInterest": 1,
                "interested": 1,
                "available": 1,
                "unavailable": 2,
                "unavailablePrefilled": 1,
                "withNote": 2,
            },
        )

    def test__a_prefilled_answer__is_not_an_answer_from_the_user(self):
        self.answer(
            self.anna,
            self.shift,
            ShiftInterest.InterestTypes.UNAVAILABLE,
            source=ShiftInterest.Source.UNAVAILABILITY,
        )
        self.assertEqual(self.stats()["usersWithAnswers"], 0)

    def test__a_member__gets_no_numbers(self):
        self.assertIsNone(self.stats(user=self.anna))


class TestSlotCoverage(FollowupTestCase):
    COVERAGE = """
        query Coverage($id: ID!) {
          planningPeriod(id: $id) {
            slotCoverage {
              shift { id }
              role
              slotCount
              openSlotCount
              candidateCount
              interestedCount
              unavailableCount
              unavailableWithNoteCount
            }
          }
        }
    """

    def coverage(self, user=None):
        executed = self.execute(self.COVERAGE, {"id": self.period_id()}, user)
        self.assertNotIn("errors", executed)
        return executed["data"]["planningPeriod"]["slotCoverage"]

    def test__the_shift_with_the_fewest_spare_candidates__is_first(self):
        self.answer(self.anna, self.shift, ShiftInterest.InterestTypes.UNAVAILABLE)
        self.answer(
            self.bob, self.shift, ShiftInterest.InterestTypes.UNAVAILABLE, note="Syk"
        )
        self.answer(self.per, self.shift, ShiftInterest.InterestTypes.INTERESTED)
        rows = self.coverage()
        self.assertEqual(
            rows[0],
            {
                "shift": {"id": to_global_id("ShiftNode", self.shift.pk)},
                "role": "BARISTA",
                "slotCount": 2,
                "openSlotCount": 2,
                "candidateCount": 1,
                "interestedCount": 1,
                "unavailableCount": 2,
                "unavailableWithNoteCount": 1,
            },
        )
        # anna and bob can work the other shift; per (opt in) did not answer
        self.assertEqual(rows[1]["candidateCount"], 2)

    def test__a_filled_slot__is_not_open(self):
        slot = self.other.slots.get()
        slot.user = self.anna
        slot.save()
        other = [row for row in self.coverage() if row["slotCount"] == 1][0]
        self.assertEqual(other["openSlotCount"], 0)

    def test__a_member__gets_no_coverage(self):
        self.assertEqual(self.coverage(user=self.anna), [])
