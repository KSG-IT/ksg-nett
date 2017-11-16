from django.test import TestCase
from economy.models import Product, Deposit
from users.models import User


class ProductTestCase(TestCase):
    def setUp(self):
        Product.objects.create(product_name='burger', price=50)
        Product.objects.create(product_name='flaskepils', price=25)

    def test_creation(self):
        self.assertIsInstance(Product.objects.get('burger'), Product)
        self.assertIsInstance(Product.objects.get('flaskepils'), Product)

