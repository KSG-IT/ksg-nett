import graphene
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions
from common.exceptions import IllegalOperation
from organization.graphql import InternalGroupPositionTypeEnum
from organization.models import InternalGroupPosition
from schedules.models import (
    DefaultAvailability,
    Schedule,
    ScheduleRoster,
    ScheduleRosterGrouping,
)
from schedules.permissions import managed_schedules, require_can_manage_schedule
from schedules.schemas.schedules import ShiftSlotRoleEnum
from schedules.utils.roster import annotate_shift_counts, apply_roster_sync
from users.models import User

MANAGE = "schedules.change_schedule"

DefaultAvailabilityEnum = graphene.Enum.from_enum(DefaultAvailability)


class ScheduleRosterGroupingNode(DjangoObjectType):
    class Meta:
        model = ScheduleRosterGrouping
        interfaces = (Node,)

    @classmethod
    def get_queryset(cls, queryset, info):
        # The rules are for the managers of the schedule only
        return queryset.filter(
            schedule__in=managed_schedules(info.context.user, MANAGE)
        )

    @classmethod
    def get_node(cls, info, id):
        return cls.get_queryset(ScheduleRosterGrouping.objects, info).get(pk=id)


class ScheduleRosterNode(DjangoObjectType):
    class Meta:
        model = ScheduleRoster
        interfaces = (Node,)

    membership_type = graphene.String(
        description="The type of the user's active membership in the schedule's group"
    )
    shifts_done = graphene.NonNull(graphene.Int)
    shifts_planned = graphene.NonNull(graphene.Int)
    last_shift = graphene.DateTime()

    @classmethod
    def get_queryset(cls, queryset, info):
        # Managers see the roster of their schedules, other users their own row
        user = info.context.user
        if not user.is_authenticated:
            return queryset.none()
        return queryset.filter(
            Q(schedule__in=managed_schedules(user, MANAGE)) | Q(user=user)
        )

    @classmethod
    def get_node(cls, info, id):
        return cls.get_queryset(ScheduleRoster.objects, info).get(pk=id)

    def _counted(self):
        # Rows from ScheduleNode.roster have the counts. Others get them here.
        if not hasattr(self, "shifts_done"):
            counted = annotate_shift_counts(
                ScheduleRoster.objects.filter(pk=self.pk)
            ).get()
            for name in ("shifts_done", "shifts_planned", "last_shift"):
                setattr(self, name, getattr(counted, name))
            self.membership_type = counted.membership_type
        return self

    def resolve_membership_type(self, info):
        return ScheduleRosterNode._counted(self).membership_type

    def resolve_shifts_done(self, info):
        return ScheduleRosterNode._counted(self).shifts_done

    def resolve_shifts_planned(self, info):
        return ScheduleRosterNode._counted(self).shifts_planned

    def resolve_last_shift(self, info):
        return ScheduleRosterNode._counted(self).last_shift


class RosterChangeNode(graphene.ObjectType):
    kind = graphene.NonNull(graphene.String)
    user = graphene.NonNull("users.schema.UserNode")
    entry = graphene.Field(ScheduleRosterNode)
    grouping = graphene.Field(ScheduleRosterGroupingNode)
    autofill_as = graphene.Field(ShiftSlotRoleEnum)
    default_availability = graphene.Field(DefaultAvailabilityEnum)
    shift_cap = graphene.Int()
    count_from = graphene.Date()
    message = graphene.String()


def schedule_for_manager(info, schedule_id):
    schedule = Schedule.objects.get(pk=disambiguate_id(schedule_id))
    require_can_manage_schedule(info.context.user, schedule, MANAGE)
    return schedule


def check_position(schedule, position):
    if (
        schedule.internal_group_id
        and position.internal_group_id != schedule.internal_group_id
    ):
        raise IllegalOperation("The position is not in the schedule's internal group")


class CreateScheduleRosterGroupingInput(graphene.InputObjectType):
    schedule_id = graphene.ID(required=True)
    internal_group_position_id = graphene.ID(required=True)
    position_type = InternalGroupPositionTypeEnum(required=True)
    role = ShiftSlotRoleEnum(required=True)
    default_availability = DefaultAvailabilityEnum(required=True)
    shift_cap = graphene.Int()


class CreateScheduleRosterGroupingMutation(graphene.Mutation):
    class Arguments:
        input = CreateScheduleRosterGroupingInput(required=True)

    grouping = graphene.Field(ScheduleRosterGroupingNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, input):
        schedule = schedule_for_manager(info, input.schedule_id)
        position = InternalGroupPosition.objects.get(
            pk=disambiguate_id(input.internal_group_position_id)
        )
        check_position(schedule, position)
        try:
            grouping = ScheduleRosterGrouping.objects.create(
                schedule=schedule,
                internal_group_position=position,
                position_type=input.position_type.value,
                role=input.role.value,
                default_availability=input.default_availability.value,
                shift_cap=input.shift_cap,
            )
        except IntegrityError:
            raise IllegalOperation("A rule for this position and type exists")
        return CreateScheduleRosterGroupingMutation(grouping=grouping)


