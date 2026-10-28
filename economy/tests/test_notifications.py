from unittest import mock

from addict import Dict
from django.test import TestCase
from graphene.test import Client
from graphql_relay import to_global_id

from chat.tests.test_mega_chats import user_with
from economy.models import Deposit, SociOrderSession
from economy.notifications import (
    notify_deposit_approved,
    notify_order_session_invited,
)
from economy.tests.factories import DepositFactory
from ksg_nett.schema import schema
from users.tests.factories import UserFactory


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

    def test_the_email_setting_turns_off_only_the_email(self):
        self.owner.notify_on_deposit = False
        self.owner.save()

        notify_deposit_approved(self.deposit)

        self.send_deposit_approved_email.assert_not_called()
        self.assertEqual(self.send_to_users.call_args.args[0], [self.owner.pk])

    def test_the_push_setting_turns_off_only_the_push(self):
        self.owner.push_on_deposit = False
        self.owner.save()

        notify_deposit_approved(self.deposit)

        self.send_deposit_approved_email.assert_called_once_with(self.deposit)
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


class NotifyOrderSessionInvitedTest(TestCase):
    def setUp(self):
        self.session = SociOrderSession.objects.create(
            status=SociOrderSession.Status.FOOD_ORDERING
        )
        self.on, self.off, self.actor = UserFactory.create_batch(3)
        self.off.push_on_order_session = False
        self.off.save()
        self.send_to_users = self.patch("economy.notifications.send_to_users")
        self.send_email = self.patch(
            "economy.utils.send_soci_order_session_invitation_email"
        )

    def patch(self, target):
        patcher = mock.patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_emails_everyone_and_pushes_all_but_the_actor_and_opted_out(self):
        notify_order_session_invited(
            self.session, [self.on.pk, self.off.pk, self.actor.pk], self.actor
        )

        emailed = self.send_email.call_args.args[1]
        self.assertEqual(set(emailed), {self.on, self.off, self.actor})
        user_ids, message = self.send_to_users.call_args.args
        self.assertEqual(user_ids, [self.on.pk])
        self.assertEqual(message.title, "Stilletime")
        self.assertEqual(message.path, "/economy/soci-sessions/live")
        self.assertEqual(message.urgency, "high")

    def test_invite_users_notifies(self):
        inviter = user_with("economy.change_sociordersession")
        invite = """
        mutation($users: [ID]!) {
            inviteUsersToOrderSession(users: $users) { sociOrderSession { id } } }
        """
        with self.captureOnCommitCallbacks(execute=True):
            result = Client(schema).execute(
                invite,
                variables={"users": [to_global_id("UserNode", self.on.pk)]},
                context=Dict(user=inviter),
            )

        self.assertNotIn("errors", result)
        self.send_email.assert_called_once()
        self.assertEqual(self.send_to_users.call_args.args[0], [self.on.pk])
