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


class TestGetAvailableInterviewLocations(TestCase):
    def setUp(self) -> None:
        # We set up 3 locations for interviews
        self.knaus = InterviewLocation.objects.create(name="Knaus")
        self.digitalt_rom_1 = InterviewLocation.objects.create(name="Digitalt rom 1")
        self.bodegaen = InterviewLocation.objects.create(name="Bodegaen")

        # Initialize the start of the interview period to 12:00
        now = timezone.datetime.now()
        self.start = timezone.datetime(
            now.year,
            now.month,
            now.day,
            hour=12,
            minute=0,
            second=0,
            tzinfo=timezone.timezone(timezone.timedelta()),
        )

        # End of interview period is next day at 23:00
        self.interview_period_end = self.start + timezone.timedelta(days=1, hours=14)

        self.schedule = InterviewScheduleTemplate.objects.create(
            interview_period_start=self.start,
            interview_period_end=self.interview_period_end,
        )

        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.start,
            datetime_to=self.start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        InterviewLocationAvailability.objects.create(
            interview_location=self.knaus,
            datetime_from=self.start + timezone.timedelta(days=1),
            datetime_to=self.start + timezone.timedelta(days=1, hours=8),
        )

        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.digitalt_rom_1,
            datetime_from=self.start,
            datetime_to=self.start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        InterviewLocationAvailability.objects.create(
            interview_location=self.digitalt_rom_1,
            datetime_from=self.start + timezone.timedelta(days=1),
            datetime_to=self.start + timezone.timedelta(days=1, hours=8),
        )
        # 12:00 to 20:00 day 1
        InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.start,
            datetime_to=self.start + timezone.timedelta(hours=8),
        )
        # 12:00 to 20:00 day 2
        self.bodegaen_day_2 = InterviewLocationAvailability.objects.create(
            interview_location=self.bodegaen,
            datetime_from=self.start + timezone.timedelta(days=1),
            datetime_to=self.start + timezone.timedelta(days=1, hours=8),
        )

    def test__3_locations_available_12_to_20_two_days_10_interviews_per_location__generates_60_interviews(
        self,
    ):
        # 3 locations. 8 hours. 2 interviews per hour. 5 interviews back to back in two sessions
        # 3 x 10 x 2 = 60
        generate_interviews_from_schedule(self.schedule)
        interviews = Interview.objects.all()
        self.assertEqual(interviews.count(), 60)

    def test__3_locations_first_dat_2_locations_next__generates_50_interviews(self):
        self.bodegaen_day_2.delete()
        generate_interviews_from_schedule(self.schedule)
        interviews = Interview.objects.all()
        self.assertEqual(interviews.count(), 50)

    def test__before_interview_time__returns_no_available_locations(self):
        now = timezone.datetime.now()
        locations = get_available_interview_locations(
            datetime_from=timezone.datetime(
                now.year, now.month, now.day, hour=9, minute=00
            ),
            datetime_to=timezone.datetime(
                now.year, now.month, now.day, hour=9, minute=45
            ),
        )
        self.assertEqual(locations.count(), 0)

    def test__start_of_interview_time__returns_3_available_locations(self):
        now = timezone.datetime.now()
        locations = get_available_interview_locations(
            datetime_from=timezone.datetime(
                now.year, now.month, now.day, hour=12, minute=00
            ),
            datetime_to=timezone.datetime(
                now.year, now.month, now.day, hour=12, minute=45
            ),
        )
        self.assertEqual(locations.count(), 3)

    def test__remove_1_location_availability__returns_2_available_locations(self):
        self.bodegaen_day_2.delete()
        now = timezone.datetime.now() + timezone.timedelta(days=1)
        locations = get_available_interview_locations(
            datetime_from=timezone.datetime(
                now.year, now.month, now.day, hour=12, minute=00
            ),
            datetime_to=timezone.datetime(
                now.year, now.month, now.day, hour=12, minute=45
            ),
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

        self.assertNotEqual(self.alex.first_name, "Alexander")
        self.assertNotEqual(self.alex.last_name, "Orvik")
        self.assertNotEqual(self.alex.phone, "12345678")
        self.assertNotEqual(self.alex.address, "Klostergata 35")

        self.assertNotEqual(self.sander.first_name, "Sander")
        self.assertNotEqual(self.sander.last_name, "Haga")
        self.assertNotEqual(self.sander.phone, "87654321")
        self.assertNotEqual(self.sander.address, "Klostergata 35")
