import pytz
from django.utils import timezone
from django.conf import settings


def group_shifts_by_day(shifts):
    """
    Groups shifts by day.
    """
    from schedules.schemas.schedules import (
        ShiftDayGroup,
        ShiftDayWeek,
    )

    if not shifts:
        return []
    # Get first date of shift

    print(shifts)
    first_date = shifts.first().datetime_start
    last_date = shifts.last().datetime_start
    # get monday from first date
    monday = first_date - timezone.timedelta(days=first_date.weekday())
    monday = timezone.datetime(
        year=monday.year,
        month=monday.month,
        day=monday.day,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
        hour=0,
        minute=0,
        second=0,
    )
    sunday = monday + timezone.timedelta(days=6)
    sunday = timezone.datetime(
        year=sunday.year,
        month=sunday.month,
        day=sunday.day,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
        hour=23,
        minute=59,
        second=59,
    )
    cursor = monday
    week_groupings = []
    while cursor <= last_date:
        week_shifts = shifts.filter(
            datetime_start__gte=monday, datetime_start__lte=sunday
        )
        day_grouping = []
        day_cursor = monday
        while day_cursor <= sunday:
            datetime_day_midnight = timezone.datetime(
                day_cursor.year,
                day_cursor.month,
                day_cursor.day,
                23,
                59,
                59,
                tzinfo=pytz.timezone(settings.TIME_ZONE),
            )
            day_shifts = week_shifts.filter(
                datetime_start__gte=day_cursor,
                datetime_start__lte=datetime_day_midnight,
            )
            if day_shifts:
                day_grouping.append(ShiftDayGroup(shifts=day_shifts, date=day_cursor))
            day_cursor += timezone.timedelta(days=1)
        week_groupings.append(ShiftDayWeek(shift_days=day_grouping, date=monday))

        monday += timezone.timedelta(days=7)
        sunday += timezone.timedelta(days=7)
        cursor += timezone.timedelta(days=7)

    return week_groupings


def group_shifts_by_location(shifts):
    """
    Groups shifts by location.
    """
    from schedules.schemas.schedules import (
        ShiftLocationDayGroup,
        ShiftLocationDay,
        ShiftLocationWeek,
    )

    if not shifts:
        return []

    # Get first date of shift
    first_date = shifts.first().datetime_start
    last_date = shifts.last().datetime_start

    # get monday from first date
    monday = first_date - timezone.timedelta(days=first_date.weekday())
    monday = timezone.datetime(
        year=monday.year,
        month=monday.month,
        day=monday.day,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
        hour=0,
        minute=0,
        second=0,
    )
    sunday = monday + timezone.timedelta(days=6)
    sunday = timezone.datetime(
        year=sunday.year,
        month=sunday.month,
        day=sunday.day,
        hour=23,
        minute=59,
        second=59,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
    )
    # Reset to midnight of first day
    day_cursor = first_date - timezone.timedelta(
        hours=first_date.hour, minutes=first_date.minute, seconds=first_date.second
    )
    # Group shifts by week
    shifts_week = []
    week_cursor = monday
    while week_cursor < last_date:
        week_shifts = shifts.filter(
            datetime_start__gte=week_cursor, datetime_start__lte=sunday
        )
        shifts_week.append(week_shifts)
        week_cursor += timezone.timedelta(days=7)
        sunday += timezone.timedelta(days=7)

    print(last_date)
    shift_location_weeks = []
    for shift_week in shifts_week:
        # Get shifts for current day
        shift_days = []
        week_last_shift = shift_week.last().datetime_start

        while day_cursor < week_last_shift:
            day_shifts = shift_week.filter(
                datetime_start__gte=day_cursor,
                datetime_start__lte=day_cursor + timezone.timedelta(days=1),
            )
            if not day_shifts:
                day_cursor += timezone.timedelta(days=1)
                continue

            # Get locations for current day
            locations = day_shifts.values_list("location", flat=True).distinct()
            # Get shifts for each location
            print(locations)
            location_shifts = []
            for location in locations:
                location_shifts.append(
                    ShiftLocationDayGroup(
                        shifts=day_shifts.filter(location=location), location=location
                    )
                )
            shift_days.append(
                ShiftLocationDay(locations=location_shifts, date=day_cursor.date())
            )
            day_cursor += timezone.timedelta(days=1)

        shift_location_weeks.append(
            ShiftLocationWeek(shift_days=shift_days, date=monday)
        )
        monday += timezone.timedelta(days=7)
        sunday += timezone.timedelta(days=7)

    return shift_location_weeks


def normalize_shifts(shifts, display_mode):
    from schedules.models import Schedule

    if display_mode == Schedule.DisplayModeOptions.SINGLE_LOCATION:
        return group_shifts_by_day(shifts)
    elif display_mode == Schedule.DisplayModeOptions.MULTIPLE_LOCATIONS:
        return group_shifts_by_location(shifts)
