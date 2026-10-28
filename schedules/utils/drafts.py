"""
Drafts of slot changes. Members see a slot change only after a lock.
"""

from collections import defaultdict

from django.db import transaction

from schedules.models import ShiftSlotDraft
from schedules.notifications import notify_new_shifts


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
    transaction. After the commit, each user gets one e-mail and one push with
    their new shifts, as their settings allow. A removal sends nothing.
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

        transaction.on_commit(lambda: notify_new_shifts(new_slots))
    return changed, len(notified)
