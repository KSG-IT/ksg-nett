import math

from django.test import TestCase
from economy.models import (
    Deposit,
    ProductOrder,
    Transfer,
    SociOrderSession,
    SociOrderSessionOrder,
    SociProduct,
)
from economy.utils import create_food_order_pdf_file, parse_transaction_history
from economy.price_strategies import calculate_stock_price_for_product
from economy.tests.factories import (
    SociBankAccountFactory,
    ProductOrderFactory,
    DepositFactory,
    TransferFactory,
    SociProductFactory,
)
from users.schema import BankAccountActivity
from users.tests.factories import UserFactory
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

    def test__parse_transaction_history_with_slice_kwarg__returns_newest_across_sources(
        self,
    ):
        """The slice keeps the newest activities, whichever table they come from."""
        now = timezone.now()
        orders = list(self.bank_account.product_orders.all())
        transfers = list(self.bank_account.source_transfers.all())
        deposits = list(self.bank_account.deposits.all())
        for i, order in enumerate(orders):
            ProductOrder.objects.filter(pk=order.pk).update(
                purchased_at=now - timezone.timedelta(days=10 + i)
            )
        for i, transfer in enumerate(transfers):
            Transfer.objects.filter(pk=transfer.pk).update(
                created_at=now - timezone.timedelta(days=20 + i)
            )
        for i, deposit in enumerate(deposits):
            Deposit.objects.filter(pk=deposit.pk).update(
                approved_at=now - timezone.timedelta(days=i)
            )

        parsed_activities = parse_transaction_history(self.bank_account, 4)

        self.assertEqual(
            [now - timezone.timedelta(days=i) for i in range(3)]
            + [now - timezone.timedelta(days=10)],
            [activity.timestamp for activity in parsed_activities],
        )


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

    def test__product_has_no_purchase_price_no_silent_fail__raises_error(self):
        no_purchase_price = SociProductFactory.create(
            price=20, purchase_price=None, name="tuborg 2"
        )

        self.assertRaises(
            RuntimeError,
            calculate_stock_price_for_product,
            no_purchase_price.id,
            fail_silently=False,
        )

    def test__product_has_no_purchase_price_silent_failing__returns_normal_price(self):
        no_purchase_price = SociProductFactory.create(
            price=20, purchase_price=None, name="tuborg 2"
        )

        result = calculate_stock_price_for_product(
            no_purchase_price.id, fail_silently=True
        )
        self.assertEqual(result, no_purchase_price.price)

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


class TestCreateFoodOrderPdfFile(TestCase):
    def setUp(self) -> None:
        self.session = SociOrderSession.objects.create(
            status=SociOrderSession.Status.FOOD_ORDERING
        )
        pizza = SociProductFactory.create(name="Pizza", type=SociProduct.Type.FOOD)
        burger = SociProductFactory.create(name="Burger", type=SociProduct.Type.FOOD)
        beer = SociProductFactory.create(name="Øl", type=SociProduct.Type.DRINK)

        for product in [pizza, pizza, burger, beer]:
            SociOrderSessionOrder.objects.create(
                session=self.session,
                user=UserFactory.create(),
                product=product,
                amount=1,
            )

    def test__create_food_order_pdf_file__returns_pdf(self):
        file = create_food_order_pdf_file(self.session)
        file.seek(0)
        content = file.read()

        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", content[-1024:])

    def test__create_food_order_pdf_file_without_orders__returns_pdf(self):
        self.session.orders.all().delete()

        file = create_food_order_pdf_file(self.session)
        file.seek(0)

        self.assertTrue(file.read().startswith(b"%PDF-"))
