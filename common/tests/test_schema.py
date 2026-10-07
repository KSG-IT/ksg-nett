from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from graphene.test import Client

from ksg_nett.schema import schema


class TestDashboardDataRequiresLogin(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)

    def test__anonymous_user__is_denied(self):
        executed = self.graphql_client.execute(
            "{ dashboardData { myUpcomingShifts { id } } }",
            context=Dict(user=AnonymousUser()),
        )
        self.assertIn("errors", executed)
        self.assertEqual(
            executed["errors"][0]["message"], "You are not permitted to view this"
        )
