import datetime

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from chat.consts import MAX_MESSAGE_LENGTH
from chat.models import Chat, ChatMembership
from chat.tests.helpers import FRIDAY_19, SATURDAY_02, make_shift
from chat.utils import mark_read, ping, send_chat_message
from common.exceptions import IllegalOperation
from schedules.models import RoleOption
from users.tests.factories import UserFactory


class ChatTestCase(TestCase):
    def setUp(self):
        self.shift, self.users = make_shift()
        self.member, self.other = self.users[0], self.users[1]
        self.chat = Chat.objects.create(
            name="Chat", closes_at=SATURDAY_02 + datetime.timedelta(hours=2)
        )
        for user in (self.member, self.other):
            ChatMembership.objects.create(chat=self.chat, user=user)


class SendMessageTest(ChatTestCase):
    def test_saves_the_role_and_moves_the_chat_up_the_inbox(self):
        message = send_chat_message(self.member, self.chat, " Hei ", now=FRIDAY_19)

        self.assertEqual(message.body, "Hei")
        self.assertEqual(message.role, RoleOption.BARTENDER)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.last_message_at, message.created_at)

    def test_role_is_empty_when_the_sender_is_not_on_a_running_shift(self):
        after = SATURDAY_02 + datetime.timedelta(hours=1)
        message = send_chat_message(
            self.member, self.chat, "Takk for i kveld", now=after
        )
        self.assertIsNone(message.role)

    def test_a_non_member_cannot_send(self):
        with self.assertRaises(PermissionDenied):
            send_chat_message(UserFactory.create(), self.chat, "Hei", now=FRIDAY_19)

    def test_nobody_can_send_after_closes_at(self):
        after = self.chat.closes_at + datetime.timedelta(seconds=1)
        with self.assertRaises(IllegalOperation):
            send_chat_message(self.member, self.chat, "Hei", now=after)
        # The last second still works
        send_chat_message(self.member, self.chat, "Hei", now=self.chat.closes_at)

    def test_rejects_empty_and_too_long_messages(self):
        for body in ("   ", "x" * (MAX_MESSAGE_LENGTH + 1)):
            with self.assertRaises(IllegalOperation):
                send_chat_message(self.member, self.chat, body, now=FRIDAY_19)


class MarkReadTest(ChatTestCase):
    def test_the_marker_only_moves_forward(self):
        first = send_chat_message(self.member, self.chat, "1", now=FRIDAY_19)
        second = send_chat_message(self.member, self.chat, "2", now=FRIDAY_19)

        self.assertTrue(mark_read(self.other, self.chat, second.pk))
        self.assertFalse(mark_read(self.other, self.chat, first.pk))
        self.assertFalse(mark_read(self.other, self.chat, second.pk))

        membership = ChatMembership.objects.get(chat=self.chat, user=self.other)
        self.assertEqual(membership.last_read_message_id, second.pk)

    def test_refuses_a_message_from_another_chat(self):
        elsewhere = Chat.objects.create(name="Else", closes_at=SATURDAY_02)
        ChatMembership.objects.create(chat=elsewhere, user=self.member)
        message = send_chat_message(self.member, elsewhere, "Hei", now=FRIDAY_19)
        with self.assertRaises(IllegalOperation):
            mark_read(self.member, self.chat, message.pk)

    def test_a_non_member_cannot_mark_read(self):
        message = send_chat_message(self.member, self.chat, "Hei", now=FRIDAY_19)
        with self.assertRaises(PermissionDenied):
            mark_read(UserFactory.create(is_superuser=True), self.chat, message.pk)


class PingTest(ChatTestCase):
    def test_writes_at_most_every_15_seconds(self):
        self.assertTrue(ping(self.member, self.chat, now=FRIDAY_19))
        soon = FRIDAY_19 + datetime.timedelta(seconds=10)
        self.assertFalse(ping(self.member, self.chat, now=soon))
        later = FRIDAY_19 + datetime.timedelta(seconds=16)
        self.assertTrue(ping(self.member, self.chat, now=later))

    def test_a_superuser_who_is_not_a_member_is_never_seen(self):
        superuser = UserFactory.create(is_superuser=True)
        with self.assertRaises(PermissionDenied):
            ping(superuser, self.chat, now=FRIDAY_19)
        self.assertFalse(
            ChatMembership.objects.filter(chat=self.chat, user=superuser).exists()
        )
