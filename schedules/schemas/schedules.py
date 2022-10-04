import graphene
import pytz
from graphene import Node
from graphene_django import DjangoObjectType
import datetime
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions
from schedules.models import (
    Schedule,
    Shift,
    ShiftTrade,
    ShiftSlot,
)
from schedules.utils.schedules import normalize_shifts
from schedules.utils.templates import apply_schedule_template
from users.models import User
from django.utils import timezone
from django.conf import settings


class ShiftSlotNode(DjangoObjectType):
    class Meta:
        model = ShiftSlot
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlot.objects.get(pk=id)


class ShiftNode(DjangoObjectType):
    class Meta:
        model = Shift
        interfaces = (Node,)

    users = graphene.NonNull(graphene.List(graphene.NonNull("users.schema.UserNode")))
    is_filled = graphene.Boolean(source="is_filled")
    slots = graphene.NonNull(graphene.List(graphene.NonNull(ShiftSlotNode)))
    filled_slots = graphene.NonNull(graphene.List(graphene.NonNull(ShiftSlotNode)))

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


class ScheduleNode(DjangoObjectType):
    class Meta:
        model = Schedule
        interfaces = (Node,)

    shifts_from_range = graphene.List(
        ShiftNode, shifts_from=graphene.Date(), number_of_weeks=graphene.Int()
    )

    def resolve_shifts_from_range(self: Schedule, info, shifts_from, number_of_weeks):
        return self.shifts_from_range(shifts_from, number_of_weeks)

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


class ScheduleQuery(graphene.ObjectType):
    schedule = Node.Field(ScheduleNode)
    all_schedules = graphene.NonNull(graphene.List(ScheduleNode, required=True))

    def resolve_all_schedules(self, info, *args, **kwargs):
        return Schedule.objects.all().order_by("name")


# === Single location grouping types ===
class ShiftDayGroup(graphene.ObjectType):
    date = graphene.Date()
    shifts = graphene.List(ShiftNode)


class ShiftDayWeek(graphene.ObjectType):
    shift_days = graphene.List(ShiftDayGroup)
    date = graphene.Date()


# === Location grouping types ===
class ShiftLocationDayGroup(graphene.ObjectType):
    location = graphene.String()
    shifts = graphene.List(ShiftNode)


class ShiftLocationDay(graphene.ObjectType):
    locations = graphene.List(ShiftLocationDayGroup)
    date = graphene.Date()


class ShiftLocationWeek(graphene.ObjectType):
    date = graphene.Date()
    shift_days = graphene.List(ShiftLocationDay)


class ShiftGroupWeeksUnion(graphene.Union):
    class Meta:
        types = (ShiftLocationWeek, ShiftDayWeek)


class ShiftQuery(graphene.ObjectType):
    all_shifts = graphene.List(
        ShiftNode,
        date_from=graphene.Date(required=True),
        date_to=graphene.Date(required=True),
    )

    all_my_shifts = graphene.List(ShiftNode)
    my_upcoming_shifts = graphene.List(ShiftNode)

    normalized_shifts_from_range = graphene.List(
        ShiftGroupWeeksUnion,
        schedule_id=graphene.ID(required=True),
        shifts_from=graphene.Date(),
        number_of_weeks=graphene.Int(),
    )

    def resolve_normalized_shifts_from_range(
        self, info, schedule_id, shifts_from, number_of_weeks
    ):
        schedule_id = disambiguate_id(schedule_id)
        schedule = Schedule.objects.get(pk=schedule_id)
        shifts = schedule.shifts_from_range(shifts_from, number_of_weeks)
        return normalize_shifts(shifts, schedule.display_mode)

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


# === MUTATIONS ===
class CreateShiftMutation(DjangoCreateMutation):
    class Meta:
        model = Shift
        exclude_fields = ("filled_by", "created_by")
        auto_context_fields = {"created_by": "user"}
        permissions = ("schedules.add_shift",)


class CreateShiftsFromTemplateMutation(graphene.Mutation):
    class Arguments:
        schedule_template_id = graphene.ID(required=True)
        apply_from = graphene.Date(required=True)
        number_of_weeks = graphene.Int(required=True)

    shifts_created = graphene.Int()

    @gql_has_permissions("schedules.add_shift")
    def mutate(self, info, schedule_template_id, apply_from, number_of_weeks):
        schedule_template = Schedule.objects.get(pk=schedule_template_id)
        shifts_created = apply_schedule_template(
            schedule_template, apply_from, number_of_weeks
        )
        return CreateShiftsFromTemplateMutation(shifts_created=shifts_created)


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


class GenerateMutation(graphene.Mutation):
    class Arguments:
        schedule_template_id = graphene.ID(required=True)
        start_date = graphene.Date(required=True)
        number_of_weeks = graphene.Int(required=True)

    shifts_created = graphene.Int()

    def mutate(self, info, schedule_template_id, start_date, number_of_weeks):
        from schedules.schemas.templates import ScheduleTemplate

        schedule_template_id = disambiguate_id(schedule_template_id)
        schedule_template = ScheduleTemplate.objects.get(pk=schedule_template_id)
        count = apply_schedule_template(schedule_template, start_date, number_of_weeks)
        return GenerateMutation(shifts_created=count)


class SchedulesMutations(graphene.ObjectType):
    create_shift = CreateShiftMutation.Field()
    delete_shift = DeleteShiftMutation.Field()
    patch_shift = PatchShiftMutation.Field()

    create_schedule = CreateScheduleMutation.Field()
    patch_schedule = PatchScheduleMutation.Field()
    delete_schedule = DeleteScheduleMutation.Field()

    generate = GenerateMutation.Field()
