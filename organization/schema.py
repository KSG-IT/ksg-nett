import graphene
from django.db.models import Q
from graphene import Node
from graphene_django import DjangoObjectType, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField

from ksg_nett import settings
from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
    CommissionMembership,
    Commission,
    Committee,
)
from users.schema import UserNode
from users.models import User


class InternalGroupPositionMembershipData(graphene.ObjectType):
    internal_group_position_name = graphene.String()
    users = graphene.List(UserNode)




class InternalGroupNode(DjangoObjectType):
    class Meta:
        model = InternalGroup
        filter_fields = ['type', 'name']
        interfaces = (Node,)

    membership_data = graphene.List(InternalGroupPositionMembershipData)

    def resolve_membership_data(self: InternalGroup, info, *args, **kwargs):
        positions = self.positions.all()
        all_users = User.objects.all().filter(internal_group_position_history__position__internal_group=self, internal_group_position_history__date_ended__isnull=True)

        user_groupings = []
        for position in positions:
            position_grouping_object = InternalGroupPositionMembershipData(
                internal_group_position_name=position.name,
                users= all_users.filter(internal_group_position_history__position=position).order_by("first_name") # filter against this position internal_group_position_history__position
        )
            user_groupings.append(position_grouping_object)

        return user_groupings






    @classmethod
    def get_node(cls, info, id):
        return InternalGroup.objects.get(pk=id)

    def resolve_group_image(self: InternalGroup, info, **kwargs):
        if self.group_image:
            return f"{settings.HOST_URL}{self.group_image.url}"
        else:
            return None

    def resolve_group_icon(self: InternalGroup, info, **kwargs):
        if self.group_icon:
            return f"{settings.HOST_URL}{self.group_icon.url}"
        else:
            return None

class GroupType(graphene.Enum):
    INTERNAL_GROUP = InternalGroup.Type.INTERNAL_GROUP
    INTEREST_GROUP = InternalGroup.Type.INTEREST_GROUP

class InternalGroupPositionNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPosition
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return InternalGroupPosition.objects.get(pk=id)


class InternalGroupPositionMembershipNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPositionMembership
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return InternalGroupPositionMembership.objects.get(pk=id)


class CommissionMembershipNode(DjangoObjectType):
    class Meta:
        model = CommissionMembership
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return CommissionMembership.objects.get(pk=id)


class CommissionNode(DjangoObjectType):
    class Meta:
        model = Commission
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Commission.objects.get(pk=id)


class CommitteeNode(DjangoObjectType):
    class Meta:
        model = Committee
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Committee.objects.get(pk=id)


# QUERIES
class InternalGroupQuery(graphene.ObjectType):
    internal_group = Node.Field(InternalGroupNode)
    all_internal_groups = graphene.List(InternalGroupNode, Type=GroupType())

    def resolve_all_internal_groups(self, info, Type, **kwargs):
        return InternalGroup.objects.filter(type=Type)




class InternalGroupPositionQuery(graphene.ObjectType):
    internal_group_position = Node.Field(InternalGroupPositionNode)
    all_internal_group_positions = DjangoConnectionField(InternalGroupPositionNode)

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
    internal_group_position_memberships = graphene.List(InternalGroupPositionMembershipNode)

    def resolve_all_internal_group_position_memberships(self, info, *args, **kwargs):
        return InternalGroupPositionMembership.objects.all()

    def resolve_all_active_internal_group_position_memberships(
            self, info, *args, **kwargs
    ):
        return InternalGroupPositionMembership.objects.filter(
            date_ended__isnull=True
        ).order_by("date_joined")


class CommissionQuery(graphene.ObjectType):
    commission = Node.Field(CommissionNode)
    all_commissions = DjangoConnectionField(CommissionNode)

    def resolve_all_commissions(self, info, *args, **kwargs):
        return Commission.objects.all()


class CommissionMembershipQuery(graphene.ObjectType):
    commission_membership = Node.Field(CommissionMembershipNode)
    all_commission_memberships = DjangoConnectionField(CommissionMembershipNode)

    def resolve_all_commission_memberships(self, info, *args, **kwargs):
        return CommissionMembership.objects.all()


class CommitteeQuery(graphene.ObjectType):
    committee = Node.Field(CommitteeNode)
    all_committees = DjangoConnectionField(CommitteeNode)

    def resolve_all_committees(self, info, *args, **kwargs):
        return Committee.objects.all()


# MUTATIONS
class CreateInternalGroupMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroup


class PatchInternalGroupMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroup


class DeleteInternalGroupMutation(DjangoDeleteMutation):
    class Meta:
        model = InternalGroup


class CreateInternalGroupPositionMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroupPosition


class PatchInternalGroupPositionMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPosition


class DeleteInternalGroupPosition(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPosition


class CreateInternalGroupPositionMembershipMutation(DjangoCreateMutation):
    class Meta:
        model = InternalGroupPositionMembership


class PatchInternalGroupPositionMembershipMutation(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPositionMembership


class DeleteInternalGroupPositionMembership(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPositionMembership


class CreateCommissionMembershipMutation(DjangoCreateMutation):
    class Meta:
        model = CommissionMembership


class PatchCommissionMembershipMutation(DjangoPatchMutation):
    class Meta:
        model = CommissionMembership


class DeleteCommissionMembership(DjangoDeleteMutation):
    class Meta:
        model = CommissionMembership


class CreateCommissionMutation(DjangoCreateMutation):
    class Meta:
        model = Commission


class PatchCommissionMutation(DjangoPatchMutation):
    class Meta:
        model = Commission


class DeleteCommissionMutation(DjangoDeleteMutation):
    class Meta:
        model = Commission


class CreateCommitteeMutation(DjangoCreateMutation):
    class Meta:
        model = Committee


class PatchCommitteeMutation(DjangoPatchMutation):
    class Meta:
        model = Committee


class DeleteCommitteeMutation(DjangoDeleteMutation):
    class Meta:
        model = Committee


class OrganizationMutations(graphene.ObjectType):
    create_internal_group = CreateInternalGroupMutation.Field()
    patch_internal_group = PatchInternalGroupMutation.Field()
    delete_internal_group = DeleteInternalGroupMutation.Field()

    create_internal_group_position = CreateInternalGroupPositionMutation.Field()
    patch_internal_group_position = PatchInternalGroupPositionMutation.Field()
    delete_internal_group_position = DeleteInternalGroupPosition.Field()

    create_internal_group_position_membership = (
        CreateInternalGroupPositionMembershipMutation.Field()
    )
    patch_internal_group_position_membership = (
        PatchInternalGroupPositionMembershipMutation.Field()
    )
    delete_internal_group_position_membership = (
        DeleteInternalGroupPositionMembership.Field()
    )

    create_commission_membership = CreateCommissionMembershipMutation.Field()
    patch_commission_membership = PatchCommissionMembershipMutation.Field()
    delete_commission_membership = DeleteCommissionMembership.Field()

    create_commission = CreateCommissionMutation.Field()
    patch_commission = PatchCommissionMutation.Field()
    delete_commission = DeleteCommissionMutation.Field()

    create_committee = CreateCommitteeMutation.Field()
    patch_committee = PatchCommitteeMutation.Field()
    delete_committee = DeleteCommitteeMutation.Field()
