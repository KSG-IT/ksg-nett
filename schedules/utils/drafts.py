"""
Drafts of slot changes. Members see a slot change only after a lock.
"""

from collections import defaultdict

from django.db import transaction

from schedules.models import ShiftSlotDraft
from schedules.utils.schedules import send_new_shifts_email


def drafts_in_range(schedule, date_from=None, date_to=None):
    """The drafts of the schedule, for shifts on local dates in the range."""
    drafts = ShiftSlotDraft.objects.filter(slot__shift__schedule=schedule)
    if date_from is not None:
        drafts = drafts.filter(slot__shift__datetime_start__date__gte=date_from)
    if date_to is not None:
        drafts = drafts.filter(slot__shift__datetime_start__date__lte=date_to)
    return drafts


def lock_drafts(schedule, date_from=None, date_to=None):
    """
    Copy the drafts in the range to the slots and delete them, in one
    transaction. After the commit, each user with notify_on_shift gets one
    email with their new shifts. A removal sends no email.
    Returns the number of changed slots and of notified users.
    """
    with transaction.atomic():
        drafts = list(
            drafts_in_range(schedule, date_from, date_to).select_related(
                "slot__shift", "user"
            )
        )
        new_slots = defaultdict(list)
        changed = 0
        for draft in drafts:
            slot = draft.slot
            if slot.user_id == draft.user_id:
                continue
            slot.user = draft.user
            slot.save(update_fields=["user"])
            changed += 1
            if draft.user is not None:
                new_slots[draft.user].append(slot)
        ShiftSlotDraft.objects.filter(pk__in=[draft.pk for draft in drafts]).delete()

        notified = [user for user in new_slots if user.notify_on_shift]

        def send_emails():
            for user in notified:
                send_new_shifts_email(user, new_slots[user])

        transaction.on_commit(send_emails)
    return changed, len(notified)
