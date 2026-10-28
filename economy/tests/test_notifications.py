from unittest import mock

from addict import Dict
from django.test import TestCase
from graphene.test import Client
from graphql_relay import to_global_id

from chat.tests.test_mega_chats import user_with
from economy.models import Deposit
from economy.notifications import notify_deposit_approved
from economy.tests.factories import DepositFactory
from ksg_nett.schema import schema


class NotifyDepositApprovedTest(TestCase):
    def setUp(self):
        self.deposit = DepositFactory.create(
            amount=1500, deposit_method=Deposit.DepositMethod.BANK_TRANSFER
        )
        self.owner = self.deposit.account.user
        self.owner.notify_on_deposit = True
        self.owner.save()
        self.send_to_users = self.patch("economy.notifications.send_to_users")
        self.send_deposit_approved_email = self.patch(
            "economy.utils.send_deposit_approved_email"
        )

    def patch(self, target):
        patcher = mock.patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_emails_and_pushes_the_amount_to_the_account_owner(self):
        notify_deposit_approved(self.deposit)

        self.send_deposit_approved_email.assert_called_once_with(self.deposit)
        user_ids, message = self.send_to_users.call_args.args
        self.assertEqual(user_ids, [self.owner.pk])
        self.assertEqual(message.title, "Innskudd godkjent")
        self.assertEqual(
            message.body, "1\u00a0500\u00a0kr er satt inn på Soci-kontoen din."
        )
        self.assertEqual(message.path, "/economy/me")
        self.assertEqual(message.tag, f"deposit-{self.deposit.pk}")

    def test_the_deposit_setting_turns_off_both_channels(self):
        self.owner.notify_on_deposit = False
        self.owner.save()

        notify_deposit_approved(self.deposit)

        self.send_deposit_approved_email.assert_not_called()
        self.send_to_users.assert_not_called()

    def test_approve_deposit_notifies_once(self):
        approver = user_with("economy.approve_deposit")
        approve = """
        mutation($depositId: ID!) {
            approveDeposit(depositId: $depositId) { deposit { approved } } }
        """
        with self.captureOnCommitCallbacks(execute=True):
            result = Client(schema).execute(
                approve,
                variables={"depositId": to_global_id("DepositNode", self.deposit.pk)},
                context=Dict(user=approver),
            )

        self.assertNotIn("errors", result)
        self.send_deposit_approved_email.assert_called_once()
        self.assertEqual(self.send_to_users.call_args.args[0], [self.owner.pk])
