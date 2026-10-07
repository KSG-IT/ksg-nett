from addict import Dict
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from quotes.tests.factories import QuoteVoteFactory
from users.tests.factories import UserFactory


class TestMeUpvotedQuoteIds(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserFactory.create()

    def execute(self):
        executed = self.graphql_client.execute(
            "{ me { upvotedQuoteIds } }", context=Dict(user=self.user)
        )
        self.assertNotIn("errors", executed)
        return executed["data"]["me"]["upvotedQuoteIds"]

    def test__upvoted_quote_ids__returns_the_voted_quotes(self):
        votes = QuoteVoteFactory.create_batch(2, caster=self.user)
        self.assertCountEqual(
            self.execute(), [to_global_id("QuoteNode", vote.quote.id) for vote in votes]
        )

    def test__upvoted_quote_ids__does_not_query_per_vote(self):
        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                self.execute()
            return len(queries)

        QuoteVoteFactory.create(caster=self.user)
        before = count_queries()
        QuoteVoteFactory.create_batch(5, caster=self.user)
        self.assertEqual(count_queries(), before)
