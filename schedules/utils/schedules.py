import secrets

from django.utils import timezone

from common.util import send_email


def group_shifts_by_day(shifts):
    from schedules.schemas.schedules import (
        ShiftDayGroup,
        ShiftDayWeek,
    )

    if not shifts:
        return []

    first_date = shifts.first().datetime_start
    last_date = shifts.last().datetime_start

    cursor = first_date - timezone.timedelta(days=first_date.weekday())
    sunday = cursor + timezone.timedelta(days=6)

    cursor = cursor.replace(hour=0)
    sunday = sunday.replace(hour=23, minute=59, second=59)

    week_groupings = []
    while cursor <= last_date:
        week_shifts = shifts.filter(
            datetime_start__gte=cursor, datetime_start__lte=sunday
        )

        day_grouping = []
        day_cursor = cursor
        while day_cursor <= sunday:
            datetime_day_midnight = day_cursor.replace(
                hour=23,
                minute=59,
                second=59,
            )
            day_shifts = week_shifts.filter(
                datetime_start__gte=day_cursor,
                datetime_start__lte=datetime_day_midnight,
            )
            if day_shifts:
                day_grouping.append(ShiftDayGroup(shifts=day_shifts, date=day_cursor))

            day_cursor += timezone.timedelta(days=1)

        week_groupings.append(ShiftDayWeek(shift_days=day_grouping, date=cursor))
        sunday += timezone.timedelta(days=7)
        cursor += timezone.timedelta(days=7)

    return week_groupings


def group_shifts_by_location(shifts):
    from schedules.schemas.schedules import (
        ShiftLocationDayGroup,
        ShiftLocationDay,
        ShiftLocationWeek,
    )

    if not shifts:
        return []

    first_date = shifts.first().datetime_start
    last_date = shifts.last().datetime_start

    monday = first_date - timezone.timedelta(days=first_date.weekday())
    monday = monday.replace(
        hour=0,
        minute=0,
        second=0,
    )
    sunday = monday + timezone.timedelta(days=6)
    sunday = sunday.replace(
        hour=23,
        minute=59,
        second=59,
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

    shift_location_weeks = []
    for shift_week in shifts_week:
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

            # values_list returns querylist with duplicates
            # Get unique values by forcing qs to a list and then recasting
            # it to a set and back to a list
            location_names = list(
                set(list(day_shifts.values_list("location", flat=True)))
            )

            # Get shifts for each location
            location_shifts = []
            for location in location_names:
                shift_location_day_group = ShiftLocationDayGroup(
                    shifts=day_shifts.filter(location=location), location=location
                )
                location_shifts.append(shift_location_day_group)

            shift_location_day = ShiftLocationDay(
                locations=location_shifts, date=day_cursor.date()
            )
            shift_days.append(shift_location_day)

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


def send_given_shift_email(shift_slot):
    user = shift_slot.user
    content = f"""
        Hei!

        Du har blitt satt opp på vakt!
        
        Vakt: {shift_slot.shift.name}
        Hvor: {shift_slot.shift.location}
        Når: {shift_slot.shift.datetime_start.strftime('%d.%m kl %H:%M')} - {shift_slot.shift.datetime_end.strftime('%H:%M')}
        
        """

    html_content = f"""
        <p>Hei!</p>
        <p>Du har blitt satt opp på vakt!</p>
        <p>Vakt: {shift_slot.shift.name}</p>
        <p>Hvor: {shift_slot.shift.location}</p>
        <p>Når: {shift_slot.shift.datetime_start.strftime('%d.%m kl %H:%M')} - {shift_slot.shift.datetime_end.strftime('%H:%M')}</p>

        
        """

    send_email(
        recipients=[user.email],
        subject="Du har blitt satt opp på vakt!",
        message=content,
        html_message=html_content,
    )
