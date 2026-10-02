from django.test import TestCase
from addict import Dict
from graphene.test import Client
from ksg_nett.schema import schema
from economy.tests.factories import SociProductFactory
from economy.models import ProductGhostOrder
from users.tests.factories import UserWithPermissionsFactory, UserFactory


class TestIncrementProductGhostOrderMutation(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.product = SociProductFactory.create(
            name="Smirnoff Ice", price=30, purchase_price=20
        )
        self.user_with_perm = UserWithPermissionsFactory.create(
            permissions="economy.add_productghostorder"
        )
        self.user_without_perm = UserFactory.create()

        self.mutation = """
            mutation IncrementGhostOrderMutation($productId: ID) {
              incrementProductGhostOrder(productId: $productId) {
                success
              }
            }
          """

    def test__correct_input_and_has_permission__creates_new_object(self):
        pre_count = ProductGhostOrder.objects.all().count()
        self.graphql_client.execute(
            self.mutation,
            variables={"productId": self.product.id},
            context=Dict(user=self.user_with_perm),
        )
        post_count = ProductGhostOrder.objects.all().count()
        diff = post_count - pre_count
        self.assertEqual(diff, 1)

    def test__correct_input_without_permission__returns_error(self):
        pre_count = ProductGhostOrder.objects.all().count()
        executed = self.graphql_client.execute(
            self.mutation,
            variables={"productId": self.product.id},
            context=Dict(user=self.user_without_perm),
        )
        result = Dict(executed)
        post_count = ProductGhostOrder.objects.all().count()
        diff = post_count - pre_count
        self.assertEqual(diff, 0)
        self.assertIsNotNone(result.data.errors)
