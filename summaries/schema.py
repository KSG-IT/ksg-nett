import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField

from summaries.models import Summary


class SummaryNode(DjangoObjectType):
    class Meta:
        model = Summary
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Summary.objects.get(pk=id)


class SummaryQuery(graphene.ObjectType):
    summary = Node.Field(SummaryNode)
    all_summaries = DjangoConnectionField(SummaryNode)

    def resolve_all_summaries(self, info, *args, **kwargs):
        return Summary.objects.all()


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
