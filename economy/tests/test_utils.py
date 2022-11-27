from django.test import TestCase
from economy.utils import parse_transaction_history
from economy.tests.factories import (
    SociBankAccountFactory,
    ProductOrderFactory,
    DepositFactory,
    TransferFactory,
)
from users.schema import BankAccountActivity


class TestParseTransactionHistory(TestCase):
    def setUp(self) -> None:
        self.bank_account = SociBankAccountFactory.create()
        ProductOrderFactory.create_batch(5, source=self.bank_account)
        TransferFactory.create_batch(5, source=self.bank_account)
        DepositFactory.create_batch(3, account=self.bank_account, approved=True)

    def test__parse_transaction_history__correctly_parses_activity(self):
        """
        Correctly parsed if
            * Same total length
            * All objects are of BankAccountType
        """
        parsed_activities = parse_transaction_history(self.bank_account)
        self.assertEqual(13, len(parsed_activities))
        assert all(
            isinstance(activity, BankAccountActivity) for activity in parsed_activities
        )

    def test__parse_transaction_history_with_slice_kwarg__returns_sliced_length(self):
        parsed_activities = parse_transaction_history(self.bank_account, 5)
        self.assertEqual(5, len(parsed_activities))
