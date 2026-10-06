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
)
from schedules.tests.factories import (
    ScheduleFactory,
    ShiftFactory,
    internal_group,
    member_of,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)


def local(day, hour, minute=0):
    return datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=LOCAL)


class PlanningTestCase(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.edgar = internal_group("Edgar")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=self.edgar)
        self.manager = UserWithPermissionsFactory.create(
            permissions="schedules.change_schedule", email="manager@example.com"
        )
        member_of(self.manager, self.edgar, Type.FUNCTIONARY)
        self.anna = UserFactory.create(email="anna@example.com")
        ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=self.anna,
            autofill_as=RoleOption.BARISTA,
            default_availability=DefaultAvailability.AVAILABLE,
        )
        self.today = timezone.localdate()
        self.period = PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=self.today + datetime.timedelta(days=14),
            date_to=self.today + datetime.timedelta(days=41),
            deadline=timezone.now() + datetime.timedelta(days=6),
        )
        self.shift = self.shift_on(self.period.date_from, 18)

    def shift_on(self, day, hour, schedule=None):
        start = local(day, hour)
        return ShiftFactory.create(
            schedule=schedule or self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=5),
        )

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )


class TestPlanningPeriodModel(PlanningTestCase):
    def test__status__is_open_before_the_deadline(self):
        self.assertEqual(self.period.status, PlanningPeriod.Status.OPEN)

    def test__status__is_closed_after_the_deadline(self):
        self.period.deadline = timezone.now() - datetime.timedelta(minutes=1)
        self.assertEqual(self.period.status, PlanningPeriod.Status.CLOSED)

    def test__status__is_published_when_published_at_is_set(self):
        self.period.published_at = timezone.now()
        self.assertEqual(self.period.status, PlanningPeriod.Status.PUBLISHED)

    def test__a_shift__belongs_to_the_period_of_its_local_start_date(self):
        late = self.shift_on(self.period.date_to, 23)
        after = self.shift_on(self.period.date_to + datetime.timedelta(days=1), 0)
        self.assertEqual(PlanningPeriod.for_shift(late), self.period)
        self.assertIsNone(PlanningPeriod.for_shift(after))

    def test__shifts__lists_the_shifts_in_the_dates(self):
        self.shift_on(self.period.date_to + datetime.timedelta(days=1), 18)
        self.shift_on(self.period.date_to, 18, schedule=ScheduleFactory.create())
        self.assertEqual(list(self.period.shifts()), [self.shift])


class TestPlanningPeriodMutations(PlanningTestCase):
    CREATE = """
        mutation Create($input: CreatePlanningPeriodInput!) {
          createPlanningPeriod(input: $input) { planningPeriod { id status } }
        }
    """
    UPDATE = """
        mutation Update($id: ID!, $input: UpdatePlanningPeriodInput!) {
          updatePlanningPeriod(id: $id, input: $input) { planningPeriod { status } }
        }
    """

    def create(self, date_from, date_to, user=None):
        return self.execute(
            self.CREATE,
            {
                "input": {
                    "scheduleId": to_global_id("ScheduleNode", self.schedule.pk),
                    "dateFrom": date_from.isoformat(),
                    "dateTo": date_to.isoformat(),
                    "deadline": (
                        timezone.now() + datetime.timedelta(days=30)
                    ).isoformat(),
                }
            },
            user,
        )

    def test__a_manager__creates_a_period_after_the_last_one(self):
        start = self.period.date_to + datetime.timedelta(days=1)
        executed = self.create(start, start + datetime.timedelta(days=27))
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["createPlanningPeriod"]["planningPeriod"]["status"], "OPEN"
        )
        self.assertEqual(PlanningPeriod.objects.latest("id").created_by, self.manager)

    def test__an_overlapping_period__is_refused(self):
        executed = self.create(
            self.period.date_to, self.period.date_to + datetime.timedelta(days=7)
        )
        self.assertIn("errors", executed)
        self.assertEqual(PlanningPeriod.objects.count(), 1)

    def test__an_end_before_the_start__is_refused(self):
        start = self.period.date_to + datetime.timedelta(days=10)
        self.assertIn("errors", self.create(start, start - datetime.timedelta(days=1)))

    def test__a_member__cannot_create_a_period(self):
        start = self.period.date_to + datetime.timedelta(days=1)
        executed = self.create(start, start, user=self.anna)
        self.assertIn("errors", executed)

    def test__a_later_deadline__opens_a_closed_period_again(self):
        self.period.deadline = timezone.now() - datetime.timedelta(days=1)
        self.period.save()
        executed = self.execute(
            self.UPDATE,
            {
                "id": to_global_id("PlanningPeriodNode", self.period.pk),
                "input": {
                    "deadline": (
                        timezone.now() + datetime.timedelta(days=2)
                    ).isoformat()
                },
            },
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["updatePlanningPeriod"]["planningPeriod"]["status"], "OPEN"
        )

    def test__an_update_that_overlaps_another_period__is_refused(self):
        start = self.period.date_to + datetime.timedelta(days=1)
        other = PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=start,
            date_to=start + datetime.timedelta(days=13),
            deadline=timezone.now(),
        )
        executed = self.execute(
            self.UPDATE,
            {
                "id": to_global_id("PlanningPeriodNode", other.pk),
                "input": {"dateFrom": self.period.date_to.isoformat()},
            },
        )
        self.assertIn("errors", executed)

    def test__a_published_period__cannot_be_deleted(self):
        self.period.published_at = timezone.now()
        self.period.save()
        executed = self.execute(
            "mutation Delete($id: ID!) { deletePlanningPeriod(id: $id) { found } }",
            {"id": to_global_id("PlanningPeriodNode", self.period.pk)},
        )
        self.assertIn("errors", executed)
        self.assertTrue(PlanningPeriod.objects.filter(pk=self.period.pk).exists())


