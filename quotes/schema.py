import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from quotes.models import Quote, QuoteVote
from quotes.filters import QuoteFilter


class QuoteNode(DjangoObjectType):
    class Meta:
        model = Quote
        interfaces = (Node,)

    sum = graphene.Int(source="sum")
    tagged = graphene.NonNull(graphene.List(graphene.NonNull("users.schema.UserNode")))
    semester = graphene.String()

    def resolve_tagged(self: Quote, info, **kwargs):
        return self.tagged.all()

    def resolve_semester(self: Quote, info, **kwargs):
        return self.get_semester_of_quote()

    @classmethod
    def get_node(cls, info, id):
        return Quote.objects.get(pk=id)


class QuoteVoteNode(DjangoObjectType):
    class Meta:
        model = QuoteVote
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return QuoteVote.objects.get(pk=id)


class QuoteQuery(graphene.ObjectType):
    quote = Node.Field(QuoteNode)
    all_quotes = DjangoConnectionField(QuoteNode)
    pending_quotes = graphene.List(QuoteNode)
    approved_quotes = DjangoFilterConnectionField(
        QuoteNode, filterset_class=QuoteFilter
    )

    def resolve_all_quotes(self, info, *args, **kwargs):
        return Quote.objects.all().order_by("created_at")

    def resolve_pending_quotes(self, info, *args, **kwargs):
        return Quote.objects.filter(verified_by__isnull=True).order_by("created_at")

    def resolve_approved_quotes(self, info, *args, **kwargs):
        return Quote.objects.filter(verified_by__isnull=False).order_by("created_at")


class CreateQuoteMutation(DjangoCreateMutation):
    class Meta:
        model = Quote

        auto_context_fields = {"reported_by": "user"}


class PatchQuoteMutation(DjangoPatchMutation):
    class Meta:
        model = Quote


class DeleteQuoteMutation(DjangoDeleteMutation):
    class Meta:
        model = Quote


class CreateQuoteVoteMutation(DjangoCreateMutation):
    class Meta:
        model = QuoteVote


class PatchQuoteVote(DjangoPatchMutation):
    class Meta:
        model = QuoteVote


class DeleteQuoteVote(DjangoDeleteMutation):
    class Meta:
        model = QuoteVote


class QuotesMutations(graphene.ObjectType):
    create_quote = CreateQuoteMutation.Field()
    patch_quote = PatchQuoteMutation.Field()
    delete_quote = DeleteQuoteMutation.Field()

    create_quote_vote = CreateQuoteVoteMutation.Field()
    patch_quote_vote = PatchQuoteMutation.Field()
    delete_quote_vote = DeleteQuoteMutation.Field()
