import datetime

import graphene
import pytz
from django.db.models import Case, When, Value
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)

from common.decorators import gql_has_permissions
from schedules.models import ScheduleTemplate, ShiftTemplate, ShiftSlotTemplate


class ShiftSlotTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotTemplate
        interfaces = (Node,)


class ShiftTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftTemplate
        interfaces = (Node,)

    duration = graphene.String()
    shift_slot_templates = graphene.List(ShiftSlotTemplateNode)

    def resolve_duration(self: ShiftTemplate, info):
        from schedules.utils.templates import shift_template_timestamps_to_datetime

        datetime_start, datetime_end = shift_template_timestamps_to_datetime(
            datetime.date.today(), self
        )
        return datetime_end - datetime_start

    def resolve_shift_slot_templates(self: ShiftTemplate, info):
        return self.shift_slot_templates.all()

    @classmethod
    @gql_has_permissions("schedules.view_shifttemplate")
    def get_node(cls, info, id):
        return ShiftTemplate.objects.get(pk=id)


class ScheduleTemplateNode(DjangoObjectType):
    class Meta:
        model = ScheduleTemplate
        interfaces = (Node,)

    shift_templates = graphene.List(ShiftTemplateNode)

    def resolve_shift_templates(self: ScheduleTemplate, info, *args, **kwargs):
        # Transform each day to a numerical value so we can sort by it
        return self.shift_templates.all().order_by(
            Case(
                When(day=ShiftTemplate.Day.MONDAY, then=Value(0)),
                When(day=ShiftTemplate.Day.TUESDAY, then=Value(1)),
                When(day=ShiftTemplate.Day.WEDNESDAY, then=Value(2)),
                When(day=ShiftTemplate.Day.THURSDAY, then=Value(3)),
                When(day=ShiftTemplate.Day.FRIDAY, then=Value(4)),
                When(day=ShiftTemplate.Day.SATURDAY, then=Value(5)),
                When(day=ShiftTemplate.Day.SUNDAY, then=Value(6)),
            ),
            "location",
            "time_start",
        )

    @classmethod
    @gql_has_permissions("schedules.view_scheduletemplate")
    def get_node(cls, info, id):
        return ScheduleTemplate.objects.get(pk=id)


class ScheduleTemplateQuery(graphene.ObjectType):
    schedule_template = Node.Field(ScheduleTemplateNode)
    all_schedule_templates = graphene.List(ScheduleTemplateNode)

    @gql_has_permissions("schedules.view_scheduletemplate")
    def resolve_all_schedule_templates(self, info, *args, **kwargs):
        return ScheduleTemplate.objects.all().order_by("schedule__name")


class CreateScheduleTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ScheduleTemplate
        permissions = ("schedules.add_scheduletemplate",)


class CreateShiftSlotTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.add_shiftslottemplate",)


class PatchShiftSlotTemplateMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.change_shiftslottemplate",)


class DeleteShiftSlotTemplateMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.delete_shiftslottemplate",)


class CreateShiftTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftTemplate
        permissions = ("schedules.add_shifttemplate",)


class DeleteShiftTemplateMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftTemplate
        permissions = ("schedules.delete_shifttemplate",)


class ScheduleTemplateMutations(graphene.ObjectType):
    create_schedule_template = CreateScheduleTemplateMutation.Field()

    create_shift_slot_template = CreateShiftSlotTemplateMutation.Field()
    patch_shift_slot_template = PatchShiftSlotTemplateMutation.Field()
    delete_shift_slot_template = DeleteShiftSlotTemplateMutation.Field()

    create_shift_template = CreateShiftTemplateMutation.Field()
    delete_shift_template = DeleteShiftTemplateMutation.Field()
