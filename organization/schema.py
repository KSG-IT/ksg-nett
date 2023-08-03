import datetime

import bleach
import graphene
from django.db import transaction
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
    DjangoBatchPatchMutation,
)
from graphene_django import DjangoConnectionField

from common.consts import BLEACH_ALLOWED_TAGS
from common.decorators import gql_has_permissions, gql_login_required
from organization.consts import InternalGroupPositionMembershipType
from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
    InternalGroupUserHighlight,
)
from graphene_django_cud.util import disambiguate_id
from organization.graphql import InternalGroupPositionTypeEnum
from users.schema import UserNode
from users.models import User, UserType, UserTypeLogEntry


class InternalGroupPositionMembershipData(graphene.ObjectType):
    internal_group_position_name = graphene.String()
    users = graphene.List(UserNode)


class InternalGroupNode(DjangoObjectType):
    class Meta:
        model = InternalGroup
        filter_fields = ["type", "name"]
        interfaces = (Node,)

    membership_data = graphene.List(InternalGroupPositionMembershipData)

    def resolve_membership_data(self: InternalGroup, info, *args, **kwargs):
        positions = self.positions.all()
        all_users = User.objects.filter(
            internal_group_position_history__position__internal_group=self,
            internal_group_position_history__date_ended__isnull=True,
        ).distinct()

        user_groupings = []
        for position in positions:
            position_grouping_object = InternalGroupPositionMembershipData(
                internal_group_position_name=position.name,
                users=all_users.filter(
                    internal_group_position_history__position=position
                ).order_by("first_name"),
            )
            user_groupings.append(position_grouping_object)

        return user_groupings

    description = graphene.String()

    def resolve_description(self: InternalGroup, info, **kwargs):
        return bleach.clean(self.description, tags=BLEACH_ALLOWED_TAGS)

    group_image = graphene.String()

    def resolve_group_image(self: InternalGroup, info, **kwargs):
        if self.group_image:
            return self.group_image.url
        else:
            return None

    @classmethod
    def get_node(cls, info, id):
        return InternalGroup.objects.get(pk=id)

    def resolve_group_icon(self: InternalGroup, info, **kwargs):
        if self.group_icon:
            return self.group_icon.url
        else:
            return None


class InternalGroupPositionNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPosition
        interfaces = (Node,)

    @classmethod
    @gql_has_permissions("organization.view_internalgroupposition")
    def get_node(cls, info, id):
        return InternalGroupPosition.objects.get(pk=id)


class InternalGroupPositionMembershipNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPositionMembership
        interfaces = (Node,)

    membership_start = graphene.String()
    membership_end = graphene.String()
    get_type_display = graphene.String()

    @classmethod
    @gql_has_permissions("organization.view_internalgrouppositionmembership")
    def get_node(cls, info, id):
        return InternalGroupPositionMembership.objects.get(pk=id)

    def resolve_membership_start(self: InternalGroupPositionMembership, info, **kwargs):
        return self.get_semester_of_membership(start=True)

    def resolve_membership_end(self: InternalGroupPositionMembership, info, **kwargs):
        return self.get_semester_of_membership(start=False)

    def resolve_get_type_display(self: InternalGroupPositionMembership, info, **kwargs):
        return self.get_type_display()


class InternalGroupTypeEnum(graphene.Enum):
    INTERNAL_GROUP = InternalGroup.Type.INTERNAL_GROUP
    INTEREST_GROUP = InternalGroup.Type.INTEREST_GROUP


# QUERIES
class InternalGroupQuery(graphene.ObjectType):
    internal_group = Node.Field(InternalGroupNode)
    all_internal_groups = graphene.List(InternalGroupNode)
    all_internal_groups_by_type = graphene.List(
        InternalGroupNode, internal_group_type=InternalGroupTypeEnum()
    )

    def resolve_all_internal_groups(self, info, *args, **kwargs):
        return InternalGroup.objects.all().order_by("name")

    def resolve_all_internal_groups_by_type(self, info, internal_group_type, **kwargs):
        return InternalGroup.objects.filter(type=internal_group_type.value).order_by(
            "name"
        )


class InternalGroupPositionQuery(graphene.ObjectType):
    internal_group_position = Node.Field(InternalGroupPositionNode)
    all_internal_group_positions = graphene.List(InternalGroupPositionNode)

    def resolve_all_internal_group_positions(self, info, *args, **kwargs):
        return InternalGroupPosition.objects.all()


