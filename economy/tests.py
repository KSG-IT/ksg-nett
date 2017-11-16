from django.test import TestCase
from economy.models import Product, Deposit
from users.models import User


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
        self.user1 = User.objects.create(id=1, email='person1@something.com')
        self.user2 = User.objects.create(id=2, email='person2@something.com')
