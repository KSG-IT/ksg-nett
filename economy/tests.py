from django.test import TestCase

from economy.models import Transaction, Deposit, SociBankAccount
from users.models import User


class TransactionTest(TestCase):
    def test_transactions_status__correct_status(self):
        self.user = User.objects.create(username='admin')
        self.valid_transaction = Transaction.objects.create(amount=69, signed_off_by=self.user)
        self.invalid_transaction = Transaction.objects.create(amount=1337, signed_off_by=None)

        self.assertTrue(self.valid_transaction.is_valid)
        self.assertFalse(self.invalid_transaction.is_valid)


class DepositTest(TestCase):
    def test_deposit_status__correct_status(self):
        self.user = User.objects.create(username='admin')
        self.valid_deposit = Deposit.objects.create(amount=69, signed_off_by=self.user)
        self.invalid_deposit = Deposit.objects.create(amount=1337, signed_off_by=None)

        self.assertTrue(self.valid_deposit.is_valid)
        self.assertFalse(self.invalid_deposit.is_valid)


class SociBankAccountTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='admin')
        self.soci_account = SociBankAccount.objects.create(user=self.user, balance=500)

    def test_soci_bank_account__correct_status(self):
        self.assertTrue(self.soci_account.has_sufficient_funds)
        self.assertFalse(self.soci_account.public_balance)

    def test_account_with_public_balance__display_balance(self):
        self.soci_account.display_balance_at_soci = True
        self.soci_account.save()

        self.assertTrue(self.soci_account.display_balance_at_soci)

    def test_account_with_transactions__transaction_history_retrieved_correctly(self):
        extra_account = SociBankAccount.objects.create(
            user=User.objects.create(username='user', email="realuser@samfundet.no"), balance=2000)
        self.first_transaction = Transaction.objects.create(
            source=self.soci_account, destination=extra_account, amount=69)
        self.second_transaction = Transaction.objects.create(
            source=extra_account, destination=self.soci_account, amount=1337)

        history = self.soci_account.transaction_history

        self.assertEqual(2, history.count())
        self.assertEqual(self.second_transaction, history.last())
