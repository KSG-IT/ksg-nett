import graphene
from django.db.models import Case, IntegerField, Value, When
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_login_required
from common.exceptions import IllegalOperation
from schedules.models import ShiftTemplate, UserUnavailability
from schedules.utils.unavailability import (
    WEEKDAYS,
    blocked_shift_count,
    prefill_user,
)

WeekdayEnum = graphene.Enum.from_enum(ShiftTemplate.Day, name="WeekdayEnum")

WEEKDAY_ORDER = Case(
    *(When(day=day, then=Value(index)) for index, day in enumerate(WEEKDAYS)),
    output_field=IntegerField(),
)


class UserUnavailabilityNode(DjangoObjectType):
    class Meta:
        model = UserUnavailability
        interfaces = (Node,)

    blocked_shift_count = graphene.NonNull(
        graphene.Int,
        description="Shifts in open planning periods of the user's rosters that "
        "the entry blocks",
    )

    def resolve_blocked_shift_count(self: UserUnavailability, info):
        return blocked_shift_count(self, self.user)

    @classmethod
    def get_queryset(cls, queryset, info):
        # Only the user sees their entries. Managers see the pre-filled answers.
        user = info.context.user
        if not user.is_authenticated:
            return queryset.none()
        return queryset.filter(user=user)

    @classmethod
    def get_node(cls, info, id):
        return cls.get_queryset(UserUnavailability.objects, info).get(pk=id)


class UserUnavailabilityQuery(graphene.ObjectType):
    my_unavailabilities = graphene.NonNull(
        graphene.List(graphene.NonNull(UserUnavailabilityNode)),
        description="Monday first",
    )
    unavailability_preview = graphene.NonNull(
        graphene.Int,
        day=WeekdayEnum(required=True),
        time_start=graphene.Time(required=True),
        time_end=graphene.Time(required=True),
        description="The shifts a new entry would block, before it is saved",
    )

    @gql_login_required()
    def resolve_my_unavailabilities(self, info):
        return (
            UserUnavailability.objects.filter(user=info.context.user)
            .annotate(weekday=WEEKDAY_ORDER)
            .order_by("weekday", "time_start")
        )

    @gql_login_required()
    def resolve_unavailability_preview(self, info, day, time_start, time_end):
        entry = UserUnavailability(
            user=info.context.user,
            day=day.value,
            time_start=time_start,
            time_end=time_end,
        )
        return blocked_shift_count(entry, info.context.user)


def check_times(time_start, time_end):
    if time_start == time_end:
        raise IllegalOperation("The start and the end must differ")


def own_entry(info, id):
    entry = UserUnavailability.objects.filter(
        pk=disambiguate_id(id), user=info.context.user
    ).first()
    if entry is None:
        raise IllegalOperation("No such unavailability")
    return entry


class CreateUserUnavailabilityInput(graphene.InputObjectType):
    day = WeekdayEnum(required=True)
    time_start = graphene.Time(required=True)
    time_end = graphene.Time(
        required=True, description="At or before timeStart means the next day"
    )
    note = graphene.String()


class CreateUserUnavailabilityMutation(graphene.Mutation):
    class Arguments:
        input = CreateUserUnavailabilityInput(required=True)

    unavailability = graphene.Field(UserUnavailabilityNode)

    @gql_login_required()
    def mutate(self, info, input):
        check_times(input.time_start, input.time_end)
        entry = UserUnavailability.objects.create(
            user=info.context.user,
            day=input.day.value,
            time_start=input.time_start,
            time_end=input.time_end,
            note=(input.note or "").strip(),
        )
        prefill_user(entry.user_id)
        return CreateUserUnavailabilityMutation(unavailability=entry)


class UpdateUserUnavailabilityInput(graphene.InputObjectType):
    day = WeekdayEnum()
    time_start = graphene.Time()
    time_end = graphene.Time()
    note = graphene.String()


class UpdateUserUnavailabilityMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = UpdateUserUnavailabilityInput(required=True)

    unavailability = graphene.Field(UserUnavailabilityNode)

    @gql_login_required()
    def mutate(self, info, id, input):
        entry = own_entry(info, id)
        if input.get("day") is not None:
            entry.day = input.day.value
        for name in ("time_start", "time_end"):
            if input.get(name) is not None:
                setattr(entry, name, input.get(name))
        if input.get("note") is not None:
            entry.note = input.note.strip()
        check_times(entry.time_start, entry.time_end)
        entry.save()
        prefill_user(entry.user_id)
        return UpdateUserUnavailabilityMutation(unavailability=entry)


class DeleteUserUnavailabilityMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_login_required()
    def mutate(self, info, id):
        own_entry(info, id).delete()
        prefill_user(info.context.user.pk)
        return DeleteUserUnavailabilityMutation(found=True)


class UserUnavailabilityMutations(graphene.ObjectType):
    create_user_unavailability = CreateUserUnavailabilityMutation.Field()
    update_user_unavailability = UpdateUserUnavailabilityMutation.Field()
    delete_user_unavailability = DeleteUserUnavailabilityMutation.Field()
