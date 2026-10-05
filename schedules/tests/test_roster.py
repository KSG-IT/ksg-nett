import datetime

from addict import Dict
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from admissions.consts import AdmissionStatus
from admissions.models import Admission
from ksg_nett.schema import schema
from organization.consts import InternalGroupPositionMembershipType as Type
from schedules.models import (
    DefaultAvailability,
    RoleOption,
    ScheduleRoster,
    ScheduleRosterGrouping,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ShiftFactory,
    ShiftSlotFactory,
    internal_group,
    member_of,
    position_in,
)
from schedules.utils.roster import (
    RosterChange,
    annotate_shift_counts,
    apply_roster_sync,
    plan_roster_sync,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory


def grouping(schedule, position, position_type, role, default, cap=None):
    return ScheduleRosterGrouping.objects.create(
        schedule=schedule,
        internal_group_position=position,
        position_type=position_type,
        role=role,
        default_availability=default,
        shift_cap=cap,
    )


class RosterTestCase(TestCase):
    def setUp(self) -> None:
        self.edgar = internal_group("Edgar")
        self.barista = position_in(self.edgar, "Barista")
        self.kafe = position_in(self.edgar, "Kafeansvarlig")
        self.schedule = ScheduleFactory.create(name="Edgar", internal_group=self.edgar)
        self.gang = grouping(
            self.schedule,
            self.barista,
            Type.GANG_MEMBER,
            RoleOption.BARISTA,
            DefaultAvailability.AVAILABLE,
        )
        self.pang = grouping(
            self.schedule,
            self.barista,
            Type.ACTIVE_GANG_MEMBER_PANG,
            RoleOption.BARISTA,
            DefaultAvailability.OPT_IN,
            cap=1,
        )
        self.hangaround = grouping(
            self.schedule,
            self.barista,
            Type.HANGAROUND,
            RoleOption.BARISTA,
            DefaultAvailability.OPT_IN,
            cap=3,
        )
        self.functionary = grouping(
            self.schedule,
            self.kafe,
            Type.FUNCTIONARY,
            RoleOption.KAFEANSVARLIG,
            DefaultAvailability.AVAILABLE,
        )
        self.anna = UserFactory.create(email="anna@example.com")
        self.anna_membership = member_of(
            self.anna, self.edgar, Type.GANG_MEMBER, position=self.barista
        )
        self.per = UserFactory.create(email="per@example.com")
        member_of(
            self.per,
            self.edgar,
            Type.HANGAROUND,
            position=self.barista,
            date_joined=datetime.date(2026, 9, 2),
        )
        self.sara = UserFactory.create(email="sara@example.com")
        member_of(self.sara, self.edgar, Type.FUNCTIONARY, position=self.kafe)
        self.ola = UserFactory.create(email="ola@example.com")
        member_of(
            self.ola, self.edgar, Type.OLD_GANG_MEMBER_PANG, position=self.barista
        )

    def kinds(self, changes):
        return {(change.kind, change.user.pk) for change in changes}

    def row(self, user):
        return ScheduleRoster.objects.get(schedule=self.schedule, user=user)


class TestRosterSync(RosterTestCase):
    def test__the_preview__lists_new_rows_and_writes_nothing(self):
        changes = plan_roster_sync(self.schedule)
        self.assertEqual(
            self.kinds(changes),
            {
                (RosterChange.ADD, self.anna.pk),
                (RosterChange.ADD, self.per.pk),
                (RosterChange.ADD, self.sara.pk),
            },
        )
        self.assertEqual(ScheduleRoster.objects.count(), 0)

    def test__apply__copies_the_values_of_the_rule(self):
        apply_roster_sync(self.schedule)
        per = self.row(self.per)
        self.assertEqual(per.autofill_as, RoleOption.BARISTA)
        self.assertEqual(per.default_availability, DefaultAvailability.OPT_IN)
        self.assertEqual(per.shift_cap, 3)
        self.assertEqual(per.grouping, self.hangaround)
        self.assertEqual(per.count_from, datetime.date(2026, 9, 2))
        self.assertEqual(self.row(self.sara).autofill_as, RoleOption.KAFEANSVARLIG)

    def test__a_second_sync__has_no_changes(self):
        apply_roster_sync(self.schedule)
        self.assertEqual(plan_roster_sync(self.schedule), [])

    def test__a_changed_rule__changes_rows_that_are_not_edited(self):
        apply_roster_sync(self.schedule)
        self.gang.shift_cap = 2
        self.gang.save()
        self.assertEqual(
            self.kinds(apply_roster_sync(self.schedule)),
            {(RosterChange.CHANGE, self.anna.pk)},
        )
        self.assertEqual(self.row(self.anna).shift_cap, 2)

    def test__a_changed_rule__keeps_the_values_of_an_edited_row(self):
        apply_roster_sync(self.schedule)
        anna = self.row(self.anna)
        anna.shift_cap = 5
        anna.manually_edited = True
        anna.save()
        self.gang.shift_cap = 2
        self.gang.save()
        self.assertEqual(
            self.kinds(apply_roster_sync(self.schedule)),
            {(RosterChange.KEEP, self.anna.pk)},
        )
        self.assertEqual(self.row(self.anna).shift_cap, 5)

    def test__a_new_membership_type__changes_the_row_and_count_from(self):
        apply_roster_sync(self.schedule)
        self.anna_membership.date_ended = datetime.date(2026, 9, 1)
        self.anna_membership.save()
        member_of(
            self.anna,
            self.edgar,
            Type.ACTIVE_GANG_MEMBER_PANG,
            position=self.barista,
            date_joined=datetime.date(2026, 9, 2),
        )
        apply_roster_sync(self.schedule)
        anna = self.row(self.anna)
        self.assertEqual(anna.grouping, self.pang)
        self.assertEqual(anna.default_availability, DefaultAvailability.OPT_IN)
        self.assertEqual(anna.shift_cap, 1)
        self.assertEqual(anna.count_from, datetime.date(2026, 9, 2))

    def test__a_user_who_leaves__is_removed_also_when_edited(self):
        apply_roster_sync(self.schedule)
        ScheduleRoster.objects.filter(user=self.anna).update(manually_edited=True)
        self.anna_membership.date_ended = datetime.date(2026, 9, 1)
        self.anna_membership.save()
        self.assertEqual(
            self.kinds(apply_roster_sync(self.schedule)),
            {(RosterChange.REMOVE, self.anna.pk)},
        )
        self.assertFalse(ScheduleRoster.objects.filter(user=self.anna).exists())

    def test__a_user_with_no_matching_rule__is_removed(self):
        apply_roster_sync(self.schedule)
        self.anna_membership.date_ended = datetime.date(2026, 9, 1)
        self.anna_membership.save()
        member_of(
            self.anna, self.edgar, Type.OLD_GANG_MEMBER_PANG, position=self.barista
        )
        apply_roster_sync(self.schedule)
        self.assertFalse(ScheduleRoster.objects.filter(user=self.anna).exists())

    def test__rows_of_a_deleted_rule__are_removed(self):
        apply_roster_sync(self.schedule)
        self.hangaround.delete()
        self.assertEqual(
            self.kinds(apply_roster_sync(self.schedule)),
            {(RosterChange.REMOVE, self.per.pk)},
        )

    def test__a_manual_row__stays_while_the_user_is_in_the_group(self):
        ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=self.ola,
            autofill_as=RoleOption.BARISTA,
            default_availability=DefaultAvailability.OPT_IN,
            added_manually=True,
            manually_edited=True,
        )
        apply_roster_sync(self.schedule)
        self.assertTrue(ScheduleRoster.objects.filter(user=self.ola).exists())

    def test__a_manual_row__is_removed_when_the_user_leaves_the_group(self):
        ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=self.ola,
            autofill_as=RoleOption.BARISTA,
            default_availability=DefaultAvailability.OPT_IN,
            added_manually=True,
            manually_edited=True,
        )
        self.ola.internal_group_position_history.update(
            date_ended=datetime.date(2026, 9, 1)
        )
        apply_roster_sync(self.schedule)
        self.assertFalse(ScheduleRoster.objects.filter(user=self.ola).exists())

    def test__a_user_who_matches_two_rules__is_a_conflict(self):
        member_of(self.anna, self.edgar, Type.FUNCTIONARY, position=self.kafe)
        changes = apply_roster_sync(self.schedule)
        self.assertIn((RosterChange.CONFLICT, self.anna.pk), self.kinds(changes))
        self.assertFalse(ScheduleRoster.objects.filter(user=self.anna).exists())


