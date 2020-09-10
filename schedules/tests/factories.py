import random
from datetime import timedelta, datetime, date

import pytz
from django.utils import timezone
from factory import Faker, SubFactory, RelatedFactory, LazyAttribute, SelfAttribute
from factory.django import DjangoModelFactory


from ksg_nett import settings
from schedules.models import Schedule, ShiftSlotGroup, ScheduleSlotType, ShiftSlot, Shift, ScheduleTemplate, \
    ShiftSlotGroupTemplate, ShiftSlotDayRule, ShiftSlotTemplate, ShiftTrade, ShiftTradeOffer, ShiftSlotGroupInterest


class ScheduleFactory(DjangoModelFactory):
    class Meta:
        model = Schedule

    name = Faker('sentence')


class ShiftSlotGroupFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotGroup

    name = Faker('sentence')
    schedule = SubFactory(ScheduleFactory)
    meet_time = Faker('future_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))
    start_time = LazyAttribute(lambda obj: obj.meet_time + timedelta(hours=1))


class ScheduleSlotTypeFactory(DjangoModelFactory):
    class Meta:
        model = ScheduleSlotType

    name = Faker('sentence')
    schedule = SubFactory(ScheduleFactory)
    role = Faker('job')
    standard_groups = RelatedFactory('organization.tests.factories.InternalGroupFactory')


class ShiftSlotFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlot

    start = timezone.now()
    end = LazyAttribute(lambda obj: obj.start + timedelta(hours=5))
    type = SubFactory(ScheduleSlotTypeFactory)
    group = SubFactory(ShiftSlotGroupFactory)


class ShiftFactory(DjangoModelFactory):
    class Meta:
        model = Shift

    user = SubFactory('users.tests.factories.UserFactory')
    slot = SubFactory(ShiftSlotFactory)


class ScheduleTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ScheduleTemplate

    name = Faker('sentence')
    schedule = SubFactory(ScheduleFactory)


class ShiftSlotGroupTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotGroupTemplate

    name = Faker('sentence')
    schedule_template = SubFactory(ScheduleTemplateFactory)
    meet_time = timezone.now().time()
    start_time = LazyAttribute(lambda obj: datetime.combine(date.today(), obj.meet_time) + timedelta(hours=1))


class ShiftSlotDayRuleFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotDayRule

    rule = random.choice(ShiftSlotDayRule.STATUS.mo)
    shift_slot_template = SubFactory(ShiftSlotGroupTemplateFactory)


class ShiftSlotTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotTemplate

    start = timezone.now().time()
    end = LazyAttribute(lambda obj: datetime.combine(date.today(), obj.start) + timedelta(hours=5))
    type = SubFactory(ScheduleSlotTypeFactory)
    group = SubFactory(ShiftSlotGroupTemplateFactory)


class ShiftTradeFactory(DjangoModelFactory):
    class Meta:
        model = ShiftTrade

    offeror = SubFactory('users.tests.factories.UserFactory')
    shift_offer = SubFactory(ShiftFactory, user=SelfAttribute('..offeror'))
    taker = SubFactory('users.tests.factories.UserFactory')
    # shift_taker = SubFactory(ShiftFactory, user=SelfAttribute('..taker')) TODO: This fails when enabled
    signed_off_by = SubFactory('users.tests.factories.UserFactory')


class ShiftTradeOfferFactory(DjangoModelFactory):
    class Meta:
        model = ShiftTradeOffer

    shift_trade = SubFactory(ShiftTradeFactory, offeror=SelfAttribute('..offeror'),
                             shift_offer=SelfAttribute('..shift_offer'))
    offeror = SubFactory('users.tests.factories.UserFactory')
    shift_offer = SubFactory(ShiftFactory, user=SelfAttribute('..offeror'))
    accepted = True


class ShiftSlotGroupInterestFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotGroupInterest

    shift_group = SubFactory(ShiftSlotGroupFactory)
    user = SubFactory('users.tests.factories.UserFactory')
