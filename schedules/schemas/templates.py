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
from schedules.models import ScheduleTemplate, ShiftTemplate


class ShiftTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftTemplate
        interfaces = (Node,)

    duration = graphene.String()

    def resolve_duration(self: ShiftTemplate, info):
        from schedules.utils.templates import shift_template_timestamps_to_datetime

        datetime_start, datetime_end = shift_template_timestamps_to_datetime(
            datetime.date.today(), self
        )
        return datetime_end - datetime_start

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


class ScheduleTemplateMutations(graphene.ObjectType):
    pass
