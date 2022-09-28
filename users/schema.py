import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from quotes.schema import QuoteNode
from users.models import (
    User,
)
from common.util import get_semester_year_shorthand
from django.db.models.functions import Concat
from economy.utils import parse_transaction_history
from economy.schema import BankAccountActivity
from users.filters import UserFilter
from graphql_relay import to_global_id
from schedules.schemas.schema_schedules import ShiftNode
from organization.models import InternalGroup, InternalGroupPositionMembership
from graphene_django_cud.util import disambiguate_id
from organization.graphql import InternalGroupPositionTypeEnum


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        exclude_fields = ("password",)

    full_name = graphene.NonNull(graphene.String)
    initials = graphene.NonNull(graphene.String)
    profile_image = graphene.String()
    balance = graphene.NonNull(graphene.Int)
    ksg_status = graphene.String()
    bank_account_activity = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    last_transactions = graphene.NonNull(
        graphene.List(graphene.NonNull(BankAccountActivity))
    )
    all_permissions = graphene.NonNull(graphene.List(graphene.String))
    upvoted_quote_ids = graphene.NonNull(graphene.List(graphene.ID))
    internal_group_position_membership_history = graphene.List(
        "organization.schema.InternalGroupPositionMembershipNode"
    )

    def resolve_internal_group_position_membership_history(
        self: User, info, *args, **kwargs
    ):
        return self.internal_group_position_history.order_by("-date_joined")

    tagged_and_verified_quotes = graphene.List(QuoteNode)

    future_shifts = graphene.List(ShiftNode)

    def resolve_future_shifts(self: User, info, *args, **kwargs):
        return self.future_shifts

    def resolve_ksg_status(self: User, info, *args, **kwargs):
        return self.ksg_status

    def resolve_tagged_and_verified_quotes(self: User, info, *args, **kwargs):
        return self.quotes.filter(verified_by__isnull=False).order_by("-created_at")

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
            return self.profile_image.url
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


class ManageInternalGroupUserObject(graphene.ObjectType):
    # We return a flattened usertype structure to reduce the data handling overhead on the frontend
    user_id = graphene.ID()
    full_name = graphene.String()
    internal_group_position_membership = graphene.Field(
        "organization.schema.InternalGroupPositionMembershipNode"
    )
    position_name = graphene.String()
    internal_group_position_type = InternalGroupPositionTypeEnum()
    # Signifies the semester this person started having this specific membership
    date_joined_semester_shorthand = graphene.String()


class UserQuery(graphene.ObjectType):
    user = Node.Field(UserNode)
    me = graphene.Field(UserNode)
    all_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)
    all_active_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)
    manage_users_data = graphene.List(
        ManageInternalGroupUserObject,
        active_only=graphene.Boolean(required=True),
        internal_group_id=graphene.ID(),
    )

    def resolve_manage_users_data(
        self, info, active_only, internal_group_id, *args, **kwargs
    ):
        django_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.filter(pk=django_id).first()

        if not internal_group:
            return []

        internal_group_position_memberships = (
            InternalGroupPositionMembership.objects.filter(
                position__internal_group=internal_group
            )
        ).order_by("user__first_name")

        # We need to get rid of multiple entries of the same user
        for membership in internal_group_position_memberships.all():
            user_memberships = internal_group_position_memberships.filter(
                user=membership.user
            ).order_by("date_joined")
            freshest_membership = user_memberships.last()
            user_memberships = user_memberships.exclude(id=freshest_membership.id)
            exclude_ids = [membership.id for membership in user_memberships]
            # Nested exclusion. We prune away the other memberships besides the freshest one
            internal_group_position_memberships = (
                internal_group_position_memberships.exclude(id__in=exclude_ids)
            )

        if active_only:
            # Additional filtering
            internal_group_position_memberships = (
                internal_group_position_memberships.filter(
                    user__is_active=True, date_ended__isnull=True
                )
            )
        membership_list = []
        for membership in internal_group_position_memberships:
            membership_list.append(
                ManageInternalGroupUserObject(
                    user_id=to_global_id("UserNode", membership.user.id),
                    full_name=membership.user.get_full_name(),
                    internal_group_position_membership=membership,
                    internal_group_position_type=membership.type,
                    position_name=membership.position.name,
                    date_joined_semester_shorthand=get_semester_year_shorthand(
                        membership.date_joined
                    ),
                )
            )
        return membership_list

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
