import graphene
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions
from schedules.models import (
    PlanningPeriod,
    Schedule,
    ScheduleAutofillRun,
    ShiftSlot,
    ShiftSlotDraft,
)
from schedules.permissions import managed_schedules, require_can_manage_schedule
from schedules.schemas.schedules import ShiftSlotNode
from schedules.utils.autofill import UnfilledReason, revert_autofill_run, run_autofill
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
            # A manual change makes the draft manual, so a new autofill run keeps it
            ShiftSlotDraft.objects.update_or_create(
                slot=slot,
                defaults={
                    "user": user,
                    "changed_by": info.context.user,
                    "autofill_run": None,
                },
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


UnfilledReasonEnum = graphene.Enum.from_enum(
    UnfilledReason,
    description=lambda reason: (
        {
            UnfilledReason.NO_ROLE_ON_ROSTER: "No roster row has the slot's role",
            UnfilledReason.NO_CANDIDATES: "No user with the role can work the shift",
            UnfilledReason.BUSY_SAME_DAY: "The candidates have a shift that day",
            UnfilledReason.WEEKLY_LIMIT: "The candidates have the most shifts that week",
            UnfilledReason.SHIFT_CAP: "The candidates have reached their shift cap",
        }.get(reason)
        if reason
        else "Why autofill left a slot empty"
    ),
)


class UnfilledSlotNode(graphene.ObjectType):
    shift_slot = graphene.Field(ShiftSlotNode)
    reason = graphene.NonNull(UnfilledReasonEnum)
    candidate_count = graphene.NonNull(graphene.Int)


class ScheduleAutofillRunNode(DjangoObjectType):
    class Meta:
        model = ScheduleAutofillRun
        interfaces = (Node,)
        exclude = ("unfilled",)

    unfilled = graphene.NonNull(graphene.List(graphene.NonNull(UnfilledSlotNode)))
    draft_count = graphene.NonNull(
        graphene.Int, description="Drafts of the run that are not locked yet"
    )

    def resolve_unfilled(self: ScheduleAutofillRun, info):
        slots = ShiftSlot.objects.in_bulk([row["slot"] for row in self.unfilled])
        return [
            UnfilledSlotNode(
                shift_slot=slots.get(row["slot"]),
                reason=row["reason"],
                candidate_count=row["candidates"],
            )
            for row in self.unfilled
        ]

    def resolve_draft_count(self: ScheduleAutofillRun, info):
        return self.drafts.count()

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(
            period__schedule__in=managed_schedules(info.context.user, CHANGE_SLOT)
        )

    @classmethod
    def get_node(cls, info, id):
        # None for a null foreign key, for example ShiftSlotDraft.autofill_run
        queryset = cls.get_queryset(ScheduleAutofillRun.objects, info)
        return queryset.filter(pk=id).first()


class RunAutofillMutation(graphene.Mutation):
    """
    Fills the empty slots of the period as drafts. The drafts of earlier runs
    of the period are replaced; manual drafts stay.
    """

    class Arguments:
        planning_period_id = graphene.ID(required=True)

    autofill_run = graphene.Field(ScheduleAutofillRunNode)

    @gql_has_permissions(CHANGE_SLOT)
    def mutate(self, info, planning_period_id):
        period = PlanningPeriod.objects.select_related("schedule").get(
            pk=disambiguate_id(planning_period_id)
        )
        require_can_manage_schedule(info.context.user, period.schedule, CHANGE_SLOT)
        run = run_autofill(period, created_by=info.context.user)
        return RunAutofillMutation(autofill_run=run)


class RevertAutofillRunMutation(graphene.Mutation):
    """Deletes the drafts of the run that are not locked or changed by hand."""

    class Arguments:
        id = graphene.ID(required=True)

    removed_drafts = graphene.NonNull(graphene.Int)

    @gql_has_permissions(CHANGE_SLOT)
    def mutate(self, info, id):
        run = ScheduleAutofillRun.objects.select_related("period__schedule").get(
            pk=disambiguate_id(id)
        )
        require_can_manage_schedule(info.context.user, run.period.schedule, CHANGE_SLOT)
        return RevertAutofillRunMutation(removed_drafts=revert_autofill_run(run))


class AutofillMutations(graphene.ObjectType):
    run_autofill = RunAutofillMutation.Field()
    revert_autofill_run = RevertAutofillRunMutation.Field()
