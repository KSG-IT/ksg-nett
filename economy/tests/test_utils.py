import math

from django.test import TestCase
from economy.utils import parse_transaction_history
from economy.price_strategies import calculate_stock_price_for_product
from economy.tests.factories import (
    SociBankAccountFactory,
    ProductOrderFactory,
    DepositFactory,
    TransferFactory,
    SociProductFactory,
)
from users.schema import BankAccountActivity
from django.conf import settings
from django.utils import timezone


class TestParseTransactionHistory(TestCase):
    def setUp(self) -> None:
        self.bank_account = SociBankAccountFactory.create()
        ProductOrderFactory.create_batch(5, source=self.bank_account)
        TransferFactory.create_batch(5, source=self.bank_account)
        DepositFactory.create_batch(3, account=self.bank_account, approved=True)

    def test__parse_transaction_history__correctly_parses_activity(self):
        """
        Correctly parsed if
            * Same total length
            * All objects are of BankAccountType
        """
        parsed_activities = parse_transaction_history(self.bank_account)
        self.assertEqual(13, len(parsed_activities))
        assert all(
            isinstance(activity, BankAccountActivity) for activity in parsed_activities
        )

    def test__parse_transaction_history_with_slice_kwarg__returns_sliced_length(self):
        parsed_activities = parse_transaction_history(self.bank_account, 5)
        self.assertEqual(5, len(parsed_activities))


class TestAuctionPriceCalculation(TestCase):
    def setUp(self) -> None:
        self.tuborg = SociProductFactory.create(
            name="tuborg",
            price=25,
            purchase_price=20,
        )

    def test__price_calculation__returns_expected_price(self):
        ProductOrderFactory.create(product=self.tuborg, order_size=4)
        ProductOrderFactory.create(product=self.tuborg, order_size=1)
        ProductOrderFactory.create(product=self.tuborg, order_size=2)

        multiplier = settings.STOCK_MODE_PRICE_MULTIPLIER
        expected = math.floor((4 + 1 + 2) * multiplier + self.tuborg.purchase_price)
        calculated_price = calculate_stock_price_for_product(self.tuborg.id)
        self.assertEqual(expected, calculated_price)

    def test__product_has_no_purchase_price__raises_error(self):
        no_purchase_price = SociProductFactory.create(
            price=20, purchase_price=None, name="tuborg 2"
        )

        self.assertRaises(
            RuntimeError, calculate_stock_price_for_product, no_purchase_price.id
        )

    def test__product_orders_outside_price_window__not_included_in_calculation(self):
        outside_window = (
            timezone.now()
            - settings.STOCK_MODE_PRICE_WINDOW
            - settings.STOCK_MODE_PRICE_WINDOW
        )
        old_purchase = ProductOrderFactory(product=self.tuborg, order_size=10)
        old_purchase.purchased_at = outside_window
        old_purchase.save()

        ProductOrderFactory(product=self.tuborg, order_size=5)
        multiplier = settings.STOCK_MODE_PRICE_MULTIPLIER
        expected = math.floor(5 * multiplier + self.tuborg.purchase_price)
        calculated_price = calculate_stock_price_for_product(self.tuborg.id)
        self.assertEqual(expected, calculated_price)
