import pytz
from django.conf import settings
from django.test import TestCase

from admissions.tests.factories import AdmissionFactory, ApplicantFactory
from admissions.utils import (
    get_available_interview_locations,
    generate_interviews_from_schedule,
    obfuscate_admission,
)
from admissions.models import (
    Interview,
    InterviewLocation,
    InterviewScheduleTemplate,
    InterviewLocationAvailability,
)
from django.utils import timezone
from common.util import date_time_combiner
import datetime


class TestGetAvailableInterviewLocations(TestCase):
    def setUp(self) -> None:
        # We set up 3 locations for interviews
        self.knaus = InterviewLocation.objects.create(name="Knaus")
        self.digitalt_rom_1 = InterviewLocation.objects.create(name="Digitalt rom 1")
        self.bodegaen = InterviewLocation.objects.create(name="Bodegaen")

        # Initialize the start of the interview period to 12:00
        self.start = datetime.date.today()
        self.datetime_start = date_time_combiner(self.start, datetime.time(hour=12))

        # End of interview period is two days later giving us a three day interview period
        self.interview_period_end_date = self.start + timezone.timedelta(days=2)

        self.schedule = InterviewScheduleTemplate.objects.create(
            interview_period_start_date=self.start,
            interview_period_end_date=self.interview_period_end_date,
            default_interview_day_start=datetime.time(hour=12),
            default_interview_day_end=datetime.time(hour=20),
        )

        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.datetime_start,
            datetime_to=self.datetime_start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.datetime_start + timezone.timedelta(days=1),
            datetime_to=self.datetime_start + timezone.timedelta(days=1, hours=8),
        )
        # 12:00 to 20:00 day 3
        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.datetime_start + timezone.timedelta(days=2),
            datetime_to=self.datetime_start + timezone.timedelta(days=2, hours=8),
        )

        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.digitalt_rom_1,
            datetime_from=self.datetime_start,
            datetime_to=self.datetime_start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        InterviewLocationAvailability.objects.create(
            interview_location=self.digitalt_rom_1,
            datetime_from=self.datetime_start + timezone.timedelta(days=1),
            datetime_to=self.datetime_start + timezone.timedelta(days=1, hours=8),
        )
        # 12:00 to 20:00 day 3
        InterviewLocationAvailability.objects.create(
            interview_location=self.digitalt_rom_1,
            datetime_from=self.datetime_start + timezone.timedelta(days=2),
            datetime_to=self.datetime_start + timezone.timedelta(days=2, hours=8),
        )
        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.datetime_start,
            datetime_to=self.datetime_start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        self.bodegaen_day_2 = InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.datetime_start + timezone.timedelta(days=1),
            datetime_to=self.datetime_start + timezone.timedelta(days=1, hours=8),
        )
        # 12:00 to 20:00 day 3
        self.bodegaen_day_3 = InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.datetime_start + timezone.timedelta(days=2),
            datetime_to=self.datetime_start + timezone.timedelta(days=2, hours=8),
        )

    def test__3_locations_available_12_to_20_three_days_10_interviews_per_location__generates_60_interviews(
        self,
    ):
        # 3 locations. 3 days, 10 interviews per day
        # 3 x 3 x 10 = 60
        generate_interviews_from_schedule(self.schedule)
        interviews = Interview.objects.all()
        self.assertEqual(interviews.count(), 90)

    def test__3_locations_first_day_2_locations_next__generates_50_interviews(self):
        self.bodegaen_day_2.delete()
        generate_interviews_from_schedule(self.schedule)
        interviews = Interview.objects.all()
        self.assertEqual(interviews.count(), 80)

    def test__before_interview_time__returns_no_available_locations(self):
        now = timezone.datetime.now()
        locations = get_available_interview_locations(
            datetime_from=timezone.datetime(
                now.year,
                now.month,
                now.day,
                hour=9,
                minute=00,
                tzinfo=pytz.timezone(settings.TIME_ZONE),
            ),
            datetime_to=timezone.datetime(
                now.year,
                now.month,
                now.day,
                hour=9,
                minute=45,
                tzinfo=pytz.timezone(settings.TIME_ZONE),
            ),
        )
        self.assertEqual(locations.count(), 0)

    def test__start_of_interview_time__returns_3_available_locations(self):
        now = timezone.datetime.now()
        datetime_from = timezone.make_aware(
            timezone.datetime(now.year, now.month, now.day, hour=12, minute=00),
            timezone=pytz.timezone(settings.TIME_ZONE),
        )
        datetime_to = timezone.make_aware(
            timezone.datetime(now.year, now.month, now.day, hour=12, minute=45),
            timezone=pytz.timezone(settings.TIME_ZONE),
        )

        locations = get_available_interview_locations(
            datetime_from=datetime_from, datetime_to=datetime_to
        )
        self.assertEqual(locations.count(), 3)

    def test__remove_1_location_availability__returns_2_available_locations(self):
        self.bodegaen_day_2.delete()
        tomorrow = timezone.datetime.now() + timezone.timedelta(days=1)
        tomorrow_datetime_from = timezone.make_aware(
            timezone.datetime(
                tomorrow.year, tomorrow.month, tomorrow.day, hour=12, minute=00
            ),
            timezone=pytz.timezone(settings.TIME_ZONE),
        )
        tomorrow_datetime_to = timezone.make_aware(
            timezone.datetime(
                tomorrow.year,
                tomorrow.month,
                tomorrow.day,
                hour=12,
                minute=45,
            ),
            timezone=pytz.timezone(settings.TIME_ZONE),
        )
        locations = get_available_interview_locations(
            datetime_from=tomorrow_datetime_from, datetime_to=tomorrow_datetime_to
        )
        self.assertEqual(locations.count(), 2)


