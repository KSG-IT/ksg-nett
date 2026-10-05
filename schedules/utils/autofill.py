"""
Autofill of a planning period: greedy, hardest slot first.

1. Take the empty slots of the period: no user and no draft. Drafts from
   earlier runs are deleted first. A manual draft stays, and its slot is
   skipped.
2. Find the candidates of each slot: roster rows with the slot's role that
   can work the shift (their answer, else the roster default).
3. Fill the slots with the fewest candidates first. For each slot, choose
   the candidate who:
   - has no other shift on the same local day, in any schedule;
   - has fewer than Schedule.max_shifts_per_week shifts in the week;
   - is below their shift_cap, if they have one;
   then the fewest shifts since the last admission, interested before
   available, and the lowest user id.
4. Save the choices as ShiftSlotDraft rows of a new ScheduleAutofillRun,
   and the empty slots with a reason.
"""

import datetime
from collections import Counter, defaultdict
from enum import Enum

from django.db import transaction
from django.utils import timezone

from schedules.models import (
    DefaultAvailability,
    ScheduleAutofillRun,
    ScheduleRoster,
    ShiftInterest,
    ShiftSlot,
    ShiftSlotDraft,
)
from schedules.utils.roster import annotate_shift_counts


class UnfilledReason(str, Enum):
    # No roster row has the slot's role
    NO_ROLE_ON_ROSTER = "NO_ROLE_ON_ROSTER"
    # Users with the role are on the roster, but none can work the shift
    NO_CANDIDATES = "NO_CANDIDATES"
    # The candidates have another shift on the same day
    BUSY_SAME_DAY = "BUSY_SAME_DAY"
    # The candidates have the most shifts for the week
    WEEKLY_LIMIT = "WEEKLY_LIMIT"
    # The candidates have reached their shift cap
    SHIFT_CAP = "SHIFT_CAP"


INTERESTED = ShiftInterest.InterestTypes.INTERESTED
UNAVAILABLE = ShiftInterest.InterestTypes.UNAVAILABLE


def _local_day(moment):
    return timezone.localdate(moment)


def _week(moment):
    return _local_day(moment).isocalendar()[:2]


def _preference(row, answer):
    """0 for interested, 1 for available, None when the user cannot work."""
    if answer is None:
        return 1 if row.default_availability == DefaultAvailability.AVAILABLE else None
    if answer == UNAVAILABLE:
        return None
    return 0 if answer == INTERESTED else 1


def _commitments(user_ids, first_day, last_day):
    """
    The planned shifts of the users in the days, in all schedules: a slot
    counts for the draft user when it has a draft, else for the slot user.
    """
    slots = ShiftSlot.objects.filter(
        shift__datetime_start__date__gte=first_day,
        shift__datetime_start__date__lte=last_day,
    ).select_related("shift", "draft")
    by_user = defaultdict(list)
    for slot in slots:
        draft = getattr(slot, "draft", None)
        user_id = draft.user_id if draft else slot.user_id
        if user_id in user_ids:
            by_user[user_id].append(slot.shift)
    return by_user


def run_autofill(period, created_by=None):
    schedule = period.schedule
    with transaction.atomic():
        # A new run replaces the drafts of the earlier runs of the period
        ShiftSlotDraft.objects.filter(autofill_run__period=period).delete()

        run = ScheduleAutofillRun.objects.create(period=period, created_by=created_by)
        slots = list(
            ShiftSlot.objects.filter(
                shift__in=period.shifts(), user__isnull=True, draft__isnull=True
            ).select_related("shift")
        )
        rows = list(
            annotate_shift_counts(
                ScheduleRoster.objects.filter(schedule=schedule), include_drafts=True
            )
        )
        user_ids = {row.user_id for row in rows}
        totals = {row.user_id: row.shifts_done + row.shifts_planned for row in rows}
        answers = {
            (answer.user_id, answer.shift_id): answer.interest_type
            for answer in ShiftInterest.objects.filter(
                shift__in=period.shifts(), user_id__in=user_ids
            )
        }

        # Whole weeks around the period, for the weekly limit
        first_day = period.date_from - datetime.timedelta(
            days=period.date_from.weekday()
        )
        last_day = period.date_to + datetime.timedelta(
            days=6 - period.date_to.weekday()
        )
        commitments = _commitments(user_ids, first_day, last_day)
        busy_days = {
            user_id: {_local_day(shift.datetime_start) for shift in shifts}
            for user_id, shifts in commitments.items()
        }
        weekly = defaultdict(Counter)
        for user_id, shifts in commitments.items():
            for shift in shifts:
                if shift.schedule_id == schedule.pk:
                    weekly[user_id][_week(shift.datetime_start)] += 1

        roles = {row.autofill_as for row in rows}
        candidates = {}
        for slot in slots:
            candidates[slot.pk] = [
                (row, preference)
                for row in rows
                if row.autofill_as == slot.role
                for preference in [
                    _preference(row, answers.get((row.user_id, slot.shift_id)))
                ]
                if preference is not None
            ]

        slots.sort(
            key=lambda slot: (
                len(candidates[slot.pk]),
                slot.shift.datetime_start,
                slot.pk,
            )
        )
        drafts = []
        unfilled = []
        for slot in slots:
            day = _local_day(slot.shift.datetime_start)
            week = _week(slot.shift.datetime_start)
            eligible = []
            failed = Counter()
            for row, preference in candidates[slot.pk]:
                if day in busy_days.get(row.user_id, set()):
                    failed[UnfilledReason.BUSY_SAME_DAY] += 1
                elif weekly[row.user_id][week] >= schedule.max_shifts_per_week:
                    failed[UnfilledReason.WEEKLY_LIMIT] += 1
                elif row.shift_cap is not None and totals[row.user_id] >= row.shift_cap:
                    failed[UnfilledReason.SHIFT_CAP] += 1
                else:
                    eligible.append((totals[row.user_id], preference, row.user_id))

            if eligible:
                _, _, user_id = min(eligible)
                drafts.append(
                    ShiftSlotDraft(
                        slot=slot,
                        user_id=user_id,
                        autofill_run=run,
                        changed_by=created_by,
                    )
                )
                totals[user_id] += 1
                weekly[user_id][week] += 1
                busy_days.setdefault(user_id, set()).add(day)
                continue

            if slot.role not in roles:
                reason = UnfilledReason.NO_ROLE_ON_ROSTER
            elif not candidates[slot.pk]:
                reason = UnfilledReason.NO_CANDIDATES
            else:
                reason = failed.most_common(1)[0][0]
            unfilled.append(
                {
                    "slot": slot.pk,
                    "reason": reason.value,
                    "candidates": len(candidates[slot.pk]),
                }
            )

        ShiftSlotDraft.objects.bulk_create(drafts)
        run.unfilled = unfilled
        run.save(update_fields=["unfilled"])
    return run


def revert_autofill_run(run):
    """Deletes the drafts of the run that are not locked or changed by hand."""
    removed, _ = run.drafts.all().delete()
    return removed
