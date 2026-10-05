"""
The roster of a schedule: the sync from the roster groupings, and the shift
counts since the last admission closed.
"""

import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import ClassVar, Optional

from django.db import transaction
from django.db.models import (
    Count,
    DateField,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from admissions.models import Admission
from organization.models import InternalGroup, InternalGroupPositionMembership
from schedules.models import ScheduleRoster, ScheduleRosterGrouping, ShiftSlot
from users.models import User

ROSTER_VALUES = ("autofill_as", "default_availability", "shift_cap")


@dataclass
class RosterChange:
    ADD: ClassVar[str] = "ADD"
    CHANGE: ClassVar[str] = "CHANGE"
    REMOVE: ClassVar[str] = "REMOVE"
    # A rule would change an edited row. The values of the row stay.
    KEEP: ClassVar[str] = "KEEP"
    # The user matches more than one rule. The sync does not touch the row.
    CONFLICT: ClassVar[str] = "CONFLICT"

    kind: str
    user: User
    entry: Optional[ScheduleRoster] = None
    grouping: Optional[ScheduleRosterGrouping] = None
    autofill_as: Optional[str] = None
    default_availability: Optional[str] = None
    shift_cap: Optional[int] = None
    count_from: Optional[datetime.date] = None
    message: str = ""


def _values(source):
    return {name: getattr(source, name) for name in ROSTER_VALUES}


def _grouping_values(grouping):
    return {
        "autofill_as": grouping.role,
        "default_availability": grouping.default_availability,
        "shift_cap": grouping.shift_cap,
    }


def _is_member(user_id, schedule):
    """A membership of any type that has not ended, in the schedule's group."""
    memberships = InternalGroupPositionMembership.objects.filter(
        user_id=user_id, date_ended__isnull=True
    )
    if schedule.internal_group_id:
        memberships = memberships.filter(
            position__internal_group_id=schedule.internal_group_id
        )
    else:
        memberships = memberships.filter(
            position__internal_group__type=InternalGroup.Type.INTERNAL_GROUP
        )
    return memberships.exists()


def plan_roster_sync(schedule):
    """The changes a sync makes, without writing them."""
    groupings = {
        (grouping.internal_group_position_id, grouping.position_type): grouping
        for grouping in schedule.roster_groupings.all()
    }
    memberships = (
        InternalGroupPositionMembership.objects.filter(
            date_ended__isnull=True,
            position_id__in={position_id for position_id, _ in groupings},
        )
        .select_related("user")
        .order_by("-date_joined")
    )
    matches = defaultdict(list)
    for membership in memberships:
        grouping = groupings.get((membership.position_id, membership.type))
        if grouping:
            matches[membership.user_id].append((membership, grouping))

    rows = {
        row.user_id: row
        for row in schedule.roster.select_related("user", "grouping").all()
    }
    changes = []

    for user_id, pairs in matches.items():
        user = pairs[0][0].user
        matched = {grouping.pk: grouping for _, grouping in pairs}
        if len(matched) > 1:
            changes.append(
                RosterChange(
                    RosterChange.CONFLICT,
                    user,
                    entry=rows.get(user_id),
                    message="; ".join(str(grouping) for grouping in matched.values()),
                )
            )
            continue

        # The newest membership, because the memberships are ordered so
        membership, grouping = pairs[0]
        row = rows.get(user_id)
        values = _grouping_values(grouping)
        if row is None:
            changes.append(
                RosterChange(
                    RosterChange.ADD,
                    user,
                    grouping=grouping,
                    count_from=membership.date_joined,
                    **values,
                )
            )
            continue

        new_grouping = row.grouping_id != grouping.pk
        count_from = membership.date_joined if new_grouping else row.count_from
        if row.manually_edited:
            if new_grouping or _values(row) != values:
                changes.append(
                    RosterChange(
                        RosterChange.KEEP,
                        user,
                        entry=row,
                        grouping=grouping,
                        count_from=count_from,
                        **_values(row),
                    )
                )
        elif new_grouping or _values(row) != values:
            changes.append(
                RosterChange(
                    RosterChange.CHANGE,
                    user,
                    entry=row,
                    grouping=grouping,
                    count_from=count_from,
                    **values,
                )
            )

    for user_id, row in rows.items():
        if user_id in matches:
            continue
        if row.added_manually and _is_member(user_id, schedule):
            continue
        changes.append(RosterChange(RosterChange.REMOVE, row.user, entry=row))

    return changes


def apply_roster_sync(schedule):
    with transaction.atomic():
        changes = plan_roster_sync(schedule)
        for change in changes:
            if change.kind == RosterChange.ADD:
                ScheduleRoster.objects.create(
                    schedule=schedule,
                    user=change.user,
                    grouping=change.grouping,
                    autofill_as=change.autofill_as,
                    default_availability=change.default_availability,
                    shift_cap=change.shift_cap,
                    count_from=change.count_from,
                )
            elif change.kind in (RosterChange.CHANGE, RosterChange.KEEP):
                row = change.entry
                row.grouping = change.grouping
                row.count_from = change.count_from
                if change.kind == RosterChange.CHANGE:
                    for name in ROSTER_VALUES:
                        setattr(row, name, getattr(change, name))
                row.save()
            elif change.kind == RosterChange.REMOVE:
                change.entry.delete()
    return changes


def shift_count_start():
    """When the last admission closed. Shifts before it do not count."""
    admission = Admission.get_last_closed_admission()
    if admission is None:
        return None
    if admission.closed_at:
        return admission.closed_at
    if admission.date:
        return timezone.make_aware(
            datetime.datetime.combine(admission.date, datetime.time.min)
        )
    return None


def annotate_shift_counts(queryset):
    """
    Add shifts_done, shifts_planned, last_shift and membership_type to roster
    rows, in one query. A shift counts from the last admission, or from
    count_from when it is later.
    """
    now = timezone.now()
    slots = ShiftSlot.objects.filter(
        user=OuterRef("user"),
        shift__schedule=OuterRef("schedule"),
        shift__datetime_start__date__gte=Coalesce(
            OuterRef("count_from"),
            Value(datetime.date(1900, 1, 1)),
            output_field=DateField(),
        ),
    )
    start = shift_count_start()
    if start is not None:
        slots = slots.filter(shift__datetime_start__gte=start)

    def count(filtered):
        return Coalesce(
            Subquery(
                filtered.order_by()
                .values("user")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
            0,
        )

    active = InternalGroupPositionMembership.objects.filter(
        user=OuterRef("user"), date_ended__isnull=True
    ).order_by("-date_joined")
    return queryset.annotate(
        shifts_done=count(slots.filter(shift__datetime_start__lt=now)),
        shifts_planned=count(slots.filter(shift__datetime_start__gte=now)),
        last_shift=Subquery(
            slots.filter(shift__datetime_start__lt=now)
            .order_by("-shift__datetime_start")
            .values("shift__datetime_start")[:1]
        ),
        membership_type=Coalesce(
            Subquery(
                active.filter(
                    position__internal_group=OuterRef("schedule__internal_group")
                ).values("type")[:1]
            ),
            Subquery(
                active.filter(
                    position__internal_group__type=InternalGroup.Type.INTERNAL_GROUP
                ).values("type")[:1]
            ),
        ),
    )
