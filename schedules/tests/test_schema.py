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
