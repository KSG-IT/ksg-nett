import graphene
from graphene import Node
from graphene_django import DjangoObjectType, DjangoConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)

from users.models import (
    User,
)
from economy.utils import parse_transaction_history
from economy.schema import BankAccountActivity


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        exclude_fields = ("password",)

    full_name = graphene.NonNull(graphene.String)
    initials = graphene.NonNull(graphene.String)
    profile_picture = graphene.String()
    balance = graphene.NonNull(graphene.Int)
    bank_account_activity = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    last_transactions = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    all_permissions = graphene.NonNull(graphene.List(graphene.String))

    def resolve_full_name(self: User, info, **kwargs):
        return self.get_full_name()

    def resolve_initials(self: User, info, **kwargs):
        return self.initials

    def resolve_profile_picture(self: User, info, **kwargs):
        return self.profile_image_url

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
    all_users = DjangoConnectionField(UserNode)

    def resolve_me(self, info, *args, **kwargs):
        if not hasattr(info.context, "user") or not info.context.user.is_authenticated:
            return None

        return info.context.user

    def resolve_all_users(self, info, *args, **kwargs):
        return User.objects.all()


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
