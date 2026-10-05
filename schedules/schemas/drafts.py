import graphene
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions
from schedules.models import PlanningPeriod, Schedule, ShiftSlot, ShiftSlotDraft
from schedules.permissions import managed_schedules, require_can_manage_schedule
from schedules.schemas.schedules import ShiftSlotNode
from schedules.utils.drafts import drafts_in_range, lock_drafts
from users.models import User

CHANGE_SLOT = "schedules.change_shiftslot"


class ShiftSlotDraftNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotDraft
        interfaces = (Node,)

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(
            slot__shift__schedule__in=managed_schedules(info.context.user, CHANGE_SLOT)
        )

    @classmethod
    def get_node(cls, info, id):
        return cls.get_queryset(ShiftSlotDraft.objects, info).get(pk=id)


class DraftSlotMutation(graphene.Mutation):
    """
    Sets the draft user of a slot. No user removes the person at the lock. A
    draft equal to the slot's current user removes the draft.
    """

    class Arguments:
        shift_slot_id = graphene.ID(required=True)
        user_id = graphene.ID()

    shift_slot = graphene.Field(ShiftSlotNode)

    @gql_has_permissions(CHANGE_SLOT)
    def mutate(self, info, shift_slot_id, user_id=None):
        slot = ShiftSlot.objects.select_related("shift__schedule").get(
            pk=disambiguate_id(shift_slot_id)
        )
        require_can_manage_schedule(info.context.user, slot.shift.schedule, CHANGE_SLOT)
        user = User.objects.get(pk=disambiguate_id(user_id)) if user_id else None
        if (user.pk if user else None) == slot.user_id:
            ShiftSlotDraft.objects.filter(slot=slot).delete()
        else:
            ShiftSlotDraft.objects.update_or_create(
                slot=slot, defaults={"user": user, "changed_by": info.context.user}
            )
        return DraftSlotMutation(shift_slot=ShiftSlot.objects.get(pk=slot.pk))


def schedule_for_slot_manager(info, schedule_id):
    schedule = Schedule.objects.get(pk=disambiguate_id(schedule_id))
    require_can_manage_schedule(info.context.user, schedule, CHANGE_SLOT)
    return schedule


class DiscardDraftMutation(graphene.Mutation):
    """Deletes the drafts. Without dates, all drafts of the schedule."""

    class Arguments:
        schedule_id = graphene.ID(required=True)
        date_from = graphene.Date()
        date_to = graphene.Date()

    discarded = graphene.NonNull(graphene.Int)

    @gql_has_permissions(CHANGE_SLOT)
    def mutate(self, info, schedule_id, date_from=None, date_to=None):
        schedule = schedule_for_slot_manager(info, schedule_id)
        discarded, _ = drafts_in_range(schedule, date_from, date_to).delete()
        return DiscardDraftMutation(discarded=discarded)


class LockDraftMutation(graphene.Mutation):
    """
    Copies the drafts to the slots and emails each user with new shifts once
    (only with notify_on_shift). Without dates, all drafts of the schedule.
    """

    class Arguments:
        schedule_id = graphene.ID(required=True)
        date_from = graphene.Date()
        date_to = graphene.Date()

    changed_slots = graphene.NonNull(graphene.Int)
    notified_users = graphene.NonNull(graphene.Int)

    @gql_has_permissions(CHANGE_SLOT)
    def mutate(self, info, schedule_id, date_from=None, date_to=None):
        schedule = schedule_for_slot_manager(info, schedule_id)
        changed, notified = lock_drafts(schedule, date_from, date_to)
        return LockDraftMutation(changed_slots=changed, notified_users=notified)


class PublishPlanningPeriodMutation(graphene.Mutation):
    """Locks the drafts in the period's dates and marks the period published."""

    class Arguments:
        id = graphene.ID(required=True)

    planning_period = graphene.Field("schedules.schemas.planning.PlanningPeriodNode")
    changed_slots = graphene.NonNull(graphene.Int)
    notified_users = graphene.NonNull(graphene.Int)

    @gql_has_permissions("schedules.change_schedule", CHANGE_SLOT)
    def mutate(self, info, id):
        period = PlanningPeriod.objects.select_related("schedule").get(
            pk=disambiguate_id(id)
        )
        require_can_manage_schedule(
            info.context.user,
            period.schedule,
            "schedules.change_schedule",
            CHANGE_SLOT,
        )
        changed, notified = lock_drafts(
            period.schedule, period.date_from, period.date_to
        )
        if period.published_at is None:
            period.published_at = timezone.now()
            period.save(update_fields=["published_at"])
        return PublishPlanningPeriodMutation(
            planning_period=period, changed_slots=changed, notified_users=notified
        )


class DraftMutations(graphene.ObjectType):
    draft_slot = DraftSlotMutation.Field()
    discard_draft = DiscardDraftMutation.Field()
    lock_draft = LockDraftMutation.Field()
    publish_planning_period = PublishPlanningPeriodMutation.Field()