class TestSetShiftInterest(PlanningTestCase):
    SET = """
        mutation Set($shift: ID!, $type: ShiftInterestTypeEnum, $note: String) {
          setShiftInterest(shiftId: $shift, interestType: $type, note: $note) {
            shift { myInterest { interestType note source } }
          }
        }
    """

    def set(self, interest_type, note=None, shift=None, user=None):
        return self.execute(
            self.SET,
            {
                "shift": to_global_id("ShiftNode", (shift or self.shift).pk),
                "type": interest_type,
                "note": note,
            },
            user or self.anna,
        )

    def test__a_member_on_the_roster__answers_in_an_open_period(self):
        executed = self.set("UNAVAILABLE", note="Forelesning")
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["setShiftInterest"]["shift"]["myInterest"],
            {"interestType": "UNAVAILABLE", "note": "Forelesning", "source": "MANUAL"},
        )

    def test__a_second_answer__changes_the_same_row(self):
        self.set("UNAVAILABLE", note="Forelesning")
        self.set("INTERESTED")
        interest = ShiftInterest.objects.get()
        self.assertEqual(interest.interest_type, ShiftInterest.InterestTypes.INTERESTED)
        self.assertEqual(interest.note, "")

    def test__no_type__removes_the_answer(self):
        self.set("INTERESTED")
        executed = self.set(None)
        self.assertNotIn("errors", executed)
        self.assertIsNone(executed["data"]["setShiftInterest"]["shift"]["myInterest"])
        self.assertEqual(ShiftInterest.objects.count(), 0)

    def test__an_answer_after_the_deadline__is_refused(self):
        self.period.deadline = timezone.now() - datetime.timedelta(minutes=1)
        self.period.save()
        self.assertIn("errors", self.set("INTERESTED"))
        self.assertEqual(ShiftInterest.objects.count(), 0)

    def test__an_answer_in_a_published_period__is_refused(self):
        self.period.published_at = timezone.now()
        self.period.save()
        self.assertIn("errors", self.set("INTERESTED"))

    def test__an_answer_for_a_shift_outside_a_period__is_refused(self):
        outside = self.shift_on(self.period.date_to + datetime.timedelta(days=3), 18)
        self.assertIn("errors", self.set("INTERESTED", shift=outside))

    def test__a_user_not_on_the_roster__cannot_answer(self):
        self.assertIn("errors", self.set("INTERESTED", user=UserFactory.create()))


class TestPlanningQueries(PlanningTestCase):
    def test__my_open_planning_periods__lists_periods_of_my_rosters(self):
        PlanningPeriod.objects.create(
            schedule=ScheduleFactory.create(name="Lyche"),
            date_from=self.period.date_from,
            date_to=self.period.date_to,
            deadline=self.period.deadline,
        )
        executed = self.execute(
            "{ myOpenPlanningPeriods { id schedule { name } shifts { id } } }",
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        periods = executed["data"]["myOpenPlanningPeriods"]
        self.assertEqual([period["schedule"]["name"] for period in periods], ["Edgar"])
        self.assertEqual(
            periods[0]["shifts"], [{"id": to_global_id("ShiftNode", self.shift.pk)}]
        )

    def test__my_open_planning_periods__includes_only_my_default(self):
        executed = self.execute(
            "{ myOpenPlanningPeriods { myDefaultAvailability } }",
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["myOpenPlanningPeriods"],
            [{"myDefaultAvailability": "AVAILABLE"}],
        )

    def test__my_open_planning_periods__returns_opt_in_default(self):
        ScheduleRoster.objects.filter(
            schedule=self.schedule, user=self.anna
        ).update(default_availability=DefaultAvailability.OPT_IN)
        executed = self.execute(
            "{ myOpenPlanningPeriods { myDefaultAvailability } }",
            user=self.anna,
        )
        self.assertEqual(
            executed["data"]["myOpenPlanningPeriods"],
            [{"myDefaultAvailability": "OPT_IN"}],
        )

    def test__my_default_availability__is_null_for_a_non_member(self):
        guest = UserFactory.create()
        executed = self.execute(
            "{ planningPeriod(id: \"%s\") { myDefaultAvailability } }"
            % to_global_id("PlanningPeriodNode", self.period.pk),
            user=guest,
        )
        self.assertNotIn("errors", executed)
        self.assertIsNone(
            executed["data"]["planningPeriod"]["myDefaultAvailability"]
        )

    def test__my_open_planning_periods__leaves_out_closed_periods(self):
        self.period.deadline = timezone.now() - datetime.timedelta(minutes=1)
        self.period.save()
        executed = self.execute("{ myOpenPlanningPeriods { id } }", user=self.anna)
        self.assertEqual(executed["data"]["myOpenPlanningPeriods"], [])

    def test__schedule_planning_periods__lists_the_periods(self):
        executed = self.execute(
            '{ schedule(id: "%s") { planningPeriods { status dateFrom } } }'
            % to_global_id("ScheduleNode", self.schedule.pk),
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["schedule"]["planningPeriods"],
            [{"status": "OPEN", "dateFrom": self.period.date_from.isoformat()}],
        )
