import graphene
import pytz
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from schedules.models import (
    Schedule,
    Shift,
    ShiftTrade,
    ShiftSlot,
)
from users.models import User
from django.utils import timezone
from django.conf import settings


class RequiredRole(graphene.ObjectType):
    name = graphene.NonNull(graphene.String)
    amount = graphene.NonNull(graphene.Int)


class RequiredRoleInput(graphene.InputObjectType):
    name = graphene.NonNull(graphene.String)
    amount = graphene.NonNull(graphene.Int)


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


class ShiftSlotNode(DjangoObjectType):
    class Meta:
        model = ShiftSlot
        interfaces = (Node,)

    role_display = graphene.String()

    def get_role_display(self):
        return self.get_role_display()

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlot.objects.get(pk=id)


class ShiftNode(DjangoObjectType):
    class Meta:
        model = Shift
        interfaces = (Node,)

    users = graphene.NonNull(graphene.List(graphene.NonNull("users.schema.UserNode")))
    is_filled = graphene.Boolean(source="is_filled")
    required_roles = graphene.List(RequiredRole)
    slots = graphene.NonNull(graphene.List(graphene.NonNull(ShiftSlotNode)))
    filled_slots = graphene.NonNull(graphene.List(graphene.NonNull(ShiftSlotNode)))
    location_display = graphene.String()

    def resolve_location_display(self: Shift, info):
        return self.get_location_display()

    def resolve_users(self, info):
        shift_slots = ShiftSlot.objects.filter(shift=self)
        users = User.objects.filter(filled_shifts__in=shift_slots)
        return users

    def resolve_slots(self: Shift, info):
        return self.slots.all()

    def resolve_filled_slots(self: Shift, info):
        return self.slots.filter(user__isnull=False)

    @classmethod
    def get_node(cls, info, id):
        return Shift.objects.get(pk=id)


class ScheduleQuery(graphene.ObjectType):
    schedule = Node.Field(ScheduleNode)
    all_schedules = graphene.NonNull(graphene.List(ScheduleNode, required=True))

    def resolve_all_schedules(self, info, *args, **kwargs):
        return Schedule.objects.all().order_by("name")


class ShiftQuery(graphene.ObjectType):
    all_shifts = graphene.List(
        ShiftNode,
        date_from=graphene.Date(required=True),
        date_to=graphene.Date(required=True),
    )

    all_my_shifts = graphene.List(ShiftNode)

    my_upcoming_shifts = graphene.List(ShiftNode)

    def resolve_my_upcoming_shifts(self, info, *args, **kwargs):
        me = info.context.user
        return Shift.objects.filter(
            datetime_end__gt=timezone.now(),
            slots__user=me,
        ).order_by("-datetime_start")

    def resolve_all_my_shifts(self, info, *args, **kwargs):
        me = info.context.user
        return Shift.objects.filter(slots__user=me).order_by("-datetime_start")

    def resolve_all_shifts(self, info, date_from, date_to, *args, **kwargs):
        datetime_from = timezone.datetime(
            date_from.year,
            date_from.month,
            date_from.day,
            0,
            0,
            0,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        datetime_to = timezone.datetime(
            date_to.year,
            date_to.month,
            date_to.day,
            23,
            59,
            59,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        return Shift.objects.filter(
            datetime_start__gt=datetime_from, datetime_end__lt=datetime_to
        ).order_by("-datetime_start")


class CreateShiftMutation(DjangoCreateMutation):
    class Meta:
        model = Shift
        exclude_fields = ("filled_by", "created_by")
        auto_context_fields = {"created_by": "user"}

    field_types = {"required_roles": graphene.List(RequiredRoleInput)}

    @classmethod
    def before_mutate(cls, root, info, input):
        return input

    @classmethod
    def handle_required_roles(cls, value):
        return value


# === MUTATIONS ===
class PatchShiftMutation(DjangoPatchMutation):
    class Meta:
        model = Shift


class DeleteShiftMutation(DjangoDeleteMutation):
    class Meta:
        model = Shift


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
    create_shift = CreateShiftMutation.Field()
    delete_shift = DeleteShiftMutation.Field()
    patch_shift = PatchShiftMutation.Field()

    create_schedule = CreateScheduleMutation.Field()
    patch_schedule = PatchScheduleMutation.Field()
    delete_schedule = DeleteScheduleMutation.Field()
