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
    pass


class ScheduleTemplateMutations(graphene.ObjectType):
    pass
