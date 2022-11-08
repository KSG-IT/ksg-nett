import graphene
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from common.decorators import gql_has_permissions, gql_login_required
from quotes.schema import QuoteNode
from users.models import User, UserType, UserTypeLogEntry
from common.util import get_semester_year_shorthand
from django.db.models.functions import Concat
from economy.utils import parse_transaction_history
from economy.schema import BankAccountActivity
from users.filters import UserFilter
from graphql_relay import to_global_id
from schedules.schemas.schedules import ShiftSlotNode
from organization.models import InternalGroup, InternalGroupPositionMembership
from graphene_django_cud.util import disambiguate_id
from organization.graphql import InternalGroupPositionTypeEnum
from users.utils import ical_token_generator
from django.utils.html import strip_tags


class UserTypeLogEntryNode(DjangoObjectType):
    class Meta:
        model = UserTypeLogEntry
        interfaces = (Node,)

    @classmethod
    @gql_has_permissions("users.view_usertypelogentry")
    def get_node(cls, info, id):
        return UserTypeLogEntry.objects.get(pk=id)


class UserTypeNode(DjangoObjectType):
    class Meta:
        model = UserType
        interfaces = (Node,)

    changelog = graphene.List(UserTypeLogEntryNode)

    def resolve_changelog(self: UserType, info, *args, **kwargs):
        return self.changelog.select_related("user").order_by("-timestamp")

    users = graphene.List(lambda: UserNode)

    def resolve_users(self: UserType, info, *args, **kwargs):
        return self.users.all().order_by("first_name", "last_name")

    @classmethod
    @gql_has_permissions("users.view_usertype")
    def get_node(cls, info, id):
        return UserType.objects.get(pk=id)


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        exclude_fields = ("password",)

    full_name = graphene.NonNull(graphene.String)
    initials = graphene.NonNull(graphene.String)
    get_clean_full_name = graphene.NonNull(graphene.String)
    get_full_with_nick_name = graphene.NonNull(graphene.String)

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
    money_spent = graphene.Int()
    legacy_work_history = graphene.List("organization.schema.LegacyUserWorkHistoryNode")

    def resolve_internal_group_position_membership_history(
        self: User, info, *args, **kwargs
    ):
        return self.internal_group_position_history.order_by("-date_joined")

    tagged_and_verified_quotes = graphene.List(QuoteNode)

    future_shifts = graphene.List(ShiftSlotNode)
    ical_token = graphene.String()

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
        if self.is_superuser:
            all_permissions = [
                "{}.{}".format(app_label, codename)
                for app_label, codename in Permission.objects.values_list(
                    "content_type__app_label", "codename"
                )
            ]
        else:
            all_permissions = self.get_all_permissions()

        return all_permissions

    def resolve_bank_account_activity(self: User, info, **kwargs):
        return parse_transaction_history(self.bank_account)

    def resolve_last_transactions(self: User, info, **kwargs):
        return parse_transaction_history(self.bank_account, 10)

    def resolve_money_spent(self: User, info, **kwargs):
        return self.bank_account.money_spent

    def resolve_legacy_work_history(self: User, info, **kwargs):
        return self.legacy_work_history.all().order_by("date_from")

    def resolve_get_clean_full_name(self: User, info, **kwargs):
        return self.get_clean_full_name()

    def resolve_get_full_with_nick_name(self: User, info, **kwargs):
        return self.get_full_with_nick_name()

    def resolve_ical_token(self: User, info, **kwargs):
        """
        Doing this in a custom migration proved to be harder than expected, so we do it here instead.
        """
        if not self.ical_token:
            token = ical_token_generator()
            self.ical_token = token
            self.save()
            return token

        return self.ical_token

    @classmethod
    @gql_login_required()
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
    date_ended_semester_shorthand = graphene.String()


class ManageInternalGroupUsersData(graphene.ObjectType):
    active_memberships = graphene.List(ManageInternalGroupUserObject)
    all_memberships = graphene.List(ManageInternalGroupUserObject)


