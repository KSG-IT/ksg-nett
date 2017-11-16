from django.test import TestCase
from economy.models import Product, Deposit
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
        self.assertEquals(self.now.microsecond, self.deposit.signed_off_time.microsecond)

    def test_signed_off_by(self):
        self.assertIsNone(self.deposit.signed_off_by)
        self.deposit.signed_off_by = self.user2
        self.assertEquals(self.user2, self.deposit.signed_off_by)