class TestObfuscateAdmission(TestCase):
    def setUp(self) -> None:
        self.admission = AdmissionFactory.create()
        self.alex = ApplicantFactory.create(
            first_name="Alexander",
            last_name="Orvik",
            phone="12345678",
            address="Klostergata 35",
            admission=self.admission,
        )
        self.sander = ApplicantFactory.create(
            first_name="Sander",
            last_name="Haga",
            phone="87654321",
            address="Klostergata 35",
            admission=self.admission,
        )

    def test__obfuscate_admission__changes__identifying_information(self):
        obfuscate_admission(self.admission)
        self.alex.refresh_from_db()
        self.sander.refresh_from_db()

        self.assertNotEqual(
            self.alex.first_name + self.alex.last_name, "AlexanderOrvik"
        )
        self.assertNotEqual(self.alex.phone, "12345678")
        self.assertNotEqual(self.alex.address, "Klostergata 35")

        self.assertNotEqual(
            self.sander.first_name + self.sander.last_name, "SanderHaga"
        )
        self.assertNotEqual(self.sander.phone, "87654321")
        self.assertNotEqual(self.sander.address, "Klostergata 35")


class TestInterviewGenerationEdgeCases(TestCase):
    def setUp(self) -> None:
        # We set up 3 locations for interviews
        self.knaus = InterviewLocation.objects.create(name="Knaus")
        self.bodegaen = InterviewLocation.objects.create(name="Bodegaen")

        # Initialize the start of the interview period to 12:00
        self.start = timezone.datetime.today()
        self.datetime_start = date_time_combiner(self.start, datetime.time(hour=12))

        # End of interview period is two days later giving us a three day interview period
        self.interview_period_end_date = self.start + timezone.timedelta(days=2)

        self.schedule = InterviewScheduleTemplate.objects.create(
            interview_period_start_date=self.start,
            interview_period_end_date=self.interview_period_end_date,
            default_interview_day_start=datetime.time(hour=12),
            default_interview_day_end=datetime.time(hour=20),
        )

        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.datetime_start,
            datetime_to=self.datetime_start + timezone.timedelta(hours=8),
        )

        InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.datetime_start + timezone.timedelta(hours=4),
            datetime_to=self.datetime_start + timezone.timedelta(hours=8),
        )

    def test__interview_location_not_available_for_first_half__does_not_create_early_interview(
        self,
    ):
        generate_interviews_from_schedule(self.schedule)
        self.assertEqual(Interview.objects.all().count(), 14)


class TestCloseAdmission(TestCase):
    def setUp(self) -> None:
        pass

    def test__interview_location_not_available_for_first_half__does_not_create_early_interview(
        self,
    ):
        pass
