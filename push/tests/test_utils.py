import threading
import time
from unittest import mock

import requests
from django.test import TestCase, override_settings

from push import webpush
from push.models import PushSubscription
from push.tests.helpers import (
    VAPID_PRIVATE_KEY,
    VAPID_PUBLIC_KEY,
    make_subscription,
    make_vapid_keys,
)
from push.utils import app_url, is_push_service_endpoint, send_to_users
from users.tests.factories import UserFactory

PAYLOAD = {"web_push": 8030, "notification": {"title": "Bar", "body": "Hei"}}


@override_settings(
    VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY=VAPID_PRIVATE_KEY
)
class SendToUsersTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.subscription = make_subscription(self.user)

    def send_with_status(self, status_code):
        response = mock.Mock(status_code=status_code)
        with mock.patch("push.webpush.requests.post", return_value=response) as post:
            send_to_users([self.user.pk], PAYLOAD, topic="chat-1", urgency="high")
        return post

    def test_201_sets_last_success_at(self):
        post = self.send_with_status(201)

        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["headers"]["Topic"], "chat-1")
        self.assertEqual(post.call_args.kwargs["headers"]["Urgency"], "high")
        self.subscription.refresh_from_db()
        self.assertIsNotNone(self.subscription.last_success_at)

    def test_404_and_410_delete_the_subscription(self):
        for status_code in (404, 410):
            with self.subTest(status_code=status_code):
                self.send_with_status(status_code)
                self.assertFalse(PushSubscription.objects.exists())
                self.subscription = make_subscription(self.user)

    def test_other_results_keep_the_subscription(self):
        for status_code in (400, 413, 429, 500):
            with self.subTest(status_code=status_code):
                self.send_with_status(status_code)
                self.subscription.refresh_from_db()
                self.assertIsNone(self.subscription.last_success_at)

    def test_a_timeout_keeps_the_subscription(self):
        with mock.patch(
            "push.webpush.requests.post", side_effect=requests.exceptions.Timeout
        ):
            send_to_users([self.user.pk], PAYLOAD)

        self.assertTrue(PushSubscription.objects.exists())

    def test_an_exception_never_escapes(self):
        with mock.patch("push.webpush.send", side_effect=RuntimeError):
            send_to_users([self.user.pk], PAYLOAD)
        with mock.patch(
            "push.utils.PushSubscription.objects.filter", side_effect=RuntimeError
        ):
            send_to_users([self.user.pk], PAYLOAD)

    def test_skips_subscriptions_made_for_another_vapid_key(self):
        # A row copied from another instance, or left over from an old key
        other_public_key, _ = make_vapid_keys()
        PushSubscription.objects.all().delete()
        make_subscription(self.user, vapid_public_key=other_public_key)

        with mock.patch("push.webpush.send") as send:
            send_to_users([self.user.pk], PAYLOAD)

        send.assert_not_called()

    @override_settings(VAPID_PRIVATE_KEY="")
    def test_an_empty_vapid_key_makes_no_calls(self):
        with mock.patch("push.webpush.send") as send:
            send_to_users([self.user.pk], PAYLOAD)

        send.assert_not_called()

    @override_settings(PUSH_TOTAL_TIMEOUT=0.2)
    def test_the_total_timeout_cuts_off_a_hanging_send(self):
        release = threading.Event()

        def hang(*args, **kwargs):
            release.wait(5)
            return webpush.SendResult(webpush.OK, 201)

        started = time.monotonic()
        with mock.patch("push.webpush.send", side_effect=hang):
            send_to_users([self.user.pk], PAYLOAD)
        elapsed = time.monotonic() - started
        release.set()

        self.assertLess(elapsed, 2)
        self.subscription.refresh_from_db()
        self.assertIsNone(self.subscription.last_success_at)


class AppUrlTest(TestCase):
    @override_settings(APP_URL="app.ksg-nett.no")
    def test_adds_https_when_the_setting_has_no_scheme(self):
        self.assertEqual(app_url("/chat/1"), "https://app.ksg-nett.no/chat/1")

    @override_settings(APP_URL="http://localhost:3012")
    def test_keeps_a_scheme_in_the_setting(self):
        self.assertEqual(app_url("/chat/1"), "http://localhost:3012/chat/1")


class IsPushServiceEndpointTest(TestCase):
    def test_accepts_only_https_on_the_push_service_hosts(self):
        cases = {
            "https://fcm.googleapis.com/fcm/send/abc": True,
            "https://web.push.apple.com/QGz": True,
            "https://updates.push.services.mozilla.com/wpush/v2/x": True,
            "https://wns2-db5p.notify.windows.com/w/?token=x": True,
            "http://fcm.googleapis.com/fcm/send/abc": False,
            "https://fcm.googleapis.com:8443/fcm/send/abc": False,
            "https://evilfcm.googleapis.com.example.com/": False,
            "https://fcm.googleapis.com@10.0.0.1/": False,
            "https://localhost/": False,
        }
        for endpoint, expected in cases.items():
            with self.subTest(endpoint=endpoint):
                self.assertEqual(is_push_service_endpoint(endpoint), expected)
