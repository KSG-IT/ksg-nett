from django.conf import settings
from django.test import TestCase
from factory import Iterator

from economy.tests.factories import SociBankAccountFactory, DepositFactory, PurchaseFactory, TransferFactory, \
    ProductOrderFactory, PurchaseCollectionFactory, DepositCommentFactory


class SociBankAccountTest(TestCase):
    def setUp(self):
        self.soci_account = SociBankAccountFactory(balance=500)

    def test_soci_bank_account__correct_status(self):
        self.assertTrue(self.soci_account.has_sufficient_funds)
        self.assertFalse(self.soci_account.public_balance)

    def test_account_with_public_balance__display_balance(self):
        self.soci_account.display_balance_at_soci = True
        self.soci_account.save()

        self.assertTrue(self.soci_account.display_balance_at_soci)

    def test_account_with_transactions__transaction_history_retrieved_correctly(self):
        SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        extra_account = SociBankAccountFactory(balance=2000)

        DepositFactory(account=self.soci_account, amount=1000)
        PurchaseFactory(source=self.soci_account)
        TransferFactory(source=extra_account, destination=self.soci_account, amount=500)
        history = self.soci_account.transaction_history

        self.assertEqual(3, len(history))
        self.assertEqual(1, history['deposits'].count())
        self.assertEqual(1, history['purchases'].count())
        self.assertEqual(1, history['transfers'].count())

    def test_account_with_balance_larger_than_soci_limit__return_balance_as_chargeable_balance(self):
        chargeable_balance = self.soci_account.chargeable_balance

        self.assertEqual(500, chargeable_balance)

    def test_account__add_funds__added_correctly(self):
        self.soci_account.add_funds(500)

        self.assertEqual(1000, self.soci_account.balance)

    def test_account__remove_funds__removed_correctly(self):
        self.soci_account.remove_funds(500)

        self.assertEqual(0, self.soci_account.balance)


class PurchaseTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        cls.purchase = PurchaseFactory()
        ProductOrderFactory.create_batch(
            2, product__name=Iterator(['first', 'second']), product__price=Iterator([100, 200]),
            order_size=1, amount=Iterator([100, 200]), purchase=cls.purchase)

    def test_valid_purchase__is_valid(self):
        self.assertTrue(self.purchase.is_valid)

    def test_total_amount__correct_amount_returned(self):
        self.assertEqual(300, self.purchase.total_amount)

    def test_products_purchased__correct_products_returned(self):
        self.assertEqual(['first', 'second'], self.purchase.products_purchased)


class PurchaseCollectionTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        cls.collection = PurchaseCollectionFactory()
        ProductOrderFactory(amount=100, purchase__collection=cls.collection)
        ProductOrderFactory(amount=200, purchase__collection=cls.collection)

    def test_total_purchases__correct_amount_returned(self):
        self.assertEqual(2, self.collection.total_purchases)

    def test_total_amount__correct_amount_returned(self):
        self.assertEqual(300, self.collection.total_amount)


class DepositTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.valid_deposit = DepositFactory()

    def test_deposit_status__correct_status(self):
        self.assertTrue(self.valid_deposit.is_valid)


class DepositCommentTest(TestCase):
    def setUp(self):
        self.deposit_comment = DepositCommentFactory()

    def test__str_and_repr_does_not_crash(self):
        str(self.deposit_comment)
        repr(self.deposit_comment)

    def test__short_comment_value__does_not_render_ellipses(self):
        self.deposit_comment.comment = "Short and sweet."
        self.deposit_comment.save()

        self.assertNotIn("..", str(self.deposit_comment))

    def test__long_comment_value__renders_ellipses(self):
        self.deposit_comment.comment = "This is definitely not short and sweet."
        self.deposit_comment.save()

        self.assertIn("..", str(self.deposit_comment))
