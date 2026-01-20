import datetime

import pytz
from django.test import TestCase
from django.utils.timezone import make_aware
from django.core import mail

from schedules.utils.templates import (
    apply_schedule_template,
    shift_template_timestamps_to_datetime,
)
from schedules.utils.schedules import send_given_shift_email
from schedules.tests.factories import (
    ScheduleFactory,
    ScheduleTemplateFactory,
    ShiftTemplateFactory,
    ShiftSlotTemplateFactory,
    ShiftFactory,
    ShiftSlotFactory,
    ShiftInterestFactory,
    ScheduleRosterGroupingFactory,
)
from organization.consts import InternalGroupPositionMembershipType
from organization.tests.factories import (
    InternalGroupPositionFactory,
    InternalGroupPositionMembershipFactory,
)
from users.models import User
from schedules.models import (
    ShiftTemplate,
    ShiftSlot,
    RoleOption,
    ShiftInterest,
    Schedule,
)
from users.tests.factories import UserFactory


class TestScheduleTemplateShiftTemplateTimestampsToDatetimeHelper(TestCase):
    def setUp(self) -> None:
        self.schedule = ScheduleFactory.create(name="Edgar")
        barista = InternalGroupPositionFactory.create(name="Barista")
        kafeansvarlig = InternalGroupPositionFactory.create(name="Kafeansvarlig")

        self.barista_active_gang_member_roster = ScheduleRosterGroupingFactory.create(
            schedule=self.schedule,
            internal_group_position=barista,
            role=RoleOption.BARISTA,
            position_type=InternalGroupPositionMembershipType.GANG_MEMBER,
            default_availability=ShiftInterest.InterestTypes.AVAILABLE,
        )
        self.barista_hangaround_roster = ScheduleRosterGroupingFactory.create(
            schedule=self.schedule,
            internal_group_position=barista,
            role=RoleOption.BARISTA,
            position_type=InternalGroupPositionMembershipType.HANGAROUND,
            default_availability=ShiftInterest.InterestTypes.UNAVAILABLE,
        )
        self.kafeansvarlige_functionary_roster = ScheduleRosterGroupingFactory.create(
            schedule=self.schedule,
            internal_group_position=kafeansvarlig,
            role=RoleOption.KAFEANSVARLIG,
            position_type=InternalGroupPositionMembershipType.FUNCTIONARY,
            default_availability=ShiftInterest.InterestTypes.AVAILABLE,
        )

        barista_users = UserFactory.create_batch(5)
        for user in barista_users:
            InternalGroupPositionMembershipFactory.create(
                user=user,
                type=InternalGroupPositionMembershipType.GANG_MEMBER,
                position=barista,
            )
        hangarond_barista_users = UserFactory.create_batch(8)
        for user in hangarond_barista_users:
            InternalGroupPositionMembershipFactory.create(
                user=user,
                type=InternalGroupPositionMembershipType.HANGAROUND,
                position=barista,
            )
        ka_users = UserFactory.create_batch(3)
        for user in ka_users:
            InternalGroupPositionMembershipFactory.create(
                user=user,
                type=InternalGroupPositionMembershipType.FUNCTIONARY,
                position=kafeansvarlig,
            )

    def test__hello_world__shit_runs(self):
        default_baristas = User.objects.filter(
            internal_group_position_history__position=self.barista_active_gang_member_roster.internal_group_position,
            internal_group_position_history__date_ended__isnull=True,
            internal_group_position_history__type=self.barista_active_gang_member_roster.position_type,
        )

        hangaround_baristas = User.objects.filter(
            internal_group_position_history__position=self.barista_hangaround_roster.internal_group_position,
            internal_group_position_history__date_ended__isnull=True,
            internal_group_position_history__type=self.barista_hangaround_roster.position_type,
        )

        active_ka_roster = User.objects.filter(
            internal_group_position_history__position=self.kafeansvarlige_functionary_roster.internal_group_position,
            internal_group_position_history__date_ended__isnull=True,
            internal_group_position_history__type=self.kafeansvarlige_functionary_roster.position_type,
        )

        self.assertEqual(default_baristas.count(), 5)
        self.assertEqual(hangaround_baristas.count(), 8)
        self.assertEqual(active_ka_roster.count(), 3)
