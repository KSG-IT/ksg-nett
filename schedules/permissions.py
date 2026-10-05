"""
Who can manage a schedule.

A user manages a schedule when they have the permission and an active
functionary membership in the internal group that staffs the schedule. A
schedule without an internal group, for example Bærevakt, can be managed by
anyone with the permission. A superuser manages every schedule. Reading shift
lists does not need this.
"""

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from graphene_django_cud.util import disambiguate_id

from organization.consts import InternalGroupPositionMembershipType
from organization.models import InternalGroupPositionMembership
from schedules.models import (
    Schedule,
    ScheduleTemplate,
    Shift,
    ShiftSlot,
    ShiftSlotTemplate,
    ShiftTemplate,
)

NOT_PERMITTED = _("You do not have permission to do this")


def managed_internal_group_ids(user):
    return InternalGroupPositionMembership.objects.filter(
        user=user,
        date_ended__isnull=True,
        type=InternalGroupPositionMembershipType.FUNCTIONARY,
    ).values_list("position__internal_group_id", flat=True)


def can_manage_schedule(user, schedule, *permissions):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if schedule is None or not user.has_perms(permissions):
        return False
    if schedule.internal_group_id is None:
        return True
    return schedule.internal_group_id in set(managed_internal_group_ids(user))


def require_can_manage_schedule(user, schedule, *permissions):
    if not can_manage_schedule(user, schedule, *permissions):
        raise PermissionDenied(NOT_PERMITTED)


def managed_schedules(user, *permissions):
    if not user or not user.is_authenticated:
        return Schedule.objects.none()
    if user.is_superuser:
        return Schedule.objects.all()
    if not user.has_perms(permissions):
        return Schedule.objects.none()
    return Schedule.objects.filter(
        Q(internal_group__isnull=True)
        | Q(internal_group_id__in=managed_internal_group_ids(user))
    )


def schedule_of(obj):
    if isinstance(obj, Schedule):
        return obj
    if isinstance(obj, (Shift, ScheduleTemplate)):
        return obj.schedule
    if isinstance(obj, ShiftSlot):
        return obj.shift.schedule
    if isinstance(obj, ShiftTemplate):
        return obj.schedule_template.schedule
    if isinstance(obj, ShiftSlotTemplate):
        return obj.shift_template.schedule_template.schedule
    raise TypeError(f"No schedule for {type(obj).__name__}")


# The input field that points to the parent of a new or moved object
PARENT_FIELDS = {
    Shift: ("schedule", Schedule),
    ShiftSlot: ("shift", Shift),
    ScheduleTemplate: ("schedule", Schedule),
    ShiftTemplate: ("schedule_template", ScheduleTemplate),
    ShiftSlotTemplate: ("shift_template", ShiftTemplate),
}


def parent_from_input(model, input):
    field, parent_model = PARENT_FIELDS[model]
    parent_id = input.get(field)
    if parent_id is None:
        return None
    return parent_model.objects.filter(pk=disambiguate_id(parent_id)).first()


class ManagedCreateMixin:
    """For a DjangoCreateMutation: the parent must be in a managed schedule."""

    @classmethod
    def check_permissions(cls, root, info, input):
        super().check_permissions(root, info, input)
        parent = parent_from_input(cls._meta.model, input)
        schedule = schedule_of(parent) if parent else None
        require_can_manage_schedule(info.context.user, schedule, *cls._meta.permissions)


class ManagedPatchMixin:
    """For a DjangoPatchMutation: the object and a new parent must be managed."""

    @classmethod
    def check_permissions(cls, root, info, input, id, obj):
        super().check_permissions(root, info, input, id, obj)
        user = info.context.user
        require_can_manage_schedule(user, schedule_of(obj), *cls._meta.permissions)
        if cls._meta.model in PARENT_FIELDS:
            field, _ = PARENT_FIELDS[cls._meta.model]
            if input.get(field) is not None:
                parent = parent_from_input(cls._meta.model, input)
                schedule = schedule_of(parent) if parent else None
                require_can_manage_schedule(user, schedule, *cls._meta.permissions)


class ManagedDeleteMixin:
    """For a DjangoDeleteMutation: the object must be in a managed schedule."""

    @classmethod
    def check_permissions(cls, root, info, id, obj):
        super().check_permissions(root, info, id, obj)
        require_can_manage_schedule(
            info.context.user, schedule_of(obj), *cls._meta.permissions
        )


def can_manage_schedule_in_request(info, schedule, *permissions):
    """can_manage_schedule, cached for the request. For fields on many rows."""
    cache = getattr(info.context, "_can_manage_schedule", None)
    if cache is None:
        cache = {}
        setattr(info.context, "_can_manage_schedule", cache)
    key = (schedule.pk if schedule else None, permissions)
    if key not in cache:
        cache[key] = can_manage_schedule(info.context.user, schedule, *permissions)
    return cache[key]