class TestRosterShiftCounts(RosterTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.now = timezone.now()
        Admission.objects.create(
            date=(self.now - datetime.timedelta(days=40)).date(),
            status=AdmissionStatus.CLOSED,
            closed_at=self.now - datetime.timedelta(days=30),
        )
        apply_roster_sync(self.schedule)
        for days in (-35, -10, -2, 5):
            self.slot(self.anna, days)
        self.slot(self.per, -10)
        self.slot(self.per, 3)

    def slot(self, user, days):
        start = self.now + datetime.timedelta(days=days)
        shift = ShiftFactory.create(
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=5),
        )
        ShiftSlotFactory.create(shift=shift, user=user, role=RoleOption.BARISTA)
        return shift

    def counts(self, user):
        return annotate_shift_counts(ScheduleRoster.objects.filter(user=user)).get()

    def test__counts_shifts_since_the_admission_closed(self):
        anna = self.counts(self.anna)
        self.assertEqual((anna.shifts_done, anna.shifts_planned), (2, 1))

    def test__last_shift__is_the_latest_shift_that_has_started(self):
        anna = self.counts(self.anna)
        self.assertEqual(
            anna.last_shift.date(), (self.now - datetime.timedelta(days=2)).date()
        )

    def test__count_from__moves_the_start_later(self):
        ScheduleRoster.objects.filter(user=self.per).update(
            count_from=(self.now - datetime.timedelta(days=5)).date()
        )
        per = self.counts(self.per)
        self.assertEqual((per.shifts_done, per.shifts_planned), (0, 1))

    def test__a_user_without_shifts__has_zero(self):
        sara = self.counts(self.sara)
        self.assertEqual((sara.shifts_done, sara.shifts_planned), (0, 0))
        self.assertIsNone(sara.last_shift)