class PatchScheduleRosterGroupingInput(graphene.InputObjectType):
    role = ShiftSlotRoleEnum()
    default_availability = DefaultAvailabilityEnum()
    shift_cap = graphene.Int(description="Null removes the cap")


class PatchScheduleRosterGroupingMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = PatchScheduleRosterGroupingInput(required=True)

    grouping = graphene.Field(ScheduleRosterGroupingNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id, input):
        grouping = ScheduleRosterGrouping.objects.get(pk=disambiguate_id(id))
        require_can_manage_schedule(info.context.user, grouping.schedule, MANAGE)
        if input.get("role") is not None:
            grouping.role = input.role.value
        if input.get("default_availability") is not None:
            grouping.default_availability = input.default_availability.value
        if "shift_cap" in input:
            grouping.shift_cap = input.shift_cap
        grouping.save()
        return PatchScheduleRosterGroupingMutation(grouping=grouping)


class DeleteScheduleRosterGroupingMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id):
        grouping = ScheduleRosterGrouping.objects.filter(pk=disambiguate_id(id)).first()
        if grouping is None:
            return DeleteScheduleRosterGroupingMutation(found=False)
        require_can_manage_schedule(info.context.user, grouping.schedule, MANAGE)
        grouping.delete()
        return DeleteScheduleRosterGroupingMutation(found=True)


class SyncScheduleRosterMutation(graphene.Mutation):
    """Applies the changes that ScheduleNode.rosterSyncPreview lists."""

    class Arguments:
        schedule_id = graphene.ID(required=True)

    changes = graphene.NonNull(graphene.List(graphene.NonNull(RosterChangeNode)))

    @gql_has_permissions(MANAGE)
    def mutate(self, info, schedule_id):
        schedule = schedule_for_manager(info, schedule_id)
        return SyncScheduleRosterMutation(changes=apply_roster_sync(schedule))


class AddScheduleRosterEntryInput(graphene.InputObjectType):
    schedule_id = graphene.ID(required=True)
    user_id = graphene.ID(required=True)
    autofill_as = ShiftSlotRoleEnum(required=True)
    default_availability = DefaultAvailabilityEnum(required=True)
    shift_cap = graphene.Int()


class AddScheduleRosterEntryMutation(graphene.Mutation):
    """Adds a user by hand. The sync removes the row only when the user leaves."""

    class Arguments:
        input = AddScheduleRosterEntryInput(required=True)

    entry = graphene.Field(ScheduleRosterNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, input):
        schedule = schedule_for_manager(info, input.schedule_id)
        user = User.objects.get(pk=disambiguate_id(input.user_id))
        try:
            entry = ScheduleRoster.objects.create(
                schedule=schedule,
                user=user,
                autofill_as=input.autofill_as.value,
                default_availability=input.default_availability.value,
                shift_cap=input.shift_cap,
                added_manually=True,
                manually_edited=True,
                count_from=timezone.localdate(),
            )
        except IntegrityError:
            raise IllegalOperation("The user is on the roster")
        return AddScheduleRosterEntryMutation(entry=entry)


class UpdateScheduleRosterEntryInput(graphene.InputObjectType):
    autofill_as = ShiftSlotRoleEnum()
    default_availability = DefaultAvailabilityEnum()
    shift_cap = graphene.Int(description="Null removes the cap")


class UpdateScheduleRosterEntryMutation(graphene.Mutation):
    """Changes a row. The sync does not change the values of the row after this."""

    class Arguments:
        id = graphene.ID(required=True)
        input = UpdateScheduleRosterEntryInput(required=True)

    entry = graphene.Field(ScheduleRosterNode)

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id, input):
        entry = ScheduleRoster.objects.get(pk=disambiguate_id(id))
        require_can_manage_schedule(info.context.user, entry.schedule, MANAGE)
        if input.get("autofill_as") is not None:
            entry.autofill_as = input.autofill_as.value
        if input.get("default_availability") is not None:
            entry.default_availability = input.default_availability.value
        if "shift_cap" in input:
            entry.shift_cap = input.shift_cap
        entry.manually_edited = True
        entry.save()
        return UpdateScheduleRosterEntryMutation(entry=entry)


class RemoveScheduleRosterEntryMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_has_permissions(MANAGE)
    def mutate(self, info, id):
        entry = ScheduleRoster.objects.filter(pk=disambiguate_id(id)).first()
        if entry is None:
            return RemoveScheduleRosterEntryMutation(found=False)
        require_can_manage_schedule(info.context.user, entry.schedule, MANAGE)
        entry.delete()
        return RemoveScheduleRosterEntryMutation(found=True)


class ScheduleRosterMutations(graphene.ObjectType):
    create_schedule_roster_grouping = CreateScheduleRosterGroupingMutation.Field()
    patch_schedule_roster_grouping = PatchScheduleRosterGroupingMutation.Field()
    delete_schedule_roster_grouping = DeleteScheduleRosterGroupingMutation.Field()
    sync_schedule_roster = SyncScheduleRosterMutation.Field()
    add_schedule_roster_entry = AddScheduleRosterEntryMutation.Field()
    update_schedule_roster_entry = UpdateScheduleRosterEntryMutation.Field()
    remove_schedule_roster_entry = RemoveScheduleRosterEntryMutation.Field()
