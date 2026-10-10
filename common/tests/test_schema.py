from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from graphene.test import Client

from django.db import connection
from django.test.utils import CaptureQueriesContext

from ksg_nett.schema import schema
from quotes.tests.factories import QuoteFactory, QuoteVoteFactory
from users.tests.factories import UserFactory


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


class TestDashboardDataQueryCount(TestCase):
    QUERY = "{ dashboardData { lastQuotes { id sum tagged { id } } } }"

    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserFactory.create()

    def count_queries(self):
        with CaptureQueriesContext(connection) as queries:
            executed = self.graphql_client.execute(
                self.QUERY, context=Dict(user=self.user)
            )
        self.assertNotIn("errors", executed)
        return len(queries), executed

    def add_approved_quotes(self, count):
        for quote in QuoteFactory.create_batch(count, approved=True):
            QuoteVoteFactory.create(quote=quote, value=1)

    def test__last_quotes__query_count_does_not_grow_with_quote_count(self):
        self.add_approved_quotes(1)
        self.count_queries()  # the first call creates the feature flag rows
        one_quote, _ = self.count_queries()
        self.add_approved_quotes(4)
        five_quotes, executed = self.count_queries()

        self.assertEqual(5, len(executed["data"]["dashboardData"]["lastQuotes"]))
        self.assertEqual(one_quote, five_quotes)
