import datetime
from unittest import mock

from addict import Dict
from django.test import TestCase, override_settings
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from chat.models import Chat, ChatMembership, ChatMessage
from chat.tests.helpers import FRIDAY_19, make_shift
from chat.tests.test_mega_chats import mega_chat_creator
from common.models import FeatureFlag
from ksg_nett.schema import schema
from push.tests.helpers import VAPID_PRIVATE_KEY, make_subscription
from push.triggers import notify_chat_added, notify_chat_message
from users.tests.factories import UserFactory


@override_settings(APP_URL="app.ksg-nett.no")
class TriggerTestCase(TestCase):
    def setUp(self):
        FeatureFlag.objects.create(name="push_notifications", enabled=True)
        FeatureFlag.objects.create(name="chat", enabled=True)
        patcher = mock.patch("push.triggers.send_to_users")
        self.send_to_users = patcher.start()
        self.addCleanup(patcher.stop)

    def make_chat(self, members, name="Bar fredag"):
        chat = Chat.objects.create(
            name=name, closes_at=timezone.now() + datetime.timedelta(hours=5)
        )
        for member in members:
            ChatMembership.objects.create(chat=chat, user=member)
        return chat

    def recipients(self):
        self.assertEqual(self.send_to_users.call_count, 1)
        return set(self.send_to_users.call_args.args[0])


class NotifyChatMessageTest(TriggerTestCase):
    def setUp(self):
        super().setUp()
        self.sender, self.offline, self.other = UserFactory.create_batch(3)
        self.chat = self.make_chat([self.sender, self.offline, self.other])

    def say(self, body="Kan noen ta med kopper?"):
        message = ChatMessage.objects.create(
            chat=self.chat, sender=self.sender, body=body
        )
        notify_chat_message(message)
        return message

    def test_sends_to_offline_members_but_not_the_sender(self):
        self.say()

        self.assertEqual(self.recipients(), {self.offline.pk, self.other.pk})

    def test_skips_online_muted_and_opted_out_members(self):
        online, muted, opted_out = UserFactory.create_batch(3)
        ChatMembership.objects.create(
            chat=self.chat, user=online, last_seen_at=timezone.now()
        )
        ChatMembership.objects.create(chat=self.chat, user=muted, muted=True)
        opted_out.notify_on_chat_message = False
        opted_out.save()
        ChatMembership.objects.create(chat=self.chat, user=opted_out)

        self.say()

        self.assertEqual(self.recipients(), {self.offline.pk, self.other.pk})

    def test_the_added_setting_does_not_stop_message_pushes(self):
        self.offline.notify_on_chat_added = False
        self.offline.save()

        self.say()

        self.assertIn(self.offline.pk, self.recipients())

    def test_payload_links_to_the_chat_and_replaces_by_tag(self):
        self.say("x" * 200)

        payload = self.send_to_users.call_args.args[1]
        notification = payload["notification"]
        self.assertEqual(payload["web_push"], 8030)
        self.assertEqual(notification["title"], "Bar fredag")
        self.assertTrue(notification["body"].startswith(f"{self.sender.first_name}: "))
        self.assertEqual(len(notification["body"]), 140)
        self.assertEqual(
            notification["navigate"],
            f"https://app.ksg-nett.no/chat/{to_global_id('ChatNode', self.chat.pk)}",
        )
        self.assertEqual(notification["tag"], f"chat-{self.chat.pk}")
        self.assertEqual(
            self.send_to_users.call_args.kwargs,
            {"topic": f"chat-{self.chat.pk}", "urgency": "high"},
        )

    def test_flag_off_sends_nothing(self):
        FeatureFlag.objects.filter(name="push_notifications").update(enabled=False)

        self.say()

        self.send_to_users.assert_not_called()


