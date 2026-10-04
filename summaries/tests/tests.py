from addict import Dict
from django.test import TestCase
from graphene import Node
from graphene.test import Client

from ksg_nett.schema import schema
from summaries.tests.factories import SummaryFactory
from users.tests.factories import UserFactory

QUERY = """
    query Summary($id: ID!) {
      summary(id: $id) {
        contents
      }
    }
"""


class TestSummaryContentsResolver(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserFactory.create()

    def resolve_contents(self, contents):
        summary = SummaryFactory.create(contents=contents)
        executed = self.graphql_client.execute(
            QUERY,
            variables={"id": Node.to_global_id("SummaryNode", summary.pk)},
            context=Dict(user=self.user),
        )
        self.assertNotIn("errors", executed)
        return executed["data"]["summary"]["contents"]

    def test__contents__keeps_allowed_tags(self):
        html = "<h2>Møte</h2><p><strong>Saker</strong></p><ul><li>a</li></ul>"
        self.assertEqual(html, self.resolve_contents(html))

    def test__contents__escapes_script(self):
        contents = self.resolve_contents("<p>x</p><script>alert(1)</script>")
        self.assertEqual("<p>x</p>&lt;script&gt;alert(1)&lt;/script&gt;", contents)
