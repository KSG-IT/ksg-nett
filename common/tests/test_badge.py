import datetime

from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client

from chat.models import Chat, ChatMembership, ChatMessage
from common.models import FeatureFlag
from ksg_nett.schema import schema
from users.tests.factories import UserFactory

QUERY = "{ badgeCount }"


class BadgeCountTest(TestCase):
    def setUp(self):
        self.client = Client(schema)
        self.me, self.other = UserFactory.create_batch(2)
        self.flag = FeatureFlag.objects.create(name="chat", enabled=True)
        for name in ("Bar", "Kafe"):
            chat = Chat.objects.create(
                name=name, closes_at=timezone.now() + datetime.timedelta(hours=5)
            )
            for user in (self.me, self.other):
                ChatMembership.objects.create(chat=chat, user=user)
            ChatMessage.objects.create(chat=chat, sender=self.other, body="Hei")
            ChatMessage.objects.create(chat=chat, sender=self.me, body="Hallo")

    def badge_count(self, user):
        return self.client.execute(QUERY, context=Dict(user=user))

    def test_counts_unread_chat_messages_from_others(self):
        result = self.badge_count(self.me)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["badgeCount"], 2)

    def test_the_chat_flag_off_leaves_chats_out(self):
        self.flag.enabled = False
        self.flag.save()

        self.assertEqual(self.badge_count(self.me)["data"]["badgeCount"], 0)

    def test_anonymous_user_is_denied(self):
        self.assertIn("errors", self.badge_count(AnonymousUser()))
