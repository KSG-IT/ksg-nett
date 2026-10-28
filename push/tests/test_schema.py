import datetime

from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from chat.models import Chat, ChatMembership
from common.models import FeatureFlag
from ksg_nett.schema import schema
from push.models import PushSubscription
from push.tests.helpers import VAPID_PUBLIC_KEY
from users.tests.factories import UserFactory

ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc"

REGISTER = """
mutation($endpoint: String!, $p256dh: String!, $auth: String!, $userAgent: String) {
    registerPushSubscription(
        endpoint: $endpoint, p256dh: $p256dh, auth: $auth, userAgent: $userAgent
    ) { ok }
}
"""

REMOVE = """
mutation($endpoint: String!) { removePushSubscription(endpoint: $endpoint) { ok } }
"""


class PushSchemaTestCase(TestCase):
    def setUp(self):
        FeatureFlag.objects.create(name="push_notifications", enabled=True)
        self.client = Client(schema)
        self.anna, self.per = UserFactory.create_batch(2)

    def run_query(self, user, query, **variables):
        return self.client.execute(query, variables=variables, context=Dict(user=user))

    def register(self, user, endpoint=ENDPOINT, **keys):
        variables = {"p256dh": "key", "auth": "secret", **keys}
        return self.run_query(user, REGISTER, endpoint=endpoint, **variables)


class PushConfigTest(PushSchemaTestCase):
    @override_settings(VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY)
    def test_returns_the_public_key(self):
        result = self.run_query(self.anna, "query { pushConfig { vapidPublicKey } }")

        self.assertNotIn("errors", result)
        self.assertEqual(
            result["data"]["pushConfig"]["vapidPublicKey"], VAPID_PUBLIC_KEY
        )


class RegisterPushSubscriptionTest(PushSchemaTestCase):
    def test_creates_then_updates_the_row_for_the_endpoint(self):
        self.register(self.anna, userAgent="Firefox")
        result = self.register(self.anna, p256dh="new key", userAgent="Firefox 2")

        self.assertNotIn("errors", result)
        subscription = PushSubscription.objects.get()
        self.assertEqual(subscription.user, self.anna)
        self.assertEqual(subscription.p256dh, "new key")
        self.assertEqual(subscription.user_agent, "Firefox 2")

    @override_settings(VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY)
    def test_stores_the_vapid_key_of_this_server(self):
        self.register(self.anna)

        self.assertEqual(
            PushSubscription.objects.get().vapid_public_key, VAPID_PUBLIC_KEY
        )

    def test_another_user_on_the_same_device_takes_the_row_over(self):
        self.register(self.anna)
        self.register(self.per)

        self.assertEqual(PushSubscription.objects.get().user, self.per)

    def test_anonymous_call_is_refused(self):
        result = self.register(AnonymousUser())

        self.assertIn("errors", result)
        self.assertFalse(PushSubscription.objects.exists())

    def test_an_endpoint_outside_the_push_services_is_refused(self):
        result = self.register(self.anna, endpoint="https://ksg-nett.samfundet.no/")

        self.assertIn("errors", result)
        self.assertFalse(PushSubscription.objects.exists())

    def test_flag_off_refuses_the_call(self):
        FeatureFlag.objects.filter(name="push_notifications").update(enabled=False)

        result = self.register(self.anna)

        self.assertIn("errors", result)
        self.assertFalse(PushSubscription.objects.exists())


class RemovePushSubscriptionTest(PushSchemaTestCase):
    def test_deletes_only_the_callers_row(self):
        self.register(self.anna, endpoint=ENDPOINT)
        self.register(self.per, endpoint=ENDPOINT + "-per")

        mine = self.run_query(self.anna, REMOVE, endpoint=ENDPOINT)
        theirs = self.run_query(self.anna, REMOVE, endpoint=ENDPOINT + "-per")

        self.assertTrue(mine["data"]["removePushSubscription"]["ok"])
        self.assertTrue(theirs["data"]["removePushSubscription"]["ok"])
        self.assertEqual(
            list(PushSubscription.objects.values_list("user", flat=True)),
            [self.per.pk],
        )


class SetChatNotificationsTest(PushSchemaTestCase):
    def test_saves_both_settings_and_shows_them_on_me(self):
        mutation = """
        mutation { setChatNotifications(onMessage: false, onAdded: true) {
            user { id } } }
        """
        result = self.run_query(self.anna, mutation)
        me = self.run_query(
            self.anna, "query { me { notifyOnChatMessage notifyOnChatAdded } }"
        )

        self.assertNotIn("errors", result)
        self.assertEqual(
            me["data"]["me"], {"notifyOnChatMessage": False, "notifyOnChatAdded": True}
        )


class SetPushSettingsTest(PushSchemaTestCase):
    def test_changes_only_the_given_settings(self):
        mutation = """
        mutation { setPushSettings(onDeposit: false, onQuote: true) {
            user { id } } }
        """
        result = self.run_query(self.anna, mutation)
        me = self.run_query(
            self.anna,
            "query { me { pushOnDeposit pushOnQuote pushOnShift notifyOnChatMessage } }",
        )

        self.assertNotIn("errors", result)
        self.assertEqual(
            me["data"]["me"],
            {
                "pushOnDeposit": False,
                "pushOnQuote": True,
                "pushOnShift": False,
                "notifyOnChatMessage": True,
            },
        )


class SetChatMutedTest(PushSchemaTestCase):
    MUTE = """
    mutation($chatId: ID!, $muted: Boolean!) {
        setChatMuted(chatId: $chatId, muted: $muted) { chat { muted } } }
    """

    def setUp(self):
        super().setUp()
        FeatureFlag.objects.create(name="chat", enabled=True)
        self.chat = Chat.objects.create(
            name="Bar", closes_at=timezone.now() + datetime.timedelta(hours=5)
        )
        ChatMembership.objects.create(chat=self.chat, user=self.anna)
        self.chat_id = to_global_id("ChatNode", self.chat.pk)

    def test_mutes_for_the_member_only(self):
        result = self.run_query(self.anna, self.MUTE, chatId=self.chat_id, muted=True)
        inbox = self.run_query(self.anna, "query { myChats { muted } }")

        self.assertNotIn("errors", result)
        self.assertTrue(result["data"]["setChatMuted"]["chat"]["muted"])
        self.assertEqual(inbox["data"]["myChats"], [{"muted": True}])

    def test_a_non_member_cannot_mute(self):
        result = self.run_query(self.per, self.MUTE, chatId=self.chat_id, muted=True)

        self.assertIn("errors", result)
