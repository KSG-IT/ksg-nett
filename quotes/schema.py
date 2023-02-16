import graphene
from django.db import transaction
from django.utils.html import strip_tags
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions, gql_login_required
from quotes.models import Quote, QuoteVote
from quotes.filters import QuoteFilter
from graphql_relay import from_global_id

from quotes.utils import send_tagged_in_quote_email


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
    popular_quotes_all_time = graphene.List(QuoteNode)
    popular_quotes_current_semester = graphene.List(QuoteNode)
    current_semester_shorthand = graphene.String()

    def resolve_current_semester_shorthand(self, info, *args, **kwargs):
        return Quote.get_current_semester_shorthand()

    def resolve_popular_quotes_current_semester(self, info, *args, **kwargs):
        return Quote.get_popular_quotes_in_current_semester()

    def resolve_popular_quotes_all_time(self, info, *args, **kwargs):
        return Quote.get_popular_quotes_all_time()

    def resolve_all_quotes(self, info, *args, **kwargs):
        return Quote.objects.all().order_by("created_at")

    def resolve_pending_quotes(self, info, *args, **kwargs):
        return Quote.get_pending_quotes()

    def resolve_approved_quotes(self, info, *args, **kwargs):
        return Quote.get_approved_quotes()


class CreateQuoteMutation(DjangoCreateMutation):
    class Meta:
        model = Quote
        auto_context_fields = {"reported_by": "user"}

    @staticmethod
    def handle_text(text, name, info):
        return strip_tags(text)

    @staticmethod
    def handle_context(context, name, info):
        return strip_tags(context)


class PatchQuoteMutation(DjangoPatchMutation):
    class Meta:
        model = Quote
        auto_context_fields = {"approved_by": "user"}


class DeleteQuoteMutation(DjangoDeleteMutation):
    class Meta:
        model = Quote


class CreateQuoteVoteMutation(DjangoCreateMutation):
    class Meta:
        model = QuoteVote
        auto_context_fields = {"caster": "user"}


class PatchQuoteVote(DjangoPatchMutation):
    class Meta:
        model = QuoteVote


class DeleteQuoteVote(DjangoDeleteMutation):
    class Meta:
        model = QuoteVote


class DeleteUserQuoteVote(graphene.Mutation):
    """
    Since a QuoteVote has a unique constraint for 'caster' and 'quote' there can only exist
    one quote vote object with the same caster and quote. Given this, a delete-mutation with
    quote_id + the user sending the request should give us a single quote vote object. The main
    motivation behind this approach is that we do not need to query every unique quote vote object
    for every quote in order to delete a vote from a user.
    """

    class Arguments:
        quote_id = graphene.ID(required=True)

    found = graphene.Boolean()
    quote_sum = graphene.Int()

    def mutate(self, info, quote_id):
        _, django_quote_id = from_global_id(quote_id)
        try:
            quote = Quote.objects.get(pk=django_quote_id)
            quote_vote = quote.votes.get(caster=info.context.user)
            quote_vote.delete()
            quote.refresh_from_db()
            return DeleteUserQuoteVote(found=True, quote_sum=quote.sum)
        except Quote.DoesNotExist:
            return None
        except QuoteVote.DoesNotExist:
            return None


class ApproveQuoteMutation(graphene.Mutation):
    class Arguments:
        quote_id = graphene.ID(required=True)

    quote = graphene.Field(QuoteNode)

    @gql_has_permissions("quotes.approve_quote")
    def mutate(self, info, quote_id):
        quote_id = disambiguate_id(quote_id)
        quote = Quote.objects.get(pk=quote_id)
        with transaction.atomic():
            quote.approved_by = info.context.user
            quote.approved = True
            tagged_users = quote.tagged.filter(notify_on_quote=True)
            if tagged_users:
                send_tagged_in_quote_email(quote, tagged_users)

            quote.save()
        return ApproveQuoteMutation(quote=quote)


class InvalidateQuoteMutation(graphene.Mutation):
    class Arguments:
        quote_id = graphene.ID(required=True)

    quote = graphene.Field(QuoteNode)

    @gql_has_permissions("quotes.invalidate_quote")
    def mutate(self, info, quote_id):
        quote_id = disambiguate_id(quote_id)
        quote = Quote.objects.get(pk=quote_id)
        with transaction.atomic():
            quote.approved_by = None
            quote.approved = False
            quote.save()
        return InvalidateQuoteMutation(quote=quote)


class QuotesMutations(graphene.ObjectType):
    create_quote = CreateQuoteMutation.Field()
    patch_quote = PatchQuoteMutation.Field()
    delete_quote = DeleteQuoteMutation.Field()

    approve_quote = ApproveQuoteMutation.Field()
    invalidate_quote = InvalidateQuoteMutation.Field()

    create_quote_vote = CreateQuoteVoteMutation.Field()
    patch_quote_vote = PatchQuoteMutation.Field()
    delete_quote_vote = DeleteQuoteMutation.Field()

    delete_user_quote_vote = DeleteUserQuoteVote.Field()