class InternalGroupPositionMembershipQuery(graphene.ObjectType):
    internal_group_position_membership = Node.Field(InternalGroupPositionMembershipNode)
    all_internal_group_position_membership = DjangoConnectionField(
        InternalGroupPositionMembershipNode
    )
    all_active_internal_group_position_memberships = DjangoConnectionField(
        InternalGroupPositionMembershipNode
    )
    internal_group_position_memberships = graphene.List(
        InternalGroupPositionMembershipNode
    )
    all_internal_group_position_memberships_by_internal_group = graphene.List(
        InternalGroupPositionMembershipNode, internal_group_id=graphene.ID()
    )

    def resolve_all_internal_group_position_memberships(self, info, *args, **kwargs):
        return InternalGroupPositionMembership.objects.all().order_by("date_ended")

    def resolve_all_internal_group_position_memberships_by_internal_group(
        self, info, internal_group_id, *args, **kwargs
    ):
        internal_group_id = disambiguate_id(internal_group_id)
        return InternalGroupPositionMembership.objects.filter(
            id=internal_group_id, date_ended__isnull=True
        ).order_by("user__first_name")

    def resolve_all_active_internal_group_position_memberships(
        self, info, *args, **kwargs
    ):
        return InternalGroupPositionMembership.objects.filter(
            date_ended__isnull=True
        ).order_by("date_joined")


# MUTATIONS
class CreateInternalGroupMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroup
        permissions = ("organization.add_internalgroup",)


class PatchInternalGroupMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroup
        permissions = ("organization.change_internalgroup",)


class DeleteInternalGroupMutation(DjangoDeleteMutation):
    class Meta:
        model = InternalGroup
        permissions = ("organization.delete_internalgroup",)


class CreateInternalGroupPositionMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroupPosition
        permissions = ("organization.add_internalgroupposition",)


class PatchInternalGroupPositionMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPosition
        permissions = ("organization.change_internalgroupposition",)


