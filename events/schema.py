import graphene
from graphene import Node
from graphene_django import DjangoObjectType, DjangoConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)

from events.models import Event


class EventNode(DjangoObjectType):
    class Meta:
        model = Event
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Event.objects.get(pk=id)


class EventQuery(graphene.ObjectType):
    event = Node.Field(EventNode)
    all_events = DjangoConnectionField(EventNode)

    def resolve_all_events(self, info, *args, **kwargs):
        return Event.objects.all().order_by("-date")


class CreateEventMutation(DjangoCreateMutation):
    class Meta:
        model = Event


class PatchEventMutation(DjangoPatchMutation):
    class Meta:
        model = Event


class DeleteEventMutation(DjangoDeleteMutation):
    class Meta:
        model = Event


class EventMutations(graphene.ObjectType):
    create_event = CreateEventMutation.Field()
    patch_event = PatchEventMutation.Field()
    delete_event = DeleteEventMutation.Field()
