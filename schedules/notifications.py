"""
The shift notifications, one function per event, with every channel. The
mutations and utils call these through transaction.on_commit.
`notify_on_shift` decides the e-mail and `push_on_shift` the push.
"""

from django.utils import timezone

from push.utils import PushMessage, send_to_users
from schedules.utils.schedules import send_given_shift_email, send_new_shifts_email


def shift_line(shift):
    start = timezone.localtime(shift.datetime_start)
    end = timezone.localtime(shift.datetime_end)
    where = shift.get_location_display() or ""
    return (
        f"{start.strftime('%d.%m kl %H:%M')}–{end.strftime('%H:%M')}: "
        f"{shift.name}{', ' + where if where else ''}"
    )


def push_new_shifts(user, shifts):
    """One push with all the new shifts of the user, sorted by start."""
    if not user.push_on_shift or not shifts:
        return
    shifts = sorted(shifts, key=lambda shift: shift.datetime_start)
    if len(shifts) == 1:
        title = "Du er satt opp på vakt"
    else:
        title = f"Du har fått {len(shifts)} nye vakter"
    send_to_users(
        [user.pk],
        PushMessage(
            title=title,
            body="\n".join(shift_line(shift) for shift in shifts),
            path="/schedules/me",
            # One notification for new shifts: a newer push replaces it
            tag="new-shifts",
        ),
    )


def notify_given_shift(shift_slot):
    """A manager put the user on one slot."""
    user = shift_slot.user
    if user.notify_on_shift:
        send_given_shift_email(shift_slot)
    push_new_shifts(user, [shift_slot.shift])


def notify_new_shifts(slots_by_user):
    """A lock of drafts gave each user these slots. A removal sends nothing."""
    for user, slots in slots_by_user.items():
        if user.notify_on_shift:
            send_new_shifts_email(user, slots)
        push_new_shifts(user, [slot.shift for slot in slots])