class UserQuery(graphene.ObjectType):
    user = Node.Field(UserNode)
    me = graphene.Field(UserNode)
    all_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)
    all_active_users = DjangoFilterConnectionField(UserNode, filterset_class=UserFilter)
    manage_users_data = graphene.Field(
        ManageInternalGroupUsersData,
        internal_group_id=graphene.ID(),
    )
    user_type = Node.Field(UserTypeNode)
    all_user_types = graphene.List(UserTypeNode)

    @gql_has_permissions("users.change_user")
    def resolve_manage_users_data(self, info, internal_group_id, *args, **kwargs):
        internal_group_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.get(pk=internal_group_id)

        active_memberships = (
            InternalGroupPositionMembership.objects.filter(
                position__internal_group=internal_group
            )
        ).order_by("user__first_name")

        # We need to get rid of multiple entries of the same user
        for membership in active_memberships.filter(
            user__is_active=True, date_ended__isnull=True
        ):
            user_memberships = active_memberships.filter(user=membership.user).order_by(
                "date_joined"
            )
            # freshest_membership = user_memberships.last()
            # user_memberships = user_memberships.exclude(id=freshest_membership.id)
            # exclude_ids = [membership.id for membership in user_memberships]
            # Nested exclusion. We prune away the other memberships besides the freshest one
            # active_memberships = active_memberships.exclude(id__in=exclude_ids)

        active_membership_list = []
        for membership in InternalGroupPositionMembership.objects.filter(
            position__internal_group=internal_group,
            user__is_active=True,
            date_ended__isnull=True,
        ).order_by("user__first_name"):
            date_joined = get_semester_year_shorthand(membership.date_joined)
            active_membership_list.append(
                ManageInternalGroupUserObject(
                    user_id=to_global_id("UserNode", membership.user.id),
                    full_name=membership.user.get_full_name(),
                    internal_group_position_membership=membership,
                    internal_group_position_type=membership.type,
                    position_name=membership.position.name,
                    date_joined_semester_shorthand=date_joined,
                    date_ended_semester_shorthand=None,
                )
            )

        all_memberships = []
        for membership in InternalGroupPositionMembership.objects.filter(
            position__internal_group=internal_group, date_ended__isnull=False
        ).order_by("user__first_name"):
            date_started = get_semester_year_shorthand(membership.date_ended)
            date_ended = get_semester_year_shorthand(membership.date_ended)
            all_memberships.append(
                ManageInternalGroupUserObject(
                    user_id=to_global_id("UserNode", membership.user.id),
                    full_name=membership.user.get_full_name(),
                    internal_group_position_membership=membership,
                    internal_group_position_type=membership.type,
                    position_name=membership.position.name,
                    date_joined_semester_shorthand=date_started,
                    date_ended_semester_shorthand=date_ended,
                )
            )
        membership_data = ManageInternalGroupUsersData(
            active_memberships=active_membership_list,
            all_memberships=all_memberships,
        )
        return membership_data

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

    all_active_users_list = graphene.List(UserNode, q=graphene.String())

    def resolve_all_active_users_list(self, info, q, *args, **kwargs):
        return (
            User.objects.filter(is_active=True)
            .annotate(full_name=Concat("first_name", "nickname", "last_name"))
            .filter(full_name__icontains=q)
            .order_by("full_name")
        )

    @gql_has_permissions("users.view_usertype")
    def resolve_all_user_types(self, info, *args, **kwargs):
        return UserType.objects.all().order_by("name")


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
        permissions = ("users.change_user",)

    @staticmethod
    def handle_first_name(first_name: str, name, info):
        return first_name.strip("")

    @staticmethod
    def handle_last_name(last_name: str, name, info):
        return last_name.strip("")


class UpdateMyInfoMutation(graphene.Mutation):
    """
    Custom mutation based on the equest sender. If they are no authenticated
    this will not trigger.
    """

    class Arguments:
        first_name = graphene.String()
        nickname = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        phone = graphene.String()
        study = graphene.String()
        date_of_birth = graphene.Date()
        study_address = graphene.String()
        home_town = graphene.String()
        card_uuid = graphene.String()

    user = graphene.Field(UserNode)

    def mutate(self, info, **kwargs):
        user = info.context.user
        card_uuid = kwargs.pop("card_uuid", None)

        for key, value in kwargs.items():
            if isinstance(value, str):
                value = strip_tags(value)
                if len(value) > 80:
                    # We can thank script kiddies for this
                    raise ValueError(f"{key} is too long")
                value = value.strip()
            setattr(user, key, value)

        user.requires_migration_wizard = False
        user.is_active = True
        user.save()
        if card_uuid:
            card_uuid = card_uuid.strip()
            bank_account = user.bank_account
            bank_account.card_uuid = card_uuid
            bank_account.save()
        return UpdateMyInfoMutation(user=user)


class AddUserToUserTypeMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        user_type_id = graphene.ID()

    user = graphene.Field(UserNode)

    @staticmethod
    @gql_has_permissions("users.change_usertype")
    def mutate(root, info, user_id, user_type_id):
        user_id = disambiguate_id(user_id)
        user_type_id = disambiguate_id(user_type_id)
        user = User.objects.get(id=user_id)
        user_type = UserType.objects.get(id=user_type_id)

        request_user = info.context.user

        if user_type.requires_superuser and not request_user.is_superuser:
            raise PermissionDenied("You do not have permission to add this user type")

        if user_type.requires_self and not request_user.is_superuser:
            self_check = user_type.users.filter(id=request_user.id).exists()
            if not self_check:
                raise PermissionDenied(
                    "You do not have permission to add this user type"
                )

        with transaction.atomic():
            user_type.users.add(user)
            UserTypeLogEntry.objects.create(
                user_type=user_type,
                user=user,
                done_by=request_user,
                timestamp=timezone.now(),
                action=UserTypeLogEntry.Action.ADD,
            )

        return AddUserToUserTypeMutation(user=user)


class RemoveUserFromUserTypeMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        user_type_id = graphene.ID()

    user = graphene.Field(UserNode)

    @staticmethod
    @gql_has_permissions("users.change_usertype")
    def mutate(root, info, user_id, user_type_id):
        user_id = disambiguate_id(user_id)
        user_type_id = disambiguate_id(user_type_id)
        user = User.objects.get(id=user_id)
        user_type = UserType.objects.get(id=user_type_id)

        request_user = info.context.user

        if user_type.requires_superuser and not request_user.is_superuser:
            raise PermissionDenied(
                "You do not have permission to remove this user type"
            )

        if user_type.requires_self and not request_user.is_superuser:
            self_check = user_type.users.filter(id=request_user.id).exists()
            if not self_check:
                raise PermissionDenied(
                    "You do not have permission to remove this user type"
                )

        with transaction.atomic():
            user_type.users.remove(user)
            UserTypeLogEntry.objects.create(
                user_type=user_type,
                user=user,
                done_by=request_user,
                timestamp=timezone.now(),
                action=UserTypeLogEntry.Action.REMOVE,
            )

        return RemoveUserFromUserTypeMutation(user=user)


class UserMutations(graphene.ObjectType):
    create_user = CreateUserMutation.Field()
    patch_user = PatchUserMutation.Field()
    delete_user = DeleteUserMutation.Field()
    update_my_info = UpdateMyInfoMutation.Field()

    add_user_to_user_type = AddUserToUserTypeMutation.Field()
    remove_user_from_user_type = RemoveUserFromUserTypeMutation.Field()
