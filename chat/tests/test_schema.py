import datetime

from addict import Dict
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from chat.models import Chat, ChatMembership, ChatMessage
from chat.tests.helpers import make_shift
from common.models import FeatureFlag
from ksg_nett.schema import schema
from users.tests.factories import UserFactory


class ChatSchemaTestCase(TestCase):
    def setUp(self):
        FeatureFlag.objects.create(name="chat", enabled=True)
        self.client = Client(schema)
        self.anna, self.per, self.outsider = UserFactory.create_batch(3)
        self.superuser = UserFactory.create(is_superuser=True)

    def run_query(self, user, query, **variables):
        return self.client.execute(query, variables=variables, context=Dict(user=user))

    def make_chat(self, name, members):
        chat = Chat.objects.create(
            name=name, closes_at=timezone.now() + datetime.timedelta(hours=5)
        )
        for member in members:
            ChatMembership.objects.create(chat=chat, user=member)
        return chat

    def say(self, chat, sender, body):
        message = ChatMessage.objects.create(chat=chat, sender=sender, body=body)
        Chat.objects.filter(pk=chat.pk).update(last_message_at=message.created_at)
        return message


MY_CHATS = """
query { myChats { name unreadCount lastMessage { body } } }
"""


class InboxTest(ChatSchemaTestCase):
    def test_sorts_by_newest_message_and_counts_unread_for_the_viewer(self):
        old = self.make_chat("Old", [self.anna, self.per])
        new = self.make_chat("New", [self.anna, self.per])
        self.make_chat("Elsewhere", [self.per])
        self.say(new, self.per, "first")
        self.say(old, self.per, "second")
        read = self.say(old, self.per, "third")
        self.say(old, self.anna, "my own message")
        self.say(new, self.per, "newest")
        ChatMembership.objects.filter(chat=old, user=self.anna).update(
            last_read_message=read
        )

        result = self.run_query(self.anna, MY_CHATS)

        self.assertNotIn("errors", result)
        chats = result["data"]["myChats"]
        self.assertEqual([c["name"] for c in chats], ["New", "Old"])
        # Own messages and messages up to the read marker do not count
        self.assertEqual([c["unreadCount"] for c in chats], [2, 0])
        self.assertEqual(chats[0]["lastMessage"]["body"], "newest")

    def test_flag_off_blocks_every_field(self):
        FeatureFlag.objects.filter(name="chat").update(enabled=False)
        result = self.run_query(self.anna, MY_CHATS)
        self.assertIn("errors", result)


class AccessTest(ChatSchemaTestCase):
    def setUp(self):
        super().setUp()
        self.chat = self.make_chat("Private", [self.anna, self.per])
        self.secret = self.say(self.chat, self.per, "secret")
        self.chat_id = to_global_id("ChatNode", self.chat.pk)

    MESSAGES = """
    query($chatId: ID!) { chatMessages(chatId: $chatId) { body } }
    """

    def test_a_non_member_cannot_read_the_messages(self):
        result = self.run_query(self.outsider, self.MESSAGES, chatId=self.chat_id)
        self.assertIn("errors", result)

    def test_a_superuser_reads_without_a_trace(self):
        result = self.run_query(self.superuser, self.MESSAGES, chatId=self.chat_id)
        self.assertEqual(result["data"]["chatMessages"], [{"body": "secret"}])

        query = """
        query($chatId: ID!) { chat(chatId: $chatId) {
            onlineCount members { online lastReadMessageId } } }
        """
        # A member is online and has a read marker
        ChatMembership.objects.filter(chat=self.chat, user=self.per).update(
            last_seen_at=timezone.now(), last_read_message=self.secret
        )
        seen = self.run_query(self.superuser, query, chatId=self.chat_id)
        seen = seen["data"]["chat"]

        self.assertEqual(seen["onlineCount"], 0)
        self.assertEqual(
            seen["members"],
            [{"online": False, "lastReadMessageId": None}] * 2,
        )
        self.assertFalse(
            ChatMembership.objects.filter(chat=self.chat, user=self.superuser).exists()
        )

    def test_all_chats_is_for_superusers_only(self):
        query = "query { allChats { name } }"
        self.assertIn("errors", self.run_query(self.anna, query))
        result = self.run_query(self.superuser, query)
        self.assertEqual(result["data"]["allChats"], [{"name": "Private"}])


class MessagesTest(ChatSchemaTestCase):
    def test_send_poll_and_mark_read(self):
        chat = self.make_chat("Talk", [self.anna, self.per])
        chat_id = to_global_id("ChatNode", chat.pk)
        send = """
        mutation($chatId: ID!, $body: String!) {
            sendChatMessage(chatId: $chatId, body: $body) { message { id body } } }
        """
        first = self.run_query(self.per, send, chatId=chat_id, body="one")
        second = self.run_query(self.per, send, chatId=chat_id, body="two")
        first_id = first["data"]["sendChatMessage"]["message"]["id"]
        second_id = second["data"]["sendChatMessage"]["message"]["id"]

        poll = """
        query($chatId: ID!, $afterId: ID) {
            chatMessages(chatId: $chatId, afterId: $afterId) { body } }
        """
        later = self.run_query(self.anna, poll, chatId=chat_id, afterId=first_id)
        self.assertEqual(later["data"]["chatMessages"], [{"body": "two"}])

        unread = "query { unreadChatCount }"
        result = self.run_query(self.anna, unread)
        self.assertEqual(result["data"]["unreadChatCount"], 2)
        mark = """
        mutation($chatId: ID!, $messageId: ID!) {
            markChatRead(chatId: $chatId, messageId: $messageId) { changed } }
        """
        self.run_query(self.anna, mark, chatId=chat_id, messageId=second_id)
        result = self.run_query(self.anna, unread)
        self.assertEqual(result["data"]["unreadChatCount"], 0)


class JoinShiftChatTest(ChatSchemaTestCase):
    def test_joinable_shift_then_join(self):
        now = timezone.now()
        shift, users = make_shift(
            start=now - datetime.timedelta(hours=1),
            end=now + datetime.timedelta(hours=5),
        )
        joinable = "query { joinableShiftChats { userCount chat { id } } }"
        result = self.run_query(users[0], joinable)
        self.assertEqual(
            result["data"]["joinableShiftChats"], [{"userCount": 3, "chat": None}]
        )

        join = """
        mutation($shiftId: ID!) {
            joinShiftChat(shiftId: $shiftId) { created chat { name } } }
        """
        shift_id = to_global_id("ShiftNode", shift.pk)
        first = self.run_query(users[0], join, shiftId=shift_id)
        second = self.run_query(users[1], join, shiftId=shift_id)

        self.assertTrue(first["data"]["joinShiftChat"]["created"])
        self.assertFalse(second["data"]["joinShiftChat"]["created"])
        self.assertEqual(Chat.objects.count(), 1)
        after = self.run_query(users[2], joinable)
        self.assertIsNotNone(after["data"]["joinableShiftChats"][0]["chat"])
