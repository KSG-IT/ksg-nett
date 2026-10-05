import datetime
from zoneinfo import ZoneInfo

from addict import Dict
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
from graphql_relay import to_global_id

from ksg_nett.schema import schema
from schedules.models import (
    DefaultAvailability,
    PlanningPeriod,
    RoleOption,
    ScheduleRoster,
    ShiftInterest,
    ShiftTemplate,
    UserUnavailability,
)
from schedules.tests.factories import (
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftFactory,
    ShiftTemplateFactory,
)
from schedules.utils.unavailability import (
    blocks,
    prefill_period,
    prefill_roster_row,
    prefill_shift,
    prefill_user,
)
from users.tests.factories import UserFactory, UserWithPermissionsFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)
Day = ShiftTemplate.Day


def local(day, hour, minute=0):
    return datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=LOCAL)


def next_weekday(weekday, after):
    """The first date with this weekday (0 = Monday) after the date."""
    return after + datetime.timedelta(days=(weekday - after.weekday()) % 7 or 7)


def entry(user, day, start, end, note=""):
    return UserUnavailability.objects.create(
        user=user,
        day=day,
        time_start=datetime.time(*start),
        time_end=datetime.time(*end),
        note=note,
    )


class TestBlocks(TestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.tuesday = datetime.date(2026, 10, 20)

    def shift(self, day, start_hour, hours):
        start = local(day, start_hour)
        return ShiftFactory.build(
            datetime_start=start, datetime_end=start + datetime.timedelta(hours=hours)
        )

    def test__an_entry__blocks_overlapping_shifts_on_its_weekday(self):
        lecture = entry(self.user, Day.TUESDAY, (14, 15), (18, 0))
        self.assertTrue(blocks(lecture, self.shift(self.tuesday, 10, 5)))
        self.assertTrue(blocks(lecture, self.shift(self.tuesday, 15, 5)))
        wednesday = self.tuesday + datetime.timedelta(days=1)
        self.assertFalse(blocks(lecture, self.shift(wednesday, 15, 5)))

    def test__an_entry_that_only_touches_a_shift__does_not_block_it(self):
        lecture = entry(self.user, Day.TUESDAY, (8, 0), (10, 0))
        self.assertFalse(blocks(lecture, self.shift(self.tuesday, 10, 5)))

    def test__an_entry_past_midnight__blocks_a_shift_on_the_next_day(self):
        night = entry(self.user, Day.MONDAY, (22, 0), (2, 0))
        self.assertTrue(blocks(night, self.shift(self.tuesday, 1, 2)))
        self.assertFalse(blocks(night, self.shift(self.tuesday, 3, 2)))

    def test__a_shift_past_midnight__is_checked_against_the_next_day(self):
        early = entry(self.user, Day.WEDNESDAY, (0, 30), (1, 30))
        self.assertTrue(blocks(early, self.shift(self.tuesday, 20, 7)))

    def test__the_night_the_clock_goes_back__works(self):
        # Summer time ends on Sunday 2026-10-25 at 03:00
        night = entry(self.user, Day.SUNDAY, (1, 0), (4, 0))
        self.assertTrue(blocks(night, self.shift(datetime.date(2026, 10, 25), 2, 1)))


class PrefillTestCase(TestCase):
    def setUp(self) -> None:
        self.schedule = ScheduleFactory.create(name="Edgar")
        self.anna = UserFactory.create(email="anna@example.com")
        self.per = UserFactory.create(email="per@example.com")
        self.roster(self.anna, DefaultAvailability.AVAILABLE)
        self.roster(self.per, DefaultAvailability.OPT_IN)
        today = timezone.localdate()
        self.tuesday = next_weekday(1, today + datetime.timedelta(days=7))
        self.tuesday_shift = self.shift_on(self.tuesday, 15)
        self.wednesday_shift = self.shift_on(
            self.tuesday + datetime.timedelta(days=1), 15
        )

    def roster(self, user, default):
        return ScheduleRoster.objects.create(
            schedule=self.schedule,
            user=user,
            autofill_as=RoleOption.BARISTA,
            default_availability=default,
        )

    def shift_on(self, day, hour):
        start = local(day, hour)
        return ShiftFactory.create(
            schedule=self.schedule,
            datetime_start=start,
            datetime_end=start + datetime.timedelta(hours=5),
        )

    def open_period(self):
        return PlanningPeriod.objects.create(
            schedule=self.schedule,
            date_from=self.tuesday - datetime.timedelta(days=1),
            date_to=self.tuesday + datetime.timedelta(days=5),
            deadline=timezone.now() + datetime.timedelta(days=3),
        )

    def answers(self, user=None):
        return {
            (interest.shift_id, interest.interest_type, interest.source, interest.note)
            for interest in ShiftInterest.objects.filter(user=user or self.anna)
        }

    def prefilled(self, shift, note=""):
        return (
            shift.pk,
            ShiftInterest.InterestTypes.UNAVAILABLE,
            ShiftInterest.Source.UNAVAILABILITY,
            note,
        )


class TestPrefill(PrefillTestCase):
    def test__a_period__is_prefilled_from_the_entries(self):
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0), note="Forelesning")
        prefill_period(self.open_period())
        self.assertEqual(
            self.answers(), {self.prefilled(self.tuesday_shift, "Forelesning")}
        )

    def test__a_user__is_prefilled_in_open_periods(self):
        self.open_period()
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        self.assertEqual(self.answers(), {self.prefilled(self.tuesday_shift)})

    def test__a_deleted_entry__removes_its_answers(self):
        self.open_period()
        lecture = entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        lecture.delete()
        prefill_user(self.anna.pk)
        self.assertEqual(self.answers(), set())

    def test__a_changed_entry__moves_its_answers(self):
        self.open_period()
        lecture = entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        lecture.day = Day.WEDNESDAY
        lecture.save()
        prefill_user(self.anna.pk)
        self.assertEqual(self.answers(), {self.prefilled(self.wednesday_shift)})

    def test__a_manual_answer__is_never_changed(self):
        self.open_period()
        ShiftInterest.objects.create(
            shift=self.tuesday_shift,
            user=self.anna,
            interest_type=ShiftInterest.InterestTypes.INTERESTED,
        )
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        self.assertEqual(
            self.answers(),
            {
                (
                    self.tuesday_shift.pk,
                    ShiftInterest.InterestTypes.INTERESTED,
                    ShiftInterest.Source.MANUAL,
                    "",
                )
            },
        )

    def test__two_entries__join_their_notes(self):
        self.open_period()
        entry(self.anna, Day.TUESDAY, (14, 15), (16, 0), note="Forelesning")
        entry(self.anna, Day.TUESDAY, (17, 0), (19, 0), note="Trening")
        prefill_user(self.anna.pk)
        self.assertEqual(
            self.answers(),
            {self.prefilled(self.tuesday_shift, "Forelesning; Trening")},
        )

    def test__a_closed_period__is_not_changed(self):
        period = self.open_period()
        period.deadline = timezone.now() - datetime.timedelta(minutes=1)
        period.save()
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        prefill_period(period)
        self.assertEqual(self.answers(), set())

    def test__an_opt_in_user__gets_no_prefill(self):
        self.open_period()
        entry(self.per, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.per.pk)
        self.assertEqual(self.answers(self.per), set())

    def test__a_shift__is_prefilled(self):
        self.open_period()
        entry(self.anna, Day.TUESDAY, (8, 0), (11, 0))
        morning = self.shift_on(self.tuesday, 10)
        prefill_shift(morning)
        self.assertEqual(self.answers(), {self.prefilled(morning)})

    def test__a_shift_with_a_new_time__loses_the_prefill(self):
        self.open_period()
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        prefill_user(self.anna.pk)
        self.tuesday_shift.datetime_start = local(self.tuesday, 19)
        self.tuesday_shift.datetime_end = local(self.tuesday, 23)
        self.tuesday_shift.save()
        prefill_shift(self.tuesday_shift)
        self.assertEqual(self.answers(), set())

    def test__a_roster_row__is_prefilled(self):
        self.open_period()
        sara = UserFactory.create(email="sara@example.com")
        entry(sara, Day.TUESDAY, (14, 15), (18, 0))
        prefill_roster_row(self.roster(sara, DefaultAvailability.AVAILABLE))
        self.assertEqual(self.answers(sara), {self.prefilled(self.tuesday_shift)})

    def test__the_roster_sync__prefills_new_rows(self):
        from organization.consts import InternalGroupPositionMembershipType as Type
        from schedules.models import ScheduleRosterGrouping
        from schedules.tests.factories import internal_group, member_of, position_in
        from schedules.utils.roster import apply_roster_sync

        self.open_period()
        group = internal_group("Bærevakt")
        position = position_in(group)
        ScheduleRosterGrouping.objects.create(
            schedule=self.schedule,
            internal_group_position=position,
            position_type=Type.FUNCTIONARY,
            role=RoleOption.BARISTA,
            default_availability=DefaultAvailability.AVAILABLE,
        )
        sara = UserFactory.create(email="sara@example.com")
        member_of(sara, group, Type.FUNCTIONARY, position=position)
        entry(sara, Day.TUESDAY, (14, 15), (18, 0))
        apply_roster_sync(self.schedule)
        self.assertEqual(self.answers(sara), {self.prefilled(self.tuesday_shift)})


