import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django.filter import DjangoFilterConnectionField

from summaries.models import Summary
from users.schema import UserNode
from summaries.filters import SummaryFilter


class SummaryNode(DjangoObjectType):
    class Meta:
        model = Summary
        interfaces = (Node,)

    participants = graphene.List(UserNode)
    type = graphene.String()

    def resolve_summary_type(self: Summary, info, *args, **kwargs):
        return self.get_type_display()

    @classmethod
    def get_node(cls, info, id):
        return Summary.objects.get(pk=id)

    def resolve_participants(self: Summary, info, *args, **kwargs):
        return self.participants.all()


class SummaryQuery(graphene.ObjectType):
    summary = Node.Field(SummaryNode)
    all_summaries = DjangoFilterConnectionField(
        SummaryNode, filterset_class=SummaryFilter
    )

    def resolve_all_summaries(self, info, *args, **kwargs):
        return Summary.objects.all().order_by("-date")


class CreateSummaryMutation(DjangoCreateMutation):
    class Meta:
        model = Summary


class PatchSummaryMutation(DjangoPatchMutation):
    class Meta:
        model = Summary


class DeleteSummaryMutation(DjangoDeleteMutation):
    class Meta:
        model = Summary


class SummariesMutations(graphene.ObjectType):
    create_summary = CreateSummaryMutation.Field()
    patch_summary = PatchSummaryMutation.Field()
    delete_summary = DeleteSummaryMutation.Field()
