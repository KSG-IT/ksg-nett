from django.test import TestCase
from economy.models import Product, Deposit, Transaction, Purchase, PurchaseList
from users.models import User
import datetime


class ProductTestCase(TestCase):

    def setUp(self):
        self.burger = Product.objects.create(product_name='burger', price=50)
        self.pils = Product.objects.create(product_name='flaskepils', price=25)

    def test_creation(self):
        self.assertIsInstance(self.burger, Product)
        self.assertIsInstance(self.pils, Product)

    def test_to_string(self):
        string = self.burger.__str__()
        self.assertEquals(string, 'A product with name burger with the price of 50 NOK')
        string = self.pils.__str__()
        self.assertEquals(string, 'A product with name flaskepils with the price of 25 NOK')


class DepositTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.user2 = User.objects.create(id=2, username='user2', email='person2@something.com')
        self.deposit = Deposit.objects.create(person=self.user1, amount=100)
        self.now = datetime.datetime.now()

    def test_creation(self):
        self.assertIsInstance(self.deposit, Deposit)

    def test_time_of_creation(self):
        self.assertEquals(self.now.date(), self.deposit.signed_off_time.date())
        self.assertEquals(self.now.hour, self.deposit.signed_off_time.hour + 1) # +1 to set to norwegian time zone
        self.assertEquals(self.now.minute, self.deposit.signed_off_time.minute)
        self.assertEquals(self.now.second, self.deposit.signed_off_time.second)

    def test_signed_off_by(self):
        self.assertIsNone(self.deposit.signed_off_by)
        self.deposit.signed_off_by = self.user2
        self.assertEquals(self.user2, self.deposit.signed_off_by)
        self.assertNotEqual(self.deposit.person, self.deposit.signed_off_by)


class TransactionTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.user2 = User.objects.create(id=2, username='user2', email='person2@something.com')
        self.user3 = User.objects.create(id=3, username='user3', email='person3@something.com')
        self.transaction = Transaction.objects.create(sender=self.user1,
                                                      recipient=self.user2,
                                                      amount=100)
        self.now = datetime.datetime.now()

    def test_creation(self):
        self.assertIsInstance(self.transaction, Transaction)

    def test_time_of_creation(self):
        self.assertEquals(self.now.date(), self.transaction.signed_off_time.date())
        self.assertEquals(self.now.hour, self.transaction.signed_off_time.hour + 1) # +1 to set to norwegian time zone
        self.assertEquals(self.now.minute, self.transaction.signed_off_time.minute)
        self.assertEquals(self.now.second, self.transaction.signed_off_time.second)

    def test_signed_off_by(self):
        self.assertIsNone(self.transaction.signed_off_by)
        self.transaction.signed_off_by = self.user3
        self.assertEquals(self.user3, self.transaction.signed_off_by)
        self.assertNotEqual(self.transaction.sender, self.transaction.signed_off_by)
        self.assertNotEqual(self.transaction.recipient, self.transaction.signed_off_by)

    def test_to_string(self):
        string = 'Transaction from user1 to user2 of 100 NOK'
        self.assertEquals(self.transaction.__str__(), string)


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
        string = "A purchase by person user1 of 2 number of product burger"
        self.assertEquals(self.purchase2.__str__(), string)


class PurchaseListTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(id=1, username='user1', email='person1@something.com')
        self.purchase_list = PurchaseList.objects.create(signed_off_by=self.user2, comment="A sample purchase list")
        
