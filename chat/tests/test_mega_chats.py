import datetime

from itertools import count

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from chat.models import Chat, ChatMembership
from chat.tests.helpers import FRIDAY_19, LOCAL, SATURDAY_02, make_shift
from schedules.models import RoleOption
from schedules.tests.factories import ShiftSlotFactory
from chat.utils import add_members, create_mega_chat, mega_chat_preview
from common.exceptions import IllegalOperation
from users.tests.factories import UserFactory, UserWithPermissionsFactory

EMAILS = count()
SUNDAY_19 = datetime.datetime(2026, 10, 18, 19, 0, tzinfo=LOCAL)
FRIDAY_17 = datetime.datetime(2026, 10, 16, 17, 30, tzinfo=LOCAL)


def user_with(*permissions):
    # The factory gives every user the same blank email, which is unique
    return UserWithPermissionsFactory.create(
        permissions=permissions, email=f"{next(EMAILS)}@example.com"
    )


def mega_chat_creator():
    return user_with("chat.create_mega_chat", "chat.add_to_mega_chat")


class CreateMegaChatTest(TestCase):
    def test_holds_everyone_on_duty_and_closes_after_the_last_shift(self):
        shift_a, users_a = make_shift(name="A")
        late_end = SATURDAY_02 + datetime.timedelta(hours=1)
        shift_b, users_b = make_shift(name="B", end=late_end)
        # A shift that is not running now
        make_shift(
            name="Later",
            start=datetime.datetime(2026, 10, 17, 18, 0, tzinfo=LOCAL),
            end=datetime.datetime(2026, 10, 18, 2, 0, tzinfo=LOCAL),
        )

        creator = mega_chat_creator()
        chat = create_mega_chat(creator, " Fredag megachat ", now=FRIDAY_19)

        self.assertEqual(chat.name, "Fredag megachat")
        self.assertTrue(chat.members_editable)
        self.assertEqual(
            set(
                ChatMembership.objects.filter(chat=chat).values_list(
                    "user_id", flat=True
                )
            ),
            {u.pk for u in users_a + users_b + [creator]},
        )
        self.assertEqual(chat.closes_at, late_end + datetime.timedelta(hours=2))

    def test_needs_the_permission(self):
        make_shift()
        with self.assertRaises(PermissionDenied):
            create_mega_chat(UserFactory.create(), "Chat", now=FRIDAY_19)

    def test_only_on_friday_and_saturday_from_18(self):
        make_shift(
            start=datetime.datetime(2026, 10, 18, 12, 0, tzinfo=LOCAL),
            end=datetime.datetime(2026, 10, 18, 23, 0, tzinfo=LOCAL),
        )
        make_shift(name="Early", start=FRIDAY_17 - datetime.timedelta(hours=3))
        for now in (FRIDAY_17, SUNDAY_19):
            with self.assertRaises(IllegalOperation):
                create_mega_chat(mega_chat_creator(), "Chat", now=now)

    def test_the_creator_is_a_member_also_when_not_on_duty(self):
        make_shift()
        creator = mega_chat_creator()

        chat = create_mega_chat(creator, "Chat", now=FRIDAY_19)

        self.assertTrue(ChatMembership.objects.filter(chat=chat, user=creator).exists())

    def test_refuses_when_nobody_is_on_duty(self):
        with self.assertRaises(IllegalOperation):
            create_mega_chat(mega_chat_creator(), "Chat", now=FRIDAY_19)


class MegaChatPreviewTest(TestCase):
    def test_lists_running_shifts_and_counts_each_user_once(self):
        late, late_users = make_shift(
            name="Late",
            start=datetime.datetime(2026, 10, 16, 18, 30, tzinfo=LOCAL),
            user_count=2,
        )
        early, early_users = make_shift(name="Early", user_count=3)
        # A user on both shifts
        ShiftSlotFactory.create(
            shift=late, user=early_users[0], role=RoleOption.BARTENDER
        )
        make_shift(
            name="Tomorrow",
            start=datetime.datetime(2026, 10, 17, 18, 0, tzinfo=LOCAL),
            end=datetime.datetime(2026, 10, 18, 2, 0, tzinfo=LOCAL),
        )

        preview = mega_chat_preview(mega_chat_creator(), now=FRIDAY_19)

        self.assertTrue(preview["open"])
        self.assertEqual(preview["user_count"], 5)
        self.assertEqual(preview["shifts"], [(early, 3), (late, 3)])

    def test_is_closed_outside_the_window(self):
        make_shift(name="Early", start=FRIDAY_17 - datetime.timedelta(hours=3))

        preview = mega_chat_preview(mega_chat_creator(), now=FRIDAY_17)

        self.assertFalse(preview["open"])
        self.assertEqual(preview["user_count"], 3)

    def test_needs_the_permission(self):
        with self.assertRaises(PermissionDenied):
            mega_chat_preview(UserFactory.create(), now=FRIDAY_19)


class AddMembersTest(TestCase):
    def setUp(self):
        make_shift()
        self.actor = mega_chat_creator()
        self.chat = create_mega_chat(self.actor, "Chat", now=FRIDAY_19)

    def test_adds_new_users_and_skips_existing_members(self):
        newcomer = UserFactory.create()

        added = add_members(
            self.actor,
            self.chat,
            [newcomer.pk, self.actor.pk, newcomer.pk],
            now=FRIDAY_19,
        )

        self.assertEqual(added, [newcomer.pk])

    def test_needs_the_permission_and_membership(self):
        plain = UserFactory.create()
        with self.assertRaises(PermissionDenied):
            add_members(plain, self.chat, [plain.pk], now=FRIDAY_19)
        outsider = user_with("chat.add_to_mega_chat")
        with self.assertRaises(PermissionDenied):
            add_members(outsider, self.chat, [outsider.pk], now=FRIDAY_19)

    def test_a_shift_chat_does_not_allow_it(self):
        chat = Chat.objects.create(name="Shift", closes_at=SATURDAY_02)
        ChatMembership.objects.create(chat=chat, user=self.actor)
        with self.assertRaises(IllegalOperation):
            add_members(self.actor, chat, [UserFactory.create().pk], now=FRIDAY_19)

    def test_a_closed_chat_does_not_allow_it(self):
        after = self.chat.closes_at + datetime.timedelta(minutes=1)
        with self.assertRaises(IllegalOperation):
            add_members(self.actor, self.chat, [UserFactory.create().pk], now=after)
