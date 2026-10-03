from smtplib import SMTPDataError
from unittest import mock

from addict import Dict
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from graphene.test import Client

from ksg_nett.schema import schema
from users.tests.factories import UserFactory

SEND = """
    mutation Send($message: String!, $anonymous: Boolean!) {
      sendFeedback(message: $message, anonymous: $anonymous) { ok }
    }
"""


class TestSendFeedback(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.graphql_client = Client(schema)
        self.user = UserFactory.create(
            first_name="Ola", last_name="Nordmann", email="ola@example.com"
        )

    def send(self, message="Kaffemaskinen piper.", anonymous=False, user=None):
        return self.graphql_client.execute(
            SEND,
            variables={"message": message, "anonymous": anonymous},
            context=Dict(user=user or self.user),
        )

    def test__sends_an_email_with_name_and_reply_to(self):
        executed = self.send()
        self.assertNotIn("errors", executed)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [settings.FEEDBACK_EMAIL])
        self.assertEqual(email.reply_to, ["ola@example.com"])
        self.assertIn("Kaffemaskinen piper.", email.body)
        self.assertIn("Ola Nordmann", email.body)
        self.assertIn("ola@example.com", email.body)

    def test__anonymous_feedback_has_no_name_and_no_reply_to(self):
        executed = self.send(anonymous=True)
        self.assertNotIn("errors", executed)
        email = mail.outbox[0]
        self.assertEqual(email.reply_to, [])
        self.assertIn("Kaffemaskinen piper.", email.body)
        self.assertNotIn("Ola", email.body)
        self.assertNotIn("ola@example.com", email.body)
        self.assertNotIn("ola@example.com", email.subject)

    def test__the_message_can_be_500_characters(self):
        self.assertNotIn("errors", self.send(message="x" * 500))
        self.assertEqual(len(mail.outbox), 1)

    def test__a_longer_message_is_refused(self):
        self.assertIn("errors", self.send(message="x" * 501))
        self.assertEqual(len(mail.outbox), 0)

    def test__an_empty_message_is_refused(self):
        self.assertIn("errors", self.send(message="   "))
        self.assertEqual(len(mail.outbox), 0)

    def test__needs_login(self):
        self.assertIn("errors", self.send(user=AnonymousUser()))
        self.assertEqual(len(mail.outbox), 0)

    def test__at_most_5_messages_per_hour_per_user(self):
        for _ in range(5):
            self.assertNotIn("errors", self.send())
        self.assertIn("errors", self.send())
        self.assertEqual(len(mail.outbox), 5)
        # Another user is not limited
        self.assertNotIn("errors", self.send(user=UserFactory.create()))

    def test__the_email_has_an_html_version_with_the_message_escaped(self):
        self.send(message="<b>Hei</b>\nNy linje")
        email = mail.outbox[0]
        self.assertEqual(len(email.alternatives), 1)
        html, mimetype = email.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn("&lt;b&gt;Hei&lt;/b&gt;", html)
        self.assertNotIn("<b>Hei</b>", html)
        self.assertIn("<br>", html)
        self.assertIn("Ola Nordmann", html)

    def test__the_anonymous_html_version_has_no_name(self):
        self.send(anonymous=True)
        html, _ = mail.outbox[0].alternatives[0]
        self.assertNotIn("Ola", html)
        self.assertNotIn("ola@example.com", html)

    def test__a_rejected_email_gives_a_clear_error(self):
        rejected = SMTPDataError(550, b"Rejected by spam filter")
        with mock.patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages",
            side_effect=rejected,
        ):
            executed = self.send()
        self.assertIn("errors", executed)
        error = executed["errors"][0]["message"]
        self.assertIn("kunne ikke sendes", error)
        self.assertNotIn("550", error)
