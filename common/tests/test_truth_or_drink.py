from addict import Dict
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from graphene.test import Client

from common.models import FeatureFlag
from ksg_nett.schema import schema
from users.tests.factories import UserFactory

ENABLED = "query { truthOrDrinkEnabled }"


class TestTruthOrDrinkEnabled(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserFactory.create()

    def query(self, user=None):
        return self.graphql_client.execute(
            ENABLED, context=Dict(user=user or self.user)
        )

    def test__is_off_without_a_flag(self):
        executed = self.query()
        self.assertNotIn("errors", executed)
        self.assertFalse(executed["data"]["truthOrDrinkEnabled"])

    def test__is_on_when_the_flag_is_enabled(self):
        FeatureFlag.objects.create(
            name=settings.TRUTH_OR_DRINK_FEATURE_FLAG, enabled=True
        )
        executed = self.query()
        self.assertTrue(executed["data"]["truthOrDrinkEnabled"])

    def test__needs_login(self):
        self.assertIn("errors", self.query(user=AnonymousUser()))