class TestPrefillTriggers(PrefillTestCase):
    """Each mutation that changes what the pre-fill reads runs the pre-fill."""

    def setUp(self) -> None:
        super().setUp()
        self.graphql_client = Client(schema)
        self.manager = UserWithPermissionsFactory.create(
            permissions=(
                "schedules.change_schedule",
                "schedules.add_shift",
                "schedules.add_shiftslot",
                "schedules.change_shift",
            ),
            email="manager@example.com",
        )
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))

    def execute(self, query, variables):
        executed = self.graphql_client.execute(
            query, variables=variables, context=Dict(user=self.manager)
        )
        self.assertNotIn("errors", executed)
        return executed

    def schedule_id(self):
        return to_global_id("ScheduleNode", self.schedule.pk)

    def test__create_planning_period(self):
        self.execute(
            """
            mutation Create($input: CreatePlanningPeriodInput!) {
              createPlanningPeriod(input: $input) { planningPeriod { id } }
            }
            """,
            {
                "input": {
                    "scheduleId": self.schedule_id(),
                    "dateFrom": self.tuesday.isoformat(),
                    "dateTo": self.tuesday.isoformat(),
                    "deadline": (
                        timezone.now() + datetime.timedelta(days=1)
                    ).isoformat(),
                }
            },
        )
        self.assertEqual(self.answers(), {self.prefilled(self.tuesday_shift)})

    def test__create_shift_with_slots(self):
        self.open_period()
        self.execute(
            """
            mutation Create($input: CreateShiftWithSlotsInput!) {
              createShiftWithSlots(input: $input) { shift { id } }
            }
            """,
            {
                "input": {
                    "scheduleId": self.schedule_id(),
                    "name": "Morgen",
                    "date": self.tuesday.isoformat(),
                    "startTime": "13:00:00",
                    "endTime": "15:00:00",
                    "slots": [],
                }
            },
        )
        self.assertEqual(len(self.answers()), 1)

    def test__update_shift_details(self):
        self.open_period()
        prefill_user(self.anna.pk)
        self.execute(
            """
            mutation Update($input: UpdateShiftDetailsInput!) {
              updateShiftDetails(input: $input) { shift { id } }
            }
            """,
            {
                "input": {
                    "shiftId": to_global_id("ShiftNode", self.tuesday_shift.pk),
                    "name": "Sen",
                    "date": self.tuesday.isoformat(),
                    "startTime": "19:00:00",
                    "endTime": "23:00:00",
                }
            },
        )
        self.assertEqual(self.answers(), set())

    def test__generate_shifts_from_template(self):
        self.tuesday_shift.delete()
        self.open_period()
        template = ScheduleTemplateFactory.create(schedule=self.schedule)
        ShiftTemplateFactory.create(
            schedule_template=template,
            day=Day.TUESDAY,
            time_start=datetime.time(15),
            time_end=datetime.time(20),
        )
        self.execute(
            """
            mutation Generate($id: ID!, $start: Date!) {
              generateShiftsFromTemplate(
                scheduleTemplateId: $id, startDate: $start, numberOfWeeks: 1
              ) { shiftsCreated }
            }
            """,
            {
                "id": to_global_id("ScheduleTemplateNode", template.pk),
                "start": (self.tuesday - datetime.timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(len(self.answers()), 1)

    def test__add_schedule_roster_entry(self):
        self.open_period()
        sara = UserFactory.create(email="sara@example.com")
        entry(sara, Day.TUESDAY, (14, 15), (18, 0))
        self.execute(
            """
            mutation Add($input: AddScheduleRosterEntryInput!) {
              addScheduleRosterEntry(input: $input) { entry { id } }
            }
            """,
            {
                "input": {
                    "scheduleId": self.schedule_id(),
                    "userId": to_global_id("UserNode", sara.pk),
                    "autofillAs": "BARISTA",
                    "defaultAvailability": "AVAILABLE",
                }
            },
        )
        self.assertEqual(self.answers(sara), {self.prefilled(self.tuesday_shift)})


class TestUnavailabilityGraphQL(PrefillTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.graphql_client = Client(schema)
        self.open_period()

    def execute(self, query, variables=None, user=None):
        return self.graphql_client.execute(
            query, variables=variables, context=Dict(user=user or self.anna)
        )

    CREATE = """
        mutation Create($input: CreateUserUnavailabilityInput!) {
          createUserUnavailability(input: $input) {
            unavailability { id day timeStart timeEnd note blockedShiftCount }
          }
        }
    """

    def create(self, **overrides):
        variables = {
            "input": {
                "day": "TUESDAY",
                "timeStart": "14:15:00",
                "timeEnd": "18:00:00",
                "note": "Forelesning",
                **overrides,
            }
        }
        return self.execute(self.CREATE, variables)

    def test__a_user__adds_an_entry_and_sees_the_blocked_shifts(self):
        executed = self.create()
        self.assertNotIn("errors", executed)
        created = executed["data"]["createUserUnavailability"]["unavailability"]
        self.assertEqual(created["day"], "TUESDAY")
        self.assertEqual(created["blockedShiftCount"], 1)
        self.assertEqual(
            self.answers(), {self.prefilled(self.tuesday_shift, "Forelesning")}
        )

    def test__an_entry_without_length__is_refused(self):
        self.assertIn("errors", self.create(timeEnd="14:15:00"))
        self.assertEqual(UserUnavailability.objects.count(), 0)

    def test__my_unavailabilities__are_sorted_by_weekday(self):
        entry(self.anna, Day.FRIDAY, (8, 0), (10, 0))
        entry(self.anna, Day.MONDAY, (8, 0), (10, 0))
        entry(self.per, Day.TUESDAY, (8, 0), (10, 0))
        executed = self.execute("{ myUnavailabilities { day } }")
        self.assertNotIn("errors", executed)
        self.assertEqual(
            [row["day"] for row in executed["data"]["myUnavailabilities"]],
            ["MONDAY", "FRIDAY"],
        )

    def test__a_user__cannot_change_the_entry_of_another_user(self):
        other = entry(self.per, Day.TUESDAY, (8, 0), (10, 0))
        executed = self.execute(
            """
            mutation Update($id: ID!, $input: UpdateUserUnavailabilityInput!) {
              updateUserUnavailability(id: $id, input: $input) { unavailability { id } }
            }
            """,
            {
                "id": to_global_id("UserUnavailabilityNode", other.pk),
                "input": {"note": "Hacked"},
            },
        )
        self.assertIn("errors", executed)
        other.refresh_from_db()
        self.assertEqual(other.note, "")

    def test__delete_user_unavailability__removes_the_entry_and_its_answers(self):
        lecture = entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        executed = self.execute(
            "mutation Delete($id: ID!) { deleteUserUnavailability(id: $id) { found } }",
            {"id": to_global_id("UserUnavailabilityNode", lecture.pk)},
        )
        self.assertNotIn("errors", executed)
        self.assertFalse(UserUnavailability.objects.exists())
        self.assertEqual(self.answers(), set())

    def test__the_preview__counts_the_shifts_an_entry_would_block(self):
        executed = self.execute(
            '{ unavailabilityPreview(day: TUESDAY, timeStart: "14:15:00",'
            ' timeEnd: "18:00:00") }'
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["unavailabilityPreview"], 1)
        self.assertFalse(UserUnavailability.objects.exists())

    def test__other_users__cannot_read_the_entries(self):
        entry(self.anna, Day.TUESDAY, (14, 15), (18, 0))
        executed = self.execute(
            '{ user(id: "%s") { unavailabilities { edges { node { id } } } } }'
            % to_global_id("UserNode", self.anna.pk),
            user=self.per,
        )
        self.assertNotIn("errors", executed)
        self.assertEqual(executed["data"]["user"]["unavailabilities"]["edges"], [])
