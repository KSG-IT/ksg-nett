import datetime

from addict import Dict
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from organization.consts import InternalGroupPositionMembershipType
from schedules.models import (
    RoleOption,
    Shift,
    ShiftInterest,
    ShiftSlot,
    ShiftTemplate,
)
from schedules.permissions import can_manage_schedule
from schedules.tests.factories import (
    internal_group,
    member_of,
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftFactory,
    ShiftSlotFactory,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory

MANAGER_PERMISSIONS = (
    "schedules.change_schedule",
    "schedules.add_shift",
    "schedules.add_shiftslot",
    "schedules.change_shift",
    "schedules.delete_shift",
    "schedules.change_shiftslot",
    "schedules.add_shifttemplate",
)


def user_with_permissions(permissions=MANAGER_PERMISSIONS):
    count = UserWithPermissionsFactory._meta.model.objects.count()
    return UserWithPermissionsFactory.create(
        permissions=permissions, email=f"manager{count}@example.com"
    )


def manager_of(group, permissions=MANAGER_PERMISSIONS):
    user = user_with_permissions(permissions)
    member_of(user, group)
    return user


class TestCanManageSchedule(TestCase):
    def setUp(self) -> None:
        self.edgar = internal_group("Edgar")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=self.edgar)

    def can_manage(self, user):
        return can_manage_schedule(user, self.schedule, "schedules.change_schedule")

    def test__a_functionary_of_the_group_with_the_permission__can_manage(self):
        self.assertTrue(self.can_manage(manager_of(self.edgar)))

    def test__a_functionary_without_the_permission__cannot_manage(self):
        user = UserFactory.create()
        member_of(user, self.edgar)
        self.assertFalse(self.can_manage(user))

    def test__a_gang_member_with_the_permission__cannot_manage(self):
        user = user_with_permissions()
        member_of(user, self.edgar, InternalGroupPositionMembershipType.GANG_MEMBER)
        self.assertFalse(self.can_manage(user))

    def test__an_active_pang_with_the_permission__cannot_manage(self):
        user = user_with_permissions()
        member_of(
            user,
            self.edgar,
            InternalGroupPositionMembershipType.ACTIVE_FUNCTIONARY_PANG,
        )
        self.assertFalse(self.can_manage(user))

    def test__a_functionary_whose_membership_ended__cannot_manage(self):
        user = user_with_permissions()
        member_of(user, self.edgar, date_ended=datetime.date(2026, 6, 1))
        self.assertFalse(self.can_manage(user))

    def test__a_functionary_of_another_group__cannot_manage(self):
        self.assertFalse(self.can_manage(manager_of(internal_group("Lyche"))))

    def test__a_schedule_without_a_group__has_no_managers(self):
        user = manager_of(self.edgar)
        self.schedule.internal_group = None
        self.schedule.save()
        self.assertFalse(self.can_manage(user))

    def test__a_superuser__can_manage_without_a_membership(self):
        superuser = UserFactory.create(is_superuser=True)
        self.schedule.internal_group = None
        self.schedule.save()
        self.assertTrue(self.can_manage(superuser))

    def test__an_anonymous_user__cannot_manage(self):
        self.assertFalse(self.can_manage(AnonymousUser()))


class GraphQLTestCase(TestCase):
    def setUp(self) -> None:
        self.graphql_client = Client(schema)
        self.edgar = internal_group("Edgar")
        self.lyche = internal_group("Lyche")
        self.edgar_schedule = ScheduleFactory.create(
            name="Edgar", internal_group=self.edgar
        )
        self.lyche_schedule = ScheduleFactory.create(
            name="Lyche", internal_group=self.lyche
        )
        self.manager = manager_of(self.edgar)

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    def shift(self, schedule, days=3):
        start = timezone.now() + datetime.timedelta(days=days)
        return ShiftFactory.create(
            schedule=schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=6),
        )


