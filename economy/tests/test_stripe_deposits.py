import json
from unittest import mock

import stripe

from addict import Dict
from django.test import TestCase, override_settings
from graphene import Node
from graphene.test import Client

from economy.models import Deposit
from economy.tests.factories import DepositFactory, SociBankAccountFactory
from ksg_nett.schema import schema
from users.tests.factories import UserFactory

DELETE_DEPOSIT = """
    mutation($id: ID!) { deleteDeposit(id: $id) { found } }
"""


def stripe_deposit(account, **kwargs):
    defaults = dict(
        account=account,
        amount=215,
        resolved_amount=200,
        deposit_method=Deposit.DepositMethod.STRIPE,
        stripe_payment_id="pi_test",
        stripe_payment_intent_status=Deposit.StripePaymentIntentStatusOptions.CREATED,
        approved=False,
        approved_by=None,
    )
    defaults.update(kwargs)
    return DepositFactory.create(**defaults)


@mock.patch("stripe.PaymentIntent.cancel")
@mock.patch("stripe.PaymentIntent.retrieve")
class TestDeleteStripeDeposit(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.owner = UserFactory.create()
        self.account = SociBankAccountFactory.create(user=self.owner)
        self.deposit = stripe_deposit(self.account)
        self.variables = {"id": Node.to_global_id("DepositNode", self.deposit.pk)}

    def delete(self, user):
        return self.graphql_client.execute(
            DELETE_DEPOSIT, variables=self.variables, context=Dict(user=user)
        )

    def test__intent_already_canceled__deletes_without_cancel(self, retrieve, cancel):
        retrieve.return_value = mock.Mock(status="canceled")

        executed = self.delete(self.owner)

        self.assertNotIn("errors", executed)
        cancel.assert_not_called()
        self.assertFalse(Deposit.objects.filter(pk=self.deposit.pk).exists())

    def test__open_intent__is_canceled_and_deleted(self, retrieve, cancel):
        retrieve.return_value = mock.Mock(status="requires_payment_method")

        executed = self.delete(self.owner)

        self.assertNotIn("errors", executed)
        cancel.assert_called_once()
        self.assertFalse(Deposit.objects.filter(pk=self.deposit.pk).exists())

    def test__paid_or_processing_intent__is_not_deleted(self, retrieve, cancel):
        for status, message in (
            ("succeeded", "The payment went through"),
            ("processing", "The payment is still being processed"),
        ):
            with self.subTest(status=status):
                retrieve.return_value = mock.Mock(status=status)

                executed = self.delete(self.owner)

                self.assertIn(message, executed["errors"][0]["message"])
                cancel.assert_not_called()
                self.assertTrue(Deposit.objects.filter(pk=self.deposit.pk).exists())

    def test__other_user__cannot_delete(self, retrieve, cancel):
        other = UserFactory.create()
        SociBankAccountFactory.create(user=other)

        executed = self.delete(other)

        self.assertIn("errors", executed)
        retrieve.assert_not_called()
        self.deposit.refresh_from_db()
        self.assertEqual(self.deposit.account, self.account)


@mock.patch("stripe.PaymentIntent.retrieve")
class TestClientSecretFromDepositId(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.owner = UserFactory.create()
        self.deposit = stripe_deposit(SociBankAccountFactory.create(user=self.owner))

    def client_secret(self, user):
        executed = self.graphql_client.execute(
            "query($id: ID!) { getClientSecretFromDepositId(depositId: $id) }",
            variables={"id": Node.to_global_id("DepositNode", self.deposit.pk)},
            context=Dict(user=user),
        )
        return executed["data"]["getClientSecretFromDepositId"]

    def test__owner__gets_client_secret(self, retrieve):
        retrieve.return_value = mock.Mock(client_secret="secret")
        self.assertEqual(self.client_secret(self.owner), "secret")

    def test__other_user__gets_null(self, retrieve):
        other = UserFactory.create()
        SociBankAccountFactory.create(user=other)

        self.assertIsNone(self.client_secret(other))
        retrieve.assert_not_called()


class TestStripeWebhook(TestCase):
    def setUp(self) -> None:
        self.owner = UserFactory.create(notify_on_deposit=False)
        self.account = SociBankAccountFactory.create(user=self.owner, balance=200)

    def post_event(self, event, url="/economy/stripe-webhook/2026-08-26"):
        # A real Event, so the handlers see what stripe.Webhook returns
        stripe_event = stripe.Event.construct_from(event, "sk_test")
        with mock.patch(
            "stripe.Webhook.construct_event", return_value=stripe_event
        ) as construct_event:
            response = self.client.post(
                url,
                data=json.dumps(event),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="signature",
            )
        self.construct_event = construct_event
        return response

    @override_settings(
        STRIPE_WEBHOOK_SECRET_2022_11_15="whsec_old",
        STRIPE_WEBHOOK_SECRET_2026_08_26="whsec_new",
    )
    def test__each_endpoint__checks_its_own_secret(self):
        event = {"type": "customer.created", "data": {"object": {}}}
        for url, secret in (
            ("/economy/stripe-webhook", "whsec_old"),
            ("/economy/stripe-webhook/2026-08-26", "whsec_new"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.post_event(event, url).status_code, 200)
                self.assertEqual(self.construct_event.call_args.args[2], secret)

    def test__refund__deletes_deposit_without_notify(self):
        deposit = stripe_deposit(self.account, approved=True)
        event = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "payment_intent": "pi_test",
                    "amount_captured": 21500,
                    "amount_refunded": 21500,
                    "amount": 21500,
                }
            },
        }

        response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Deposit.objects.filter(pk=deposit.pk).exists())
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 0)

    def test__canceled_intent__deletes_unapproved_deposit(self):
        deposit = stripe_deposit(self.account)
        event = {
            "type": "payment_intent.canceled",
            "data": {"object": {"id": "pi_test"}},
        }

        response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Deposit.objects.filter(pk=deposit.pk).exists())

    @mock.patch("sentry_sdk.capture_message")
    def test__unhandled_event__is_acknowledged_and_reported(self, capture_message):
        event = {"type": "customer.created", "data": {"object": {}}}

        response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        capture_message.assert_called_once_with(
            "Unhandled Stripe event type customer.created", level="warning"
        )
