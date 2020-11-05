from django.test import TestCase

from schedules.tests.factories import ScheduleFactory, ShiftSlotGroupFactory, ScheduleSlotTypeFactory, \
    ShiftSlotFactory, ShiftFactory, ScheduleTemplateFactory, ShiftSlotGroupTemplateFactory, ShiftSlotDayRuleFactory, \
    ShiftSlotTemplateFactory, ShiftTradeFactory, ShiftTradeOfferFactory, ShiftSlotGroupInterestFactory


class ScheduleModelTest(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule)
        repr(self.schedule)


class ShiftSlotGroupModelTest(TestCase):
    def setUp(self):
        self.shift_slot_group = ShiftSlotGroupFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group)
        repr(self.shift_slot_group)


class ScheduleSlotTypeModelTest(TestCase):
    def setUp(self):
        self.schedule_slot_type = ScheduleSlotTypeFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule_slot_type)
        repr(self.schedule_slot_type)


class ShiftSlotModelTest(TestCase):

    def setUp(self):
        self.shift_slot = ShiftSlotFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot)
        repr(self.shift_slot)


class ShiftModelTest(TestCase):
    @classmethod
    def setUp(self):
        self.shift = ShiftFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift)
        repr(self.shift)


class ScheduleTemplateModelTest(TestCase):

    def setUp(self):
        self.schedule_template = ScheduleTemplateFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.schedule_template)
        repr(self.schedule_template)


class ShiftSlotGroupTemplateModelTest(TestCase):
    def setUp(self):
        self.shift_slot_group_template = ShiftSlotGroupTemplateFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group_template)
        repr(self.shift_slot_group_template)


class ShiftSlotDayRuleModelTest(TestCase):
    @classmethod
    def setUp(self):
        self.shift_slot_day_rule = ShiftSlotDayRuleFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_day_rule)
        repr(self.shift_slot_day_rule)


class ShiftSlotTemplateModelTest(TestCase):
    def setUp(self):
        self.shift_slot_template = ShiftSlotTemplateFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_template)
        repr(self.shift_slot_template)


class ShiftTradeModelTest(TestCase):
    def setUp(self):
        self.shift_trade = ShiftTradeFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_trade)
        repr(self.shift_trade)


class ShiftTradeOfferModelTest(TestCase):
    def setUp(self):
        self.shift_trade_offer = ShiftTradeOfferFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_trade_offer)
        repr(self.shift_trade_offer)


class ShiftSlotGroupInterestModelTest(TestCase):
    def setUp(self):
        self.shift_slot_group_interest = ShiftSlotGroupInterestFactory()

    def test_str_and_repr_should_not_crash(self):
        str(self.shift_slot_group_interest)
        repr(self.shift_slot_group_interest)