class TestScheduleOverviewIsScoped(GraphQLTestCase):
    QUERY = """
        {
          allSchedules {
            name
            canManage
            plannedUntil
            upcomingSlots { total }
            recentLocations
          }
        }
    """

    def setUp(self) -> None:
        super().setUp()
        for schedule in (self.edgar_schedule, self.lyche_schedule):
            ShiftSlotFactory.create(
                shift=self.shift(schedule), user=None, role=RoleOption.BARISTA
            )

    def overview(self):
        executed = self.execute(self.QUERY)
        self.assertNotIn("errors", executed)
        return {row["name"]: row for row in executed["data"]["allSchedules"]}

    def test__the_own_schedule__has_the_overview_fields(self):
        edgar = self.overview()["Edgar"]
        self.assertTrue(edgar["canManage"])
        self.assertIsNotNone(edgar["plannedUntil"])
        self.assertEqual(edgar["upcomingSlots"], {"total": 1})
        self.assertEqual(edgar["recentLocations"], ["Edgar"])

    def test__a_schedule_of_another_group__has_empty_overview_fields(self):
        lyche = self.overview()["Lyche"]
        self.assertFalse(lyche["canManage"])
        self.assertIsNone(lyche["plannedUntil"])
        self.assertIsNone(lyche["upcomingSlots"])
        self.assertEqual(lyche["recentLocations"], [])

    def test__a_member__can_read_can_manage(self):
        executed = self.execute(
            "{ allSchedules { name canManage } }", user=UserFactory.create()
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(
            [row["canManage"] for row in executed["data"]["allSchedules"]],
            [False, False],
        )


class TestShiftMutationsAreScoped(GraphQLTestCase):
    CREATE = """
        mutation Create($input: CreateShiftWithSlotsInput!) {
          createShiftWithSlots(input: $input) { shift { id } }
        }
    """

    def create_variables(self, schedule):
        return {
            "input": {
                "scheduleId": to_global_id("ScheduleNode", schedule.pk),
                "name": "Kveld",
                "date": "2026-10-09",
                "startTime": "16:00:00",
                "endTime": "23:00:00",
                "slots": [{"shiftSlotRole": "BARISTA", "count": 1}],
            }
        }

    def test__create_shift_with_slots__in_the_own_schedule__works(self):
        executed = self.execute(self.CREATE, self.create_variables(self.edgar_schedule))
        self.assertNotIn("errors", executed)
        self.assertEqual(Shift.objects.get().schedule, self.edgar_schedule)

    def test__create_shift_with_slots__in_another_schedule__is_denied(self):
        executed = self.execute(self.CREATE, self.create_variables(self.lyche_schedule))
        self.assertIn("errors", executed)
        self.assertEqual(Shift.objects.count(), 0)

    def test__a_superuser__can_create_in_any_schedule(self):
        self.lyche_schedule.internal_group = None
        self.lyche_schedule.save()
        executed = self.execute(
            self.CREATE,
            self.create_variables(self.lyche_schedule),
            user=UserFactory.create(is_superuser=True),
        )
        self.assertNotIn("errors", executed)

    def test__add_user_to_a_slot_in_another_schedule__is_denied(self):
        slot = ShiftSlotFactory.create(
            shift=self.shift(self.lyche_schedule), user=None, role=RoleOption.BARISTA
        )
        executed = self.execute(
            """
            mutation Add($slot: ID!, $user: ID!) {
              addUserToShiftSlot(shiftSlotId: $slot, userId: $user) { shiftSlot { id } }
            }
            """,
            {
                "slot": to_global_id("ShiftSlotNode", slot.pk),
                "user": to_global_id("UserNode", self.manager.pk),
            },
        )
        self.assertIn("errors", executed)
        slot.refresh_from_db()
        self.assertIsNone(slot.user)

    def test__delete_a_shift_in_another_schedule__is_denied(self):
        shift = self.shift(self.lyche_schedule)
        executed = self.execute(
            "mutation Delete($id: ID!) { deleteShift(id: $id) { found } }",
            {"id": to_global_id("ShiftNode", shift.pk)},
        )
        self.assertIn("errors", executed)
        self.assertTrue(Shift.objects.filter(pk=shift.pk).exists())

    def test__patch_a_shift_into_another_schedule__is_denied(self):
        shift = self.shift(self.edgar_schedule)
        executed = self.execute(
            """
            mutation Patch($id: ID!, $input: PatchShiftInput!) {
              patchShift(id: $id, input: $input) { shift { id } }
            }
            """,
            {
                "id": to_global_id("ShiftNode", shift.pk),
                "input": {
                    "schedule": to_global_id("ScheduleNode", self.lyche_schedule.pk)
                },
            },
        )
        self.assertIn("errors", executed)
        shift.refresh_from_db()
        self.assertEqual(shift.schedule, self.edgar_schedule)

    def test__create_a_shift_template_for_another_schedule__is_denied(self):
        template = ScheduleTemplateFactory.create(schedule=self.lyche_schedule)
        executed = self.execute(
            """
            mutation Create($input: CreateShiftTemplateInput!) {
              createShiftTemplate(input: $input) { shiftTemplate { id } }
            }
            """,
            {
                "input": {
                    "name": "Kveld",
                    "scheduleTemplate": to_global_id(
                        "ScheduleTemplateNode", template.pk
                    ),
                    "day": "MONDAY",
                    "timeStart": "16:00:00",
                    "timeEnd": "23:00:00",
                }
            },
        )
        self.assertIn("errors", executed)
        self.assertEqual(ShiftTemplate.objects.count(), 0)

    def test__patch_schedule__cannot_set_the_internal_group(self):
        executed = self.execute(
            """
            mutation Patch($id: ID!, $input: PatchScheduleInput!) {
              patchSchedule(id: $id, input: $input) { schedule { id } }
            }
            """,
            {
                "id": to_global_id("ScheduleNode", self.edgar_schedule.pk),
                "input": {
                    "internalGroup": to_global_id("InternalGroupNode", self.lyche.pk)
                },
            },
        )
        self.assertIn("errors", executed)
        self.edgar_schedule.refresh_from_db()
        self.assertEqual(self.edgar_schedule.internal_group, self.edgar)


class TestShiftInterestsAreHidden(GraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.shift_obj = self.shift(self.edgar_schedule)
        self.anna = UserFactory.create()
        self.bob = UserFactory.create()
        for user in (self.anna, self.bob):
            ShiftInterest.objects.create(
                shift=self.shift_obj,
                user=user,
                interest_type=ShiftInterest.InterestTypes.UNAVAILABLE,
            )

    def interests_on_shift(self, user):
        executed = self.execute(
            '{ shift(id: "%s") { interests { edges { node { user { id } } } } } }'
            % to_global_id("ShiftNode", self.shift_obj.pk),
            user=user,
        )
        self.assertNotIn("errors", executed)
        edges = executed["data"]["shift"]["interests"]["edges"]
        return [edge["node"]["user"]["id"] for edge in edges]

    def test__a_member__sees_only_the_own_interest_on_a_shift(self):
        self.assertEqual(
            self.interests_on_shift(self.anna),
            [to_global_id("UserNode", self.anna.pk)],
        )

    def test__a_manager__sees_all_interests_on_a_shift(self):
        self.assertEqual(len(self.interests_on_shift(self.manager)), 2)

    def test__a_manager_of_another_group__sees_none(self):
        self.assertEqual(self.interests_on_shift(manager_of(self.lyche)), [])

    def test__a_member__cannot_read_the_interests_of_another_user(self):
        executed = self.execute(
            '{ user(id: "%s") { shiftinterestSet { edges { node { id } } } } }'
            % to_global_id("UserNode", self.bob.pk),
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["user"]["shiftinterestSet"]["edges"], [])

    def test__a_member__reads_the_own_interests(self):
        executed = self.execute(
            "{ me { shiftinterestSet { edges { node { id } } } } }", user=self.anna
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(len(executed["data"]["me"]["shiftinterestSet"]["edges"]), 1)
