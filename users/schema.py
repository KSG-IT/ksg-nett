import bleach
import jwt
import graphene
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Value, Q
from django.conf import settings
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
)

from admissions.models import Admission
from common.decorators import gql_has_permissions, gql_login_required
from quotes.schema import QuoteNode
from users.models import KnightHood, User, UserType, UserTypeLogEntry, Allergy
from common.util import get_semester_year_shorthand
from django.db.models.functions import Concat
from economy.utils import parse_transaction_history
from economy.schema import BankAccountActivity
from economy.models import SociBankAccount
from users.filters import UserFilter
from graphql_relay import to_global_id
from schedules.schemas.schedules import ShiftSlotNode
from organization.models import InternalGroup, InternalGroupPositionMembership
from graphene_django_cud.util import disambiguate_id
from organization.graphql import InternalGroupPositionTypeEnum
from users.utils import ical_token_generator
from django.utils.html import strip_tags
from .emails import welcome_single_user_email


class UserTypeLogEntryNode(DjangoObjectType):
    class Meta:
        model = UserTypeLogEntry
        interfaces = (Node,)

    @classmethod
    @gql_has_permissions("users.view_usertypelogentry")
    def get_node(cls, info, id):
        return UserTypeLogEntry.objects.get(pk=id)


class AllergyNode(DjangoObjectType):
    class Meta:
        model = Allergy
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Allergy.objects.get(pk=id)


class KnightHoodNode(DjangoObjectType):
    class Meta:
        model = KnightHood
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return KnightHood.objects.get(pk=id)


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
    active_internal_group_position = graphene.Field(
        "organization.schema.InternalGroupPositionNode",
        source="active_internal_group_position",
    )
    money_spent = graphene.Int()

    def resolve_internal_group_position_membership_history(
        self: User, info, *args, **kwargs
    ):
        return self.internal_group_position_history.order_by("-date_joined")

    tagged_and_verified_quotes = graphene.List(QuoteNode)

    future_shifts = graphene.List(ShiftSlotNode)
    ical_token = graphene.String()
    owes_money = graphene.Boolean(source="owes_money")
    allergies = graphene.List(AllergyNode)

    def resolve_future_shifts(self: User, info, *args, **kwargs):
        return self.future_shifts

    def resolve_ksg_status(self: User, info, *args, **kwargs):
        return self.ksg_status

    def resolve_tagged_and_verified_quotes(self: User, info, *args, **kwargs):
        return self.quotes.filter(approved=True).order_by("-created_at")

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

    def resolve_allergies(self: User, info, **kwargs):
        return self.allergies.all().order_by("name")

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
    searchbar_users = graphene.List(UserNode, search_string=graphene.String())
    manage_users_data = graphene.Field(
        ManageInternalGroupUsersData,
        internal_group_id=graphene.ID(),
    )
    user_type = Node.Field(UserTypeNode)
    all_user_types = graphene.List(UserTypeNode)
    newbies = graphene.List(UserNode)

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
            date_started = get_semester_year_shorthand(membership.date_joined)
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

    @gql_login_required()
    def resolve_all_users(self, info, *args, **kwargs):
        return User.objects.all()

    @gql_login_required()
    def resolve_all_active_users(self, info, *args, **kwargs):
        return (
            User.objects.filter(is_active=True)
            .annotate(full_name=Concat("first_name", "last_name"))
            .order_by("full_name")
        )

    all_active_users_list = graphene.List(UserNode, q=graphene.String())

    @gql_login_required()
    def resolve_all_active_users_list(self, info, q, *args, **kwargs):
        return (
            User.objects.filter(is_active=True)
            .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
            .filter(full_name__icontains=q)
            .order_by("full_name")
        )

    @gql_has_permissions("users.view_usertype")
    def resolve_all_user_types(self, info, *args, **kwargs):
        return UserType.objects.all().order_by("name")

    @gql_login_required()
    def resolve_searchbar_users(self, info, search_string, *args, **kwargs):
        search_string = search_string.strip()
        if search_string == "":
            return []

        return (
            User.objects.filter(is_active=True)
            .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
            .filter(
                Q(full_name__icontains=search_string)
                | Q(email__icontains=search_string)
                | Q(nickname__icontains=search_string)
                | Q(phone__icontains=search_string)
            )
            .order_by("full_name")[0:10]
        )

    @gql_login_required()
    def resolve_newbies(self, info, *args, **kwargs):
        admission = Admission.get_last_closed_admission()
        if admission is None:
            return []

        return User.objects.filter(admission=admission).order_by("first_name")


class AllergyQuery(graphene.ObjectType):
    all_allergies = graphene.List(AllergyNode)

    def resolve_all_allergies(self, info, *args, **kwargs):
        return Allergy.objects.all().order_by("name")


class KnightHoodQuery(graphene.ObjectType):
    all_knighthoods = graphene.List(KnightHoodNode)

    def resolve_all_knighthoods(self, info, *args, **kwargs):
        return KnightHood.objects.prefetch_related("user").all().order_by("knighted_at")


class KnightUserMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        knighted_at = graphene.Date(required=False)

    user = graphene.Field(UserNode)

    @staticmethod
    @gql_has_permissions("users.change_user")
    def mutate(root, info, user_id, knighted_at=None):
        user_id = disambiguate_id(user_id)
        user = User.objects.get(id=user_id)
        if knighted_at is None:
            knighted_at = timezone.now().date()
        KnightHood.objects.create(user=user, knighted_at=knighted_at)
        return KnightUserMutation(user=user)


