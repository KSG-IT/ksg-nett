import datetime
import pytz
from django.conf import settings
from django.utils import timezone
from schedules.models import ShiftTemplate, Shift, ShiftSlot, ScheduleTemplate


def apply_shift_template(shift_template: ShiftTemplate, monday_of_week: datetime.date):
    """
    Apply a shift template to the schedule
    """

    day_offset = get_shift_template_day_offset(shift_template.day)
    shift_date = monday_of_week + datetime.timedelta(days=day_offset)
    shift_date = timezone.datetime(
        year=shift_date.year,
        month=shift_date.month,
        day=shift_date.day,
        hour=0,
        minute=0,
        second=0,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
    )
    datetime_start, datetime_end = shift_template_timestamps_to_datetime(
        shift_date, shift_template
    )

    shift, created = Shift.objects.update_or_create(
        name=shift_template.name,
        schedule=shift_template.schedule_template.schedule,
        datetime_start=datetime_start,
        datetime_end=datetime_end,
        location=shift_template.location,
    )

    for slot_template in shift_template.shift_slot_templates.all():
        # For each template slot we have a slot count set for each specific role.
        # Typically 1 shift leader and 3-5 workers
        for slot in range(slot_template.count):
            ShiftSlot.objects.create(
                shift=shift,
                role=slot_template.role,
            )


def apply_schedule_template(
    template: ScheduleTemplate, apply_from: datetime.date, number_of_weeks=1
):
    """
    Runs through all the shift templates and applies them to the schedule
    """
    first_day_of_week = apply_from - datetime.timedelta(days=apply_from.weekday())
    shifts_created = 0
    for week in range(number_of_weeks):
        for shift_template in template.shift_templates.all():
            apply_shift_template(shift_template, first_day_of_week)
            shifts_created += 1
        first_day_of_week += datetime.timedelta(days=7)

    return shifts_created


def shift_template_timestamps_to_datetime(
    shift_date: datetime.date, shift_template: ShiftTemplate
):
    """
    A shift template has only a timestamp and a given day of the week. If the time for the
    end of the shift is smaller than the time for the start of the shift, the shift happens
    over midnight
    """

    time_start = shift_template.time_start
    time_end = shift_template.time_end

    datetime_start = datetime.datetime.combine(shift_date, time_start)
    datetime_start = timezone.make_aware(
        datetime_start, timezone=pytz.timezone(settings.TIME_ZONE)
    )

    if time_end < time_start:
        # Shift happens over midnight. We combine the next day with this time
        shift_date = shift_date + datetime.timedelta(days=1)

    datetime_end = datetime.datetime.combine(shift_date, time_end)
    datetime_end = timezone.make_aware(
        datetime_end, timezone=pytz.timezone(settings.TIME_ZONE)
    )

    return datetime_start, datetime_end


def get_shift_template_day_offset(day: ShiftTemplate.Day):
    """
    Convert a day of the week to an offset within a week
    """
    if day == ShiftTemplate.Day.MONDAY:
        return 0
    elif day == ShiftTemplate.Day.TUESDAY:
        return 1
    elif day == ShiftTemplate.Day.WEDNESDAY:
        return 2
    elif day == ShiftTemplate.Day.THURSDAY:
        return 3
    elif day == ShiftTemplate.Day.FRIDAY:
        return 4
    elif day == ShiftTemplate.Day.SATURDAY:
        return 5
    elif day == ShiftTemplate.Day.SUNDAY:
        return 6
    else:
        raise ValueError("Invalid day of the week")
