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
    ShiftSlotTemplateFactory, ShiftFactory, ShiftSlotFactory, ShiftInterestFactory, ScheduleRosterFactory,
)
from schedules.models import ShiftTemplate, ShiftSlot, RoleOption
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
            shift_template=self.early_shift, role=RoleOption.BARISTA, count=4
        )
        ShiftSlotTemplateFactory.create(
            shift_template=self.early_shift,
            role=RoleOption.KAFEANSVARLIG,
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
            shift_template=self.late_shift, role=RoleOption.BARISTA, count=5
        )
        ShiftSlotTemplateFactory.create(
            shift_template=self.late_shift,
            role=RoleOption.KAFEANSVARLIG,
            count=1,
        )

    def test__schedule_template__is_applied_correctly(self):
        apply_schedule_template(self.template, datetime.date.today(), 1)

        slots = ShiftSlot.objects.filter(shift__schedule=self.schedule)
        self.assertEqual(self.schedule.shifts.all().count(), 2)
        self.assertEqual(slots.count(), 11)


class TestShiftInterest(TestCase):
    def setUp(self):
        start = make_aware(datetime.datetime(2022, 5, 2, 15, 0), timezone=pytz.timezone("Europe/Oslo"))
        end = start + datetime.timedelta(hours=8)
        self.schedule = ScheduleFactory.create(name="Edgar", default_role=RoleOption.BARISTA)
        users = UserFactory.create_batch(5)
        roster = []
        for user in users:
            roster.append(
                ScheduleRosterFactory.create(user=user, schedule=self.schedule, autofill_as=self.schedule.default_role))

        shift = ShiftFactory(name="Edgar tidligvakt", schedule=self.schedule, datetime_start=start,
                             datetime_end=end)
        ShiftSlotFactory.create_batch(4, shift=shift, user=None, role=RoleOption.BARISTA)
        ShiftSlotFactory.create(shift=shift, user=None, role=RoleOption.KAFEANSVARLIG)

        shift2 = ShiftFactory(name="Edgar Senvakt", schedule=self.schedule,
                              datetime_start=start + datetime.timedelta(days=1),
                              datetime_end=end + datetime.timedelta(days=1, hours=8))

        ShiftSlotFactory.create_batch(4, shift=shift2, user=None, role=RoleOption.BARISTA)

        ShiftInterestFactory.create(shift=shift, user=users[0])
        ShiftInterestFactory.create(shift=shift, user=users[1])
        ShiftInterestFactory.create(shift=shift, user=users[2])
        ShiftInterestFactory.create(shift=shift2, user=users[3])
        ShiftInterestFactory.create(shift=shift, user=users[4])
        ShiftInterestFactory.create(shift=shift2, user=users[4])

    def test__hello_world(self):
        start = make_aware(datetime.datetime(2022, 5, 2, 14, 0), timezone=pytz.timezone("Europe/Oslo"))
        end = start + datetime.timedelta(days=3)
        self.schedule.autofill_slots(start, end)
