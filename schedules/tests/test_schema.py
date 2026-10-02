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
