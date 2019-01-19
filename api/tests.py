from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from economy.models import SociBankAccount, SociProduct
from users.models import User


# ===============================
# ECONOMY
# ===============================


class SociProductsViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('api:products')
        self.client = APIClient()
        self.user = User.objects.create(username='admin')
        self.client.force_authenticate(user=self.user)

        SociProduct.objects.create(sku_number='DAHLS', name="Dahls", price=30,
                                   description="En gammel slager. Nytes lunken.", icon="beverage-can-small")
        SociProduct.objects.create(sku_number='ICE', name="Smirnoff ICE", price=35,
                                   description="Når du føler for å imponere.", icon="bottle-small")
        SociProduct.objects.create(sku_number='LYCHE-PIZZABOLLE', name="Pizzabolle", price=20,
                                   description="Kjøkkenet har Soci. Hurra!", icon="food-item")

    def test_get__valid_request__ok(self):
        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 3)
        self.assertEqual((len(response.data[0])), 6)

    def test_get__product_without_description__description_blank(self):
        SociProduct.objects.create(sku_number='NORDLANDS', name="Nordlands Pils", price=30)

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 4)
        self.assertFalse(response.data[-1]['description'])


class CheckBalanceViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('api:check-balance')
        self.client = APIClient()
        self.user = User.objects.create(username='Christian')
        self.client.force_authenticate(user=self.user)
        self.soci_account = SociBankAccount.objects.create(user=self.user, card_uuid=1234567890)
        self.client.credentials(HTTP_CARD_NUMBER=self.soci_account.card_uuid)

    def test_get_balance__positive_amount__ok(self):
        self.soci_account.add_funds(amount=1337)

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 3)
        self.assertFalse(response.data['balance'])
        self.assertTrue(response.data['has_sufficient_funds'])

    def test_get_balance__negative_amount__payment_required(self):
        self.soci_account.remove_funds(amount=2000)

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEquals(len(response.data), 3)
        self.assertFalse(response.data['balance'])
        self.assertFalse(response.data['has_sufficient_funds'])

    def test_get_balance__user_wants_amount_shown__ok_and_amount_shown(self):
        self.soci_account.add_funds(amount=1337)
        self.soci_account.display_balance_at_soci = True
        self.soci_account.save()

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 3)
        self.assertTrue(response.data['has_sufficient_funds'])

    def test_get_balance__invalid_card__not_found(self):
        self.client.credentials(HTTP_CARD_NUMBER='01189998819991197253')
        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class ChargeSociBankAccountViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('api:charge')
        self.client = APIClient()
        self.user = User.objects.create(username='User', email='user@samfundet.no', first_name='user')
        self.soci = User.objects.create(username='Soci', email='soci@samfundet.no', first_name='soci')
        self.client.force_authenticate(user=self.soci)
        SociBankAccount.objects.create(user=self.soci, card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)
        self.soci_account = SociBankAccount.objects.create(user=self.user, balance=1000, card_uuid=1234567890)

        self.dahls = SociProduct.objects.create(sku_number='DAHLS', name="Dahls", price=30,
                                                description="En gammel slager. Nytes lunken.")
        self.smirre = SociProduct.objects.create(sku_number='ICE', name="Smirnoff ICE", price=35,
                                                 description="Når du føler for å imponere.")
        self.direct_charge = SociProduct.objects.create(sku_number=settings.DIRECT_CHARGE_SKU, name="Direct charge",
                                                        price=0, description="Kryss direkte beløp her.")
        self.client.credentials(HTTP_CARD_NUMBER=self.soci_account.card_uuid)

    def test_charge_valid_products__sufficient_balance__created_and_charged_correctly(self):
        data = [
            {"sku": self.smirre.sku_number, "order_size": 5},
            {"sku": self.dahls.sku_number},
            {"sku": settings.DIRECT_CHARGE_SKU, "direct_charge_amount": 200}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(3, len(response.data))
        self.assertEqual(405, response.data['amount_charged'])
        self.assertFalse(response.data['amount_remaining'])  # Balance hidden
        self.assertTrue(self.user.bank_account.transaction_history['purchases'].last().is_valid)

    def test_charge__user_wants_balance_shown__created_and_return_balance(self):
        self.soci_account.display_balance_at_soci = True
        self.soci_account.save()
        data = [
            {"sku": self.smirre.sku_number}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(965, response.data['amount_remaining'])

    def test_charge__insufficient_balance__payment_required(self):
        self.soci_account.remove_funds(1000)
        data = [
            {"sku": self.smirre.sku_number}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_charge__incorrect_card_id__not_found(self):
        self.client.credentials(HTTP_CARD_NUMBER="01189998819991197253")
        data = [
            {"sku": self.smirre.sku_number}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_charge__invalid_sku__bad_request(self):
        data = [
            {"sku": "ABSINTHE"}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge__negative_direct_charge_amount__bad_request(self):
        data = [
            {"sku": settings.DIRECT_CHARGE_SKU, "direct_charge_amount": -100}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge__amount_but_not_direct_charge__bad_request(self):
        data = [
            {"sku": self.smirre.sku_number, "direct_charge_amount": 100}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge__direct_charge_but_not_amount__bad_request(self):
        data = [{"sku": self.direct_charge.sku_number}]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge__non_list_as_body__bad_request(self):
        data = {"sku": self.direct_charge.sku_number}

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