class DeleteInternalGroupPosition(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPosition
        permissions = ("organization.delete_internalgroupposition",)


class AssignNewInternalGroupPositionMembership(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        internal_group_position_id = graphene.ID()
        internal_group_position_type = InternalGroupPositionTypeEnum()

    internal_group_position_membership = graphene.Field(
        InternalGroupPositionMembershipNode
    )

    @gql_has_permissions("organization.add_internalgrouppositionmembership")
    def mutate(
        self,
        info,
        user_id,
        internal_group_position_id,
        internal_group_position_type,
        *args,
        **kwargs,
    ):
        django_user_id = disambiguate_id(user_id)
        user = User.objects.filter(pk=django_user_id).first()
        if not user:
            return None

        django_internal_group_position_id = disambiguate_id(internal_group_position_id)
        internal_group_position = InternalGroupPosition.objects.filter(
            pk=django_internal_group_position_id
        ).first()
        if not internal_group_position:
            return None

        # We have found relevant model instances and now need to check any active memberships to terminate
        active_membership = user.current_internal_group_position_membership
        today = datetime.date.today()
        if active_membership:
            active_membership.date_ended = today
            active_membership.save()

        new_internal_group_position_membership = (
            InternalGroupPositionMembership.objects.create(
                user=user,
                type=internal_group_position_type.value,
                position=internal_group_position,
                date_joined=datetime.date.today(),
            )
        )

        has_usertype_perm = info.context.user.has_perm("users.change_usertype")

        if (
            getattr(active_membership, "type", None)
            == InternalGroupPositionMembershipType.FUNCTIONARY
        ):
            functionary_user_type = UserType.objects.filter(name="Funksjonær").first()
            if functionary_user_type and has_usertype_perm:
                # Can make this a bit more robust in the future
                with transaction.atomic():
                    functionary_user_type.users.remove(user)
                    UserTypeLogEntry.objects.create(
                        user_type=functionary_user_type,
                        user=user,
                        done_by=info.context.user,
                        timestamp=timezone.now(),
                        action=UserTypeLogEntry.Action.REMOVE,
                    )

        if (
            new_internal_group_position_membership.type
            == InternalGroupPositionMembershipType.FUNCTIONARY
        ):
            functionary_user_type = UserType.objects.filter(name="Funksjonær").first()
            # Same as above
            if functionary_user_type and has_usertype_perm:
                with transaction.atomic():
                    functionary_user_type.users.add(user)
                    UserTypeLogEntry.objects.create(
                        user_type=functionary_user_type,
                        user=user,
                        done_by=info.context.user,
                        timestamp=timezone.now(),
                        action=UserTypeLogEntry.Action.ADD,
                    )

        return AssignNewInternalGroupPositionMembership(
            internal_group_position_membership=new_internal_group_position_membership
        )


class CreateInternalGroupPositionMembershipMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroupPositionMembership
        permissions = ("organization.add_internalgrouppositionmembership",)


class PatchInternalGroupPositionMembershipMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPositionMembership
        permissions = ("organization.change_internalgrouppositionmembership",)


class DeleteInternalGroupPositionMembership(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPositionMembership
        permissions = ("organization.delete_internalgrouppositionmembership",)


class QuitKSGMutation(graphene.Mutation):
    class Arguments:
        membership_id = graphene.ID()

    internal_group_position_membership = graphene.Field(
        InternalGroupPositionMembershipNode
    )

    @gql_has_permissions("organization.change_internalgrouppositionmembership")
    def mutate(self, info, membership_id, *args, **kwargs):
        # consider terminating all active memberships?
        membership_id = disambiguate_id(membership_id)
        membership = InternalGroupPositionMembership.objects.get(pk=membership_id)
        membership.date_ended = datetime.date.today()
        membership.save()
        return QuitKSGMutation(internal_group_position_membership=membership)


class InternalGroupUserHighlightNode(DjangoObjectType):
    class Meta:
        model = InternalGroupUserHighlight
        filter_fields = ["internal_group", "user"]
        interfaces = (Node,)

    image = graphene.String()

    def resolve_image(self: InternalGroupUserHighlight, info, **kwargs):
        if self.image:
            return self.image.url
        else:
            return None

    @classmethod
    @gql_login_required()
    def get_node(cls, info, id):
        return InternalGroupPosition.objects.get(pk=id)


class CreateInternalGroupUserHighlightMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroupUserHighlight
        permissions = ("organization.add_internalgroupuserhighlight",)


class PatchInternalGroupUserHighlightMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroupUserHighlight
        permissions = ("organization.change_internalgroupuserhighlight",)


class DeleteInternalGroupUserHighlight(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupUserHighlight
        permissions = ("organization.delete_internalgroupuserhighlight",)


class InternalGroupUserHighlightQuery(graphene.ObjectType):
    all_internal_group_user_highlights = graphene.List(InternalGroupUserHighlightNode)
    internal_group_user_highlight = Node.Field(InternalGroupUserHighlightNode)
    internal_group_user_highlights_by_internal_group = graphene.List(
        InternalGroupUserHighlightNode, internal_group_id=graphene.ID()
    )

    @gql_login_required()
    def resolve_all_internal_group_user_highlights(self, info, *args, **kwargs):
        return InternalGroupUserHighlight.objects.all()

    @gql_login_required()
    def resolve_internal_group_user_highlights_by_internal_group(
        self, info, internal_group_id, *args, **kwargs
    ):
        internal_group_id = disambiguate_id(internal_group_id)
        return InternalGroupUserHighlight.objects.filter(
            internal_group__id=internal_group_id
        )


class OrganizationMutations(graphene.ObjectType):
    create_internal_group = CreateInternalGroupMutation.Field()
    patch_internal_group = PatchInternalGroupMutation.Field()
    delete_internal_group = DeleteInternalGroupMutation.Field()

    create_internal_group_position = CreateInternalGroupPositionMutation.Field()
    patch_internal_group_position = PatchInternalGroupPositionMutation.Field()
    delete_internal_group_position = DeleteInternalGroupPosition.Field()

    create_internal_group_user_highlight = (
        CreateInternalGroupUserHighlightMutation.Field()
    )
    patch_internal_group_user_highlight = (
        PatchInternalGroupUserHighlightMutation.Field()
    )
    delete_internal_group_user_highlight = DeleteInternalGroupUserHighlight.Field()

    create_internal_group_position_membership = (
        CreateInternalGroupPositionMembershipMutation.Field()
    )
    patch_internal_group_position_membership = (
        PatchInternalGroupPositionMembershipMutation.Field()
    )
    delete_internal_group_position_membership = (
        DeleteInternalGroupPositionMembership.Field()
    )

    assign_new_internal_group_position_membership = (
        AssignNewInternalGroupPositionMembership.Field()
    )

    quit_KSG = QuitKSGMutation.Field()
