import graphene
import pytz
from django.db import transaction
from graphene import Node
from graphene_django import DjangoObjectType
import datetime
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions, gql_login_required
from schedules.models import (
    Schedule,
    Shift,
    ShiftTrade,
    ShiftSlot,
    RoleOption,
    ShiftInterest,
)
from schedules.utils.schedules import normalize_shifts, send_given_shift_email
from schedules.utils.templates import apply_schedule_template
from users.models import User
from django.utils import timezone
from django.conf import settings


class ShiftInterestNode(DjangoObjectType):
    class Meta:
        model = ShiftInterest
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftInterest.objects.get(pk=id)


class ShiftSlotNode(DjangoObjectType):
    class Meta:
        model = ShiftSlot
        interfaces = (Node,)

    role_display = graphene.String()

    def resolve_role_display(self, info):
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
    @gql_login_required()
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
    shift = Node.Field(ShiftNode)
    all_shifts = graphene.List(
        ShiftNode,
        date=graphene.Date(required=True),
    )
    all_my_shifts = graphene.List(ShiftNode)
    my_upcoming_shifts = graphene.List(ShiftNode)
    normalized_shifts_from_range = graphene.List(
        ShiftGroupWeeksUnion,
        schedule_id=graphene.ID(required=True),
        shifts_from=graphene.Date(),
        number_of_weeks=graphene.Int(),
    )
    all_users_working_today = graphene.List("users.schema.UserNode")

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

    def resolve_all_shifts(self, info, date, *args, **kwargs):
        datetime_from = timezone.datetime(
            date.year,
            date.month,
            date.day,
            0,
            0,
            0,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        datetime_to = timezone.datetime(
            date.year,
            date.month,
            date.day,
            23,
            59,
            59,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        return Shift.objects.filter(
            datetime_start__gt=datetime_from, datetime_start__lt=datetime_to
        ).order_by("datetime_start")

    def resolve_all_users_working_today(self, info, *args, **kwargs):
        date = datetime.date.today()
        datetime_from = timezone.datetime(
            date.year,
            date.month,
            date.day,
            0,
            0,
            0,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        datetime_to = timezone.datetime(
            date.year,
            date.month,
            date.day,
            23,
            59,
            59,
            tzinfo=pytz.timezone(settings.TIME_ZONE),
        )
        return User.objects.filter(
            filled_shifts__shift__datetime_start__gt=datetime_from,
            filled_shifts__shift__datetime_start__lt=datetime_to,
        ).order_by("first_name", "last_name")


# === MUTATIONS ===
class CreateShiftMutation(DjangoCreateMutation):
    class Meta:
        model = Shift
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
        permissions = ("schedules.change_shift",)


class DeleteShiftMutation(DjangoDeleteMutation):
    class Meta:
        model = Shift
        permissions = ("schedules.delete_shift",)


class CreateScheduleMutation(DjangoCreateMutation):
    class Meta:
        model = Schedule
        permissions = ("schedules.add_schedule",)


class PatchScheduleMutation(DjangoPatchMutation):
    class Meta:
        model = Schedule
        permissions = ("schedules.change_schedule",)


class DeleteScheduleMutation(DjangoDeleteMutation):
    class Meta:
        model = Schedule
        permissions = ("schedules.delete_schedule",)


class CreateShiftTradeMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftTrade


class PatchShiftTradeMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftTrade


class DeleteShiftTradeMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftTrade


class GenerateShiftsFromTemplateMutation(graphene.Mutation):
    class Arguments:
        schedule_template_id = graphene.ID(required=True)
        start_date = graphene.Date(required=True)
        number_of_weeks = graphene.Int(required=True)

    shifts_created = graphene.Int()

    @gql_has_permissions("schedules.add_shift")
    def mutate(self, info, schedule_template_id, start_date, number_of_weeks):
        from schedules.schemas.templates import ScheduleTemplate

        schedule_template_id = disambiguate_id(schedule_template_id)
        schedule_template = ScheduleTemplate.objects.get(pk=schedule_template_id)
        count = apply_schedule_template(schedule_template, start_date, number_of_weeks)
        return GenerateShiftsFromTemplateMutation(shifts_created=count)


class RemoveUserFromShiftSlotMutation(graphene.Mutation):
    class Arguments:
        shift_slot_id = graphene.ID(required=True)

    shift_slot = graphene.Field(ShiftSlotNode)

    @gql_has_permissions("schedules.change_shiftslot")
    def mutate(self, info, shift_slot_id, *args, **kwargs):
        shift_slot_id = disambiguate_id(shift_slot_id)
        shift_slot = ShiftSlot.objects.get(pk=shift_slot_id)
        shift_slot.user = None
        shift_slot.save()
        return RemoveUserFromShiftSlotMutation(shift_slot=shift_slot)


class AddUserToShiftSlotMutation(graphene.Mutation):
    class Arguments:
        shift_slot_id = graphene.ID(required=True)
        user_id = graphene.ID(required=True)

    shift_slot = graphene.Field(ShiftSlotNode)

    @gql_has_permissions("schedules.change_shiftslot")
    def mutate(self, info, shift_slot_id, user_id):
        shift_slot_id = disambiguate_id(shift_slot_id)
        user_id = disambiguate_id(user_id)
        with transaction.atomic():
            shift_slot = ShiftSlot.objects.get(pk=shift_slot_id)
            user = User.objects.get(pk=user_id)
            shift_slot.user = user
            if user.notify_on_shift:
                send_given_shift_email(shift_slot)
            shift_slot.save()
        return AddUserToShiftSlotMutation(shift_slot=shift_slot)


class CreateShiftSlotMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlot
        permissions = ("schedules.add_shiftslot",)


class DeleteShiftSlotMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlot
        permissions = ("schedules.delete_shiftslot",)


class ShiftSlotRoleEnum(graphene.Enum):
    BARISTA = RoleOption.BARISTA
    KAFEANSVARLIG = RoleOption.KAFEANSVARLIG
    BARSERVITOR = RoleOption.BARSERVITOR
    HOVMESTER = RoleOption.HOVMESTER
    KOKK = RoleOption.KOKK
    SOUSCHEF = RoleOption.SOUSCHEF
    ARRANGEMENTBARTENDER = RoleOption.ARRANGEMENTBARTENDER
    ARRANGEMENTANSVARLIG = RoleOption.ARRANGEMENTANSVARLIG
    BRYGGER = RoleOption.BRYGGER
    BARTENDER = RoleOption.BARTENDER
    BARSJEF = RoleOption.BARSJEF
    SPRITBARTENDER = RoleOption.SPRITBARTENDER
    SPRITBARSJEF = RoleOption.SPRITBARSJEF
    UGLE = RoleOption.UGLE
    BRANNVAKT = RoleOption.BRANNVAKT
    RYDDEVAKT = RoleOption.RYDDEVAKT
    BAEREVAKT = RoleOption.BAEREVAKT
    SOCIVAKT = RoleOption.SOCIVAKT


class AddSlotToShiftInput(graphene.InputObjectType):
    shift_slot_role = ShiftSlotRoleEnum(required=True)
    count = graphene.Int(required=True)


class AddSlotsToShiftMutation(graphene.Mutation):
    class Arguments:
        shift_id = graphene.ID(required=True)
        slots = graphene.List(AddSlotToShiftInput, required=True)

    shift = graphene.Field(ShiftNode)

    @gql_has_permissions("schedules.add_shiftslot")
    def mutate(self, info, shift_id, slots):
        shift_id = disambiguate_id(shift_id)
        shift = Shift.objects.get(pk=shift_id)
        for slot in slots:
            for i in range(slot.count):
                ShiftSlot.objects.create(shift=shift, role=slot.shift_slot_role.value)
        return AddSlotsToShiftMutation(shift=shift)


class AutofillShiftSlotsMutation(graphene.Mutation):
    class Arguments:
        schedule_id = graphene.ID(required=True)
        from_date = graphene.Date(required=True)
        to_date = graphene.Date(required=True)

    success = graphene.Boolean()

    @gql_has_permissions("schedules.change_shiftslot")
    def mutate(self, info, schedule_id, from_date, to_date):
        today = timezone.now().date()

        if from_date < today:
            raise ValueError("From date must be in the future")

        if to_date < today:
            raise ValueError("To date must be in the future")

        if to_date < from_date:
            raise ValueError("To date must be after from date")

        schedule_id = disambiguate_id(schedule_id)
        schedule = Schedule.objects.get(pk=schedule_id)
        schedule.autofill_slots(from_date, to_date)
        return AutofillShiftSlotsMutation(success=True)


class CreateShiftInterestMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftInterest
        auto_context_field = {"user": "user"}


class DeleteShiftInterestMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftInterest


class MyShiftAvailabilityObject(graphene.ObjectType):
    shift = graphene.NonNull(graphene.Field(ShiftNode))
    shift_interest = graphene.Field(ShiftInterestNode)


class SchedulesMutations(graphene.ObjectType):
    create_shift = CreateShiftMutation.Field()
    delete_shift = DeleteShiftMutation.Field()
    patch_shift = PatchShiftMutation.Field()

    create_schedule = CreateScheduleMutation.Field()
    patch_schedule = PatchScheduleMutation.Field()
    delete_schedule = DeleteScheduleMutation.Field()

    generate_shifts_from_template = GenerateShiftsFromTemplateMutation.Field()
    add_user_to_shift_slot = AddUserToShiftSlotMutation.Field()
    remove_user_from_shift_slot = RemoveUserFromShiftSlotMutation.Field()
    create_shift_slot = CreateShiftSlotMutation.Field()
    delete_shift_slot = DeleteShiftSlotMutation.Field()
    add_slots_to_shift = AddSlotsToShiftMutation.Field()

    create_shift_interest = CreateShiftInterestMutation.Field()
    autofill_shift_slots = AutofillShiftSlotsMutation.Field()
