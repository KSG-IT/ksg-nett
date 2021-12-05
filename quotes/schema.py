import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from quotes.models import Quote, QuoteVote


class QuoteNode(DjangoObjectType):
    class Meta:
        model = Quote
        interfaces = (Node,)

    sum = graphene.Int(source="sum")
    tagged = graphene.List("users.schema.UserNode")

    def resolve_tagged(self: Quote, info, **kwargs):
        return self.tagged.all()

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
    pending_quotes = DjangoConnectionField(QuoteNode)
    verified_quotes = DjangoConnectionField(QuoteNode)

    def resolve_all_quotes(self, info, *args, **kwargs):
        return Quote.objects.all()

    def resolve_pending_quotes(self, info, *args, **kwargs):
        return Quote.objects.filter(verified_by__isnull=True)

    def resolve_verified_quotes(self, info, *args, **kwargs):
        return Quote.objects.filter(verified_by__isnull=False)


class CreateQuoteMutation(DjangoCreateMutation):
    class Meta:
        model = Quote


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
