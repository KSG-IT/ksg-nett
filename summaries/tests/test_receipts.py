from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from graphene import Node
from graphene.test import Client

from ksg_nett.schema import schema
from summaries.models import SummaryReadReceipt
from summaries.tests.factories import SummaryFactory, SummaryReadReceiptFactory
from users.tests.factories import UserFactory

FIELDS = "openedCount readCount openedByMe readByMe"

OPEN = f"""
    mutation OpenSummary($id: ID!) {{
      openSummary(summaryId: $id) {{ summary {{ {FIELDS} }} }}
    }}
"""
READ = f"""
    mutation ReadSummary($id: ID!) {{
      readSummary(summaryId: $id) {{ summary {{ {FIELDS} }} }}
    }}
"""
ONE = f"""
    query Summary($id: ID!) {{ summary(id: $id) {{ {FIELDS} }} }}
"""
ALL = f"""
    query {{
      allSummaries(first: 50) {{ edges {{ node {{ id {FIELDS} }} }} }}
    }}
"""


class SummaryReceiptTestCase(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.reporter = UserFactory.create()
        self.user = UserFactory.create()
        self.summary = SummaryFactory.create(reporter=self.reporter)

    def execute(self, query, user=None, summary=None):
        summary = summary or self.summary
        return self.graphql_client.execute(
            query,
            variables={"id": Node.to_global_id("SummaryNode", summary.pk)},
            context=Dict(user=user or self.user),
        )

    def receipt(self, user=None):
        return SummaryReadReceipt.objects.get(
            summary=self.summary, user=user or self.user
        )


class TestOpenSummary(SummaryReceiptTestCase):
    def test__open__creates_a_receipt_without_read_at(self):
        executed = self.execute(OPEN)

        self.assertNotIn("errors", executed)
        summary = executed["data"]["openSummary"]["summary"]
        self.assertEqual(1, summary["openedCount"])
        self.assertEqual(0, summary["readCount"])
        self.assertTrue(summary["openedByMe"])
        self.assertFalse(summary["readByMe"])
        self.assertIsNone(self.receipt().read_at)

    def test__open__twice__keeps_the_first_opened_at(self):
        self.execute(OPEN)
        first = self.receipt().opened_at

        self.execute(OPEN)

        self.assertEqual(1, SummaryReadReceipt.objects.count())
        self.assertEqual(first, self.receipt().opened_at)

    def test__open__unknown_summary__gives_an_error(self):
        executed = self.graphql_client.execute(
            OPEN,
            variables={"id": Node.to_global_id("SummaryNode", 999999)},
            context=Dict(user=self.user),
        )

        self.assertIn("errors", executed)
        self.assertEqual(0, SummaryReadReceipt.objects.count())

    def test__open__anonymous__is_refused(self):
        executed = self.execute(OPEN, user=AnonymousUser())

        self.assertIn("errors", executed)
        self.assertEqual(0, SummaryReadReceipt.objects.count())


class TestReadSummary(SummaryReceiptTestCase):
    def test__read__sets_read_at(self):
        self.execute(OPEN)

        executed = self.execute(READ)

        self.assertNotIn("errors", executed)
        summary = executed["data"]["readSummary"]["summary"]
        self.assertEqual(1, summary["readCount"])
        self.assertTrue(summary["readByMe"])
        self.assertIsNotNone(self.receipt().read_at)

    def test__read__twice__keeps_the_first_read_at(self):
        self.execute(READ)
        first = self.receipt().read_at

        self.execute(READ)

        self.assertEqual(first, self.receipt().read_at)

    def test__read__without_open__creates_the_receipt(self):
        self.execute(READ)

        receipt = self.receipt()
        self.assertIsNotNone(receipt.opened_at)
        self.assertIsNotNone(receipt.read_at)


class TestReceiptCounts(SummaryReceiptTestCase):
    def test__counts__leave_out_the_reporter(self):
        SummaryReadReceiptFactory.create(summary=self.summary, user=self.reporter)
        SummaryReadReceiptFactory.create(summary=self.summary, user=self.user)
        self.execute(READ, user=self.reporter)

        summary = self.execute(ONE)["data"]["summary"]

        self.assertEqual(1, summary["openedCount"])
        self.assertEqual(0, summary["readCount"])

    def test__counts__without_a_reporter__count_every_receipt(self):
        summary = SummaryFactory.create(reporter=None)
        SummaryReadReceiptFactory.create(summary=summary, user=self.user)
        SummaryReadReceiptFactory.create(summary=summary, user=UserFactory.create())

        executed = self.execute(ONE, summary=summary)["data"]["summary"]

        self.assertEqual(2, executed["openedCount"])

    def test__counts__are_per_summary(self):
        other = SummaryFactory.create(reporter=self.reporter)
        SummaryReadReceiptFactory.create(summary=other, user=self.user)

        summary = self.execute(ONE)["data"]["summary"]

        self.assertEqual(0, summary["openedCount"])
        self.assertFalse(summary["openedByMe"])

    def test__by_me__is_for_the_current_user_only(self):
        SummaryReadReceiptFactory.create(
            summary=self.summary, user=UserFactory.create()
        )

        summary = self.execute(ONE)["data"]["summary"]

        self.assertEqual(1, summary["openedCount"])
        self.assertFalse(summary["openedByMe"])


class TestAllSummaries(SummaryReceiptTestCase):
    def nodes(self):
        edges = self.execute(ALL)["data"]["allSummaries"]["edges"]
        return {edge["node"]["id"]: edge["node"] for edge in edges}

    def test__list__matches_the_single_summary(self):
        SummaryReadReceiptFactory.create(summary=self.summary, user=self.reporter)
        SummaryReadReceiptFactory.create(
            summary=self.summary, user=UserFactory.create()
        )
        self.execute(READ)
        no_reporter = SummaryFactory.create(reporter=None)
        SummaryReadReceiptFactory.create(summary=no_reporter, user=self.user)

        nodes = self.nodes()

        for summary in (self.summary, no_reporter):
            node = nodes[Node.to_global_id("SummaryNode", summary.pk)]
            single = self.execute(ONE, summary=summary)["data"]["summary"]
            for field in ("openedCount", "readCount", "openedByMe", "readByMe"):
                self.assertEqual(single[field], node[field], field)

    def test__list__runs_the_same_queries_for_more_summaries(self):
        with CaptureQueriesContext(connection) as few:
            self.execute(ALL)

        for _ in range(5):
            summary = SummaryFactory.create(reporter=self.reporter)
            SummaryReadReceiptFactory.create(summary=summary, user=self.user)

        with CaptureQueriesContext(connection) as many:
            self.execute(ALL)

        self.assertEqual(len(few), len(many))


class TestReceiptConstraint(SummaryReceiptTestCase):
    def test__one_receipt_per_user_and_summary(self):
        SummaryReadReceiptFactory.create(summary=self.summary, user=self.user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            SummaryReadReceipt.objects.create(summary=self.summary, user=self.user)
