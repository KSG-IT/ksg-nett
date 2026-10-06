"""
Weekly unavailability, and the pre-fill of "cannot work" answers from it.

The pre-fill only writes ShiftInterest rows with source=unavailability, only
for shifts in open planning periods, and only for roster rows with
default_availability=available. It never changes an answer the user gave.

The mutations that change entries, periods, shifts and roster rows call the
prefill functions. A change in the Django admin does not pre-fill.
"""

import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from schedules.models import (
    DefaultAvailability,
    PlanningPeriod,
    ScheduleRoster,
    ShiftInterest,
    ShiftTemplate,
    UserUnavailability,
)

WEEKDAYS = list(ShiftTemplate.Day.values)  # Monday first, like date.weekday()
NOTE_LENGTH = ShiftInterest._meta.get_field("note").max_length


def _occurrences(entry, first_day, last_day):
    local = ZoneInfo(settings.TIME_ZONE)
    day = first_day
    while day <= last_day:
        if WEEKDAYS[day.weekday()] == entry.day:
            end_day = (
                day + datetime.timedelta(days=1)
                if entry.time_end <= entry.time_start
                else day
            )
            yield (
                datetime.datetime.combine(day, entry.time_start, tzinfo=local),
                datetime.datetime.combine(end_day, entry.time_end, tzinfo=local),
            )
        day += datetime.timedelta(days=1)


def blocks(entry, shift):
    """If the entry overlaps the shift. Touching ends do not overlap."""
    start, end = shift.datetime_start, shift.datetime_end
    # An entry that starts the day before can pass midnight into the shift
    first_day = timezone.localdate(start) - datetime.timedelta(days=1)
    last_day = timezone.localdate(end)
    return any(
        entry_start < end and start < entry_end
        for entry_start, entry_end in _occurrences(entry, first_day, last_day)
    )


def _entries_by_user(user_ids):
    entries = defaultdict(list)
    for entry in UserUnavailability.objects.filter(user_id__in=user_ids).order_by(
        "time_start"
    ):
        entries[entry.user_id].append(entry)
    return entries


def prefill_shifts(schedule, shifts, users=None):
    """Write the pre-filled answers of the schedule's roster for the shifts."""
    shifts = list(shifts)
    rows = ScheduleRoster.objects.filter(schedule=schedule)
    if users is not None:
        rows = rows.filter(user__in=users)
    rows = list(rows)
    if not shifts or not rows:
        return

    user_ids = [row.user_id for row in rows]
    entries = _entries_by_user(user_ids)
    answers = {
        (answer.user_id, answer.shift_id): answer
        for answer in ShiftInterest.objects.filter(
            shift__in=shifts, user_id__in=user_ids
        )
    }
    for row in rows:
        for shift in shifts:
            answer = answers.get((row.user_id, shift.pk))
            if answer and answer.source == ShiftInterest.Source.MANUAL:
                continue
            matched = []
            if row.default_availability == DefaultAvailability.AVAILABLE:
                matched = [
                    entry for entry in entries[row.user_id] if blocks(entry, shift)
                ]
            if not matched:
                if answer:
                    answer.delete()
                continue
            note = "; ".join(entry.note for entry in matched if entry.note)
            note = note[:NOTE_LENGTH]
            if answer is None:
                ShiftInterest.objects.create(
                    shift=shift,
                    user_id=row.user_id,
                    interest_type=ShiftInterest.InterestTypes.UNAVAILABLE,
                    source=ShiftInterest.Source.UNAVAILABILITY,
                    note=note,
                )
            elif (
                answer.interest_type != ShiftInterest.InterestTypes.UNAVAILABLE
                or answer.note != note
            ):
                answer.interest_type = ShiftInterest.InterestTypes.UNAVAILABLE
                answer.note = note
                answer.save()


def _open_periods(schedule):
    periods = PlanningPeriod.objects.filter(
        schedule=schedule, published_at__isnull=True, deadline__gt=timezone.now()
    )
    return [period for period in periods if period.status == PlanningPeriod.Status.OPEN]


def prefill_period(period):
    if period.status == PlanningPeriod.Status.OPEN:
        prefill_shifts(period.schedule, period.shifts())


def prefill_roster_row(row):
    for period in _open_periods(row.schedule):
        prefill_shifts(row.schedule, period.shifts(), users=[row.user_id])


def prefill_user(user_id):
    for row in ScheduleRoster.objects.filter(user_id=user_id).select_related(
        "schedule"
    ):
        prefill_roster_row(row)


def prefill_schedule(schedule):
    for period in _open_periods(schedule):
        prefill_shifts(schedule, period.shifts())


def prefill_shift(shift):
    period = PlanningPeriod.for_shift(shift)
    if period and period.status == PlanningPeriod.Status.OPEN:
        prefill_shifts(shift.schedule, [shift])


def blocked_shift_count(entry, user):
    """The shifts in open periods that the entry blocks, for the user's rosters."""
    count = 0
    for row in ScheduleRoster.objects.filter(
        user=user, default_availability=DefaultAvailability.AVAILABLE
    ).select_related("schedule"):
        for period in _open_periods(row.schedule):
            count += sum(blocks(entry, shift) for shift in period.shifts())
    return count