class TestRosterGraphQL(RosterTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.graphql_client = Client(schema)
        self.manager = UserWithPermissionsFactory.create(
            permissions="schedules.change_schedule", email="manager@example.com"
        )
        member_of(self.manager, self.edgar, Type.FUNCTIONARY)
        apply_roster_sync(self.schedule)
        self.schedule_id = to_global_id("ScheduleNode", self.schedule.pk)

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.manager)
        )

    ROSTER = """
        query Roster($id: ID!) {
          schedule(id: $id) {
            roster {
              user { id }
              autofillAs
              defaultAvailability
              shiftCap
              membershipType
              shiftsDone
              shiftsPlanned
            }
          }
        }
    """

    def roster(self, user=None):
        executed = self.execute(self.ROSTER, {"id": self.schedule_id}, user)
        self.assertNotIn("errors", executed)
        return executed["data"]["schedule"]["roster"]

    def test__a_manager__reads_the_whole_roster(self):
        rows = {row["user"]["id"]: row for row in self.roster()}
        self.assertEqual(len(rows), 3)
        per = rows[to_global_id("UserNode", self.per.pk)]
        self.assertEqual(per["defaultAvailability"], "OPT_IN")
        self.assertEqual(per["shiftCap"], 3)
        self.assertEqual(per["membershipType"], "hangaround")
        self.assertEqual((per["shiftsDone"], per["shiftsPlanned"]), (0, 0))

    def test__a_member__reads_only_the_own_row(self):
        rows = self.roster(user=self.anna)
        self.assertEqual(
            [row["user"]["id"] for row in rows],
            [to_global_id("UserNode", self.anna.pk)],
        )

    def test__a_member__cannot_read_the_rosters_of_another_user(self):
        executed = self.execute(
            '{ user(id: "%s") { rosters { edges { node { id } } } } }'
            % to_global_id("UserNode", self.per.pk),
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["user"]["rosters"]["edges"], [])

    def test__the_sync_preview__needs_a_manager(self):
        query = '{ schedule(id: "%s") { rosterSyncPreview { kind } } }' % (
            self.schedule_id
        )
        self.assertIn("errors", self.execute(query, user=self.anna))
        executed = self.execute(query)
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["schedule"]["rosterSyncPreview"], [])

    def test__sync_schedule_roster__applies_the_changes(self):
        ScheduleRoster.objects.all().delete()
        executed = self.execute(
            """
            mutation Sync($id: ID!) {
              syncScheduleRoster(scheduleId: $id) { changes { kind user { id } } }
            }
            """,
            {"id": self.schedule_id},
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(len(executed["data"]["syncScheduleRoster"]["changes"]), 3)
        self.assertEqual(ScheduleRoster.objects.count(), 3)

    UPDATE = """
        mutation Update($id: ID!, $input: UpdateScheduleRosterEntryInput!) {
          updateScheduleRosterEntry(id: $id, input: $input) {
            entry { shiftCap manuallyEdited }
          }
        }
    """

    def test__update_schedule_roster_entry__marks_the_row_as_edited(self):
        executed = self.execute(
            self.UPDATE,
            {
                "id": to_global_id("ScheduleRosterNode", self.row(self.per).pk),
                "input": {"shiftCap": 2},
            },
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(
            executed["data"]["updateScheduleRosterEntry"]["entry"],
            {"shiftCap": 2, "manuallyEdited": True},
        )

    def test__update_schedule_roster_entry__needs_a_manager(self):
        executed = self.execute(
            self.UPDATE,
            {
                "id": to_global_id("ScheduleRosterNode", self.row(self.per).pk),
                "input": {"shiftCap": 9},
            },
            user=self.anna,
        )
        self.assertIn("errors", executed)
        self.assertEqual(self.row(self.per).shift_cap, 3)

    def test__add_and_remove_a_roster_entry_by_hand(self):
        executed = self.execute(
            """
            mutation Add($input: AddScheduleRosterEntryInput!) {
              addScheduleRosterEntry(input: $input) { entry { id addedManually } }
            }
            """,
            {
                "input": {
                    "scheduleId": self.schedule_id,
                    "userId": to_global_id("UserNode", self.ola.pk),
                    "autofillAs": "BARISTA",
                    "defaultAvailability": "OPT_IN",
                    "shiftCap": 1,
                }
            },
        )
        self.assertNotIn("errors", executed)
        entry = executed["data"]["addScheduleRosterEntry"]["entry"]
        self.assertTrue(entry["addedManually"])
        executed = self.execute(
            "mutation Remove($id: ID!) { removeScheduleRosterEntry(id: $id) { found } }",
            {"id": entry["id"]},
        )
        self.assertNotIn("errors", executed)
        self.assertFalse(ScheduleRoster.objects.filter(user=self.ola).exists())

    CREATE_GROUPING = """
        mutation Create($input: CreateScheduleRosterGroupingInput!) {
          createScheduleRosterGrouping(input: $input) { grouping { id } }
        }
    """

    def grouping_input(self, position):
        return {
            "input": {
                "scheduleId": self.schedule_id,
                "internalGroupPositionId": to_global_id(
                    "InternalGroupPositionNode", position.pk
                ),
                "positionType": "INTEREST_GROUP_MEMBER",
                "role": "BARISTA",
                "defaultAvailability": "OPT_IN",
                "shiftCap": 1,
            }
        }

    def test__create_schedule_roster_grouping__for_a_position_of_the_group(self):
        executed = self.execute(self.CREATE_GROUPING, self.grouping_input(self.barista))
        self.assertNotIn("errors", executed)
        self.assertEqual(ScheduleRosterGrouping.objects.count(), 5)

    def test__create_schedule_roster_grouping__refuses_a_position_of_another_group(
        self,
    ):
        lyche_position = position_in(internal_group("Lyche"))
        executed = self.execute(
            self.CREATE_GROUPING, self.grouping_input(lyche_position)
        )
        self.assertIn("errors", executed)
        self.assertEqual(ScheduleRosterGrouping.objects.count(), 4)

    def test__a_member__cannot_read_the_rules(self):
        executed = self.execute(
            '{ schedule(id: "%s") { rosterGroupings { id } } }' % self.schedule_id,
            user=self.anna,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["schedule"]["rosterGroupings"], [])
