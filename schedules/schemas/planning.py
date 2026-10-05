import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions, gql_login_required
from common.exceptions import IllegalOperation
from schedules.models import (
    PlanningPeriod,
    Schedule,
    ScheduleRoster,
    Shift,
    ShiftInterest,
)
from schedules.permissions import require_can_manage_schedule
from schedules.schemas.schedules import ShiftNode
from schedules.utils.unavailability import prefill_period

MANAGE = "schedules.change_schedule"

PlanningPeriodStatusEnum = graphene.Enum.from_enum(
    PlanningPeriod.Status, name="PlanningPeriodStatus"
)
ShiftInterestTypeEnum = graphene.Enum.from_enum(
    ShiftInterest.InterestTypes, name="ShiftInterestTypeEnum"
)


class PlanningPeriodNode(DjangoObjectType):
    class Meta:
        model = PlanningPeriod
        interfaces = (Node,)

    status = graphene.NonNull(PlanningPeriodStatusEnum)
    autofill_runs = graphene.NonNull(
        graphene.List(
            graphene.NonNull("schedules.schemas.drafts.ScheduleAutofillRunNode")
        ),
        description="Newest first. Empty for users who do not manage the schedule",
    )
    shifts = graphene.NonNull(graphene.List(graphene.NonNull(ShiftNode)))

    def resolve_status(self: PlanningPeriod, info):
        return self.status

    def resolve_autofill_runs(self: PlanningPeriod, info):
        from schedules.schemas.drafts import ScheduleAutofillRunNode

        return ScheduleAutofillRunNode.get_queryset(self.autofill_runs.all(), info)

    def resolve_shifts(self: PlanningPeriod, info):
        return self.shifts()

    @classmethod
    @gql_login_required()
    def get_node(cls, info, id):
        return PlanningPeriod.objects.get(pk=id)


class PlanningPeriodQuery(graphene.ObjectType):
    planning_period = Node.Field(PlanningPeriodNode)
    my_open_planning_periods = graphene.NonNull(
        graphene.List(graphene.NonNull(PlanningPeriodNode)),
        description="Open periods of the schedules where the user is on the roster",
    )

    @gql_login_required()
    def resolve_my_open_planning_periods(self, info):
        schedules = ScheduleRoster.objects.filter(user=info.context.user).values(
            "schedule"
        )
        periods = PlanningPeriod.objects.filter(
            schedule__in=schedules, published_at__isnull=True
        ).select_related("schedule")
        return [
            period
            for period in periods.order_by("deadline")
            if period.status == PlanningPeriod.Status.OPEN
        ]


def check_period_dates(schedule, date_from, date_to, exclude=None):
    if date_to < date_from:
        raise IllegalOperation("The period must end on or after its start")
    if PlanningPeriod.overlapping(schedule, date_from, date_to, exclude).exists():
        raise IllegalOperation("The period overlaps another period of the schedule")


class CreatePlanningPeriodInput(graphene.InputObjectType):
    schedule_id = graphene.ID(required=True)
    date_from = graphene.Date(required=True)
    date_to = graphene.Date(required=True)
    deadline = graphene.DateTime(required=True)


class CreatePlanningPeriodMutation(graphene.Mutation):
    class Arguments:
        input = CreatePlanningPeriodInput(required=True)

    planning_period = graphene.Field(PlanningPeriodNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, input):
        schedule = Schedule.objects.get(pk=disambiguate_id(input.schedule_id))
        require_can_manage_schedule(info.context.user, schedule, MANAGE)
        check_period_dates(schedule, input.date_from, input.date_to)
        period = PlanningPeriod.objects.create(
            schedule=schedule,
            date_from=input.date_from,
            date_to=input.date_to,
            deadline=input.deadline,
            created_by=info.context.user,
        )
        prefill_period(period)
        return CreatePlanningPeriodMutation(planning_period=period)


class UpdatePlanningPeriodInput(graphene.InputObjectType):
    date_from = graphene.Date()
    date_to = graphene.Date()
    deadline = graphene.DateTime(
        description="A deadline in the future opens a closed period again"
    )


class UpdatePlanningPeriodMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = UpdatePlanningPeriodInput(required=True)

    planning_period = graphene.Field(PlanningPeriodNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id, input):
        period = PlanningPeriod.objects.get(pk=disambiguate_id(id))
        require_can_manage_schedule(info.context.user, period.schedule, MANAGE)
        for name in ("date_from", "date_to", "deadline"):
            if input.get(name) is not None:
                setattr(period, name, input.get(name))
        check_period_dates(period.schedule, period.date_from, period.date_to, period)
        period.save()
        prefill_period(period)
        return UpdatePlanningPeriodMutation(planning_period=period)


class DeletePlanningPeriodMutation(graphene.Mutation):
    """Deletes a period that is not published. The answers stay on the shifts."""

    class Arguments:
        id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id):
        period = PlanningPeriod.objects.filter(pk=disambiguate_id(id)).first()
        if period is None:
            return DeletePlanningPeriodMutation(found=False)
        require_can_manage_schedule(info.context.user, period.schedule, MANAGE)
        if period.published_at:
            raise IllegalOperation("A published period cannot be deleted")
        period.delete()
        return DeletePlanningPeriodMutation(found=True)


class SetShiftInterestMutation(graphene.Mutation):
    """
    Sets the user's answer for a shift: interested, available or unavailable.
    No type removes the answer, so the roster default applies. The shift must
    be in an open planning period, and the user on the schedule's roster.
    """

    class Arguments:
        shift_id = graphene.ID(required=True)
        interest_type = ShiftInterestTypeEnum()
        note = graphene.String()

    shift = graphene.Field(ShiftNode)
    shift_interest = graphene.Field("schedules.schemas.schedules.ShiftInterestNode")

    @gql_login_required()
    def mutate(self, info, shift_id, interest_type=None, note=None):
        user = info.context.user
        shift = Shift.objects.get(pk=disambiguate_id(shift_id))
        if not ScheduleRoster.objects.filter(
            schedule_id=shift.schedule_id, user=user
        ).exists():
            raise IllegalOperation("You are not on the roster of this schedule")
        period = PlanningPeriod.for_shift(shift)
        if period is None:
            raise IllegalOperation("The shift is not in a planning period")
        if period.status != PlanningPeriod.Status.OPEN:
            raise IllegalOperation("The planning period is not open")

        if interest_type is None:
            ShiftInterest.objects.filter(shift=shift, user=user).delete()
            return SetShiftInterestMutation(shift=shift, shift_interest=None)

        interest, _ = ShiftInterest.objects.update_or_create(
            shift=shift,
            user=user,
            defaults={
                "interest_type": interest_type.value,
                "note": (note or "").strip(),
                "source": ShiftInterest.Source.MANUAL,
            },
        )
        return SetShiftInterestMutation(shift=shift, shift_interest=interest)


class PlanningPeriodMutations(graphene.ObjectType):
    create_planning_period = CreatePlanningPeriodMutation.Field()
    update_planning_period = UpdatePlanningPeriodMutation.Field()
    delete_planning_period = DeletePlanningPeriodMutation.Field()
    set_shift_interest = SetShiftInterestMutation.Field()
