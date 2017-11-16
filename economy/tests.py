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


class DepositTestCase(TestCase):

    def setUp(self):
        User.objects.create(id=1, email='person1@something.com')
        User.objects.create(id=2, email='person2@something.com')
