import datetime
from zoneinfo import ZoneInfo
from django.conf import settings
from django.utils import timezone

from dataclasses import dataclass

from schedules.models import (
    ShiftInterest,
    ShiftTemplate,
    Shift,
    ShiftSlot,
    ShiftSlotDraft,
    ScheduleTemplate,
)


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
        tzinfo=ZoneInfo(settings.TIME_ZONE),
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
        generated_from=shift_template.schedule_template,
    )

    for slot_template in shift_template.shift_slot_templates.all():
        # For each template slot we have a slot count set for each specific role.
        # Typically, 1 shift leader and 3-5 workers
        for slot in range(slot_template.count):
            ShiftSlot.objects.create(
                shift=shift,
                role=slot_template.role,
            )


def apply_schedule_template(
    template: ScheduleTemplate,
    apply_from: datetime.date,
    number_of_weeks=1,
    overwrite=True,
):
    """
    Runs through all the shift templates and applies them to the schedule, for
    whole weeks from the Monday of apply_from. With overwrite, the template's
    shifts in those weeks are deleted first, with their slots, answers and
    drafts. Check replace_impact before.
    """

    if number_of_weeks < 1:
        raise ValueError("Number of weeks must be 1 or more")

    if number_of_weeks > 20:
        raise ValueError("Number of weeks must be 20 or less")

    first_day_of_week = apply_from - datetime.timedelta(days=apply_from.weekday())
    shifts_created = 0

    if overwrite:
        # Only the weeks we generate. A later week keeps its shifts.
        replaced_shifts(template, apply_from, number_of_weeks).delete()

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

    datetime_start = timezone.make_aware(
        timezone.datetime(
            year=shift_date.year,
            month=shift_date.month,
            day=shift_date.day,
            hour=time_start.hour,
            minute=time_start.minute,
            second=0,
        ),
        timezone=ZoneInfo("Europe/Belgrade"),
    )
    if time_end < time_start:
        # Shift happens over midnight. We combine the next day with this time
        shift_date = shift_date + datetime.timedelta(days=1)

    datetime_end = timezone.datetime(
        year=shift_date.year,
        month=shift_date.month,
        day=shift_date.day,
        hour=time_end.hour,
        minute=time_end.minute,
        second=0,
    )
    """
    # Need to revisit this. Not sure if we should just ignore this completely
    # https://stackoverflow.com/questions/21465528/resolving-ambiguoustimeerror-from-djangos-make-aware
    # https://docs.djangoproject.com/en/4.1/ref/utils/#django.utils.timezone.make_aware
    # https://code.djangoproject.com/ticket/27921
    This happens when trying to make a datetime tz aware during a daylight savings transition. Could probably be fixed
    by using correct timezone timestamps to begin with instead of casting everything using make_aware
    
    Context:
    Trigger the Generate mutation with a schedule template id, a date to start shift generation
    from and number of weeks to generate. We then call on the 'apply_schedule_template' function
    which calls on the 'apply_shift_template' function for each shift template in the schedule template. 
    The 'apply_shift_template' function then again calls on this function in order to get the datetimestamps
    from the shift template because they are given in local time and are not timestamps. They need to be
    stitched together. 
    
    timezone make_aware makes an error in the following scenario
    
    input: 
        - Shift generation from before Oktober 30th 2022 and goes a week after 30th
        - Only a problem with Bargjengen schedule template
        
    '''
    FRIDAY
        20:00:00
        02:00:00
    FRIDAY
        20:00:00
        02:00:00
    SATURDAY
        17:00:00
        22:00:00
    SATURDAY
        20:00:00
        02:00:00
    SATURDAY
        20:00:00
        02:00:00
    SATURDAY
        20:00:00
        02:00:00
    FRIDAY
        20:00:00
        02:00:00
    FRIDAY
        20:00:00
        02:00:00
    '''
    
    This day is daylight savings where the mutation just returns null with an error returning
    the timestamp 2022 30th october 2022 02:00:00 
    Daylight savings is night to 30th -> 29th is a saturday meaning the shift in bargjengen goes over midnight
    pytz raised AmbiguousTimeError(dt) for this time:
        graphql.error.located_error.GraphQLLocatedError: 2022-10-30 02:00:00
    """
    # When daylight saving time ends, 02:00-03:00 happens two times. fold=1
    # picks the second time (standard time), the same as is_dst=False did with
    # pytz. fold has no effect on other times.
    datetime_end = timezone.make_aware(
        datetime_end.replace(fold=1), timezone=ZoneInfo(settings.TIME_ZONE)
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


def generation_days(apply_from: datetime.date, number_of_weeks: int):
    """The first and the last day a generation covers: whole weeks from Monday."""
    first_day = apply_from - datetime.timedelta(days=apply_from.weekday())
    last_day = first_day + datetime.timedelta(days=7 * number_of_weeks - 1)
    return first_day, last_day


def replaced_shifts(template, apply_from, number_of_weeks):
    """The shifts of the template that a generation deletes and makes again."""
    first_day, last_day = generation_days(apply_from, number_of_weeks)
    local = ZoneInfo(settings.TIME_ZONE)
    start = datetime.datetime.combine(first_day, datetime.time.min, tzinfo=local)
    end = datetime.datetime.combine(
        last_day + datetime.timedelta(days=1), datetime.time.min, tzinfo=local
    )
    return Shift.objects.filter(
        generated_from=template, datetime_start__gte=start, datetime_start__lt=end
    )


@dataclass
class ReplaceImpact:
    first_day: datetime.date
    last_day: datetime.date
    shifts_to_create: int
    shifts_to_delete: int
    filled_slots_to_delete: int
    answers_to_delete: int
    drafts_to_delete: int

    @property
    def needs_confirmation(self):
        # Empty shifts without answers or drafts can be made again silently
        return bool(
            self.filled_slots_to_delete
            or self.answers_to_delete
            or self.drafts_to_delete
        )


def replace_impact(template, apply_from, number_of_weeks):
    shifts = replaced_shifts(template, apply_from, number_of_weeks)
    first_day, last_day = generation_days(apply_from, number_of_weeks)
    return ReplaceImpact(
        first_day=first_day,
        last_day=last_day,
        shifts_to_create=template.shift_templates.count() * number_of_weeks,
        shifts_to_delete=shifts.count(),
        filled_slots_to_delete=ShiftSlot.objects.filter(
            shift__in=shifts, user__isnull=False
        ).count(),
        answers_to_delete=ShiftInterest.objects.filter(shift__in=shifts).count(),
        drafts_to_delete=ShiftSlotDraft.objects.filter(slot__shift__in=shifts).count(),
    )
