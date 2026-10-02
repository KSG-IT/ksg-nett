from django.test import TestCase
from addict import Dict
from graphene.test import Client
from ksg_nett.schema import schema
import datetime

from django.utils import timezone
from graphene import Node

from economy.tests.factories import ProductOrderFactory, SociProductFactory
from economy.models import ProductGhostOrder, ProductOrder
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


class TestProductOrdersByItemAndDateListQuery(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.user = UserWithPermissionsFactory.create(
            permissions="economy.view_productorder"
        )
        self.beer = SociProductFactory.create(name="Dahls", price=30)
        self.cider = SociProductFactory.create(name="Smirnoff Ice", price=40)
        self.day = datetime.date(2026, 9, 1)
        self.order(self.beer, self.day, order_size=2, cost=60)
        self.order(self.beer, self.day, order_size=1, cost=30)
        self.order(self.beer, self.day + datetime.timedelta(days=2), 1, cost=50)
        # Outside the range
        self.order(self.beer, self.day + datetime.timedelta(days=5), 1, cost=30)
        self.query = """
            query Stats($productIds: [ID!]!, $dateFrom: Date!, $dateTo: Date!) {
              productOrdersByItemAndDateList(
                productIds: $productIds, dateFrom: $dateFrom, dateTo: $dateTo
              ) {
                name total quantity average data { day sum }
              }
            }
        """

    def order(self, product, day, order_size, cost):
        order = ProductOrderFactory.create(
            product=product, order_size=order_size, cost=cost
        )
        purchased_at = timezone.make_aware(
            datetime.datetime.combine(day, datetime.time(20, 0))
        )
        # purchased_at is auto_now_add, so set it after create
        ProductOrder.objects.filter(pk=order.pk).update(purchased_at=purchased_at)

    def execute(self, user):
        return self.graphql_client.execute(
            self.query,
            variables={
                "productIds": [
                    Node.to_global_id("SociProductNode", self.beer.pk),
                    Node.to_global_id("SociProductNode", self.cider.pk),
                ],
                "dateFrom": "2026-09-01",
                "dateTo": "2026-09-03",
            },
            context=Dict(user=user),
        )

    def test__sales__are_summed_per_day_with_empty_days(self):
        executed = self.execute(self.user)
        self.assertNotIn("errors", executed)
        beer, cider = executed["data"]["productOrdersByItemAndDateList"]

        self.assertEqual(beer["name"], "Dahls")
        self.assertEqual([day["sum"] for day in beer["data"]], [90, 0, 50])
        self.assertEqual(beer["total"], 140)
        # Items sold, not revenue divided by the current price
        self.assertEqual(beer["quantity"], 4)
        # Revenue per day with sales: 140 / 2
        self.assertEqual(beer["average"], 70)

        self.assertEqual(cider["total"], 0)
        self.assertEqual(cider["quantity"], 0)
        self.assertEqual(cider["average"], 0)
        self.assertEqual([day["sum"] for day in cider["data"]], [0, 0, 0])

    def test__without_permission__returns_error(self):
        executed = self.execute(UserFactory.create())
        self.assertIn("errors", executed)

    def test__all_product_orders_without_permission__returns_error(self):
        executed = self.graphql_client.execute(
            "{ allProductOrders { edges { node { id } } } }",
            context=Dict(user=UserFactory.create()),
        )
        self.assertIn("errors", executed)
