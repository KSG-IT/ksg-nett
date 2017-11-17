
from django.test import TestCase
from django.utils import timezone

from schedules.models import Schedule, ShiftSlotGroup, ScheduleSlotType, ShiftSlot, Shift, ScheduleTemplate, \
    ShiftSlotGroupTemplate, ShiftSlotDayRule, ShiftSlotTemplate, ShiftTrade, ShiftTradeOffer, ShiftSlotGroupInterest
from users.models import User


class ScheduleModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(
            name='schedule'
        )
        cls.schedule.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule)
        repr(self.schedule)


class ShiftSlotGroupModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group)
        repr(self.shift_slot_group)


class ScheduleSlotTypeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule_slot_type)
        repr(self.schedule_slot_type)


class ShiftSlotModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()
        cls.shift_slot = ShiftSlot(
            start=timezone.now(),
            end=timezone.now(),
            type=cls.schedule_slot_type,
            group=cls.shift_slot_group,
        )
        cls.shift_slot.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot)
        repr(self.shift_slot)


class ShiftModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()
        cls.shift_slot = ShiftSlot(
            start=timezone.now(),
            end=timezone.now(),
            type=cls.schedule_slot_type,
            group=cls.shift_slot_group,
        )
        cls.shift_slot.save()
        cls.user = User(
            username='user',
            email='user@example.com',
        )
        cls.user.save()
        cls.shift = Shift(
            slot=cls.shift_slot,
            user=cls.user
        )

    def test_str_and_repr_should_not_crash(self):
        str(self.shift)
        repr(self.shift)


class ScheduleTemplateModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_template = ScheduleTemplate(
            name='schedule_template',
            schedule=cls.schedule
        )
        cls.schedule_template.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule_template)
        repr(self.schedule_template)


class ShiftSlotGroupTemplateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_template = ScheduleTemplate(
            name='schedule_template',
            schedule=cls.schedule
        )
        cls.schedule_template.save()
        cls.shift_slot_group_template = ShiftSlotGroupTemplate(
            name='shift slot group template' ,
            schedule_template=cls.schedule_template,
            meet_time=timezone.now(),
            start_time=timezone.now()
        )
        cls.shift_slot_group_template.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group_template)
        repr(self.shift_slot_group_template)


class ShiftSlotDayRuleModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_template = ScheduleTemplate(
            name='schedule_template',
            schedule=cls.schedule
        )
        cls.schedule_template.save()
        cls.shift_slot_group_template = ShiftSlotGroupTemplate(
            name='shift slot group template' ,
            schedule_template=cls.schedule_template,
            meet_time=timezone.now(),
            start_time=timezone.now()
        )
        cls.shift_slot_group_template.save()
        cls.shift_slot_day_rule = ShiftSlotDayRule(
            rule='mo',
            shift_slot_template=cls.shift_slot_group_template
        )
        cls.shift_slot_day_rule.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group_template)
        repr(self.shift_slot_group_template)


class ShiftSlotTemplateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_template = ScheduleTemplate(
            name='schedule_template',
            schedule=cls.schedule
        )
        cls.schedule_template.save()
        cls.shift_slot_group_template = ShiftSlotGroupTemplate(
            name='shift slot group template' ,
            schedule_template=cls.schedule_template,
            meet_time=timezone.now(),
            start_time=timezone.now()
        )
        cls.shift_slot_group_template.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()
        cls.shift_slot_template = ShiftSlotTemplate(
            start=timezone.now(),
            end=timezone.now(),
            type=cls.schedule_slot_type,
            group=cls.shift_slot_group_template
        )
        cls.shift_slot_template.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_template)
        repr(self.shift_slot_template)


class ShiftTradeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()
        cls.shift_slot = ShiftSlot(
            start=timezone.now(),
            end=timezone.now(),
            type=cls.schedule_slot_type,
            group=cls.shift_slot_group,
        )
        cls.shift_slot.save()
        cls.user = User(
            username='user',
            email='user@example.com',
        )
        cls.user.save()
        cls.shift = Shift(
            slot=cls.shift_slot,
            user=cls.user
        )
        cls.shift.save()
        cls.shift_trade = ShiftTrade(
            offeror=cls.user,
            shift_offer=cls.shift
        )
        cls.shift_trade.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_trade)
        repr(self.shift_trade)


class ShiftTradeOfferModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.schedule_slot_type = ScheduleSlotType(
            name='schedule slot type',
            schedule=cls.schedule,
            role='Some role'
        )
        cls.schedule_slot_type.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()
        cls.shift_slot = ShiftSlot(
            start=timezone.now(),
            end=timezone.now(),
            type=cls.schedule_slot_type,
            group=cls.shift_slot_group,
        )
        cls.shift_slot.save()
        cls.user = User(
            username='user',
            email='user@example.com',
        )
        cls.user.save()
        cls.shift = Shift(
            slot=cls.shift_slot,
            user=cls.user
        )
        cls.shift.save()
        cls.shift_trade = ShiftTrade(
            offeror=cls.user,
            shift_offer=cls.shift
        )
        cls.shift_trade.save()
        cls.shift_trade_offer = ShiftTradeOffer(
            shift_trade=cls.shift_trade,
            offeror=cls.user,
            shift_offer=cls.shift
        )
        cls.shift_trade_offer.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift)
        repr(self.shift)


class ShiftSlotGroupInterestModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.schedule = Schedule(name='schedule')
        cls.schedule.save()
        cls.shift_slot_group = ShiftSlotGroup(
            name='shift slot group',
            schedule=cls.schedule,
            meet_time=timezone.now(),
            start_time=timezone.now(),
        )
        cls.shift_slot_group.save()
        cls.user = User(
            username='user',
            email='user@example.com',
        )
        cls.user.save()
        cls.shift_slot_group_interest = ShiftSlotGroupInterest(
            shift_group=cls.shift_slot_group,
            user=cls.user
        )

        cls.shift_slot_group_interest.save()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group_interest)
        repr(self.shift_slot_group_interest)
