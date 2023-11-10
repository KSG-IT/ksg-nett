import json
from datetime import timedelta
from random import randint

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import SlidingToken

from economy.models import SociSession
from economy.tests.factories import (
    SociProductFactory,
    SociBankAccountFactory,
    SociSessionFactory,
    ProductOrderFactory,
)
from common.tests.factories import FeatureFlagFactory
from django.conf import settings
from users.tests.factories import UserFactory


class CustomTokenObtainSlidingViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.user = SociBankAccountFactory().user
        cls.url = reverse("api:obtain-token")

    def test_obtain_token__with_valid_user_credentials__token_obtained_successfully(
        self,
    ):
        data = {"card_uuid": self.user.bank_account.card_uuid}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.data.get("token"))

    def test_obtain_token__with_invalid_user_credentials__unauthorized(self):
        data = {"card_uuid": randint(1000, 10000)}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get("token"))

    def test_obtain_token__with_valid_user_credentials_for_non_active_user__bad_request(
        self,
    ):
        user = UserFactory(is_active=False)
        SociBankAccountFactory(user=user)
        data = {"card_uuid": user.bank_account.card_uuid}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get("token"))

    def test_obtain_token__start_soci_session_and_terminate_previous(self):
        unterminated_session = SociSessionFactory()
        # sessions without any sales are deleted on termination
        ProductOrderFactory.create_batch(3, session=unterminated_session)
        data = {"card_uuid": self.user.bank_account.card_uuid}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        unterminated_session.refresh_from_db()
        self.assertIsNotNone(unterminated_session.closed_at)
        self.assertTrue(
            SociSession.objects.filter(
                created_at__gt=unterminated_session.closed_at,
                closed_at__isnull=True,
                created_by=self.user,
            ).exists()
        )


class CustomTokenRefreshSlidingViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.url = reverse("api:refresh-token")

    def setUp(self):
        self.token = SlidingToken.for_user(UserFactory())

    def test_refresh_token__valid_token__token_refreshed_successfully(self):
        data = {"token": str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.data.get("token"))

    def test_refresh_token__token_has_expired__unauthorized(self):
        self.token.payload["exp"] -= 100000
        data = {"token": str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get("token"))
        self.assertEqual("token_not_valid", response.data.get("code"))


class CustomTokenVerifyViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.url = reverse("api:verify-token")

    def setUp(self):
        self.token = SlidingToken.for_user(UserFactory())

    def test_verify_token__valid_token__return_valid_token(self):
        data = {"token": str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(200, response.status_code)
        self.assertEqual({}, response.data)

    def test_verify_token__token_has_expired__unauthorized(self):
        self.token.payload["exp"] -= 100000
        data = {"token": str(self.token)}

        response = self.client.post(self.url, data)

        self.assertEqual(401, response.status_code)
        self.assertIsNone(response.data.get("token"))
        self.assertEqual("token_not_valid", response.data.get("code"))


class TerminateSociSessionViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.url = reverse("api:terminate-session")

    def setUp(self):
        self.client.force_authenticate(UserFactory(is_staff=True))
        now = timezone.now()
        session_one = SociSessionFactory(
            created_at=now - timedelta(days=3), closed_at=now - timedelta(days=2)
        )
        ProductOrderFactory.create_batch(3, session=session_one)
        session_two = SociSessionFactory(
            created_at=now - timedelta(days=2), closed_at=now - timedelta(days=1)
        )
        ProductOrderFactory.create_batch(3, session=session_two)
        self.active_session = SociSessionFactory(created_at=now - timedelta(days=1))
        ProductOrderFactory.create_batch(3, session=self.active_session)

    def test_delete__active_session__ok_and_update_session_with_end_date(self):
        response = self.client.delete(self.url)

        self.assertEqual(200, response.status_code)
        self.active_session.refresh_from_db()
        self.assertIsNotNone(self.active_session.closed_at)

    def test_delete__no_active_session__ok_and_update_nothing(self):
        now = timezone.now()
        self.active_session.closed_at = now
        self.active_session.save()

        response = self.client.delete(self.url)

        self.assertEqual(200, response.status_code)
        self.active_session.refresh_from_db()
        self.assertEqual(self.active_session.closed_at, now)


class SociProductListViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = reverse("api:products")
        cls.client = APIClient()

        SociProductFactory(
            sku_number="dahls",
            name="Dahls",
            description="En gammel slager. Nytes lunken.",
        )
        SociProductFactory(
            sku_number="ice",
            name="Smirnoff ICE",
            description="Når du føler for å imponere.",
        )
        SociProductFactory(
            sku_number="pizzabolle",
            name="Pizzabolle",
            description="Kjøkkenet har Soci. Hurra!",
        )

    def setUp(self):
        self.client.force_authenticate(UserFactory(is_staff=True))

    def test_get__valid_request__ok(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual((len(response.data[0])), 5)

    def test_get__expired_product__do_not_include_in_response(self):
        expired_product = SociProductFactory(end=timezone.now() - timedelta(hours=1))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(
            expired_product.sku_number,
            [product["sku_number"] for product in response.data],
        )

    def test_get__not_available_product__do_not_include_in_response(self):
        future_available_product = SociProductFactory(
            start=timezone.now() + timedelta(hours=1)
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(
            future_available_product.sku_number,
            [product["sku_number"] for product in response.data],
        )


class SociBankAccountBalanceDetailViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

    def setUp(self):
        self.user_account = SociBankAccountFactory(user__is_staff=True)
        self.client.force_authenticate(self.user_account.user)
        self.url = reverse("api:balance")

    def test_get_balance__positive_amount__ok(self):
        self.user_account.add_funds(amount=1337)

        response = self.client.get(self.url, {"card_uuid": self.user_account.card_uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(1337, response.data["balance"])

    def test_get_balance__negative_amount__ok(self):
        self.user_account.remove_funds(amount=2000)

        response = self.client.get(self.url, {"card_uuid": self.user_account.card_uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(-2000, response.data["balance"])

    def test_get_balance__invalid_card__not_found(self):
        response = self.client.get(self.url, {"card_uuid": "01189998819991197253"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_balance__no_card_provided__bad_request(self):
        self.url = reverse("api:balance")
        response = self.client.get(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChargeAccountStockMarketEnabled(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

    def setUp(self):
        self.user_account = SociBankAccountFactory(user__is_staff=True)
        self.tuborg = SociProductFactory.create(
            name="tuborg", sku_number="TBGR", price=25, purchase_price=20
        )
        self.tuborg_no_purchase_price = SociProductFactory.create(
            name="tuborg", sku_number="TBGR2", price=25
        )
        self.ice = SociProductFactory.create(
            name="Smirnoff Ice", sku_number="ICE", price=45, purchase_price=39
        )
        self.ice_no_purchase_price = SociProductFactory.create(
            name="Smirnoff Ice", sku_number="ICE2", price=45
        )
        self.client.force_authenticate(self.user_account.user)
        self.url = reverse("api:charge")

        SociSessionFactory.create()
        self.initial_funds = 1000
        self.user_account.add_funds(self.initial_funds)
        self.flag = FeatureFlagFactory.create(
            name=settings.X_APP_STOCK_MARKET_MODE, enabled=True
        )

    def test__no_existing_sales__charge_purchase_price(self):
        ice_order_size = 1
        tuborg_order_size = 2
        self.client.post(
            self.url,
            {
                "bank_account_id": f"{self.user_account.id}",
                "products": [
                    {
                        "sku": self.ice_no_purchase_price.sku_number,
                        "order_size": ice_order_size,
                    },
                    {
                        "sku": self.tuborg_no_purchase_price.sku_number,
                        "order_size": tuborg_order_size,
                    },
                ],
            },
            format="json",
        )
        self.user_account.refresh_from_db()
        account_charge = self.initial_funds - self.user_account.balance
        expected_ice_cost = ice_order_size * self.ice_no_purchase_price.price
        expected_tuborg_cost = tuborg_order_size * self.tuborg_no_purchase_price.price
        expected_total_cost = expected_tuborg_cost + expected_ice_cost

        self.assertEqual(account_charge, expected_total_cost)

    def test__no_purchase_price_set__charge_ordinary_price(self):
        ice_order_size = 1
        tuborg_order_size = 2
        self.client.post(
            self.url,
            {
                "bank_account_id": f"{self.user_account.id}",
                "products": [
                    {"sku": self.ice.sku_number, "order_size": ice_order_size},
                    {"sku": self.tuborg.sku_number, "order_size": tuborg_order_size},
                ],
            },
            format="json",
        )
        self.user_account.refresh_from_db()
        account_charge = self.initial_funds - self.user_account.balance
        expected_ice_cost = ice_order_size * self.ice.purchase_price
        expected_tuborg_cost = tuborg_order_size * self.tuborg.purchase_price
        expected_total_cost = expected_tuborg_cost + expected_ice_cost

        self.assertEqual(account_charge, expected_total_cost)


class ChargeAccountStockMarketDisabled(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

    def setUp(self):
        self.user_account = SociBankAccountFactory(user__is_staff=True)
        self.tuborg = SociProductFactory.create(
            name="tuborg", sku_number="TBGR", price=25, purchase_price=20
        )
        self.ice = SociProductFactory.create(
            name="Smirnoff Ice", sku_number="ICE", price=45, purchase_price=39
        )
        self.client.force_authenticate(self.user_account.user)
        self.url = reverse("api:charge")

        SociSessionFactory.create()
        self.initial_funds = 1000
        self.user_account.add_funds(self.initial_funds)
        self.flag = FeatureFlagFactory.create(
            name=settings.X_APP_STOCK_MARKET_MODE, enabled=False
        )

    def test__stock_mode_disabled__charge_ordinary_price(self):
        ice_order_size = 1
        tuborg_order_size = 2
        self.client.post(
            self.url,
            {
                "bank_account_id": f"{self.user_account.id}",
                "products": [
                    {"sku": self.ice.sku_number, "order_size": ice_order_size},
                    {"sku": self.tuborg.sku_number, "order_size": tuborg_order_size},
                ],
            },
            format="json",
        )
        self.user_account.refresh_from_db()
        account_charge = self.initial_funds - self.user_account.balance
        expected_ice_cost = ice_order_size * self.ice.price
        expected_tuborg_cost = tuborg_order_size * self.tuborg.price
        expected_total_cost = expected_tuborg_cost + expected_ice_cost

        self.assertEqual(account_charge, expected_total_cost)
