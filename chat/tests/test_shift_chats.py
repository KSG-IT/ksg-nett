import datetime

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from chat.models import Chat, ChatMembership
from chat.tests.helpers import FRIDAY_19, SATURDAY_02, make_shift
from chat.utils import fetch_chat_for_shift
from common.exceptions import IllegalOperation
from users.tests.factories import UserFactory


def member_ids(chat):
    return set(
        ChatMembership.objects.filter(chat=chat).values_list("user_id", flat=True)
    )


class FetchChatForShiftTest(TestCase):
    def test_first_call_creates_the_chat_with_everyone_on_the_shift(self):
        shift, users = make_shift(user_count=4)

        chat, created = fetch_chat_for_shift(users[0], shift, now=FRIDAY_19)

        self.assertTrue(created)
        self.assertEqual(chat.name, "Bar fredag gruppechat")
        self.assertEqual(member_ids(chat), {u.pk for u in users})
        self.assertEqual(chat.closes_at, SATURDAY_02 + datetime.timedelta(hours=2))

    def test_later_calls_return_the_same_chat(self):
        shift, users = make_shift()

        first, _ = fetch_chat_for_shift(users[0], shift, now=FRIDAY_19)
        second, created = fetch_chat_for_shift(users[1], shift, now=FRIDAY_19)

        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Chat.objects.count(), 1)

    def test_two_shifts_with_other_users_get_separate_chats(self):
        shift_a, users_a = make_shift(name="A")
        shift_b, users_b = make_shift(name="B")

        chat_a, _ = fetch_chat_for_shift(users_a[0], shift_a, now=FRIDAY_19)
        chat_b, _ = fetch_chat_for_shift(users_b[0], shift_b, now=FRIDAY_19)

        self.assertNotEqual(chat_a.pk, chat_b.pk)

    def test_a_user_who_is_not_on_the_shift_is_refused(self):
        shift, _ = make_shift()
        with self.assertRaises(PermissionDenied):
            fetch_chat_for_shift(UserFactory.create(), shift, now=FRIDAY_19)

    def test_a_shift_with_two_users_has_no_chat(self):
        shift, users = make_shift(user_count=2)
        with self.assertRaises(IllegalOperation):
            fetch_chat_for_shift(users[0], shift, now=FRIDAY_19)

    def test_join_window_is_one_hour_before_to_one_hour_after(self):
        shift, users = make_shift()
        start = shift.datetime_start
        end = shift.datetime_end
        hour = datetime.timedelta(hours=1)
        minute = datetime.timedelta(minutes=1)

        with self.assertRaises(IllegalOperation):
            fetch_chat_for_shift(users[0], shift, now=start - hour - minute)
        with self.assertRaises(IllegalOperation):
            fetch_chat_for_shift(users[0], shift, now=end + hour + minute)
        _, created = fetch_chat_for_shift(users[0], shift, now=start - hour)
        self.assertTrue(created)
        # Still found after midnight, when the chat is not from "today"
        _, created = fetch_chat_for_shift(users[1], shift, now=end + hour)
        self.assertFalse(created)
