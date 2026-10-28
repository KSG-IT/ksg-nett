import datetime
from unittest import mock

from addict import Dict
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from chat.tests.test_mega_chats import user_with
from ksg_nett.schema import schema
from schedules.models import RoleOption, ShiftSlotDraft
from schedules.notifications import notify_given_shift, notify_new_shifts
from schedules.tests.factories import ScheduleFactory, ShiftFactory, ShiftSlotFactory
from schedules.utils.drafts import lock_drafts
from users.tests.factories import UserFactory


class ShiftNotificationTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create(push_on_shift=True, notify_on_shift=True)
        self.schedule = ScheduleFactory.create()
        self.send_to_users = self.patch("schedules.notifications.send_to_users")
        self.send_given = self.patch("schedules.notifications.send_given_shift_email")
        self.send_new = self.patch("schedules.notifications.send_new_shifts_email")

    def patch(self, target):
        patcher = mock.patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def slot(self, name, hour, user=None):
        start = timezone.make_aware(datetime.datetime(2026, 10, 31, hour))
        shift = ShiftFactory.create(
            name=name,
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=4),
        )
        return ShiftSlotFactory.create(shift=shift, user=user, role=RoleOption.BARISTA)

    def message(self):
        self.assertEqual(self.send_to_users.call_count, 1)
        user_ids, message = self.send_to_users.call_args.args
        self.assertEqual(user_ids, [self.user.pk])
        return message

    def test_one_shift_names_it(self):
        notify_given_shift(self.slot("Bar", 19, self.user))

        self.send_given.assert_called_once()
        message = self.message()
        self.assertEqual(message.title, "Du er satt opp på vakt")
        self.assertEqual(message.body, "31.10 kl 19:00–23:00: Bar, Edgar")
        self.assertEqual(message.path, "/schedules/me")

    def test_several_shifts_give_one_push_sorted_by_start(self):
        slots = [self.slot("Natt", 22, self.user), self.slot("Kveld", 17, self.user)]

        notify_new_shifts({self.user: slots})

        self.send_new.assert_called_once_with(self.user, slots)
        message = self.message()
        self.assertEqual(message.title, "Du har fått 2 nye vakter")
        self.assertEqual(
            message.body.splitlines(),
            ["31.10 kl 17:00–21:00: Kveld, Edgar", "31.10 kl 22:00–02:00: Natt, Edgar"],
        )

    def test_each_setting_decides_its_own_channel(self):
        self.user.push_on_shift = False
        self.user.save()
        notify_given_shift(self.slot("Bar", 19, self.user))
        self.send_given.assert_called_once()
        self.send_to_users.assert_not_called()

        self.user.push_on_shift, self.user.notify_on_shift = True, False
        self.user.save()
        notify_given_shift(self.slot("Bar", 19, self.user))
        self.send_given.assert_called_once()
        self.send_to_users.assert_called_once()

    def test_add_user_to_shift_slot_notifies(self):
        slot = self.slot("Bar", 19)
        add = """
        mutation($slot: ID!, $userId: ID!) {
            addUserToShiftSlot(shiftSlotId: $slot, userId: $userId) { shiftSlot { id } } }
        """
        with self.captureOnCommitCallbacks(execute=True):
            result = Client(schema).execute(
                add,
                variables={
                    "slot": to_global_id("ShiftSlotNode", slot.pk),
                    "userId": to_global_id("UserNode", self.user.pk),
                },
                context=Dict(user=user_with("schedules.change_shiftslot")),
            )

        self.assertNotIn("errors", result)
        self.send_given.assert_called_once()
        self.message()

    def test_lock_drafts_notifies_each_user_once(self):
        first, second = self.slot("Kveld", 17), self.slot("Natt", 22)
        removed = self.slot("Dag", 12, UserFactory.create())
        for slot, user in ((first, self.user), (second, self.user), (removed, None)):
            ShiftSlotDraft.objects.create(slot=slot, user=user)

        with self.captureOnCommitCallbacks(execute=True):
            lock_drafts(self.schedule)

        self.send_new.assert_called_once()
        self.assertEqual(self.message().title, "Du har fått 2 nye vakter")
