from django.test import TestCase
from django.utils import timezone

from economy.models import Product, Deposit, Transaction, Purchase, PurchaseList
from users.models import User


class ProductTestCase(TestCase):

    def setUp(self):
        self.burger = Product.objects.create(product_name='burger', price=50)
        self.pils = Product.objects.create(product_name='flaskepils', price=25)

    def test_creation(self):
        self.assertIsInstance(self.burger, Product)
        self.assertIsInstance(self.pils, Product)

    def test_to_string(self):
        str(self.burger)

    def test_repr(self):
        repr(self.burger)


class DepositTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.user2 = User.objects.create(id=2, username='user2', email='person2@something.com')
        self.deposit = Deposit.objects.create(person=self.user1, amount=100)

    def test_creation(self):
        self.assertIsInstance(self.deposit, Deposit)

    def test_invalid(self):
        self.assertTrue(self.deposit.invalid)

    def test_signed_off_by(self):
        self.assertIsNone(self.deposit.signed_off_by)
        self.deposit.signed_off_by = self.user2
        self.assertEquals(self.user2, self.deposit.signed_off_by)
        self.assertNotEqual(self.deposit.person, self.deposit.signed_off_by)

    def test_sign_off_time(self):
        self.deposit.signed_off_time = timezone.now()
        self.now = timezone.now()
        self.assertEquals(self.now.date(), self.deposit.signed_off_time.date())
        self.assertEquals(self.now.hour, self.deposit.signed_off_time.hour)
        self.assertEquals(self.now.minute, self.deposit.signed_off_time.minute)
        self.assertEquals(self.now.second, self.deposit.signed_off_time.second)

    def test_valid(self):
        self.deposit.signed_off_by = self.user2
        self.assertTrue(self.deposit.valid)

    def test_str(self):
        str(self.deposit)

    def test_repr(self):
        repr(self.deposit)


class TransactionTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.user2 = User.objects.create(id=2, username='user2', email='person2@something.com')
        self.user3 = User.objects.create(id=3, username='user3', email='person3@something.com')
        self.transaction = Transaction.objects.create(sender=self.user1,
                                                      recipient=self.user2,
                                                      amount=100, signed_off_time=timezone.now())

    def test_creation(self):
        self.assertIsInstance(self.transaction, Transaction)

    def test_invalid(self):
        self.assertTrue(self.transaction.invalid)

    def test_signed_off_by(self):
        self.assertIsNone(self.transaction.signed_off_by)
        self.transaction.signed_off_by = self.user3
        self.assertEquals(self.user3, self.transaction.signed_off_by)
        self.assertNotEqual(self.transaction.sender, self.transaction.signed_off_by)
        self.assertNotEqual(self.transaction.recipient, self.transaction.signed_off_by)
        self.transaction.signed_off_time = timezone.now()

    def test_sign_off_time(self):
        self.now = timezone.now()
        self.assertEquals(self.now.date(), self.transaction.signed_off_time.date())
        self.assertEquals(self.now.hour, self.transaction.signed_off_time.hour)
        self.assertEquals(self.now.minute, self.transaction.signed_off_time.minute)
        self.assertEquals(self.now.second, self.transaction.signed_off_time.second)

    def test_valid(self):
        self.transaction.signed_off_by = self.user3
        self.assertTrue(self.transaction.valid)

    def test_to_string(self):
        str(self.transaction)

    def test_repr(self):
        repr(self.transaction)


class PurchaseTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.user2 = User.objects.create(id=2, username='user2', email='person2@something.com')
        self.product = Product.objects.create(product_name='burger', price=50)
        self.purchase_list = PurchaseList.objects.create(signed_off_by=self.user1, comment="hello")
        self.purchase1 = Purchase.objects.create(person=self.user2, product=self.product, amount=1,
                                                 purchase_list=self.purchase_list)
        self.purchase2 = Purchase.objects.create(person=self.user1,
                                                 product=self.product,
                                                 amount=2,
                                                 purchase_list=self.purchase_list)

    def test_creation(self):
        self.assertIsInstance(self.purchase1, Purchase)
        self.assertIsInstance(self.purchase2, Purchase)

    def test_to_string(self):
        str(self.purchase1)

    def test_repr(self):
        repr(self.purchase1)


class PurchaseListTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.purchase_list = PurchaseList.objects.create(signed_off_by=self.user1,
                                                         date_purchased=timezone.now(),
                                                         date_registered=timezone.now(),
                                                         comment="A sample purchase list")

    def test_creation(self):
        self.assertIsInstance(self.purchase_list, PurchaseList)

    def test_invalid(self):
        self.assertFalse(self.purchase_list.invalid)

    def test_signed_off_by(self):
        self.assertEquals(self.purchase_list.signed_off_by.username, 'user1')

    def test_purchased_date(self):
        self.assertEquals(self.purchase_list.date_purchased, timezone.now().date())

    def test_registered_date(self):
        self.assertEquals(self.purchase_list.date_registered, timezone.now().date())

    def test_valid(self):
        self.assertTrue(self.purchase_list.valid)

    def test_to_string_does_not_crash(self):
        str(self.purchase_list)

    def test_repr(self):
        repr(self.purchase_list)

