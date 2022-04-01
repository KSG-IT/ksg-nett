# This schedule deals with all models pertaining to actual shift management and nothing
# automated through templates

import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from schedules.models import (
    Schedule,
    Shift,
    ShiftTrade,
    UserShift,
)
from users.models import User
from users.schema import UserNode
from datetime import datetime


class RequiredRole(graphene.ObjectType):
    name = graphene.NonNull(graphene.String)
    amount = graphene.NonNull(graphene.Int)


class RequiredRoleInput(graphene.InputObjectType):
    name = graphene.NonNull(graphene.String)
    amount = graphene.NonNull(graphene.Int)


class ShiftNode(DjangoObjectType):
    users = graphene.NonNull(graphene.List(graphene.NonNull(UserNode)))  # [UserNode!]!
    is_filled = graphene.Boolean(source="is_filled")
    required_roles = graphene.List(RequiredRole)

    class Meta:
        model = Shift
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Schedule.objects.get(pk=id)

    def resolve_users(self, info):
        shifts = UserShift.objects.filter(shift=self)
        users = User.objects.filter(shifts__in=shifts)
        return users


class CreateNewShiftMutation(DjangoCreateMutation):
    class Meta:
        model = Shift
        exclude_fields = ('filled_by', 'created_by')
        auto_context_fields = {'created_by' : 'user'}


    field_types = {
        "required_roles": graphene.List(RequiredRoleInput)
    }


    @classmethod
    def before_mutate(cls, root, info, input):
        print(input)
        return input
    
    @classmethod
    def handle_required_roles(cls, value):
        return value



class UpdateNewShiftMutation(DjangoPatchMutation):
    class Meta:
        model = Shift
        exclude_fields = ('filled_by',)
        field_types = {
            "required_roles": graphene.List(RequiredRoleInput)
        }

        @classmethod
        def handle_required_roles(cls, value):
            return value


class DeleteNewShiftMutation(DjangoDeleteMutation):
    class Meta:
        model = Shift
        exclude_fields = ('filled_by',)


# class AddUserToShiftMutation(graphene.Mutation):
#    class Arguments:
#        user = graphene.ID(required=True)
#        shift = graphene.ID(required=True)
#    add_user_to_shift = NewShiftNode


class ScheduleNode(DjangoObjectType):
    class Meta:
        model = Schedule
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Schedule.objects.get(pk=id)


class ShiftTradeNode(DjangoObjectType):
    class Meta:
        model = ShiftTrade
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftTrade.objects.get(pk=id)


# QUERIES

class ScheduleQuery(graphene.ObjectType):
    schedule = Node.Field(ScheduleNode)
    all_schedules = graphene.NonNull(graphene.List(ScheduleNode, required=True)) # [Schedule!]!
    all_shifts = graphene.NonNull(graphene.List(ShiftNode, required=True))  # [NewShift!]!
    upcoming_shifts = graphene.NonNull(graphene.List(ShiftNode, required=True))  # [NewShift!]!

    def resolve_all_schedules(self, info, *args, **kwargs):
        return Schedule.objects.all()

    def resolve_all_shifts(self, info, *args, **kwargs):
        shifts = Shift.objects.filter(filled_by__user=info.context.user)
        return shifts

    def resolve_upcoming_shifts(self, info):
        today = datetime.today().date()
        shifts = Shift.objects.filter(start__gte=today, filled_by__user=info.context.user)
        return shifts


class ShiftQuery(graphene.ObjectType):
    pass


# MUTATIONS


class CreateScheduleMutation(DjangoCreateMutation):
    class Meta:
        model = Schedule


class PatchScheduleMutation(DjangoPatchMutation):
    class Meta:
        model = Schedule


class DeleteScheduleMutation(DjangoDeleteMutation):
    class Meta:
        model = Schedule


class CreateShiftTradeMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftTrade


class PatchShiftTradeMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftTrade


class DeleteShiftTradeMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftTrade


class SchedulesMutations(graphene.ObjectType):
    create_new_shift = CreateNewShiftMutation.Field()
    delete_new_shift = DeleteNewShiftMutation.Field()
    update_new_shift = UpdateNewShiftMutation.Field()

    create_schedule = CreateScheduleMutation.Field()
    patch_schedule = PatchScheduleMutation.Field()
    delete_schedule = DeleteScheduleMutation.Field()
