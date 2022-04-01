import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from django.conf import settings
from users.models import (
    User,
)
from django.db.models.functions import Concat
from economy.utils import parse_transaction_history
from economy.schema import BankAccountActivity
from users.filters import UserFilter
from graphql_relay import to_global_id
from schedules.schemas.schema_schedules import ShiftNode


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        exclude_fields = ("password",)

    full_name = graphene.NonNull(graphene.String)
    initials = graphene.NonNull(graphene.String)
    profile_image = graphene.String()
    balance = graphene.NonNull(graphene.Int)
    bank_account_activity = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    last_transactions = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    all_permissions = graphene.NonNull(graphene.List(graphene.String))
    upvoted_quote_ids = graphene.NonNull(graphene.List(graphene.ID))

    future_shifts = graphene.List(ShiftNode)

    def resolve_future_shifts(self: User, info, *args, **kwargs):
        return self.future_shifts

    def resolve_upvoted_quote_ids(self: User, info, **kwargs):
        return [
            to_global_id("QuoteNode", quote_vote.quote.id)
            for quote_vote in self.quote_votes.all()
        ]

    def resolve_full_name(self: User, info, **kwargs):
        if not self.get_full_name():
            return self.username
        return self.get_full_name()

    def resolve_initials(self: User, info, **kwargs):
        return self.initials

    def resolve_profile_image(self: User, info, **kwargs):
        if self.profile_image:
            return f"{settings.HOST_URL}{self.profile_image.url}"
        else:
            return None

    def resolve_balance(self: User, info, **kwargs):
        return self.balance

    def resolve_all_permissions(self: User, info, **kwargs):
        return self.get_all_permissions()

    def resolve_bank_account_activity(self: User, info, **kwargs):
        return parse_transaction_history(self.bank_account)

    def resolve_last_transactions(self: User, info, **kwargs):
        return parse_transaction_history(self.bank_account, 10)

    @classmethod
    def get_node(cls, info, id):
        return User.objects.get(pk=id)


class UserQuery(graphene.ObjectType):
    user = Node.Field(UserNode)
    me = graphene.Field(UserNode)
    all_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)
    all_active_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)

    def resolve_me(self, info, *args, **kwargs):
        if not hasattr(info.context, "user") or not info.context.user.is_authenticated:
            return None

        return info.context.user

    def resolve_all_users(self, info, *args, **kwargs):
        return User.objects.all()

    def resolve_all_active_users(self, info, *args, **kwargs):
        return (
            User.objects.filter(is_active=True)
            .annotate(full_name=Concat("first_name", "last_name"))
            .order_by("full_name")
        )


class CreateUserMutation(DjangoCreateMutation):
    class Meta:
        model = User


class DeleteUserMutation(DjangoDeleteMutation):
    class Meta:
        model = User


class PatchUserMutation(DjangoPatchMutation):
    class Meta:
        model = User
        exclude_fields = ("password",)


class UserMutations(graphene.ObjectType):
    create_user = CreateUserMutation.Field()
    patch_user = PatchUserMutation.Field()
    delete_user = DeleteUserMutation.Field()
