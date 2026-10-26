import json
from unittest import mock

from django.contrib.admin import helpers
from django.test import TestCase, override_settings
from django.urls import reverse

from push import webpush
from push.models import PushSubscription
from push.tests.helpers import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, make_subscription
from users.tests.factories import UserFactory

CHANGELIST = reverse("admin:push_pushsubscription_changelist")


@override_settings(
    APP_URL="app.ksg-nett.no",
    VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY,
    VAPID_PRIVATE_KEY=VAPID_PRIVATE_KEY,
)
class SendTestPushActionTest(TestCase):
    def setUp(self):
        admin_user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(admin_user)
        self.subscription = make_subscription(UserFactory.create())

    def run_action(self, **form):
        data = {
            "action": "send_test_push",
            helpers.ACTION_CHECKBOX_NAME: [self.subscription.pk],
            **form,
        }
        return self.client.post(CHANGELIST, data, follow=True)

    def test_first_shows_the_form(self):
        with mock.patch("push.webpush.send") as send:
            response = self.run_action()

        self.assertContains(response, "Send a test push")
        self.assertContains(response, 'name="title"')
        send.assert_not_called()

    def test_sends_the_typed_notification_and_reports_the_result(self):
        result = webpush.SendResult(webpush.OK, 201)
        with mock.patch("push.webpush.send", return_value=result) as send:
            response = self.run_action(
                apply="Send", title="Hei", body="Fra admin", link="/chat"
            )

        payload = json.loads(send.call_args.args[1])
        self.assertEqual(
            payload["notification"],
            {
                "title": "Hei",
                "body": "Fra admin",
                "navigate": "https://app.ksg-nett.no/chat",
                "tag": "test",
                "lang": "nb",
            },
        )
        self.assertContains(
            response, f"Push subscription {self.subscription.pk}: sent (status 201)"
        )
        self.subscription.refresh_from_db()
        self.assertIsNotNone(self.subscription.last_success_at)

    def test_a_refused_push_shows_the_reason(self):
        result = webpush.SendResult(webpush.REJECTED, 400, '{"reason":"BadJwtToken"}')
        with mock.patch("push.webpush.send", return_value=result):
            response = self.run_action(apply="Send", title="Hei", body="", link="/")

        self.assertContains(response, "rejected (status 400)")
        self.assertContains(response, "BadJwtToken")
        self.assertTrue(PushSubscription.objects.exists())