class NotifyChatAddedTest(TriggerTestCase):
    def setUp(self):
        super().setUp()
        self.actor, self.added, self.opted_out = UserFactory.create_batch(3)
        self.opted_out.notify_on_chat_added = False
        self.opted_out.save()
        self.chat = self.make_chat([self.actor, self.added, self.opted_out])

    def test_skips_the_actor_and_opted_out_users(self):
        notify_chat_added(
            self.chat, [self.actor.pk, self.added.pk, self.opted_out.pk], self.actor
        )

        self.assertEqual(self.recipients(), {self.added.pk})
        body = self.send_to_users.call_args.args[1]["notification"]["body"]
        self.assertEqual(body, f"{self.actor.first_name} la deg til i chatten")

    def test_without_an_actor_the_text_has_no_name(self):
        notify_chat_added(self.chat, [self.added.pk])

        body = self.send_to_users.call_args.args[1]["notification"]["body"]
        self.assertEqual(body, "Du ble lagt til i chatten")

    def test_a_chat_mute_and_the_message_setting_do_not_apply(self):
        ChatMembership.objects.filter(user=self.added).update(muted=True)
        self.added.notify_on_chat_message = False
        self.added.save()

        notify_chat_added(self.chat, [self.added.pk], self.actor)

        self.assertEqual(self.recipients(), {self.added.pk})


class CallSiteTest(TriggerTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(schema)

    def run_query(self, user, query, **variables):
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.execute(
                query, variables=variables, context=Dict(user=user)
            )
        self.assertNotIn("errors", result)
        return result

    def test_join_shift_chat_pushes_only_when_it_creates_the_chat(self):
        now = timezone.now()
        shift, users = make_shift(
            start=now - datetime.timedelta(hours=1),
            end=now + datetime.timedelta(hours=5),
        )
        join = """
        mutation($shiftId: ID!) { joinShiftChat(shiftId: $shiftId) { created } }
        """
        shift_id = to_global_id("ShiftNode", shift.pk)

        self.run_query(users[0], join, shiftId=shift_id)
        self.run_query(users[1], join, shiftId=shift_id)

        self.assertEqual(self.recipients(), {users[1].pk, users[2].pk})

    def test_create_mega_chat_pushes_to_everyone_but_the_creator(self):
        _, users = make_shift()
        creator = mega_chat_creator()
        with mock.patch("chat.utils.megachat.timezone.now", return_value=FRIDAY_19):
            self.run_query(
                creator, 'mutation { createMegaChat(name: "Mega") { chat { id } } }'
            )

        self.assertEqual(self.recipients(), {user.pk for user in users})

    def test_add_chat_members_pushes_only_to_the_new_users(self):
        creator = mega_chat_creator()
        member, new = UserFactory.create_batch(2)
        chat = self.make_chat([creator, member])
        Chat.objects.filter(pk=chat.pk).update(members_editable=True)
        add = """
        mutation($chatId: ID!, $userIds: [ID!]!) {
            addChatMembers(chatId: $chatId, userIds: $userIds) { addedCount } }
        """
        self.run_query(
            creator,
            add,
            chatId=to_global_id("ChatNode", chat.pk),
            userIds=[to_global_id("UserNode", u.pk) for u in (member, new)],
        )

        self.assertEqual(self.recipients(), {new.pk})


@override_settings(VAPID_PRIVATE_KEY=VAPID_PRIVATE_KEY)
class SendChatMessageTest(TestCase):
    def test_returns_the_message_when_the_push_fails(self):
        FeatureFlag.objects.create(name="push_notifications", enabled=True)
        FeatureFlag.objects.create(name="chat", enabled=True)
        sender, other = UserFactory.create_batch(2)
        chat = Chat.objects.create(
            name="Bar", closes_at=timezone.now() + datetime.timedelta(hours=5)
        )
        for user in (sender, other):
            ChatMembership.objects.create(chat=chat, user=user)
        make_subscription(other)
        send = """
        mutation($chatId: ID!) {
            sendChatMessage(chatId: $chatId, body: "Hei") { message { body } } }
        """

        with mock.patch("push.webpush.send", side_effect=RuntimeError) as push:
            with self.captureOnCommitCallbacks(execute=True):
                result = Client(schema).execute(
                    send,
                    variables={"chatId": to_global_id("ChatNode", chat.pk)},
                    context=Dict(user=sender),
                )

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["sendChatMessage"]["message"]["body"], "Hei")
        push.assert_called_once()
