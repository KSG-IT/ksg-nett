from django.conf import settings
from django.test import TestCase

from economy.tests.factories import (
    SociBankAccountFactory,
    DepositFactory,
    TransferFactory,
    ProductOrderFactory,
    DepositCommentFactory,
    SociSessionFactory,
    SociProductFactory,
)


class SociBankAccountTest(TestCase):
    def setUp(self):
        self.soci_account = SociBankAccountFactory(balance=500)

    def test_account_with_transactions__transaction_history_retrieved_correctly(self):
        SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        extra_account = SociBankAccountFactory(balance=2000)

        DepositFactory(account=self.soci_account, amount=1000)
        ProductOrderFactory(source=self.soci_account)
        TransferFactory(source=extra_account, destination=self.soci_account, amount=500)
        history = self.soci_account.transaction_history

        self.assertEqual(3, len(history))
        self.assertEqual(1, history["deposits"].count())
        self.assertEqual(1, history["product_orders"].count())
        self.assertEqual(1, history["transfers"].count())

    def test_account__add_funds__added_correctly(self):
        self.soci_account.add_funds(500)

        self.assertEqual(1000, self.soci_account.balance)

    def test_account__remove_funds__removed_correctly(self):
        self.soci_account.remove_funds(500)

        self.assertEqual(0, self.soci_account.balance)


class SociSessionTest(TestCase):
    def setUp(self):
        SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        self.session = SociSessionFactory()
        self.product = SociProductFactory(price=30)
        ProductOrderFactory(
            order_size=100,
            cost=self.product.price * 100,
            session=self.session,
            product=self.product,
        )
        ProductOrderFactory(
            order_size=200,
            cost=self.product.price * 200,
            session=self.session,
            product=self.product,
        )

    def test_total_product_orders__correct_amount_returned(self):
        self.assertEqual(2, self.session.total_product_orders)

    def test__total_revenue__returns_correct_sum(self):
        expected_revenue = (30 * 100) + (30 * 200)
        self.assertEqual(expected_revenue, self.session.total_revenue)
