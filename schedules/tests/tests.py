import datetime

import pytz
from django.test import TestCase
from django.utils.timezone import make_aware

from schedules.utils.templates import (
    apply_schedule_template,
    shift_template_timestamps_to_datetime,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftTemplateFactory,
    ShiftSlotTemplateFactory, ShiftFactory, ShiftSlotFactory, ShiftInterestFactory,
)
from schedules.models import ShiftTemplate, ShiftSlot, Shift, Schedule
from users.tests.factories import UserFactory


class TestScheduleTemplateShiftTemplateTimestampsToDatetimeHelper(TestCase):
    def setUp(self) -> None:
        schedule = ScheduleFactory.create(name="Edgar")
        self.template = ScheduleTemplateFactory.create(
            schedule=schedule, name="Standarduke"
        )
        self.early_shift = ShiftTemplateFactory.create(
            name="Onsdag tidlig",
            schedule_template=self.template,
            day=ShiftTemplate.Day.WEDNESDAY,
            time_start=datetime.time(15, 0),
            time_end=datetime.time(21, 0),
        )
        self.late_shift = ShiftTemplateFactory.create(
            name="Onsdag sent",
            schedule_template=self.template,
            day=ShiftTemplate.Day.WEDNESDAY,
            time_start=datetime.time(20, 0),
            time_end=datetime.time(1, 0),
        )

    def test__start_and_end_times__are_corretly_applied(self):
        apply_schedule_template(self.template, datetime.date(2021, 1, 1), 1)
        early_start, early_end = shift_template_timestamps_to_datetime(
            datetime.date.today(), self.late_shift
        )
        late_start, late_end = shift_template_timestamps_to_datetime(
            datetime.date.today(), self.early_shift
        )
        self.assertLess(early_start, early_end)
        self.assertLess(late_start, late_end)


class TestApplyScheduleTemplateHelper(TestCase):
    def setUp(self) -> None:
        self.schedule = ScheduleFactory.create(name="Edgar")
        self.template = ScheduleTemplateFactory.create(
            schedule=self.schedule, name="Standarduke"
        )
        self.early_shift = ShiftTemplateFactory.create(
            name="Onsdag tidlig",
            schedule_template=self.template,
            day=ShiftTemplate.Day.WEDNESDAY,
            time_start=datetime.time(15, 0),
            time_end=datetime.time(21, 0),
        )

        ShiftSlotTemplateFactory.create(
            shift_template=self.early_shift, role=ShiftSlot.RoleOption.BARISTA, count=4
        )
        ShiftSlotTemplateFactory.create(
            shift_template=self.early_shift,
            role=ShiftSlot.RoleOption.KAFEANSVARLIG,
            count=1,
        )

        self.late_shift = ShiftTemplateFactory.create(
            name="Onsdag sent",
            schedule_template=self.template,
            day=ShiftTemplate.Day.WEDNESDAY,
            time_start=datetime.time(20, 0),
            time_end=datetime.time(1, 0),
        )

        ShiftSlotTemplateFactory.create(
            shift_template=self.late_shift, role=ShiftSlot.RoleOption.BARISTA, count=5
        )
        ShiftSlotTemplateFactory.create(
            shift_template=self.late_shift,
            role=ShiftSlot.RoleOption.KAFEANSVARLIG,
            count=1,
        )

    def test__schedule_template__is_applied_correctly(self):
        apply_schedule_template(self.template, datetime.date.today(), 1)

        slots = ShiftSlot.objects.filter(shift__schedule=self.schedule)
        self.assertEqual(self.schedule.shifts.all().count(), 2)
        self.assertEqual(slots.count(), 11)


class TestShiftInterest(TestCase):
    def setUp(self):
        self.start = make_aware(datetime.datetime(2022, 5, 2, 15, 0), timezone=pytz.timezone("Europe/Oslo"))
        self.end = self.start + datetime.timedelta(hours=8)
        self.schedule = ScheduleFactory.create(name="Edgar")

        shift = ShiftFactory(name="Edgar tidligvakt", schedule=self.schedule, datetime_start=self.start,
                             datetime_end=self.end)
        ShiftSlotFactory.create_batch(4, shift=shift, user=None, role=ShiftSlot.RoleOption.BARISTA)

        shift2 = ShiftFactory(name="Edgar tidligvakt", schedule=self.schedule,
                              datetime_start=self.start + datetime.timedelta(days=1),
                              datetime_end=self.end + datetime.timedelta(days=1, hours=8))
        ShiftSlotFactory.create_batch(4, shift=shift2, user=None, role=ShiftSlot.RoleOption.BARISTA)

        interested_user = UserFactory()
        ShiftInterestFactory.create_batch(2, shift=shift)
        ShiftInterestFactory.create(shift=shift, user=interested_user)
        ShiftInterestFactory.create(shift=shift2, user=interested_user)
        ShiftInterestFactory.create_batch(3, shift=shift2)

    def test__hello_world(self):
        self.schedule.autofill_slots(self.start, self.end + datetime.timedelta(days=2))
