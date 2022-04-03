import datetime

import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField

from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
    CommissionMembership,
    Commission,
    Committee,
)
from graphene_django_cud.util import disambiguate_id
from users.models import User
from organization.graphql import InternalGroupPositionTypeEnum


class InternalGroupNode(DjangoObjectType):
    class Meta:
        model = InternalGroup
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return InternalGroup.objects.get(pk=id)


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
    all_internal_groups = graphene.List(InternalGroupNode)

    def resolve_all_internal_groups(self, info, *args, **kwargs):
        return InternalGroup.objects.all().order_by("name")


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


class AssignNewInternalGroupPositionMembership(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        internal_group_position_id = graphene.ID()
        internal_group_position_type = InternalGroupPositionTypeEnum()

    internal_group_position_membership = graphene.Field(
        InternalGroupPositionMembershipNode
    )

    def mutate(
        self,
        info,
        user_id,
        internal_group_position_id,
        internal_group_position_type,
        *args,
        **kwargs
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
                type=internal_group_position_type,
                position=internal_group_position,
                date_joined=datetime.date.today(),
            )
        )

        return AssignNewInternalGroupPositionMembership(
            internal_group_position_membership=new_internal_group_position_membership
        )


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

    assign_new_internal_group_position_membership = (
        AssignNewInternalGroupPositionMembership.Field()
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
