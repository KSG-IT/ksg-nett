from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import SlidingToken

from economy.tests.factories import SociProductFactory, SociBankAccountFactory
from users.tests.factories import UserFactory


class CustomObtainJwtTokenViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.user = SociBankAccountFactory(user__is_staff=True).user
        cls.user.set_password('password')
        cls.user.save()
        cls.url = reverse('api:obtain-token')

    def test_obtain_token__with_valid_user_credentials__token_obtained_successfully(self):
        data = {'username': self.user.bank_account.card_uuid, 'password': 'password'}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.data.get('token'))

    def test_obtain_token__with_invalid_user_credentials__bad_request(self):
        data = {'username': self.user.bank_account.card_uuid, 'password': 'wrong_password'}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get('token'))


class CustomRefreshJwtTokenViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.url = reverse('api:refresh-token')

    def setUp(self):
        self.token = SlidingToken.for_user(UserFactory())

    def test_refresh_token__valid_token__token_refreshed_successfully(self):
        data = {'token': str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.data.get('token'))

    def test_refresh_token__token_has_expired__unauthorized(self):
        self.token.payload['exp'] -= 100000
        data = {'token': str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get('token'))
        self.assertEqual('token_not_valid', response.data.get('code'))


class CustomVerifyJwtTokenViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.url = reverse('api:verify-token')

    def setUp(self):
        self.token = SlidingToken.for_user(UserFactory())

    def test_verify_token__valid_token__return_valid_token(self):
        data = {'token': str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertEqual({}, response.data)

    def test_verify_token__token_has_expired__unauthorized(self):
        self.token.payload['exp'] -= 100000
        data = {'token': str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get('token'))
        self.assertEqual('token_not_valid', response.data.get('code'))


class SociProductListViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = reverse('api:products')
        cls.client = APIClient()

        SociProductFactory(sku_number="dahls", name="Dahls", description="En gammel slager. Nytes lunken.")
        SociProductFactory(sku_number="ice", name="Smirnoff ICE", description="Når du føler for å imponere.")
        SociProductFactory(sku_number="pizzabolle", name="Pizzabolle", description="Kjøkkenet har Soci. Hurra!")

    def setUp(self):
        self.client.force_authenticate(UserFactory(is_staff=True))

    def test_get__valid_request__ok(self):
        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 3)
        self.assertEqual((len(response.data[0])), 6)

    def test_get__product_without_description__description_blank(self):
        SociProductFactory(sku_number="z", name="Nordlands Pils", description=None)

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 4)
        self.assertFalse(response.data[-1]['description'])

    def test_get__expired_product__do_not_include_in_response(self):
        expired_product = SociProductFactory(end=timezone.now() - timedelta(hours=1))

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(expired_product.sku_number, [product['sku_number'] for product in response.data])

    def test_get__not_available_product__do_not_include_in_response(self):
        future_available_product = SociProductFactory(start=timezone.now() + timedelta(hours=1))

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(future_available_product.sku_number, [product['sku_number'] for product in response.data])

    def test_get__sorted_by_sku_number(self):
        first_product = SociProductFactory(sku_number="a")

        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_product.sku_number, response.data[0]['sku_number'])
        self.assertEqual('dahls', response.data[1]['sku_number'])
        self.assertEqual('ice', response.data[2]['sku_number'])
        self.assertEqual('pizzabolle', response.data[3]['sku_number'])


class SociBankAccountBalanceDetailViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

    def setUp(self):
        self.user_account = SociBankAccountFactory(user__is_staff=True)
        self.client.force_authenticate(self.user_account.user)
        self.url = reverse('api:balance')

    def test_get_balance__positive_amount__ok(self):
        self.user_account.add_funds(amount=1337)

        response = self.client.get(self.url, {'card_uuid': self.user_account.card_uuid})

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 4)
        self.assertFalse(response.data['balance'])
        self.assertTrue(response.data['has_sufficient_funds'])

    def test_get_balance__negative_amount__payment_required(self):
        self.user_account.remove_funds(amount=2000)

        response = self.client.get(self.url, {'card_uuid': self.user_account.card_uuid})

        self.assertEquals(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEquals(len(response.data), 4)
        self.assertFalse(response.data['balance'])
        self.assertFalse(response.data['has_sufficient_funds'])

    def test_get_balance__user_wants_amount_shown__ok_and_amount_shown(self):
        self.user_account.add_funds(amount=1337)
        self.user_account.display_balance_at_soci = True
        self.user_account.save()

        response = self.client.get(self.url, {'card_uuid': self.user_account.card_uuid})

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 4)
        self.assertTrue(response.data['has_sufficient_funds'])

    def test_get_balance__invalid_card__not_found(self):
        response = self.client.get(self.url, {'card_uuid': '01189998819991197253'})

        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_balance__no_card_provided__bad_request(self):
        self.url = reverse('api:balance')
        response = self.client.get(self.url, {})

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


class SociBankAccountChargeViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.soci_account = SociBankAccountFactory(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID, user__is_staff=True)
        cls.dahls = SociProductFactory(name="Dahls", price=30)
        cls.smirre = SociProductFactory(name="Smirnoff ICE", price=35)
        cls.direct_charge = SociProductFactory(sku_number=settings.DIRECT_CHARGE_SKU, price=0)

    def setUp(self):
        self.user_account = SociBankAccountFactory(balance=1000)
        self.client.force_authenticate(self.soci_account.user)
        self.url = reverse('api:charge', args=[self.user_account.id])

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
        self.assertTrue(self.user_account.transaction_history['purchases'].last().is_valid)

    def test_charge__user_wants_balance_shown__created_and_return_balance(self):
        self.user_account.display_balance_at_soci = True
        self.user_account.save()
        data = [
            {"sku": self.smirre.sku_number}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(965, response.data['amount_remaining'])

    def test_charge__insufficient_balance__payment_required(self):
        self.user_account.remove_funds(1000)
        data = [
            {"sku": self.smirre.sku_number}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEquals(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_charge__sum_of_same_product_exceeds_balance__payment_required(self):
        """
        Regression test
        """
        data = [
            {'sku': self.smirre.sku_number, 'order_size': 30},
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_charge__sum_of_multiple_products_exceed_balance__payment_required(self):
        """
        Regression test
        """
        data = [
            {'sku': self.smirre.sku_number, 'order_size': 15},
            {'sku': self.dahls.sku_number, 'order_size': 17}
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

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
