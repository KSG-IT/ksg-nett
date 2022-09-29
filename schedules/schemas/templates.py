import graphene
import pytz
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)

from common.decorators import gql_has_permissions
from schedules.models import (
    ScheduleTemplate,
    ShiftTemplate,
)
from users.models import User
from django.utils import timezone
from django.conf import settings


class ScheduleTemplateNode(DjangoObjectType):
    class Meta:
        model = ScheduleTemplate
        interfaces = (Node,)


class ScheduleTemplateQuery(graphene.ObjectType):
    all_schedule_templates = graphene.List(ScheduleTemplateNode)

    @gql_has_permissions("schedules.view_scheduletemplate")
    def resolve_all_schedule_templates(self, info, *args, **kwargs):
        return ScheduleTemplate.objects.all().order_by("schedule__name")


class ScheduleTemplateMutations(graphene.ObjectType):
    pass
