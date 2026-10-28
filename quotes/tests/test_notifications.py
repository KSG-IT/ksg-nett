from unittest import mock

from addict import Dict
from django.test import TestCase
from graphene.test import Client
from graphql_relay import to_global_id

from chat.tests.test_mega_chats import user_with
from ksg_nett.schema import schema
from quotes.notifications import notify_tagged_in_quote
from quotes.tests.factories import QuoteFactory
from users.tests.factories import UserFactory


class NotifyTaggedInQuoteTest(TestCase):
    APPROVE = """
    mutation($quoteId: ID!) { approveQuote(quoteId: $quoteId) { quote { id } } }
    """

    def setUp(self):
        self.pushed, self.emailed = UserFactory.create_batch(2)
        self.pushed.push_on_quote = True
        self.pushed.save()
        self.emailed.notify_on_quote = True
        self.emailed.save()
        self.quote = QuoteFactory.create(
            text="Det er ikke fyll, det er kultur",
            tagged=[self.pushed, self.emailed],
        )
        self.send_to_users = self.patch("quotes.notifications.send_to_users")
        self.send_email = self.patch("quotes.notifications.send_tagged_in_quote_email")

    def patch(self, target):
        patcher = mock.patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def approve(self):
        with self.captureOnCommitCallbacks(execute=True):
            result = Client(schema).execute(
                self.APPROVE,
                variables={"quoteId": to_global_id("QuoteNode", self.quote.pk)},
                context=Dict(user=user_with("quotes.approve_quote")),
            )
        self.assertNotIn("errors", result)

    def test_each_setting_decides_its_own_channel(self):
        notify_tagged_in_quote(self.quote)

        self.assertEqual(set(self.send_email.call_args.args[1]), {self.emailed})
        user_ids, message = self.send_to_users.call_args.args
        self.assertEqual(user_ids, [self.pushed.pk])
        self.assertEqual(message.title, "Du er sitert")
        self.assertEqual(message.body, "Det er ikke fyll, det er kultur")
        self.assertEqual(message.path, "/quotes")

    def test_the_approver_gets_no_push(self):
        notify_tagged_in_quote(self.quote, approver=self.pushed)

        self.send_to_users.assert_not_called()

    def test_approve_quote_notifies_only_the_first_time(self):
        self.approve()
        self.approve()

        self.send_email.assert_called_once()
        self.send_to_users.assert_called_once()
