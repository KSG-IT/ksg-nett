import graphene
import bleach
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django.filter import DjangoFilterConnectionField

from common.consts import BLEACH_ALLOWED_TAGS
from common.decorators import gql_login_required
from summaries.models import Summary
from users.schema import UserNode
from summaries.filters import SummaryFilter


class SummaryNode(DjangoObjectType):
    class Meta:
        model = Summary
        interfaces = (Node,)

    participants = graphene.List(UserNode)
    display_name = graphene.String(source="get_display_name")

    @classmethod
    def get_node(cls, info, id):
        return Summary.objects.get(pk=id)

    contents = graphene.String()

    def resolve_contents(self: Summary, info, *args, **kwargs):
        return bleach.clean(self.contents, tags=BLEACH_ALLOWED_TAGS)

    def resolve_participants(self: Summary, info, *args, **kwargs):
        return self.participants.all()


class SummaryQuery(graphene.ObjectType):
    summary = Node.Field(SummaryNode)
    all_summaries = DjangoFilterConnectionField(
        SummaryNode, filterset_class=SummaryFilter
    )

    @gql_login_required()
    def resolve_all_summaries(self, info, *args, **kwargs):
        return Summary.objects.all().prefetch_related("participants").order_by("-date")


class CreateSummaryMutation(DjangoCreateMutation):
    class Meta:
        model = Summary
        permissions = ("summaries.add_summary",)


class PatchSummaryMutation(DjangoPatchMutation):
    class Meta:
        model = Summary
        permissions = ("summaries.change_summary",)


class DeleteSummaryMutation(DjangoDeleteMutation):
    class Meta:
        model = Summary
        permissions = ("summaries.delete_summary",)


class SummariesMutations(graphene.ObjectType):
    create_summary = CreateSummaryMutation.Field()
    patch_summary = PatchSummaryMutation.Field()
    delete_summary = DeleteSummaryMutation.Field()
