import datetime
from types import SimpleNamespace

from django.test import TestCase

from schedules.utils.templates import shift_template_timestamps_to_datetime

ONE_HOUR = datetime.timedelta(hours=1)
TWO_HOURS = datetime.timedelta(hours=2)


def template(start: str, end: str):
    return SimpleNamespace(
        time_start=datetime.time.fromisoformat(start),
        time_end=datetime.time.fromisoformat(end),
    )


class TestShiftTemplateTimestampsToDatetime(TestCase):
    def test__winter_shift__uses_standard_time_offset(self):
        start, end = shift_template_timestamps_to_datetime(
            datetime.date(2026, 1, 15), template("15:00", "23:00")
        )
        self.assertEqual(start.utcoffset(), ONE_HOUR)
        self.assertEqual((start.hour, start.minute), (15, 0))
        self.assertEqual(end - start, datetime.timedelta(hours=8))

    def test__summer_shift__uses_daylight_saving_offset(self):
        start, end = shift_template_timestamps_to_datetime(
            datetime.date(2026, 7, 15), template("15:00", "23:00")
        )
        self.assertEqual(start.utcoffset(), TWO_HOURS)
        self.assertEqual(end.utcoffset(), TWO_HOURS)

    def test__shift_over_midnight__ends_next_day(self):
        start, end = shift_template_timestamps_to_datetime(
            datetime.date(2026, 1, 16), template("20:00", "02:00")
        )
        self.assertEqual(end.date(), datetime.date(2026, 1, 17))
        self.assertEqual(end - start, datetime.timedelta(hours=6))

    def test__shift_ends_when_daylight_saving_ends__uses_standard_time(self):
        # 2026-10-25 02:00-03:00 happens two times. The second time is used.
        start, end = shift_template_timestamps_to_datetime(
            datetime.date(2026, 10, 24), template("20:00", "02:00")
        )
        self.assertEqual(start.utcoffset(), TWO_HOURS)
        self.assertEqual(end.utcoffset(), ONE_HOUR)
        # Compare in UTC. Python ignores the offsets when both values have
        # the same tzinfo object.
        utc = datetime.timezone.utc
        self.assertEqual(
            end.astimezone(utc) - start.astimezone(utc), datetime.timedelta(hours=7)
        )