class DeleteUserMutation(DjangoDeleteMutation):
    class Meta:
        model = User


class PatchUserMutation(DjangoPatchMutation):
    class Meta:
        model = User
        exclude_fields = ("password", "about_me")
        permissions = ("users.change_user",)

    @staticmethod
    def handle_first_name(first_name: str, name, info):
        return strip_tags(first_name.strip(""))

    @staticmethod
    def handle_last_name(last_name: str, name, info):
        return strip_tags(last_name.strip(""))

    @staticmethod
    def handle_nickname(nickname: str, name, info):
        return strip_tags(nickname.strip(""))

    @staticmethod
    def handle_study(study: str, name, info):
        return strip_tags(study.strip(""))

    @staticmethod
    def handle_about_me(about_me: str, name, info):
        return strip_tags(about_me.strip(""))

    @staticmethod
    def handle_study_address(study_address: str, name, info):
        return strip_tags(study_address.strip(""))

    @staticmethod
    def handle_home_town(home_town: str, name, info):
        return strip_tags(home_town.strip(""))


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
        if not user.requires_migration_wizard:
            raise Exception("User does not require migration wizard")

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


class UpdateMyAllergies(graphene.Mutation):
    class Arguments:
        allergy_ids = graphene.List(graphene.ID)

    user = graphene.Field(UserNode)

    def mutate(self, info, allergy_ids):
        user = info.context.user
        allergy_ids = [disambiguate_id(allergy_id) for allergy_id in allergy_ids]
        allergies = Allergy.objects.filter(id__in=allergy_ids)
        user.allergies.set(allergies)
        return UpdateMyAllergies(user=user)


class UpdateMyEmailSettingsMutation(graphene.Mutation):
    class Arguments:
        notify_on_shift = graphene.Boolean(required=True)
        notify_on_deposit = graphene.Boolean(required=True)
        notify_on_quote = graphene.Boolean(required=True)

    user = graphene.Field(UserNode)

    def mutate(self, info, notify_on_shift, notify_on_deposit, notify_on_quote):
        user = info.context.user
        user.notify_on_shift = notify_on_shift
        user.notify_on_deposit = notify_on_deposit
        user.notify_on_quote = notify_on_quote
        user.save()
        return UpdateMyEmailSettingsMutation(user=user)


class UpdateMyAddressSettingsMutation(graphene.Mutation):
    class Arguments:
        study_address = graphene.String()

    user = graphene.Field(UserNode)

    def mutate(self, info, study_address):
        user = info.context.user

        study_address = study_address.strip()

        if len(study_address) == 0:
            raise ValueError("Study address cannot be empty")

        if len(study_address) > 64:
            raise ValueError("Study address cannot be longer than 64 characters")

        study_address = strip_tags(study_address)
        user.study_address = study_address
        user.save()
        return UpdateMyAddressSettingsMutation(user=user)


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


class UpdateAboutMeMutation(graphene.Mutation):
    class Arguments:
        about_me = graphene.String()

    user = graphene.Field(UserNode)

    @staticmethod
    def mutate(root, info, about_me):
        user = info.context.user

        if not user.first_time_login and not user.can_rewrite_about_me:
            raise PermissionDenied("You can't rewrite your about me anymore")

        if len(about_me) > 300:
            raise ValueError("Value too long")

        about_me = about_me.strip()
        about_me_strip_check = about_me.strip("\r\n")
        about_me_strip_check = about_me_strip_check.strip(".")

        if about_me_strip_check == "":
            raise ValueError("Value too short")

        if not user.first_time_login and user.can_rewrite_about_me:
            user.can_rewrite_about_me = False
            user.save()

        user.about_me = strip_tags(about_me)
        user.first_time_login = False
        user.save()
        return UpdateAboutMeMutation(user=user)


class InviteNewUserMutation(graphene.Mutation):
    class Arguments:
        email = graphene.String()  # Can this be an email field?
        first_name = graphene.String()
        last_name = graphene.String()
        send_welcome_email = graphene.Boolean()

    user = graphene.Field(UserNode)

    @gql_has_permissions("users.add_user")
    def mutate(
        root, info, email, first_name, last_name, send_welcome_email, *args, **kwargs
    ):
        user = User.objects.create(
            email=email, username=email, first_name=first_name, last_name=last_name
        )

        SociBankAccount.objects.create(card_uuid=None, user=user)

        if send_welcome_email:
            jwt_reset_token = jwt.encode(
                {
                    "action": "reset_password",
                    "user_id": user.id,
                    "iss": "KSG-nett",
                    "iat": timezone.now(),
                    "exp": timezone.now() + timezone.timedelta(hours=24),
                },
                settings.AUTH_JWT_SECRET,
                algorithm=settings.AUTH_JWT_METHOD,
            )
            welcome_single_user_email(email, jwt_reset_token)

        return InviteNewUserMutation(user=user)


class UserMutations(graphene.ObjectType):
    invite_new_user = InviteNewUserMutation.Field()
    patch_user = PatchUserMutation.Field()
    delete_user = DeleteUserMutation.Field()
    update_my_info = UpdateMyInfoMutation.Field()
    update_about_me = UpdateAboutMeMutation.Field()
    update_my_allergies = UpdateMyAllergies.Field()
    update_my_email_notifications = UpdateMyEmailSettingsMutation.Field()
    update_my_address = UpdateMyAddressSettingsMutation.Field()
    add_user_to_user_type = AddUserToUserTypeMutation.Field()
    remove_user_from_user_type = RemoveUserFromUserTypeMutation.Field()
    knight_user = KnightUserMutation.Field()
