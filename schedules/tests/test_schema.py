import datetime
from zoneinfo import ZoneInfo

from addict import Dict
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from schedules.models import RoleOption
from schedules.tests.factories import ShiftFactory, ShiftSlotFactory
from users.tests.factories import UserFactory


class TestMyShiftsQueries(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserFactory.create()
        start = timezone.now() + datetime.timedelta(days=1)
        self.shift = ShiftFactory.create(
            datetime_start=start, datetime_end=start + datetime.timedelta(hours=6)
        )
        # The same user in two slots on one shift
        ShiftSlotFactory.create(
            shift=self.shift, user=self.user, role=RoleOption.BARISTA
        )
        ShiftSlotFactory.create(
            shift=self.shift, user=self.user, role=RoleOption.KAFEANSVARLIG
        )

    def execute(self, query):
        executed = self.graphql_client.execute(query, context=Dict(user=self.user))
        self.assertNotIn("errors", executed)
        return Dict(executed).data

    def test__my_upcoming_shifts__returns_each_shift_once(self):
        data = self.execute("{ myUpcomingShifts { id } }")
        self.assertEqual(len(data.myUpcomingShifts), 1)

    def test__all_my_shifts__returns_each_shift_once(self):
        data = self.execute("{ allMyShifts { id } }")
        self.assertEqual(len(data.allMyShifts), 1)


class TestScheduleAllergiesV2Query(TestCase):
    def setUp(self) -> None:
        from users.models import Allergy
        from users.tests.factories import UserWithPermissionsFactory

        self.graphql_client = Client(schema)
        self.planner = UserWithPermissionsFactory.create(
            permissions="schedules.change_schedule"
        )
        gluten = Allergy.objects.create(name="Gluten")
        lactose = Allergy.objects.create(name="Laktose")
        self.anna = UserFactory.create(first_name="Anna", last_name="A")
        self.anna.allergies.add(gluten, lactose)
        self.bob = UserFactory.create(first_name="Bob", last_name="B")
        self.carl = UserFactory.create(first_name="Carl", last_name="C")
        self.carl.allergies.add(gluten)
        self.dina = UserFactory.create(first_name="Dina", last_name="D")
        self.dina.allergies.add(gluten)

        # The week from Monday 2026-09-07 to Sunday 2026-09-13
        self.slot(self.anna, datetime.date(2026, 9, 7))
        self.slot(self.anna, datetime.date(2026, 9, 9))
        self.slot(self.bob, datetime.date(2026, 9, 7))
        self.slot(self.carl, datetime.date(2026, 9, 13))
        # The Monday after: not in the week
        self.slot(self.dina, datetime.date(2026, 9, 14))

    def slot(self, user, day):
        start = timezone.make_aware(datetime.datetime.combine(day, datetime.time(18)))
        shift = ShiftFactory.create(
            datetime_start=start, datetime_end=start + datetime.timedelta(hours=6)
        )
        ShiftSlotFactory.create(shift=shift, user=user, role=RoleOption.BARISTA)

    def execute(self, user):
        return self.graphql_client.execute(
            """
            {
              scheduleAllergiesV2(shiftsFrom: "2026-09-10") {
                allergies
                users { name allergies days }
                allergyCounts
                peopleAtWork
                days { date peopleAtWork }
              }
            }
            """,
            context=Dict(user=user),
        )

    def test__week__gives_a_matrix_of_people_at_work(self):
        executed = self.execute(self.planner)
        self.assertNotIn("errors", executed)
        week = executed["data"]["scheduleAllergiesV2"]

        self.assertEqual(week["allergies"], ["Gluten", "Laktose"])
        self.assertEqual(
            week["users"],
            [
                {
                    "name": "Anna A",
                    "allergies": [True, True],
                    "days": ["2026-09-07", "2026-09-09"],
                },
                {"name": "Carl C", "allergies": [True, False], "days": ["2026-09-13"]},
            ],
        )
        self.assertEqual(week["allergyCounts"], [2, 1])
        # Anna, Bob and Carl; Dina works the week after
        self.assertEqual(week["peopleAtWork"], 3)
        self.assertEqual(
            week["days"],
            [
                {"date": "2026-09-07", "peopleAtWork": 2},
                {"date": "2026-09-09", "peopleAtWork": 1},
                {"date": "2026-09-13", "peopleAtWork": 1},
            ],
        )

    def test__without_permission__returns_error(self):
        self.assertIn("errors", self.execute(UserFactory.create()))


class TestScheduleOverviewFields(TestCase):
    def setUp(self) -> None:
        from schedules.models import Shift
        from schedules.tests.factories import ScheduleFactory

        from users.tests.factories import UserWithPermissionsFactory

        self.graphql_client = Client(schema)
        self.user = UserWithPermissionsFactory.create(
            permissions="schedules.change_schedule"
        )
        self.schedule = ScheduleFactory.create(name="Edgar")
        self.empty = ScheduleFactory.create(name="Arrangement")
        now = timezone.now()

        def shift(days, location=Shift.Location.EDGAR, filled=1, open_slots=0):
            start = now + datetime.timedelta(days=days)
            created = ShiftFactory.create(
                schedule=self.schedule,
                location=location,
                datetime_start=start,
                datetime_end=start + datetime.timedelta(hours=6),
            )
            for _ in range(filled):
                ShiftSlotFactory.create(shift=created, role=RoleOption.BARISTA)
            for _ in range(open_slots):
                ShiftSlotFactory.create(
                    shift=created, user=None, role=RoleOption.BARISTA
                )
            return created

        # Old shift: counts for locations, not for slots or planned until
        shift(-20, location=Shift.Location.BODEGAEN)
        shift(-200, location=Shift.Location.STROSSA)
        shift(2, filled=2, open_slots=1)
        shift(10, filled=1, open_slots=2)
        self.last = shift(20, filled=3)

    def execute(self, query):
        executed = self.graphql_client.execute(query, context=Dict(user=self.user))
        self.assertNotIn("errors", executed)
        return Dict(executed).data

    def test__a_member_without_the_permission_gets_no_overview_fields(self):
        member = UserFactory.create()
        for field in (
            "plannedUntil",
            "upcomingSlots { total }",
            "recentLocations",
        ):
            executed = self.graphql_client.execute(
                "{ allSchedules { name %s } }" % field,
                context=Dict(user=member),
            )
            self.assertIn("errors", executed, field)

    def overview(self):
        data = self.execute("""
            {
              allSchedules {
                name
                plannedUntil
                upcomingSlots { filled total }
                recentLocations
              }
            }
            """)
        return {schedule.name: schedule for schedule in data.allSchedules}

    def test__planned_until__is_the_start_of_the_last_upcoming_shift(self):
        planned_until = self.overview()["Edgar"].plannedUntil
        self.assertEqual(
            datetime.datetime.fromisoformat(planned_until),
            self.last.datetime_start,
        )

    def test__planned_until__is_null_without_upcoming_shifts(self):
        self.assertIsNone(self.overview()["Arrangement"].plannedUntil)

    def test__upcoming_slots__counts_the_next_14_days(self):
        slots = self.overview()["Edgar"].upcomingSlots
        self.assertEqual((slots.filled, slots.total), (3, 6))

    def test__upcoming_slots__is_zero_without_shifts(self):
        slots = self.overview()["Arrangement"].upcomingSlots
        self.assertEqual((slots.filled, slots.total), (0, 0))

    def test__recent_locations__most_used_first_and_not_too_old(self):
        self.assertEqual(
            self.overview()["Edgar"].recentLocations, ["EDGAR", "BODEGAEN"]
        )


class TestAllSchedulesLogin(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import AnonymousUser
        from schedules.tests.factories import ScheduleFactory

        self.graphql_client = Client(schema)
        self.anonymous = AnonymousUser()
        ScheduleFactory.create(name="Edgar")

    def test__all_schedules__needs_login(self):
        executed = self.graphql_client.execute(
            "{ allSchedules { name } }", context=Dict(user=self.anonymous)
        )
        self.assertIn("errors", executed)

    def test__all_schedules__works_for_a_member(self):
        executed = self.graphql_client.execute(
            "{ allSchedules { name } }", context=Dict(user=UserFactory.create())
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["allSchedules"], [{"name": "Edgar"}])

    def test__shifts_from_range__needs_login(self):
        from graphql_relay import to_global_id
        from schedules.models import Schedule

        schedule_id = to_global_id("ScheduleNode", Schedule.objects.get().pk)
        # schedule(id) has no guard, so check the field through it
        query = (
            '{ schedule(id: "%s") { shiftsFromRange(shiftsFrom: "2026-10-05", '
            "numberOfWeeks: 1) { id } } }" % schedule_id
        )
        member = UserFactory.create()
        self.assertNotIn(
            "errors", self.graphql_client.execute(query, context=Dict(user=member))
        )
        self.assertIn(
            "errors",
            self.graphql_client.execute(query, context=Dict(user=self.anonymous)),
        )


class TestCreateAndUpdateShiftV2(TestCase):
    def setUp(self) -> None:
        from schedules.tests.factories import ScheduleFactory
        from users.tests.factories import UserWithPermissionsFactory

        self.graphql_client = Client(schema)
        self.manager = UserWithPermissionsFactory.create(
            permissions=(
                "schedules.add_shift",
                "schedules.add_shiftslot",
                "schedules.change_shift",
            )
        )
        self.schedule = ScheduleFactory.create(name="Edgar")
        self.schedule_id = to_global_id("ScheduleNode", self.schedule.pk)

    def execute(self, query, variables, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    CREATE = """
        mutation Create($input: CreateShiftWithSlotsInput!) {
          createShiftWithSlots(input: $input) {
            shift { id name location datetimeStart datetimeEnd slots { role } }
          }
        }
    """

    def create(self, **overrides):
        variables = {
            "input": {
                "scheduleId": self.schedule_id,
                "name": "Kveld",
                "location": "EDGAR",
                "date": "2026-10-09",
                "startTime": "16:00:00",
                "endTime": "23:00:00",
                "slots": [
                    {"shiftSlotRole": "BARISTA", "count": 2},
                    {"shiftSlotRole": "KAFEANSVARLIG", "count": 1},
                ],
                **overrides,
            }
        }
        return self.execute(self.CREATE, variables)

    def test__creates_the_shift_and_its_slots_in_local_time(self):
        from schedules.models import Shift

        executed = self.create()
        self.assertNotIn("errors", executed)
        shift = Shift.objects.get()
        local = ZoneInfo(settings.TIME_ZONE)
        self.assertEqual(
            shift.datetime_start, datetime.datetime(2026, 10, 9, 16, tzinfo=local)
        )
        self.assertEqual(
            shift.datetime_end, datetime.datetime(2026, 10, 9, 23, tzinfo=local)
        )
        self.assertEqual(shift.schedule, self.schedule)
        self.assertEqual(
            sorted(shift.slots.values_list("role", flat=True)),
            ["BARISTA", "BARISTA", "KAFEANSVARLIG"],
        )

    def test__an_end_before_the_start_is_the_next_day(self):
        from schedules.models import Shift

        self.assertNotIn(
            "errors", self.create(startTime="20:00:00", endTime="03:00:00")
        )
        shift = Shift.objects.get()
        self.assertEqual(
            shift.datetime_end - shift.datetime_start, datetime.timedelta(hours=7)
        )

    def test__an_unknown_location_creates_nothing(self):
        from schedules.models import Shift

        self.assertIn("errors", self.create(location="NOWHERE"))
        self.assertEqual(Shift.objects.count(), 0)

    def test__needs_the_permissions(self):
        from schedules.models import Shift

        executed = self.execute(
            self.CREATE,
            {
                "input": {
                    "scheduleId": self.schedule_id,
                    "name": "Kveld",
                    "date": "2026-10-09",
                    "startTime": "16:00:00",
                    "endTime": "23:00:00",
                    "slots": [],
                }
            },
            user=UserFactory.create(),
        )
        self.assertIn("errors", executed)
        self.assertEqual(Shift.objects.count(), 0)

    def test__update_shift_details_changes_name_location_and_times(self):
        from schedules.models import Shift

        self.create()
        shift = Shift.objects.get()
        executed = self.execute(
            """
            mutation Update($input: UpdateShiftDetailsInput!) {
              updateShiftDetails(input: $input) { shift { id } }
            }
            """,
            {
                "input": {
                    "shiftId": to_global_id("ShiftNode", shift.pk),
                    "name": "Sen kveld",
                    "location": "BODEGAEN",
                    "date": "2026-10-10",
                    "startTime": "21:30:00",
                    "endTime": "02:00:00",
                }
            },
        )
        self.assertNotIn("errors", executed)
        shift.refresh_from_db()
        local = ZoneInfo(settings.TIME_ZONE)
        self.assertEqual(shift.name, "Sen kveld")
        self.assertEqual(shift.location, "BODEGAEN")
        self.assertEqual(
            shift.datetime_start,
            datetime.datetime(2026, 10, 10, 21, 30, tzinfo=local),
        )
        self.assertEqual(
            shift.datetime_end, datetime.datetime(2026, 10, 11, 2, tzinfo=local)
        )
