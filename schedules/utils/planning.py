"""
Follow-up of a planning period for the managers: the reminder email, the
response numbers and the coverage of the open slots.
"""

from collections import defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape

from common.util import send_email
from schedules.models import (
    DefaultAvailability,
    ScheduleRoster,
    ShiftInterest,
    ShiftSlot,
)
from schedules.utils.autofill import candidates

AVAILABILITY_PATH = "/schedules/me/availability"


def send_period_reminder(period):
    """
    Emails the roster users with the default "available" about the deadline,
    also without notify_on_shift. Opt-in users get no reminder. The emails go
    after the commit. Returns the number of recipients.
    """
    users = [
        row.user
        for row in ScheduleRoster.objects.filter(
            schedule=period.schedule,
            default_availability=DefaultAvailability.AVAILABLE,
        ).select_related("user")
        if row.user.email
    ]
    local = ZoneInfo(settings.TIME_ZONE)
    deadline = timezone.localtime(period.deadline, local).strftime("%d.%m kl %H:%M")
    dates = f"{period.date_from.strftime('%d.%m')}–{period.date_to.strftime('%d.%m')}"
    link = settings.APP_URL + AVAILABILITY_PATH
    subject = f"Frist {deadline}: tilgjengelighet for {period.schedule.name}"
    message = (
        "Hei!\n\n"
        f"Oppgi tilgjengeligheten din for {period.schedule.name} {dates} "
        f"innen {deadline}.\n"
        "Du står som tilgjengelig på alle vakter du ikke har markert.\n\n"
        f"{link}\n"
    )
    html_message = (
        "<p>Hei!</p>"
        f"<p>Oppgi tilgjengeligheten din for {escape(period.schedule.name)} "
        f"{dates} innen {deadline}.</p>"
        "<p>Du står som tilgjengelig på alle vakter du ikke har markert.</p>"
        f'<p><a href="{escape(link)}">Gå til tilgjengelighet</a></p>'
    )

    period.reminder_sent_at = timezone.now()
    period.save(update_fields=["reminder_sent_at"])

    def send_emails():
        for user in users:
            send_email(
                recipients=[user.email],
                subject=subject,
                message=message,
                html_message=html_message,
            )

    transaction.on_commit(send_emails)
    return len(users)


@dataclass
class ResponseStats:
    roster_count: int
    opt_in_count: int
    # Users with at least one answer they gave themselves
    users_with_answers: int
    # Opt-in users with at least one INTERESTED or AVAILABLE answer
    opt_in_with_interest: int
    interested: int
    available: int
    unavailable: int
    # UNAVAILABLE answers from the weekly unavailability
    unavailable_prefilled: int
    with_note: int


def response_stats(period):
    rows = list(ScheduleRoster.objects.filter(schedule=period.schedule))
    opt_in = {
        row.user_id
        for row in rows
        if row.default_availability == DefaultAvailability.OPT_IN
    }
    answers = ShiftInterest.objects.filter(
        shift__in=period.shifts(), user_id__in=[row.user_id for row in rows]
    )
    types = ShiftInterest.InterestTypes
    counts = defaultdict(int)
    answered = set()
    opt_in_interest = set()
    for answer in answers:
        counts[answer.interest_type] += 1
        if answer.note:
            counts["note"] += 1
        if answer.source == ShiftInterest.Source.UNAVAILABILITY:
            counts["prefilled"] += 1
        else:
            answered.add(answer.user_id)
        if answer.user_id in opt_in and answer.interest_type != types.UNAVAILABLE:
            opt_in_interest.add(answer.user_id)
    return ResponseStats(
        roster_count=len(rows),
        opt_in_count=len(opt_in),
        users_with_answers=len(answered),
        opt_in_with_interest=len(opt_in_interest),
        interested=counts[types.INTERESTED],
        available=counts[types.AVAILABLE],
        unavailable=counts[types.UNAVAILABLE],
        unavailable_prefilled=counts["prefilled"],
        with_note=counts["note"],
    )


@dataclass
class SlotCoverage:
    shift: object
    role: str
    slot_count: int
    # Slots without a user in the plan with the drafts
    open_slot_count: int
    candidate_count: int
    interested_count: int
    unavailable_count: int
    unavailable_with_note_count: int


def slot_coverage(period):
    """
    One row per shift and role: the slots and the users who can work them,
    by the same rule as autofill. The rows with the fewest spare candidates
    come first.
    """
    rows = list(ScheduleRoster.objects.filter(schedule=period.schedule))
    shifts = list(period.shifts())
    answers = {}
    unavailable = defaultdict(lambda: [0, 0])
    for answer in ShiftInterest.objects.filter(
        shift__in=shifts, user_id__in=[row.user_id for row in rows]
    ):
        answers[(answer.user_id, answer.shift_id)] = answer.interest_type
        if answer.interest_type == ShiftInterest.InterestTypes.UNAVAILABLE:
            unavailable[(answer.shift_id, answer.user_id)] = [1, int(bool(answer.note))]

    slots = defaultdict(lambda: [0, 0])
    for slot in ShiftSlot.objects.filter(shift__in=shifts).select_related("draft"):
        draft = getattr(slot, "draft", None)
        user_id = draft.user_id if draft else slot.user_id
        slots[(slot.shift_id, slot.role)][0] += 1
        if user_id is None:
            slots[(slot.shift_id, slot.role)][1] += 1

    coverage = []
    by_id = {shift.pk: shift for shift in shifts}
    for (shift_id, role), (slot_count, open_count) in slots.items():
        shift = by_id[shift_id]
        can_work = candidates(rows, answers, shift, role)
        with_role = [row for row in rows if row.autofill_as == role]
        marks = [unavailable.get((shift_id, row.user_id)) for row in with_role]
        marks = [mark for mark in marks if mark]
        coverage.append(
            SlotCoverage(
                shift=shift,
                role=role,
                slot_count=slot_count,
                open_slot_count=open_count,
                candidate_count=len(can_work),
                interested_count=sum(
                    1 for _, preference in can_work if preference == 0
                ),
                unavailable_count=len(marks),
                unavailable_with_note_count=sum(mark[1] for mark in marks),
            )
        )
    coverage.sort(
        key=lambda row: (
            row.candidate_count - row.open_slot_count,
            row.shift.datetime_start,
            row.role,
        )
    )
    return coverage
