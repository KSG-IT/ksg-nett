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
from graphene_django_cud.util import disambiguate_id
from graphql import GraphQLError

from common.consts import BLEACH_ALLOWED_TAGS
from common.decorators import gql_login_required
from summaries.models import Summary
from summaries.receipts import (
    counted_receipts,
    record_opened,
    record_read,
    with_receipt_data,
)
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

    opened_count = graphene.Int(
        required=True,
        description="Users who opened the summary. The reporter is not counted",
    )
    read_count = graphene.Int(
        required=True,
        description="Users who read the summary to the end. The reporter is not counted",
    )
    opened_by_me = graphene.Boolean(required=True)
    read_by_me = graphene.Boolean(required=True)

    # The list resolver annotates these (`with_receipt_data`). A single summary
    # reads them with a query each.
    def resolve_opened_count(self: Summary, info, *args, **kwargs):
        if hasattr(self, "receipts_opened"):
            return self.receipts_opened
        return counted_receipts(self).count()

    def resolve_read_count(self: Summary, info, *args, **kwargs):
        if hasattr(self, "receipts_read"):
            return self.receipts_read
        return counted_receipts(self).filter(read_at__isnull=False).count()

    def resolve_opened_by_me(self: Summary, info, *args, **kwargs):
        if hasattr(self, "receipts_opened_by_me"):
            return self.receipts_opened_by_me
        return self.read_receipts.filter(user=info.context.user).exists()

    def resolve_read_by_me(self: Summary, info, *args, **kwargs):
        if hasattr(self, "receipts_read_by_me"):
            return self.receipts_read_by_me
        return self.read_receipts.filter(
            user=info.context.user, read_at__isnull=False
        ).exists()


class SummaryQuery(graphene.ObjectType):
    summary = Node.Field(SummaryNode)
    all_summaries = DjangoFilterConnectionField(
        SummaryNode, filterset_class=SummaryFilter
    )

    @gql_login_required()
    def resolve_all_summaries(self, info, *args, **kwargs):
        summaries = (
            Summary.objects.select_related("reporter", "internal_group")
            .prefetch_related("participants")
            .order_by("-date")
        )
        return with_receipt_data(summaries, info.context.user)


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


def get_summary_or_error(summary_id) -> Summary:
    try:
        return Summary.objects.get(pk=disambiguate_id(summary_id))
    except (Summary.DoesNotExist, ValueError):
        raise GraphQLError("Summary does not exist")


class OpenSummaryMutation(graphene.Mutation):
    """The SPA calls this once, when the summary opens."""

    class Arguments:
        summary_id = graphene.ID(required=True)

    summary = graphene.Field(SummaryNode)

    @gql_login_required()
    def mutate(self, info, summary_id):
        summary = get_summary_or_error(summary_id)
        record_opened(summary, info.context.user)
        return OpenSummaryMutation(summary=summary)


class ReadSummaryMutation(graphene.Mutation):
    """The SPA calls this once, when the user scrolls to the end of the summary."""

    class Arguments:
        summary_id = graphene.ID(required=True)

    summary = graphene.Field(SummaryNode)

    @gql_login_required()
    def mutate(self, info, summary_id):
        summary = get_summary_or_error(summary_id)
        record_read(summary, info.context.user)
        return ReadSummaryMutation(summary=summary)


class SummariesMutations(graphene.ObjectType):
    create_summary = CreateSummaryMutation.Field()
    patch_summary = PatchSummaryMutation.Field()
    delete_summary = DeleteSummaryMutation.Field()

    open_summary = OpenSummaryMutation.Field()
    read_summary = ReadSummaryMutation.Field()
