import datetime

from addict import Dict
from django.test import TestCase
from graphene import Node
from graphene.test import Client

from ksg_nett.schema import schema
from organization.consts import InternalGroupPositionMembershipType
from organization.models import InternalGroup, InternalGroupPositionMembership
from organization.tests.factories import (
    InternalGroupFactory,
    InternalGroupPositionFactory,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory

MUTATION = """
    mutation SetUserMembershipHistory(
      $userId: ID!
      $memberships: [MembershipHistoryInput!]!
    ) {
      setUserMembershipHistory(userId: $userId, memberships: $memberships) {
        memberships {
          id
          dateJoined
          dateEnded
        }
        errors {
          index
          message
        }
      }
    }
"""


def gid(node_name, pk):
    return Node.to_global_id(node_name, pk)


class TestSetUserMembershipHistoryMutation(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.editor = UserWithPermissionsFactory.create(
            permissions=(
                "organization.add_internalgrouppositionmembership",
                "organization.change_internalgrouppositionmembership",
                "organization.delete_internalgrouppositionmembership",
            )
        )
        self.user = UserFactory.create()
        gang = InternalGroupFactory.create(type=InternalGroup.Type.INTERNAL_GROUP)
        interest_group = InternalGroupFactory.create(
            type=InternalGroup.Type.INTEREST_GROUP
        )
        self.barista = InternalGroupPositionFactory.create(internal_group=gang)
        self.ka = InternalGroupPositionFactory.create(internal_group=gang)
        self.interest = InternalGroupPositionFactory.create(
            internal_group=interest_group
        )
        self.old = InternalGroupPositionMembership.objects.create(
            user=self.user,
            position=self.barista,
            type=InternalGroupPositionMembershipType.GANG_MEMBER,
            date_joined=datetime.date(2020, 1, 1),
            date_ended=None,
        )

    def row(self, position, joined, ended=None, membership=None):
        row = {
            "positionId": gid("InternalGroupPositionNode", position.pk),
            "type": "GANG_MEMBER",
            "dateJoined": joined,
            "dateEnded": ended,
        }
        if membership:
            row["id"] = gid("InternalGroupPositionMembershipNode", membership.pk)
        return row

    def execute(self, memberships, user=None):
        executed = self.graphql_client.execute(
            MUTATION,
            variables={
                "userId": gid("UserNode", self.user.pk),
                "memberships": memberships,
            },
            context=Dict(user=user or self.editor),
        )
        return executed

    def result(self, memberships):
        executed = self.execute(memberships)
        self.assertNotIn("errors", executed)
        return Dict(executed["data"]["setUserMembershipHistory"])

    def test__valid_history__updates_creates_and_deletes(self):
        to_delete = InternalGroupPositionMembership.objects.create(
            user=self.user,
            position=self.interest,
            type=InternalGroupPositionMembershipType.INTEREST_GROUP_MEMBER,
            date_joined=datetime.date(2019, 1, 1),
        )
        result = self.result(
            [
                self.row(self.barista, "2020-01-01", "2021-08-01", self.old),
                self.row(self.ka, "2021-08-01"),
            ]
        )

        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.memberships), 2)
        self.old.refresh_from_db()
        self.assertEqual(self.old.date_ended, datetime.date(2021, 8, 1))
        self.assertFalse(
            InternalGroupPositionMembership.objects.filter(pk=to_delete.pk).exists()
        )
        self.assertEqual(
            self.user.current_internal_group_position_membership.position, self.ka
        )

    def test__end_before_start__returns_error_and_saves_nothing(self):
        result = self.result(
            [self.row(self.barista, "2020-01-01", "2019-01-01", self.old)]
        )

        self.assertEqual(result.errors[0].index, 0)
        self.assertIsNone(result.memberships)
        self.old.refresh_from_db()
        self.assertIsNone(self.old.date_ended)

    def test__two_open_internal_group_memberships__returns_error(self):
        result = self.result(
            [
                self.row(self.barista, "2020-01-01", None, self.old),
                self.row(self.ka, "2021-01-01"),
            ]
        )

        self.assertEqual([error.index for error in result.errors], [1, 1])
        self.assertEqual(
            InternalGroupPositionMembership.objects.filter(user=self.user).count(), 1
        )

    def test__overlapping_internal_group_memberships__returns_error(self):
        result = self.result(
            [
                self.row(self.barista, "2020-01-01", "2021-01-01", self.old),
                self.row(self.ka, "2020-06-01", "2022-01-01"),
            ]
        )

        self.assertEqual(result.errors[0].index, 1)

    def test__interest_group_may_overlap_and_be_open(self):
        result = self.result(
            [
                self.row(self.barista, "2020-01-01", None, self.old),
                self.row(self.interest, "2020-06-01"),
            ]
        )

        self.assertEqual(result.errors, [])

    def test__membership_of_other_user__returns_error(self):
        other = InternalGroupPositionMembership.objects.create(
            user=UserFactory.create(),
            position=self.barista,
            type=InternalGroupPositionMembershipType.GANG_MEMBER,
            date_joined=datetime.date(2020, 1, 1),
        )
        result = self.result([self.row(self.barista, "2020-01-01", None, other)])

        self.assertEqual(result.errors[0].index, 0)
        other.refresh_from_db()
        self.assertNotEqual(other.user, self.user)

    def test__without_permission__returns_error(self):
        executed = self.execute(
            [self.row(self.barista, "2020-01-01", None, self.old)],
            user=UserFactory.create(),
        )

        self.assertIn("errors", executed)
