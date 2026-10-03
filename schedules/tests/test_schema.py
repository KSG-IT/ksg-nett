import datetime

from addict import Dict
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client

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
