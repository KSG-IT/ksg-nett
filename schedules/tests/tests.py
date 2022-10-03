import datetime
from django.test import TestCase
from schedules.utils.templates import (
    apply_schedule_template,
    shift_template_timestamps_to_datetime,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftTemplateFactory,
    ShiftSlotTemplateFactory,
)
from schedules.models import ShiftTemplate, ShiftSlot


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
