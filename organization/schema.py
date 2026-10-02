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

    admission_membership_type = graphene.String()

    def resolve_admission_membership_type(
        self: InternalGroupPosition, info, *args, **kwargs
    ):
        # This rarely changes ever
        from admissions.models import Admission

        active_admission = Admission.get_active_admission()

        data_instance = self.admission_data_instances.filter(
            admission=active_admission
        ).first()

        if not data_instance:
            raise RuntimeError(
                "`data_instance` is None. Cannot determing membership type"
            )

        return data_instance.membership_type

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
    internal_group_positions_by_internal_group = graphene.List(
        InternalGroupPositionNode, internal_group_id=graphene.ID()
    )

    def resolve_all_internal_group_positions(self, info, *args, **kwargs):
        return InternalGroupPosition.objects.all()

    def resolve_internal_group_positions_by_internal_group(
        self, info, internal_group_id, **kwargs
    ):
        internal_group_id = disambiguate_id(internal_group_id)
        return InternalGroupPosition.objects.filter(
            internal_group__id=internal_group_id
        ).order_by("name")


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


class MembershipHistoryInput(graphene.InputObjectType):
    id = graphene.ID()
    position_id = graphene.ID(required=True)
    type = InternalGroupPositionTypeEnum(required=True)
    date_joined = graphene.Date(required=True)
    date_ended = graphene.Date()


class MembershipHistoryError(graphene.ObjectType):
    index = graphene.Int()
    message = graphene.String()


def validate_membership_history(rows):
    """
    Returns a list of (index, message) for rows that break a timeline rule.
    Each row is a dict with "position", "date_joined" and "date_ended".
    Only memberships in internal groups count for overlaps and the open
    membership, the same as User.current_internal_group_position_membership.
    """
    errors = []
    for index, row in enumerate(rows):
        if row["date_ended"] and row["date_ended"] < row["date_joined"]:
            errors.append((index, "The end date is before the start date"))

    internal_rows = [
        (index, row)
        for index, row in enumerate(rows)
        if row["position"].internal_group.type == InternalGroup.Type.INTERNAL_GROUP
    ]

    open_rows = [index for index, row in internal_rows if not row["date_ended"]]
    for index in open_rows[1:]:
        errors.append(
            (index, "Only one membership in an internal group can be current")
        )

    # A membership may start on the day the previous one ended, which is what
    # AssignNewInternalGroupPositionMembership does.
    for a, (index_a, row_a) in enumerate(internal_rows):
        for index_b, row_b in internal_rows[a + 1 :]:
            a_starts_before_b_ends = (
                row_b["date_ended"] is None
                or row_a["date_joined"] < row_b["date_ended"]
            )
            b_starts_before_a_ends = (
                row_a["date_ended"] is None
                or row_b["date_joined"] < row_a["date_ended"]
            )
            if a_starts_before_b_ends and b_starts_before_a_ends:
                errors.append(
                    (index_b, f"Overlaps with membership number {index_a + 1}")
                )

    return errors


class SetUserMembershipHistoryMutation(graphene.Mutation):
    """
    Replaces the whole membership history of a user. Rows with an id are
    updated, rows without an id are created, and memberships that are not in
    the input are deleted. Nothing is saved when a row breaks a rule. The
    Funksjonær user type is not changed, because a correction is not a new
    position.
    """

    class Arguments:
        user_id = graphene.ID(required=True)
        memberships = graphene.List(
            graphene.NonNull(MembershipHistoryInput), required=True
        )

    memberships = graphene.List(InternalGroupPositionMembershipNode)
    errors = graphene.List(graphene.NonNull(MembershipHistoryError))

    @gql_has_permissions(
        "organization.add_internalgrouppositionmembership",
        "organization.change_internalgrouppositionmembership",
        "organization.delete_internalgrouppositionmembership",
    )
    def mutate(self, info, user_id, memberships, *args, **kwargs):
        user = User.objects.get(pk=disambiguate_id(user_id))
        existing = {
            membership.pk: membership
            for membership in user.internal_group_position_history.all()
        }

        rows = []
        input_errors = []
        for index, membership in enumerate(memberships):
            membership_id = (
                int(disambiguate_id(membership.id)) if membership.id else None
            )
            if membership_id is not None and membership_id not in existing:
                input_errors.append((index, "The membership is not on this user"))
            position = (
                InternalGroupPosition.objects.select_related("internal_group")
                .filter(pk=disambiguate_id(membership.position_id))
                .first()
            )
            if position is None:
                input_errors.append((index, "The position does not exist"))
                continue
            rows.append(
                {
                    "index": index,
                    "id": membership_id,
                    "position": position,
                    "type": membership.type.value,
                    "date_joined": membership.date_joined,
                    "date_ended": membership.date_ended,
                }
            )

        errors = input_errors
        if not errors:
            errors = [
                (rows[row_index]["index"], message)
                for row_index, message in validate_membership_history(rows)
            ]
        if errors:
            return SetUserMembershipHistoryMutation(
                memberships=None,
                errors=[
                    MembershipHistoryError(index=index, message=message)
                    for index, message in sorted(errors)
                ],
            )

        kept_ids = {row["id"] for row in rows if row["id"] is not None}
        with transaction.atomic():
            InternalGroupPositionMembership.objects.filter(user=user).exclude(
                pk__in=kept_ids
            ).delete()
            for row in rows:
                membership = existing.get(
                    row["id"], InternalGroupPositionMembership(user=user)
                )
                membership.position = row["position"]
                membership.type = row["type"]
                membership.date_joined = row["date_joined"]
                membership.date_ended = row["date_ended"]
                membership.save()

        return SetUserMembershipHistoryMutation(
            memberships=user.internal_group_position_history.order_by("-date_joined"),
            errors=[],
        )


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
        InternalGroupUserHighlightNode,
        internal_group_id=graphene.ID(),
        include_archived=graphene.Boolean(),
    )

    @gql_login_required()
    def resolve_all_internal_group_user_highlights(self, info, *args, **kwargs):
        return InternalGroupUserHighlight.objects.all()

    @gql_login_required()
    def resolve_internal_group_user_highlights_by_internal_group(
        self, info, internal_group_id, include_archived, *args, **kwargs
    ):
        internal_group_id = disambiguate_id(internal_group_id)
        highlights = InternalGroupUserHighlight.objects.filter(
            internal_group__id=internal_group_id,
        )
        if not include_archived:
            highlights = highlights.filter(archived=False)

        return highlights


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

    set_user_membership_history = SetUserMembershipHistoryMutation.Field()

    quit_KSG = QuitKSGMutation.Field()
